from flask_restx import Namespace, Resource, fields
from ..bom_config_api_doc import bom_config_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model

# Initialize API routes

bom_config_api_route = Namespace('BOM_CONFIG', path='/am-asset_config')

single_bom_config_model = bom_config_api_route.model('create_bom_config_model', bom_config_fields)

create_bom_config_response = bom_config_api_route.model('create_bom_config_response', create_record_response)

bom_config_list_response = bom_config_api_route.model('bom_config_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(single_bom_config_model))
    }
})

# Update user record
update_bom_config_fields = bom_config_fields
update_bom_config_model = bom_config_api_route.model('update_bom_config_model', update_bom_config_fields)
update_bom_config_response = bom_config_api_route.model('update_bom_config_response', update_record_response)

