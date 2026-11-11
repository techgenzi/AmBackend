from flask_restx import Namespace, Resource, fields
from ..api_doc.process_config import process_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model

# Initialize API routes

process_api_route = Namespace('Process_Config', path='/baseConfig/process_config')

# List variant_attributes API docs
process_model = process_api_route.model('process_model', process_fields)

process_list_response = process_api_route.model('process_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(process_model))
    }
})

create_variant_attribute_model = process_api_route.model('create_variant_attributes_model',
                                                                   process_fields)
bulk_post_model = process_api_route.model('variant_attribute_model', {
    "data": fields.List(fields.Nested(process_model))
})

create_process_response = process_api_route.model('create_variant_attributes_response',
                                                                      create_record_response)

# Get variant_attributes records model
get_variant_attribute_response = process_api_route.model('get_variant_attributes_response',
                                                                   process_fields)

# Update user record

update_process_model = process_api_route.model('update_process_model', update_record_response)

update_variant_attribute_response = process_api_route.model('update_process_response', process_fields)

