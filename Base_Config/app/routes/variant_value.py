from flask_restx import Namespace, Resource, fields
from ..api_doc.varient_value_api_doc import variant_value_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

variant_value_api_route = Namespace('variant_value', path='/baseConfig/variant_value')

# List variant_values API docs
variant_value_model = variant_value_api_route.model('variant_values_model', variant_value_fields)

variant_value_list_response = variant_value_api_route.model('variant_values_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(variant_value_model))
    }
})


create_variant_value_model = variant_value_api_route.model('create_variant_values_model', variant_value_fields)
bulk_post_model=variant_value_api_route.model('bulk_variant_value_model',{
    "data":fields.List(fields.Nested(variant_value_model))
})
create_variant_value_response = variant_value_api_route.model('create_variant_values_response', create_record_response)

# Get variant_values records model
get_variant_value_response = variant_value_api_route.model('get_variant_values_response', variant_value_fields)

# Update user record
update_variant_value_fields = variant_value_fields
update_variant_value_model = variant_value_api_route.model('update_variant_values_model', update_variant_value_fields)
update_variant_value_response = variant_value_api_route.model('update_variant_values_response', update_record_response)
    
