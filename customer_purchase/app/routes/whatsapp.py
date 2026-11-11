from flask_restx import Namespace, fields
from ipss_utils.ipss_api_doc import list_api_params, list_response_model

whatsappRoute = Namespace('whatsappRoute', path='/am-whatsapp')

incoming_message_model = whatsappRoute.model('IncomingMessageModel', {
    'id': fields.Integer,
    'message_sid': fields.String,
    'tenant_id': fields.Integer,
    'compcode': fields.String,
    'sender_mobile': fields.String,
    'raw_text': fields.String,
    'message_type': fields.String,
    'extracted_json': fields.Raw,
    'status': fields.String,
    'created_at': fields.DateTime
})

incoming_message_response = whatsappRoute.model('IncomingMessageResponse', {
    **list_response_model,
    'results': fields.List(fields.Nested(incoming_message_model))
})
