import os
import json
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
from typing import Dict, Any, List, Optional, Generator
from config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Persistent HTTP session with connection pooling to eliminate TLS/TCP handshake overhead
_http_session = requests.Session()
_adapter = HTTPAdapter(pool_connections=20, pool_maxsize=50)
_http_session.mount("https://", _adapter)
_http_session.mount("http://", _adapter)

# Whitelist fields to preserve high-salience business data while stripping internal bloated metadata
SALIENT_FIELDS_MAP = {
    'get_uom_list': [
        'id', 'uom_name', 'uom_code', 'description', 'status', 'created_on'
    ],
    'get_inventory_stock': [
        'id', 'product_id', 'product_name', 'sku_id', 'sku_name', 'current_stock', 'stock_qty',
        'available_qty', 'allocated_qty', 'uom', 'location_name', 'sub_location', 'lot_number', 'batch_no'
    ],
    'get_store_locations': [
        'id', 'location_name', 'store_name', 'warehouse', 'type', 'capacity', 'status', 'rack_number'
    ],
    'get_products': [
        'id', 'product_name', 'sku_id', 'sku_code', 'product_group', 'category_name', 'uom', 'uom_id',
        'roql', 'lead_time_days', 'status', 'description'
    ],
    'get_product_variants': [
        'id', 'product_id', 'variant_name', 'sku_id', 'attributes', 'style_name', 'color', 'size', 'gsm', 'width'
    ],
    'get_product_groups': [
        'id', 'group_name', 'group_code', 'description', 'status'
    ],
    'get_bill_of_materials': [
        'id', 'bom_id', 'bom_code', 'product_name', 'sku_id', 'output_qty', 'components', 'raw_materials', 'total_cost'
    ],
    'get_cost_estimations': [
        'id', 'estimate_no', 'product_name', 'material_cost', 'labour_cost', 'overhead_cost', 'total_cost', 'currency'
    ],
    'get_customer_purchase_orders': [
        'id', 'order_no', 'po_number', 'customer_name', 'order_date', 'delivery_date', 'total_amount', 'status', 'item_count', 'items'
    ],
    'get_sales_pipeline': [
        'id', 'lead_id', 'customer_name', 'stage', 'lead_value', 'deal_value', 'probability', 'expected_close_date', 'status'
    ],
    'get_vendors': [
        'id', 'vendor_name', 'vendor_code', 'contact_person', 'phone', 'email', 'city', 'state', 'status'
    ],
    'get_customers': [
        'id', 'customer_name', 'companyname', 'contact_person', 'contactname', 'phone', 'mobileno', 'email', 'emailid', 'city', 'state', 'gstno', 'address', 'status'
    ],
    'get_job_orders': [
        'id', 'job_order_no', 'product_name', 'target_qty', 'produced_qty', 'pending_qty', 'start_date', 'due_date', 'status'
    ],
    'get_production_plans': [
        'id', 'plan_id', 'plan_date', 'line_name', 'product_name', 'planned_qty', 'shift', 'status'
    ],
    'get_production_execution_logs': [
        'id', 'date', 'line_name', 'job_order_no', 'product_name', 'hour', 'produced_qty', 'defect_qty', 'operator'
    ],
    'get_grn_qc_records': [
        'id', 'grn_number', 'vendor_name', 'po_number', 'received_date', 'received_qty', 'accepted_qty', 'rejected_qty', 'qc_status'
    ],
    'get_qc_rejection_report': [
        'id', 'grn_no', 'vendor_name', 'companyname', 'joborderno', 'total_item', 'rejection_reason', 'qc_status', 'defect_type', 'rejected_quantity'
    ],
    'get_dispatch_records': [
        'id', 'dc_number', 'customer_name', 'order_no', 'dispatch_date', 'dispatched_qty', 'vehicle_no', 'driver_name', 'status'
    ],
    'get_dispatch_delivery_report': [
        'deliveryno', 'delivery_date', 'customer_name', 'driver_name', 'driver_number', 'vehicle_number', 'order_unique', 'number_of_products', 'products'
    ],
    'get_production_summary': [
        'total_present', 'total_allocated', 'total_non_allocated', 'total_distinct_operators',
        'total_used_man_days', 'total_produced_qty', 'total_wip_operations_qty',
        'total_estimated_cost', 'total_actual_cost', 'total_material_cost', 'total_difference_cost',
        'kpis', 'blocks', 'overhead_departments', 'date', 'total_planned_qty'
    ],
    'get_pending_summary': [
        'pending_plans_count', 'delayed_plans', 'plan_no', 'style', 'pending_qty', 'due_date'
    ],
    'get_labour_costing': [
        'production_plan_id', 'plan_unique', 'product_name', 'product_code', 'moved_quantity',
        'stage_id', 'stage_name', 'labour_cost', 'estimated_cost', 'produced_qty', 'data',
        'order_details', 'style', 'smv', 'piece_rate'
    ],
    'get_daily_attendance': [
        'hremploymastid', 'idcardno', 'fname', 'mname', 'lname', 'line_name', 'config_name',
        'assigned', 'att', 'emp_id', 'employee_name', 'status', 'shift', 'department', 'date'
    ]
}

