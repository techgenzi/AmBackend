from flask_restx import Namespace, Resource, fields

from ..api_doc.product_group_atttribute_group_api_doc import product_group_attributes_group_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

product_group_attributes_group_api_route = Namespace('product_group_attributes_group', path='/baseConfig/product_group_attributes_group')

# List product_group_attributes_groups API docs
product_group_attributes_group_model = product_group_attributes_group_api_route.model('product_group_attributes_groups_model', {
            **product_group_attributes_group_fields,**{ "compcode": fields.Integer,
 "created_on": fields.String,
 "modified_on": fields.String,
 "modified_by": fields.String,
 "deleted_at": fields.String,
 "deleted": fields.Boolean,
                                                        "attribute_name":fields.String,
                                                        "group_name":fields.String}
        })

product_group_attributes_group_list_response = product_group_attributes_group_api_route.model('product_group_attributes_groups_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(product_group_attributes_group_model))
    }
})


create_product_group_attributes_group_model = product_group_attributes_group_api_route.model('create_product_group_attributes_groups_model', product_group_attributes_group_fields)
bulk_post_attribute_model=product_group_attributes_group_api_route.model('bulk_post_model',
                                                               {"data":fields.List(fields.Nested(create_product_group_attributes_group_model))})
create_product_group_attributes_group_response = product_group_attributes_group_api_route.model('create_product_group_attributes_groups_response', create_record_response)

# Get product_group_attributes_groups records model
get_product_group_attributes_group_response = product_group_attributes_group_api_route.model('get_product_group_attributes_groups_response', product_group_attributes_group_fields)

# Update user record
update_product_group_attributes_group_fields = product_group_attributes_group_fields
update_product_group_attributes_group_model = product_group_attributes_group_api_route.model('update_product_group_attributes_groups_model', update_product_group_attributes_group_fields)
update_product_group_attributes_group_response = product_group_attributes_group_api_route.model('update_product_group_attributes_groups_response', update_record_response)
    
