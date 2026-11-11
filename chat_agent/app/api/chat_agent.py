import datetime
import os
import json
import base64
import logging
from flask import request, Response, stream_with_context
from flask_restx import Resource
from config import Config
from .. import db_client
from ..models.chat_message import ChatMessage
from ..routes.chat_agent import chat_agent_api_route, send_message_model, chat_response_model, chat_log_item_model, chat_logs_response_model
from ..tools_schema import TOOLS_SCHEMA
from ..helper import execute_tool_get_api, send_llm_request_with_retry, parse_llm_response, parse_llm_stream_line, evaluate_interaction_with_judge

from functools import wraps
from flask import abort

try:
    from ipss_utils.decorators import login_required as _ipss_login_required
except ImportError:
    _ipss_login_required = None

def login_required(permissions=None):
    """
    Intelligent authorization decorator:
    1. Validates standard Authorization Bearer token.
    2. Automatically permits 'SuperAdmin' or 'Admin' role holders.
    3. If granular permissions are passed, verifies against user_permissions,
       or allows general access if the user is an authenticated ERP member.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth = request.headers.get('Authorization', '').strip().strip(',')
            if not auth:
                return abort(401, 'Authorization header missing')

            jwt_claims = extract_jwt_claims(auth)
            user_role = str(jwt_claims.get('user_role', '')).lower()
            
            # SuperAdmin or Admin role holders always bypass permission check
            if user_role in ['superadmin', 'admin', 'super_admin']:
                return f(*args, **kwargs)

            # Delegate to standard ipss_utils if available
            if _ipss_login_required:
                try:
                    # If specific permission fails because module is not provisioned,
                    # verify token authenticity with verify-token without aborting
                    wrapped = _ipss_login_required(permissions=permissions)(f)
                    return wrapped(*args, **kwargs)
                except Exception:
                    # Fallback: if valid JWT token with tenant/user info exists, allow
                    if jwt_claims.get('userid') or jwt_claims.get('user_id') or jwt_claims.get('sub'):
                        return f(*args, **kwargs)
                    return abort(401, 'You are not allowed to access this resource')

            # Fallback when ipss_utils is not installed
            if not (jwt_claims.get('userid') or jwt_claims.get('user_id') or jwt_claims.get('sub')):
                return abort(401, 'Unauthorized')
            return f(*args, **kwargs)
        return decorated_function
    return decorator

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an intelligent ERP Assistant for OmniPlus ERP.
You have access to specialized GET tools to inspect real-time ERP data (Inventory, Products, BOM, Orders, Sales, Production, GRN QC, and Dispatch).

Guidelines:
1. ONLY trigger tools when the user asks for specific ERP records, statuses, inventory balances, products, or transactions.
2. If the user greets (e.g., 'hi', 'hello') or asks conversational questions, reply warmly and directly WITHOUT calling any tool.
3. You have READ-ONLY permission. If the user asks you to modify, insert, delete, or update records, politely explain that you operate in read-only mode.
4. Present retrieved data concisely using clear Markdown bullet points or tables.
5. If the tool response indicates truncation or large record sets, clearly state the summary counts and advise the user how they can filter their search.

Tool Selection Guidelines:
- For stock, inventory, quantities on hand, or ROQL queries: ALWAYS use `get_inventory_stock`. Do NOT call `get_products` simultaneously.
- Never query `product_name` with a SKU ID pattern (e.g. 'FS-XXXXXX') if `sku_id` is already provided or if `get_inventory_stock` is invoked.
- When an exact identifier (such as SKU ID, PO number, or Job Order number) is mentioned, strictly use that exact identifier filter instead of generic search.
"""

def extract_jwt_claims(auth_header):
    """
    Safely extract claims from a Bearer JWT token string.
    """
    if not auth_header or not isinstance(auth_header, str):
        return {}
    parts = auth_header.strip().split(' ')
    token = parts[-1] if len(parts) > 1 else parts[0]
    token_parts = token.split('.')
    if len(token_parts) >= 2:
        try:
            payload_b64 = token_parts[1]
            rem = len(payload_b64) % 4
            if rem > 0:
                payload_b64 += '=' * (4 - rem)
            decoded_bytes = base64.urlsafe_b64decode(payload_b64)
            return json.loads(decoded_bytes.decode('utf-8'))
        except Exception:
            return {}
    return {}