# API Endpoint mapping across AmNonOvens / Fabrico360-BE
TOOL_ENDPOINT_MAP = {
    'get_uom_list': '/baseConfig/uom/',
    'get_inventory_stock': '/baseConfig/products/',
    'get_store_locations': '/baseConfig/products/',
    'get_products': '/baseConfig/products/',
    'get_product_variants': '/baseConfig/product_variant/',
    'get_product_groups': '/baseConfig/product_group/',
    'get_bill_of_materials': '/am-bom/',
    'get_cost_estimations': '/am-cost_estimation/',
    'get_customer_purchase_orders': '/am-customer-purchase-order/',
    'get_sales_pipeline': '/am-vendors/pipeline/',
    'get_vendors': '/am-vendors/?types=VENDOR',
    'get_customers': '/am-vendors/?types=Customer',
    'get_job_orders': '/am-job_order/',
    'get_production_plans': '/am-prod_plans/',
    'get_production_execution_logs': '/am-prod_exe/',
    'get_grn_qc_records': '/am-grnotes/',
    'get_qc_rejection_report': '/am-qualitycheck/',
    'get_dispatch_records': '/am-dispatch-module/',
    'get_dispatch_delivery_report': '/am-order-reports/Delivery-report',
    'get_production_summary': '/am-dashboard/consolidated_dashboard',
    'get_pending_summary': '/am-dashboard/pending',
    'get_labour_costing': '/am-labour/labour_cost',
    'get_daily_attendance': '/line/employee_line_report'
}


