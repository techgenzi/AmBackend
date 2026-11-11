from flask_restx import Namespace, Resource, fields
from ..api_doc.varient_attribute_api_doc import variant_attribute_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

variant_attribute_api_route = Namespace('variant_attribute', path='/baseConfig/variant_attribute')

# List variant_attributes API docs
variant_attribute_model = variant_attribute_api_route.model('variant_attributes_model', {
            **variant_attribute_fields,**{"compcode": fields.Integer,
 "created_on": fields.String,
 "modified_on": fields.String,
 "modified_by": fields.String,
 "deleted_at": fields.String,
 "deleted": fields.Boolean}
})

variant_attribute_list_response = variant_attribute_api_route.model('variant_attributes_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(variant_attribute_model))
    }
})


create_variant_attribute_model = variant_attribute_api_route.model('create_variant_attributes_model', variant_attribute_fields)
bulk_post_model=variant_attribute_api_route.model('variant_attribute_model',{
    "data":fields.List(fields.Nested(variant_attribute_model))
})
create_variant_attribute_response = variant_attribute_api_route.model('create_variant_attributes_response', create_record_response)

# Get variant_attributes records model
get_variant_attribute_response = variant_attribute_api_route.model('get_variant_attributes_response', variant_attribute_fields)

# Update user record
update_variant_attribute_fields = variant_attribute_fields
update_variant_attribute_model = variant_attribute_api_route.model('update_variant_attributes_model', update_variant_attribute_fields)
update_variant_attribute_response = variant_attribute_api_route.model('update_variant_attributes_response', update_record_response)
    
