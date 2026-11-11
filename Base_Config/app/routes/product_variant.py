from flask_restx import Namespace, Resource, fields
from ..api_doc.product_varient_api_doc import product_variant_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

product_variant_api_route = Namespace('product_variant', path='/baseConfig/product_variant')

# List product_variants API docs
product_variant_model = product_variant_api_route.model('product_variants_model', {
            **product_variant_fields,**{ "compcode": fields.Integer,
 "created_on": fields.String,
 "modified_on": fields.String,
 "modified_by": fields.String,
 "deleted_at": fields.String,
 "deleted": fields.Boolean}
        })

product_variant_list_response = product_variant_api_route.model('product_variants_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(product_variant_model))
    }
})


create_product_variant_model = product_variant_api_route.model('create_product_variants_model', product_variant_fields)
bulk_post_model=product_variant_api_route.model('bulk_post_model',{
    "data":fields.List(fields.Nested(create_product_variant_model))
})
create_product_variant_response = product_variant_api_route.model('create_product_variants_response', create_record_response)

# Get product_variants records model
get_product_variant_response = product_variant_api_route.model('get_product_variants_response', product_variant_fields)

# Update user record
update_product_variant_fields = product_variant_fields
update_product_variant_model = product_variant_api_route.model('update_product_variants_model', update_product_variant_fields)
update_product_variant_response = product_variant_api_route.model('update_product_variants_response', update_record_response)
    
