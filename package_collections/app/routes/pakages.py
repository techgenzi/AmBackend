from flask_restx import Namespace, Resource, fields
from ..api_doc import pakage_collections_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

pakage_collections_api_route = Namespace('package_collections', path='/am-package_collections')

# List pakage_collectionss API docs
pakage_fields=pakage_collections_fields.copy()
product_model=pakage_collections_api_route.model('pakage_collections_api_route',{
    "product_code":fields.String,
    "is_package_material":fields.Boolean,
    "id":fields.String,
    "pakage_id":fields.String,
    "product_id":fields.Integer,
    'uom_id': fields.Integer,
    'uom': fields.String,
    "needded_count":fields.String,
    "product_name":fields.String,
    "product_sku":fields.String,
})
pakage_collections_model = pakage_collections_api_route.model('pakage_collectionss_model', {

            **pakage_fields,**{
        "product_code":fields.String,
        "pakage_name":fields.String,
        "pakage_sku":fields.String,
        'uom': fields.String,
        "compcode": fields.Integer,
     "created_on": fields.String,
     "modified_on": fields.String,
     "modified_by": fields.String,
     "deleted_at": fields.String,
     "deleted": fields.Boolean,
        "products": fields.List(fields.Nested(product_model)),
    }
        })

pakage_collections_list_response = pakage_collections_api_route.model('pakage_collectionss_list_response', {
    **list_response_model,
    **{

        'results': fields.List(fields.Nested(pakage_collections_model))
    }
})


create_pakage_collections_model = pakage_collections_api_route.model('create_pakage_collectionss_model', {**pakage_fields,
                                                                                                          **{ "deleted": fields.Boolean}})
create_bulk=pakage_collections_api_route.model('crrate_bulk', {
    "data":fields.List(fields.Nested(create_pakage_collections_model))})
create_pakage_collections_response = pakage_collections_api_route.model('create_pakage_collectionss_response', create_record_response)

# Get pakage_collectionss records model
get_pakage_collections_response = pakage_collections_api_route.model('get_pakage_collectionss_response', pakage_collections_fields)

# Update user record
update_pakage_collections_fields = pakage_collections_fields
update_pakage_collections_model = pakage_collections_api_route.model('update_pakage_collectionss_model', pakage_fields)
update_pakage_collections_response = pakage_collections_api_route.model('update_pakage_collectionss_response', update_record_response)
    
