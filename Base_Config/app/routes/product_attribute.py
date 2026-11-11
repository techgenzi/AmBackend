from flask_restx import Namespace, Resource, fields
from ..api_doc.product_attribute_api_doc import product_attribute_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

product_attribute_api_route = Namespace('product_attribute', path='/baseConfig/product_attribute')

# List product_attributes API docs
product_attribute_model = product_attribute_api_route.model('product_attributes_model', {
            **product_attribute_fields,**{
        "compcode": fields.Integer,
        "created_on": fields.String,
        "modified_on": fields.String,
        "modified_by": fields.String,
        "deleted_at": fields.String,
        "deleted": fields.Boolean
    }
        })

product_attribute_list_response = product_attribute_api_route.model('product_attributes_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(product_attribute_model))
    }
})


create_product_attribute_model = product_attribute_api_route.model('create_product_attributes_model', product_attribute_fields)
bulk_post_model=product_attribute_api_route.model('bulk_post_model',{
                                     "data":fields.List(fields.Nested(create_product_attribute_model))       }      )
create_product_attribute_response = product_attribute_api_route.model('create_product_attributes_response', create_record_response)

# Get product_attributes records model
get_product_attribute_response = product_attribute_api_route.model('get_product_attributes_response', product_attribute_fields)

# Update user record
update_product_attribute_fields = product_attribute_fields
update_product_attribute_model = product_attribute_api_route.model('update_product_attributes_model', update_product_attribute_fields)
update_product_attribute_response = product_attribute_api_route.model('update_product_attributes_response', update_record_response)
    
