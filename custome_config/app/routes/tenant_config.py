from flask_restx import Namespace, fields
from ..api_doc import custom_config_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model

# Initialize API routes
custom_config_api_route = Namespace('custome_config', path='/custome_config')

# Configuration model
custom_config_model = custom_config_api_route.model('custom_config_model', {
    **custom_config_fields
})

# List response model
custom_config_list_response = custom_config_api_route.model('custom_config_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(custom_config_model))
    }
})

create_custom_config_model = custom_config_api_route.model('create_custom_config_model', custom_config_model)
create_custom_config_response = custom_config_api_route.model('create_custom_config_response', create_record_response)
