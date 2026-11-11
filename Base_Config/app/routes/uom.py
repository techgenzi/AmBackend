from flask_restx import Namespace, Resource, fields
from ..api_doc.api_doc import uom_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

uom_api_route = Namespace('uom', path='/baseConfig/uom')



single_uom_model = uom_api_route.model('create_uom_model', uom_fields)

create_uom_response = uom_api_route.model('create_uom_response', create_record_response)

uom_list_response = uom_api_route.model('uom_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(single_uom_model))
    }
})

# Update user record
update_uom_fields = uom_fields
update_uom_model = uom_api_route.model('update_floor_model', update_uom_fields)
update_uom_response = uom_api_route.model('update_floor_response', update_record_response)
    