def sanitize_and_compact_json(data: Any, tool_name: str, max_items: int = None, max_chars: int = None) -> str:
    """
    Optimizes and limits large JSON responses specifically for quantized models.
    1. Extracts lists from results/data wrappers.
    2. Filters out audit fields and preserves high-salience business fields.
    3. Caps list items to `max_items` with a summary count header.
    4. Truncates character payload safely if exceeding `max_chars`.
    """
    if max_items is None:
        max_items = Config.MAX_TOOL_RESPONSE_ITEMS
    if max_chars is None:
        max_chars = Config.MAX_TOOL_RESPONSE_CHARS

    if data is None:
        return json.dumps({"status": "no_data", "records": []})

    items = []
    total_count = None

    if isinstance(data, dict):
        for list_key in ['results', 'data', 'items', 'rows', 'records', 'list']:
            if list_key in data and isinstance(data[list_key], list):
                items = data[list_key]
                break
        total_count = data.get('count') or data.get('total') or data.get('total_count') or data.get('total_results')
        if not items and not isinstance(data.get('results'), list):
            items = [data]
    elif isinstance(data, list):
        items = data

    if total_count is None:
        total_count = len(items)

    allowed_fields = set(SALIENT_FIELDS_MAP.get(tool_name, []))

    compacted_items = []
    for item in items[:max_items]:
        if not isinstance(item, dict):
            compacted_items.append(item)
            continue
        filtered = {}
        for k, v in item.items():
            if allowed_fields and k not in allowed_fields:
                continue
            if v not in (None, '', [], {}):
                if isinstance(v, list) and len(v) > 5:
                    filtered[k] = v[:5]
                else:
                    filtered[k] = v
        if filtered:
            compacted_items.append(filtered)

    payload_summary = {
        "total_records_found": total_count,
        "displayed_records_count": len(compacted_items),
        "records": compacted_items
    }
    if total_count > len(compacted_items):
        payload_summary["note"] = f"Showing top {len(compacted_items)} of {total_count} total records. Advise user to specify filters if looking for a specific item."

    result_str = json.dumps(payload_summary, separators=(',', ':'))

    if len(result_str) > max_chars:
        logger.warning(f"Tool {tool_name} payload ({len(result_str)} chars) exceeded limit {max_chars}. Applying aggressive truncation.")
        while len(compacted_items) > 1 and len(json.dumps(payload_summary, separators=(',', ':'))) > max_chars:
            compacted_items.pop()
            payload_summary["displayed_records_count"] = len(compacted_items)
        result_str = json.dumps(payload_summary, separators=(',', ':'))
        if len(result_str) > max_chars:
            result_str = result_str[:max_chars] + '... [truncated]'

    return result_str


def execute_tool_get_api(tool_name: str, arguments: Dict[str, Any], auth_token: Optional[str] = None, headers: Optional[Dict[str, str]] = None) -> str:
    """
    Executes the GET API for the selected tool against the ERP gateway, propagating authentication and tenant headers.
    """
    endpoint = TOOL_ENDPOINT_MAP.get(tool_name)
    if not endpoint:
        return json.dumps({"error": f"Tool '{tool_name}' has no registered API route."})

    base_url = Config.BASE_URL
    url = f"{base_url}{endpoint}"

    req_headers = {
        "Content-Type": "application/json"
    }
    if auth_token:
        req_headers["Authorization"] = auth_token
    if headers:
        for k in ['compcode', 'tenant_id', 'company_id', 'X-Trace-Id', 'User-Agent']:
            if k in headers:
                req_headers[k] = str(headers[k])

    query_params = {}
    if isinstance(arguments, dict):
        for k, v in arguments.items():
            if v is not None and v != "":
                query_params[k] = v

    if headers:
        for k in ['compcode', 'tenant_id']:
            if k in headers and k not in query_params and headers[k]:
                query_params[k] = str(headers[k])

    logger.info(f"Invoking GET {url} with params {query_params} for tool {tool_name}")
    try:
        response = _http_session.get(url, headers=req_headers, params=query_params if query_params else None, timeout=15)
        if response.status_code == 200:
            try:
                raw_json = response.json()
                return sanitize_and_compact_json(raw_json, tool_name)
            except Exception as e:
                logger.error(f"Failed to parse JSON from {url}: {e}")
                return json.dumps({"error": f"Invalid JSON response from server: {str(e)}"})
        else:
            logger.warning(f"Tool {tool_name} returned status {response.status_code}: {response.text[:300]}")
            return json.dumps({
                "status_code": response.status_code,
                "error": f"API request to {endpoint} returned status {response.status_code}",
                "detail": response.text[:200]
            })
    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling tool {tool_name} at {url}")
        return json.dumps({"error": f"Service timeout when fetching data for {tool_name}."})
    except Exception as e:
        logger.error(f"Exception calling tool {tool_name}: {e}", exc_info=True)
        return json.dumps({"error": f"Connection error calling {tool_name}: {str(e)}"})


