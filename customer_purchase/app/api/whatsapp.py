import os
import json
import requests
import datetime
from flask import request
from flask_restx import Resource
from sqlalchemy import text
from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.ipss_db import query_to_dict
from ipss_utils.decorators import login_required
from ..routes.whatsapp import whatsappRoute, incoming_message_response
from ..model.whatsapp import WhatsAppTenantConfig, WhatsAppIncomingMessage
from .. import db_client, ipss_db

def parse_message_with_groq(message_text):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Warning: GROQ_API_KEY environment variable is not set.")
        return "Unknown", []

    prompt = f"""
    Analyze the following message from a customer and classify it:
    1. If the user is trying to place an order, classify it as "Order". Extract a list of products and quantities.
    2. If the user is asking a general question, saying hello, or talking about something else, classify it as "Chat".

    Return ONLY a JSON object with this structure:
    {{
      "classification": "Order" | "Chat",
      "items": [
        {{"product_raw_name": "string", "quantity": number}}
      ]
    }}
    Message: "{message_text}"
    """

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result_data = response.json()
            content = result_data['choices'][0]['message']['content']
            parsed = json.loads(content)
            return parsed.get("classification", "Unknown"), parsed.get("items", [])
        else:
            print(f"Groq API error: {response.status_code} - {response.text}")
            return "Unknown", []
    except Exception as e:
        print(f"Error calling Groq API: {str(e)}")
        return "Unknown", []

@whatsappRoute.route('/webhook')
class WhatsAppWebhook(Resource):
    def get(self):
        # Verification flow for Meta webhook registration
        verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "techgenzi_verify_token_secure_xyz")
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode and token:
            if mode == 'subscribe' and token == verify_token:
                print("Webhook verified successfully!")
                return int(challenge)
            else:
                return 'Forbidden', 403
        return 'Invalid request', 400

    def post(self):
        try:
            payload = request.json
            if not payload:
                return {"error": "Invalid payload"}, 400

            # Verify that this is a valid Meta WhatsApp status/message payload
            entry = payload.get('entry', [])
            if not entry:
                return {"status": "ignored", "reason": "No entry found"}, 200

            changes = entry[0].get('changes', [])
            if not changes:
                return {"status": "ignored", "reason": "No changes found"}, 200

            value = changes[0].get('value', {})
            messages = value.get('messages', [])
            metadata = value.get('metadata', {})

            if not messages:
                # This could be a status update (delivered, read) rather than a message
                return {"status": "received", "type": "status_update"}, 200

            message = messages[0]
            phone_number_id = metadata.get('phone_number_id')
            sender = message.get('from')
            message_sid = message.get('id')
            text_body = message.get('text', {}).get('body', '')

            if not phone_number_id or not sender:
                return {"error": "Missing metadata"}, 400

            # 1. Resolve Tenant Context
            tenant = WhatsAppTenantConfig.query.filter_by(phone_number_id=str(phone_number_id), status='Active').first()
            if not tenant:
                # Log as generic if tenant configuration is missing
                print(f"Warning: No active tenant config found for Phone Number ID {phone_number_id}")
                return {"error": "Unknown phone number ID destination"}, 400

            # Check if message already logged to prevent duplicates
            existing = WhatsAppIncomingMessage.query.filter_by(message_sid=message_sid).first()
            if existing:
                return {"status": "success", "message": "already processed"}, 200

            # 2. Classify and parse using Groq Llama 3.1 8B
            classification, items = parse_message_with_groq(text_body)

            # 3. Log to Incoming Messages
            new_log = WhatsAppIncomingMessage(
                message_sid=message_sid,
                tenant_id=tenant.tenant_id,
                compcode=tenant.compcode,
                sender_mobile=sender,
                raw_text=text_body,
                message_type=classification,
                extracted_json=items,
                status='Parsed' if classification in ['Order', 'Chat'] else 'Failed'
            )
            db_client.session.add(new_log)
            db_client.session.commit()

            return {"status": "success", "classification": classification}, 200

        except Exception as e:
            db_client.session.rollback()
            print(f"Error processing webhook: {str(e)}")
            return {"error": str(e)}, 500

@whatsappRoute.route('/messages')
class WhatsAppMessagesList(Resource):
    @whatsappRoute.marshal_with(incoming_message_response)
    @whatsappRoute.doc(params={**list_api_params, 'status': 'Filter by status', 'message_type': 'Filter by type'})
    @login_required(permissions='customerpurchase.list')
    def get(self):
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get('results_per_page') else 20
        offset = (paged - 1) * results_per_page
        
        compcode = request.args.get('current_user', {}).get('company_id', None)
        
        sql_condition = ""
        params = {
            'ccode': compcode,
            'limit': results_per_page,
            'offset': offset
        }

        if request.args.get('status'):
            sql_condition += " AND status = :status"
            params['status'] = request.args.get('status')
            
        if request.args.get('message_type'):
            sql_condition += " AND message_type = :message_type"
            params['message_type'] = request.args.get('message_type')

        sql_query = text(f"""
            SELECT * FROM whatsapp_incoming_messages
            WHERE compcode = :ccode {sql_condition}
            ORDER BY id DESC
            LIMIT :limit OFFSET :offset
        """)

        results = query_to_dict(db_client.engine.execute(sql_query, **params))

        sql_count = text(f"""
            SELECT count(id) FROM whatsapp_incoming_messages
            WHERE compcode = :ccode {sql_condition}
        """)
        
        # Remove pagination params for count
        count_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
        count_result = query_to_dict(db_client.engine.execute(sql_count, **count_params))
        total_results = count_result[0].get('count', 0) if count_result else 0

        return {
            'primary_key': 'id',
            'total_results': total_results,
            'page': paged,
            'results_per_page': results_per_page,
            'results': results
        }