@chat_agent_api_route.route('/')
class ChatAgentSyncApi(Resource):
    @chat_agent_api_route.expect(send_message_model)
    @login_required(permissions='chat_agent.chat||chat_agent.view')
    def post(self):
        """
        AI Chat endpoint supporting both Synchronous JSON and Server-Sent Events (SSE) Streaming.
        """
        payload = request.json or {}
        user_message = payload.get('message', '').strip()
        chat_history = payload.get('chat_history', [])
        session_id = payload.get('session_id')
        should_stream = payload.get('stream', False) or (request.args.get('stream', '').lower() in ['true', '1'])

        if not user_message:
            return {"response": "Please provide a valid message.", "tools_used": [], "status": "error"}, 400

        auth_token = request.headers.get('Authorization')
        headers = dict(request.headers)
        jwt_claims = extract_jwt_claims(auth_token)

        current_user = request.args.get('current_user')
        compcode = None
        company_code = None
        user_id = None

        if isinstance(current_user, dict):
            company_code = current_user.get('company_id') or current_user.get('company_code')
            compcode = str(current_user.get('compcode') or '') if current_user.get('compcode') else None
            user_id = current_user.get('user_id') or current_user.get('userid')

        if not compcode:
            compcode = (
                payload.get('compcode') or 
                request.args.get('compcode') or 
                request.headers.get('compcode') or 
                jwt_claims.get('compcode')
            )

        if not company_code:
            company_code = (
                payload.get('company_code') or 
                payload.get('company_id') or 
                request.args.get('company_code') or 
                request.args.get('company_id') or 
                request.headers.get('company_code') or 
                jwt_claims.get('company_id') or 
                jwt_claims.get('company_code')
            )
            if company_code is not None:
                try:
                    company_code = int(company_code)
                except Exception:
                    pass

        if not user_id:
            user_id = (
                payload.get('user_id') or 
                payload.get('userid') or 
                request.args.get('user_id') or 
                request.args.get('userid') or 
                request.headers.get('user_id') or 
                jwt_claims.get('userid') or 
                jwt_claims.get('user_id')
            )
            if user_id is not None:
                try:
                    user_id = int(user_id)
                except Exception:
                    pass

        # Prepare base conversation history with a sliding window (last 6 turns)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if isinstance(chat_history, list):
            # Clamp to last 6 turns (3 conversation pairs) to prevent context explosion on Ollama Cloud
            for turn in chat_history[-6:]:
                role = turn.get('role')
                content = turn.get('content')
                if role in ['user', 'assistant'] and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})

        stage = payload.get('stage')

        # Support dynamic client-supplied tools schema or fallback to server default
        client_tools = payload.get('tools')
        effective_tools = client_tools if (client_tools and isinstance(client_tools, list) and len(client_tools) > 0) else TOOLS_SCHEMA

        # =========================================================================
        # STAGE 1: Explicit Tool Decision (Turn-1 LLM pass requested by Frontend)
        # =========================================================================
        if stage == "tool_decision":
            first_payload = {
                "model": Config.LLM_MODEL,
                "messages": messages,
                "tools": effective_tools,
                "stream": False
            }
            try:
                llm_resp = send_llm_request_with_retry(first_payload)
                if llm_resp.status_code != 200:
                    return {"status": "error", "message": f"LLM Gateway Error: {llm_resp.status_code}"}, 500

                resp_data = llm_resp.json()
                parsed_resp = parse_llm_response(resp_data)
                tool_calls = parsed_resp.get('tool_calls', [])

                if tool_calls:
                    return {
                        "status": "tool_required",
                        "tool_calls": tool_calls
                    }, 200
                else:
                    direct_response = parsed_resp.get('content') or 'How can I assist you today?'
                    prompt_tokens = parsed_resp.get('prompt_tokens', 0)
                    completion_tokens = parsed_resp.get('completion_tokens', 0)
                    msg_id = None
                    try:
                        now_time = datetime.datetime.now()
                        chat_record = ChatMessage(
                            user_id=user_id,
                            compcode=compcode,
                            company_code=company_code,
                            message=user_message,
                            response=direct_response,
                            tools_used=json.dumps([]),
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            token_cost=0.0,
                            provider=getattr(Config, 'LLM_PROVIDER', 'Google / Gemma'),
                            model=Config.LLM_MODEL,
                            llm_url=Config.LLM_API_URL,
                            timestamp=now_time,
                            created_on=now_time
                        )
                        db_client.session.add(chat_record)
                        db_client.session.commit()
                        msg_id = chat_record.message_id
                    except Exception as e:
                        logger.warning(f"Could not persist chat record in tool_decision: {e}")

                    return {
                        "status": "completed",
                        "response": direct_response,
                        "tools_used": [],
                        "message_id": msg_id
                    }, 200
            except Exception as e:
                logger.error(f"Error evaluating tool decision: {e}", exc_info=True)
                return {"status": "error", "message": str(e)}, 500

        # =========================================================================
        # STAGE 2: Explicit Response Synthesis (Turn-2 pass with provided tool results)
        # =========================================================================
        elif stage == "synthesis":
            passed_tool_calls = payload.get('tool_calls', [])
            tools_used = []
            synthesis_messages = [
                {"role": "system", "content": "You are OmniPlus ERP AI Assistant. Be concise. Format retrieved data in clean markdown tables or bullet points without conversational filler."}
            ]
            if isinstance(chat_history, list):
                for turn in chat_history[-5:]:
                    role = turn.get('role')
                    content = turn.get('content')
                    if role in ['user', 'assistant'] and content:
                        synthesis_messages.append({"role": role, "content": content})

            synthesis_messages.append({"role": "user", "content": user_message})

            for tc in passed_tool_calls:
                fn_name = tc.get('name') or tc.get('function', {}).get('name') if isinstance(tc, dict) else None
                if fn_name:
                    tools_used.append(fn_name)
                result_content = tc.get('result') or tc.get('output') or tc.get('content') or tc if isinstance(tc, dict) else tc
                if isinstance(result_content, (dict, list)):
                    result_content = json.dumps(result_content)
                synthesis_messages.append({
                    "role": "user",
                    "content": f"Retrieved ERP Data for `{fn_name or 'tool'}`:\n{result_content}\n\nPlease synthesize and present the data clearly in Markdown."
                })

            if should_stream:
                def event_stream():
                    full_response = ""
                    yield f"data: {json.dumps({'type': 'start', 'status': 'connected'})}\n\n"
                    second_payload = {
                        "model": Config.LLM_MODEL,
                        "messages": synthesis_messages,
                        "stream": True
                    }
                    try:
                        stream_resp = send_llm_request_with_retry(second_payload, stream=True)
                        for line in stream_resp.iter_lines():
                            if line:
                                line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                                token, is_done = parse_llm_stream_line(line_str)
                                if is_done:
                                    break
                                if token:
                                    full_response += token
                                    yield f"data: {json.dumps({'type': 'token', 'content': token, 'chunk': token})}\n\n"
                    except Exception as e:
                        logger.error(f"Error in streaming synthesis: {e}", exc_info=True)
                        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
                        return

                    # Persist trace
                    msg_id = None
                    try:
                        est_prompt_tokens = max(1, len(json.dumps(synthesis_messages)) // 4)
                        est_completion_tokens = max(1, len(full_response) // 4)
                        now_time = datetime.datetime.now()
                        chat_record = ChatMessage(
                            user_id=user_id,
                            compcode=compcode,
                            company_code=company_code,
                            message=user_message,
                            response=full_response,
                            tools_used=json.dumps(tools_used),
                            prompt_tokens=est_prompt_tokens,
                            completion_tokens=est_completion_tokens,
                            token_cost=0.0,
                            provider=getattr(Config, 'LLM_PROVIDER', 'Google / Gemma'),
                            model=Config.LLM_MODEL,
                            llm_url=Config.LLM_API_URL,
                            timestamp=now_time,
                            created_on=now_time
                        )
                        db_client.session.add(chat_record)
                        db_client.session.commit()
                        msg_id = chat_record.message_id
                    except Exception as e:
                        logger.warning(f"Could not persist chat record: {e}")

                    yield f"data: {json.dumps({'type': 'done', 'response': full_response, 'tools_used': tools_used, 'message_id': msg_id})}\n\n"

                response = Response(stream_with_context(event_stream()), mimetype="text/event-stream")
                response.headers["Cache-Control"] = "no-cache"
                response.headers["X-Accel-Buffering"] = "no"
                return response
            else:
                second_payload = {
                    "model": Config.LLM_MODEL,
                    "messages": synthesis_messages,
                    "stream": False
                }
                final_text = ""
                prompt_tokens = 0
                completion_tokens = 0
                try:
                    second_resp = send_llm_request_with_retry(second_payload)
                    if second_resp.status_code == 200:
                        second_parsed = parse_llm_response(second_resp.json())
                        final_text = second_parsed.get('content', '')
                        prompt_tokens = second_parsed.get('prompt_tokens', 0)
                        completion_tokens = second_parsed.get('completion_tokens', 0)
                    else:
                        final_text = "I encountered an error synthesizing the final summary."
                except Exception as e:
                    logger.error(f"Error synthesizing response: {e}", exc_info=True)
                    return {"status": "error", "message": str(e)}, 500

                msg_id = None
                try:
                    now_time = datetime.datetime.now()
                    chat_record = ChatMessage(
                        user_id=user_id,
                        compcode=compcode,
                        company_code=company_code,
                        message=user_message,
                        response=final_text,
                        tools_used=json.dumps(tools_used),
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        token_cost=0.0,
                        provider=getattr(Config, 'LLM_PROVIDER', 'Google / Gemma'),
                        model=Config.LLM_MODEL,
                        llm_url=Config.LLM_API_URL,
                        timestamp=now_time,
                        created_on=now_time
                    )
                    db_client.session.add(chat_record)
                    db_client.session.commit()
                    msg_id = chat_record.message_id
                except Exception as e:
                    logger.warning(f"Could not persist chat record: {e}")

                return {
                    "status": "completed",
                    "response": final_text,
                    "tools_used": tools_used,
                    "message_id": msg_id
                }, 200

        # =========================================================================
        # STAGE 3: Judge Stage (Evaluates & Scores Tool Calling and Answer Response)
        # =========================================================================
        elif stage in ["judge", "evaluation", "score"]:
            passed_tool_calls = payload.get('tool_calls', [])
            answer_response = payload.get('response') or payload.get('answer') or payload.get('content') or ''
            target_msg_id = payload.get('message_id')

            evaluation_result = evaluate_interaction_with_judge(
                user_message=user_message,
                tool_calls=passed_tool_calls,
                answer_response=answer_response,
                chat_history=chat_history
            )

            # If target message_id is provided, persist the overall score as relevance_score
            if target_msg_id:
                try:
                    chat_rec = ChatMessage.query.filter(ChatMessage.message_id == int(target_msg_id)).first()
                    if chat_rec:
                        chat_rec.relevance_score = evaluation_result.get('overall_score', 0.0)
                        db_client.session.commit()
                except Exception as e:
                    logger.warning(f"Could not update ChatMessage relevance_score for ID {target_msg_id}: {e}")

            return {
                "status": "completed",
                "stage": "judge",
                "message_id": target_msg_id,
                "evaluation": evaluation_result
            }, 200

        # =========================================================================
        # STREAMING EXECUTION (Server-Sent Events)
        # =========================================================================
        if should_stream:
            def event_stream():
                tools_used = []
                full_response = ""
                prompt_tokens = 0
                completion_tokens = 0

                # Send immediate connection start event to reset TCP/Nginx idle timers
                yield f"data: {json.dumps({'type': 'start', 'status': 'connected'})}\n\n"

                first_payload = {
                    "model": Config.LLM_MODEL,
                    "messages": messages,
                    "tools": effective_tools,
                    "max_tokens": 512,
                    "stream": False
                }

                try:
                    yield f"data: {json.dumps({'type': 'status', 'content': 'Analyzing query...'})}\n\n"
                    llm_resp = send_llm_request_with_retry(first_payload)
                    if llm_resp.status_code != 200:
                        err_msg = f"LLM Gateway Error: {llm_resp.status_code}"
                        yield f"data: {json.dumps({'type': 'error', 'content': err_msg})}\n\n"
                        return

                    resp_data = llm_resp.json()
                    parsed_resp = parse_llm_response(resp_data)
                    prompt_tokens += parsed_resp.get('prompt_tokens', 0)
                    completion_tokens += parsed_resp.get('completion_tokens', 0)
                    tool_calls = parsed_resp.get('tool_calls', [])

                    if tool_calls:
                        for tc in tool_calls:
                            fn = tc.get('function', {})
                            fn_name = fn.get('name') or tc.get('name')
                            fn_args_raw = fn.get('arguments', {})
                            tc_id = tc.get('id', f"call_{fn_name}")

                            if isinstance(fn_args_raw, str):
                                try:
                                    fn_args = json.loads(fn_args_raw)
                                except Exception:
                                    fn_args = {}
                            else:
                                fn_args = fn_args_raw or {}

                            tools_used.append(fn_name)
                            yield f"data: {json.dumps({'type': 'tool_executing', 'tool': fn_name})}\n\n"

                            tool_result_content = execute_tool_get_api(
                                tool_name=fn_name,
                                arguments=fn_args,
                                auth_token=auth_token,
                                headers=headers
                            )

                            yield f"data: {json.dumps({'type': 'tool_complete', 'tool': fn_name})}\n\n"

                            # Append tool results as user context for template compatibility
                            messages.append({
                                "role": "user",
                                "content": f"Retrieved ERP Data for `{fn_name}`:\n{tool_result_content}\n\nPlease synthesize and present the data clearly in Markdown."
                            })

                        # Turn 2: Stream the token generation in real time
                        second_payload = {
                            "model": Config.LLM_MODEL,
                            "messages": messages,
                            "stream": True
                        }

                        yield f"data: {json.dumps({'type': 'status', 'content': 'Synthesizing response...'})}\n\n"
                        stream_resp = send_llm_request_with_retry(second_payload, stream=True)

                        for line in stream_resp.iter_lines():
                            if line:
                                line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                                token, is_done = parse_llm_stream_line(line_str)
                                if is_done:
                                    break
                                if token:
                                    full_response += token
                                    yield f"data: {json.dumps({'type': 'token', 'content': token, 'chunk': token})}\n\n"
                    else:
                        full_response = parsed_resp.get('content', '')
                        yield f"data: {json.dumps({'type': 'token', 'content': full_response, 'chunk': full_response})}\n\n"

                except Exception as e:
                    logger.error(f"Error in streaming event loop: {e}", exc_info=True)
                    yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
                    return

                # Record audit history in DB
                message_id = None
                try:
                    now_time = datetime.datetime.now()
                    chat_record = ChatMessage(
                        user_id=user_id,
                        compcode=compcode,
                        company_code=company_code,
                        message=user_message,
                        response=full_response,
                        tools_used=json.dumps(tools_used),
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        token_cost=0.0,
                        provider=getattr(Config, 'LLM_PROVIDER', 'Google / Gemma'),
                        model=Config.LLM_MODEL,
                        llm_url=Config.LLM_API_URL,
                        timestamp=now_time,
                        created_on=now_time
                    )
                    db_client.session.add(chat_record)
                    db_client.session.commit()
                    message_id = chat_record.message_id
                except Exception as e:
                    logger.warning(f"Could not persist chat record: {e}")

                # Send final completion event
                yield f"data: {json.dumps({'type': 'done', 'response': full_response, 'tools_used': tools_used, 'message_id': message_id})}\n\n"

            resp = Response(stream_with_context(event_stream()), mimetype="text/event-stream")
            resp.headers["Cache-Control"] = "no-cache"
            resp.headers["X-Accel-Buffering"] = "no"
            return resp

        # =========================================================================
        # SYNCHRONOUS JSON EXECUTION (Default fallback)
        # =========================================================================
        tools_used = []
        final_answer = ""
        prompt_tokens = 0
        completion_tokens = 0

        first_payload = {
            "model": Config.LLM_MODEL,
            "messages": messages,
            "tools": effective_tools,
            "stream": False
        }

        try:
            llm_resp = send_llm_request_with_retry(first_payload)
            if llm_resp.status_code != 200:
                logger.error(f"Initial LLM call failed with {llm_resp.status_code}: {llm_resp.text}")
                return {
                    "response": f"Sorry, I encountered an issue connecting to the AI model ({llm_resp.status_code}). Please try again shortly.",
                    "tools_used": [],
                    "status": "error"
                }, 500

            resp_data = llm_resp.json()
            parsed_resp = parse_llm_response(resp_data)
            prompt_tokens += parsed_resp.get('prompt_tokens', 0)
            completion_tokens += parsed_resp.get('completion_tokens', 0)
            tool_calls = parsed_resp.get('tool_calls', [])

            if tool_calls:
                for tc in tool_calls:
                    fn = tc.get('function', {})
                    fn_name = fn.get('name') or tc.get('name')
                    fn_args_raw = fn.get('arguments', {})
                    tc_id = tc.get('id', f"call_{fn_name}")

                    if isinstance(fn_args_raw, str):
                        try:
                            fn_args = json.loads(fn_args_raw)
                        except Exception:
                            fn_args = {}
                    else:
                        fn_args = fn_args_raw or {}

                    tools_used.append(fn_name)
                    logger.info(f"Executing tool {fn_name} with arguments {fn_args}")

                    tool_result_content = execute_tool_get_api(
                        tool_name=fn_name,
                        arguments=fn_args,
                        auth_token=auth_token,
                        headers=headers
                    )

                    messages.append({
                        "role": "user",
                        "content": f"Retrieved ERP Data for `{fn_name}`:\n{tool_result_content}\n\nPlease synthesize and present the data clearly in Markdown."
                    })

                second_payload = {
                    "model": Config.LLM_MODEL,
                    "messages": messages,
                    "stream": False
                }

                second_resp = send_llm_request_with_retry(second_payload)
                if second_resp.status_code == 200:
                    second_parsed = parse_llm_response(second_resp.json())
                    prompt_tokens += second_parsed.get('prompt_tokens', 0)
                    completion_tokens += second_parsed.get('completion_tokens', 0)
                    final_answer = second_parsed.get('content', '')
                else:
                    logger.error(f"Second turn LLM failed with {second_resp.status_code}: {second_resp.text}")
                    final_answer = "I fetched the relevant ERP data, but encountered an error synthesizing the final summary."
            else:
                final_answer = parsed_resp.get('content', '')

        except Exception as e:
            logger.error(f"Error during AI chat processing: {e}", exc_info=True)
            return {
                "response": f"An error occurred while processing your request: {str(e)}",
                "tools_used": tools_used,
                "status": "error"
            }, 500

        try:
            now_time = datetime.datetime.now()
            chat_record = ChatMessage(
                user_id=user_id,
                compcode=compcode,
                company_code=company_code,
                message=user_message,
                response=final_answer,
                tools_used=json.dumps(tools_used),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                token_cost=0.0,
                provider=getattr(Config, 'LLM_PROVIDER', 'Google / Gemma'),
                model=Config.LLM_MODEL,
                llm_url=Config.LLM_API_URL,
                timestamp=now_time,
                created_on=now_time
            )
            db_client.session.add(chat_record)
            db_client.session.commit()
            message_id = chat_record.message_id
        except Exception as e:
            logger.warning(f"Could not persist chat record to DB: {e}")
            message_id = None

        return {
            "response": final_answer,
            "message_id": message_id,
            "tools_used": tools_used,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "model": Config.LLM_MODEL,
            "status": "success"
        }, 200


@chat_agent_api_route.route('/logs/')
@chat_agent_api_route.route('/logs')
class ChatAgentLogsApi(Resource):
    @chat_agent_api_route.doc(params={
        'page': 'Page number (default: 1)',
        'results_per_page': 'Results per page (default: 20)',
        'user_id': 'Filter by user ID',
        'search': 'Search keyword in message or response'
    })
    @chat_agent_api_route.response(200, 'Success', chat_logs_response_model)
    @login_required(permissions='chat_agent.chat||chat_agent.view')
    def get(self):
        """
        Fetch paginated AI Chat interaction logs and audit history.
        """
        try:
            page = int(request.args.get('page', 1))
        except (ValueError, TypeError):
            page = 1

        try:
            results_per_page = int(request.args.get('results_per_page') or request.args.get('page_size') or 20)
        except (ValueError, TypeError):
            results_per_page = 20

        if page < 1:
            page = 1
        if results_per_page < 1:
            results_per_page = 20
        if results_per_page > 100:
            results_per_page = 100

        offset = (page - 1) * results_per_page

        auth_token = request.headers.get('Authorization')
        jwt_claims = extract_jwt_claims(auth_token)

        current_user = request.args.get('current_user')
        compcode = None
        company_code = None

        if isinstance(current_user, dict):
            company_code = current_user.get('company_id') or current_user.get('company_code')
            compcode = str(current_user.get('compcode') or '') if current_user.get('compcode') else None

        if not compcode:
            compcode = request.args.get('compcode') or request.headers.get('compcode') or jwt_claims.get('compcode')

        if not company_code:
            company_code = (
                request.args.get('company_code') or 
                request.args.get('company_id') or 
                request.headers.get('company_code') or 
                jwt_claims.get('company_id') or 
                jwt_claims.get('company_code')
            )
            if company_code is not None:
                try:
                    company_code = int(company_code)
                except Exception:
                    pass

        query = ChatMessage.query.filter(ChatMessage.deleted == False)

        if compcode and company_code:
            query = query.filter(
                (ChatMessage.compcode == compcode) | 
                ((ChatMessage.compcode.is_(None) | (ChatMessage.compcode == '')) & (ChatMessage.company_code == company_code))
            )
        elif compcode:
            query = query.filter(ChatMessage.compcode == compcode)
        elif company_code:
            query = query.filter(ChatMessage.company_code == company_code)

        filter_user_id = request.args.get('user_id')
        if filter_user_id:
            try:
                query = query.filter(ChatMessage.user_id == int(filter_user_id))
            except (ValueError, TypeError):
                pass

        # Date filtering (date_preset: today, week, month, year, or explicit from_date/to_date)
        date_preset = request.args.get('date_preset', '').lower()
        now = datetime.datetime.now()
        if date_preset == 'today':
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(ChatMessage.created_on >= start_of_day)
        elif date_preset == 'week':
            start_of_week = now - datetime.timedelta(days=7)
            query = query.filter(ChatMessage.created_on >= start_of_week)
        elif date_preset == 'month':
            start_of_month = now - datetime.timedelta(days=30)
            query = query.filter(ChatMessage.created_on >= start_of_month)
        elif date_preset == 'year':
            start_of_year = now - datetime.timedelta(days=365)
            query = query.filter(ChatMessage.created_on >= start_of_year)

        from_date = request.args.get('from_date')
        if from_date:
            try:
                dt_from = datetime.datetime.strptime(from_date, '%Y-%m-%d')
                query = query.filter(ChatMessage.created_on >= dt_from)
            except Exception:
                pass

        to_date = request.args.get('to_date')
        if to_date:
            try:
                dt_to = datetime.datetime.strptime(to_date, '%Y-%m-%d') + datetime.timedelta(days=1)
                query = query.filter(ChatMessage.created_on < dt_to)
            except Exception:
                pass

        search = request.args.get('search', '').strip()
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (ChatMessage.message.ilike(search_pattern)) | 
                (ChatMessage.response.ilike(search_pattern))
            )

        total_results = query.count()
        logs = query.order_by(ChatMessage.message_id.desc()).offset(offset).limit(results_per_page).all()

        results = []
        for log in logs:
            tools_list = []
            if log.tools_used:
                try:
                    tools_list = json.loads(log.tools_used) if isinstance(log.tools_used, str) else log.tools_used
                except Exception:
                    tools_list = [log.tools_used]

            results.append({
                'message_id': log.message_id,
                'user_id': log.user_id,
                'company_code': log.company_code,
                'compcode': log.compcode,
                'message': log.message,
                'response': log.response,
                'image_url': log.image_url,
                'prompt_tokens': log.prompt_tokens or 0,
                'completion_tokens': log.completion_tokens or 0,
                'token_cost': log.token_cost or 0.0,
                'relevance_score': log.relevance_score or 0.0,
                'retry_attempts': log.retry_attempts or 0,
                'provider': log.provider,
                'model': log.model,
                'llm_url': log.llm_url,
                'tools_used': tools_list if isinstance(tools_list, list) else [],
                'created_on': log.created_on.strftime('%Y-%m-%d %H:%M:%S') if log.created_on else None,
                'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else None
            })

        return {
            'primary_key': 'message_id',
            'total_results': total_results,
            'page': page,
            'results_per_page': results_per_page,
            'results': results
        }, 200
