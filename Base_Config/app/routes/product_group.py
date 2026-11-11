from flask_restx import Namespace, Resource, fields
from ..api_doc.product_group_api_doc import product_group_fields,product_group,variant_att
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

product_group_api_route = Namespace('product_group', path='/baseConfig/product_group')


# List product_groups API docs
product_group_model = product_group_api_route.model('product_groups_model', {
            **product_group_fields
        })

product_group_list_response = product_group_api_route.model('product_groups_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(product_group_model))
    }
})
attribute_model = product_group_api_route.model('variant_model',variant_att)

create_product_group_model = product_group_api_route.model('create_product_groups_model', product_group_fields)


bulk_model=product_group_api_route.model('bulk_post_data_model',{
            **product_group,
            **{
                'data': fields.List(fields.Nested(attribute_model))
            }
})
bulk_model_get = product_group_api_route.model('bulk_model_get',{
                                               **{
                                                   'total_results': fields.Integer,
                                                   'page': fields.Integer,
                                                   'results_per_page': fields.Integer,
                                               },
                                               **{
                                                  'results':fields.List(fields.Nested(bulk_model))
                                               }
})
create_product_group_response = product_group_api_route.model('create_product_groups_response', create_record_response)

# Get product_groups records model
get_product_group_response = product_group_api_route.model('get_product_groups_response', product_group_fields)

# Update user record
update_product_group_fields = product_group_fields
update_product_group_model = product_group_api_route.model('update_product_groups_model', update_product_group_fields)
update_product_group_response = product_group_api_route.model('update_product_groups_response', update_record_response)
    