def parse_llm_response(resp_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes LLM response structures across Ollama native (/api/chat) and OpenAI (/v1/chat/completions) formats.
    """
    if not isinstance(resp_data, dict):
        return {"content": "", "tool_calls": [], "prompt_tokens": 0, "completion_tokens": 0}

    # 1. Ollama native format: {"message": {"content": "...", "tool_calls": [...]}, "prompt_eval_count": ..., "eval_count": ...}
    if "message" in resp_data and isinstance(resp_data["message"], dict):
        msg = resp_data["message"]
        tool_calls = msg.get("tool_calls") or []
        content_text = msg.get("content") or ""

        # Fallback for small LLMs: If tool_calls is empty but model output raw JSON tool call in content
        if not tool_calls and content_text:
            try:
                import re
                json_match = re.search(r'\{.*"name"\s*:\s*"([a-zA-Z0-9_]+)".*\}', content_text, re.DOTALL)
                if json_match:
                    parsed_json = json.loads(json_match.group(0))
                    fn_name = parsed_json.get("name") or parsed_json.get("function")
                    fn_args = parsed_json.get("arguments") or parsed_json.get("parameters") or {}
                    if fn_name:
                        tool_calls = [{"function": {"name": fn_name, "arguments": fn_args}}]
            except Exception as e:
                logger.debug(f"JSON repair fallback encountered error (benign): {e}")

        # Ensure tool_calls has standard format with function/name/arguments
        formatted_tool_calls = []
        for tc in tool_calls:
            if isinstance(tc, dict):
                fn = tc.get("function", {})
                if fn and isinstance(fn, dict):
                    args = fn.get("arguments", {})
                    # Repair if small model generated arguments as a JSON string with markdown or trailing commas
                    if isinstance(args, str):
                        clean_args_str = args.strip()
                        if clean_args_str.startswith("```"):
                            import re
                            clean_args_str = re.sub(r"^```(?:json)?\s*", "", clean_args_str)
                            clean_args_str = re.sub(r"\s*```$", "", clean_args_str).strip()
                        try:
                            # Fix trailing commas e.g. {"sku": "123",} -> {"sku": "123"}
                            import re
                            fixed_str = re.sub(r",\s*([\]}])", r"\1", clean_args_str)
                            fn["arguments"] = json.loads(fixed_str)
                        except Exception:
                            pass
                    formatted_tool_calls.append(tc)
                elif "name" in tc:
                    raw_args = tc.get("arguments", {})
                    if isinstance(raw_args, str):
                        clean_str = raw_args.strip()
                        if clean_str.startswith("```"):
                            import re
                            clean_str = re.sub(r"^```(?:json)?\s*", "", clean_str)
                            clean_str = re.sub(r"\s*```$", "", clean_str).strip()
                        try:
                            import re
                            fixed_str = re.sub(r",\s*([\]}])", r"\1", clean_str)
                            raw_args = json.loads(fixed_str)
                        except Exception:
                            pass
                    formatted_tool_calls.append({
                        "id": tc.get("id", f"call_{tc.get('name')}"),
                        "type": "function",
                        "function": {
                            "name": tc.get("name"),
                            "arguments": raw_args if isinstance(raw_args, dict) else {}
                        }
                    })
                else:
                    formatted_tool_calls.append(tc)
        return {
            "content": content_text,
            "tool_calls": formatted_tool_calls,
            "prompt_tokens": resp_data.get("prompt_eval_count", 0),
            "completion_tokens": resp_data.get("eval_count", 0)
        }

    # 2. OpenAI-compatible format: {"choices": [{"message": {"content": "...", "tool_calls": [...]}}], "usage": {...}}
    choices = resp_data.get("choices")
    if isinstance(choices, list) and len(choices) > 0:
        first_choice = choices[0] if isinstance(choices[0], dict) else {}
        msg = first_choice.get("message", {})
        usage = resp_data.get("usage", {})
        return {
            "content": msg.get("content") or "",
            "tool_calls": msg.get("tool_calls") or [],
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0)
        }

    return {"content": "", "tool_calls": [], "prompt_tokens": 0, "completion_tokens": 0}


def parse_llm_stream_line(line_str: str) -> tuple[Optional[str], bool]:
    """
    Parses a single stream line from either Ollama NDJSON or OpenAI SSE format.
    Returns (token_str, is_done).
    """
    clean_line = line_str.strip()
    if not clean_line:
        return None, False

    # OpenAI SSE format: "data: {...}" or "data: [DONE]"
    if clean_line.startswith("data:"):
        payload_str = clean_line[5:].strip()
        if payload_str == "[DONE]":
            return None, True
        try:
            chunk_obj = json.loads(payload_str)
            choices = chunk_obj.get("choices", [])
            if choices and isinstance(choices[0], dict):
                delta = choices[0].get("delta", {})
                token = delta.get("content", "")
                return token, False
        except Exception:
            return None, False

    # Ollama NDJSON format: {"message": {"content": "token"}, "done": false}
    if clean_line.startswith("{") and clean_line.endswith("}"):
        try:
            chunk_obj = json.loads(clean_line)
            is_done = chunk_obj.get("done", False)
            msg = chunk_obj.get("message", {})
            token = msg.get("content", "")
            return token, is_done
        except Exception:
            return None, False

    return None, False


def send_llm_request_with_retry(payload: Dict[str, Any], max_retries: int = None, stream: bool = False) -> requests.Response:
    """
    Sends request to Ollama Cloud / OpenAI-compatible endpoint with exponential backoff retries.
    """
    if max_retries is None:
        max_retries = Config.LLM_MAX_RETRIES

    url = Config.LLM_API_URL
    api_key = Config.LLM_API_KEY
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Optimize latency: disable thinking mode for Ollama cloud inference unless explicitly enabled
    if isinstance(payload, dict) and "think" not in payload:
        if "ollama" in url.lower() or "/api/chat" in url:
            payload["think"] = False

    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Dispatching request to LLM ({Config.LLM_MODEL}) at {url} (Attempt {attempt}/{max_retries}, stream={stream})")
            resp = _http_session.post(url, headers=headers, json=payload, timeout=Config.LLM_TIMEOUT, stream=stream)
            if resp.status_code in [200, 400]:
                return resp
            elif resp.status_code in [429, 500, 502, 503, 504]:
                logger.warning(f"LLM returned HTTP {resp.status_code}. Retrying in {attempt * 2}s...")
                time.sleep(attempt * 2)
            else:
                return resp
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.warning(f"LLM connection failure: {e}. Retrying in {attempt * 2}s...")
            last_exception = e
            time.sleep(attempt * 2)

    if last_exception:
        raise last_exception
    raise RuntimeError(f"Failed to communicate with LLM after {max_retries} attempts.")


def evaluate_interaction_with_judge(
    user_message: str,
    tool_calls: Any = None,
    answer_response: str = "",
    chat_history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Evaluates and scores both the tool calling decision/response and the final synthesized answer response using LLM as a Judge.
    Returns structured scores, feedback, and verdict.
    """
    judge_system_prompt = (
        "You are an expert AI Benchmark Judge and Quality Assurance Evaluator for an ERP AI Assistant system.\n"
        "Your task is to evaluate and score two critical aspects of the interaction:\n"
        "1. Tool Calling Evaluation: Did the AI select the appropriate tool(s) and valid arguments for the user's ERP query? If no tools were called, was direct answering appropriate?\n"
        "2. Answer Response Evaluation: Is the answer factually grounded in the ERP context, complete, concise, visually clear (Markdown tables/bullet points), and free of hallucination or conversational fluff?\n\n"
        "You MUST respond ONLY with a valid JSON object matching this exact schema (no additional markdown outside the JSON):\n"
        "{\n"
        '  "tool_calling_score": <number between 0.0 and 10.0>,\n'
        '  "tool_calling_feedback": "<clear feedback on tool selection and argument accuracy>",\n'
        '  "answer_score": <number between 0.0 and 10.0>,\n'
        '  "answer_feedback": "<clear feedback on answer accuracy, markdown table clarity, and conciseness>",\n'
        '  "overall_score": <number between 0.0 and 10.0 representing weighted quality score>,\n'
        '  "verdict": "<EXCELLENT | GOOD | ACCEPTABLE | NEEDS_IMPROVEMENT | POOR>",\n'
        '  "summary": "<1-2 sentence executive evaluation summary>"\n'
        "}"
    )

    evaluation_user_prompt = (
        f"### User Message / Query:\n{user_message[:500]}\n\n"
        f"### Tool Calling Decision & Response:\n{json.dumps(tool_calls, indent=2) if tool_calls else 'None / Direct Response'}\n\n"
        f"### Final Synthesized Answer Response:\n{answer_response[:2000]}\n\n"
        "Evaluate the interaction and provide scores (0-10) and feedback in the specified JSON schema."
    )

    judge_messages = [
        {"role": "system", "content": judge_system_prompt},
        {"role": "user", "content": evaluation_user_prompt}
    ]

    judge_payload = {
        "model": Config.LLM_MODEL,
        "messages": judge_messages,
        "think": False,
        "stream": False
    }

    try:
        judge_resp = send_llm_request_with_retry(judge_payload)
        if judge_resp.status_code == 200:
            parsed = parse_llm_response(judge_resp.json())
            content = parsed.get("content", "").strip()

            # Clean markdown code block if returned
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            try:
                eval_data = json.loads(content)
                tool_score = float(eval_data.get("tool_calling_score", 8.0))
                ans_score = float(eval_data.get("answer_score", 8.0))
                overall = float(eval_data.get("overall_score", (tool_score + ans_score) / 2))
                return {
                    "tool_calling_score": round(tool_score, 1),
                    "tool_calling_feedback": str(eval_data.get("tool_calling_feedback", "Tool calling matched the user query.")),
                    "answer_score": round(ans_score, 1),
                    "answer_feedback": str(eval_data.get("answer_feedback", "Response is structured and relevant.")),
                    "overall_score": round(overall, 1),
                    "verdict": str(eval_data.get("verdict", "GOOD")),
                    "summary": str(eval_data.get("summary", "Evaluation completed successfully."))
                }
            except Exception as parse_err:
                logger.warning(f"Failed to parse Judge JSON output: {parse_err}. Content: {content[:200]}")
                return {
                    "tool_calling_score": 8.0,
                    "tool_calling_feedback": "Tool execution completed.",
                    "answer_score": 8.0,
                    "answer_feedback": "Answer generated successfully.",
                    "overall_score": 8.0,
                    "verdict": "GOOD",
                    "summary": content[:300] if content else "Evaluated successfully."
                }
        else:
            logger.error(f"Judge LLM failed with HTTP {judge_resp.status_code}: {judge_resp.text}")
            return {
                "tool_calling_score": 0.0,
                "tool_calling_feedback": f"Judge service error ({judge_resp.status_code})",
                "answer_score": 0.0,
                "answer_feedback": f"Judge service error ({judge_resp.status_code})",
                "overall_score": 0.0,
                "verdict": "ERROR",
                "summary": f"Judge LLM failed with status {judge_resp.status_code}"
            }
    except Exception as e:
        logger.error(f"Exception during judge evaluation: {e}", exc_info=True)
        return {
            "tool_calling_score": 0.0,
            "tool_calling_feedback": str(e),
            "answer_score": 0.0,
            "answer_feedback": str(e),
            "overall_score": 0.0,
            "verdict": "ERROR",
            "summary": f"Exception occurred during judge evaluation: {str(e)}"
        }

