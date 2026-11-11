from flask_restx import Namespace, Resource, fields
from ..floor_api_doc import floor_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

floor_api_route = Namespace('floor', path='/production_config/floor')



single_floor_model = floor_api_route.model('create_floor_model', floor_fields)

create_floor_response = floor_api_route.model('create_floor_response', create_record_response)

floor_list_response = floor_api_route.model('floor_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(single_floor_model))
    }
})

# Update user record
update_floor_fields = floor_fields
update_floor_model = floor_api_route.model('update_floor_model', update_floor_fields)
update_floor_response = floor_api_route.model('update_floor_response', update_record_response)
    
