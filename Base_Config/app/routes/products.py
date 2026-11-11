from flask_restx import Namespace, Resource, fields
from ..api_doc.product_api_doc import products_fields, product_variant_fields, product_variant_get
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

products_api_route = Namespace('products', path='/baseConfig/products')


bulk_get_response = products_api_route.model('bulk_get_response_model',product_variant_get)
# List productss API docs
products_model = products_api_route.model('productss_model', {
    **{"roql":fields.String,
        "product_group_id":fields.Integer,
        "group_name": fields.String,
     "product_id": fields.Integer,
       'cost': fields.Float,
     "product_name": fields.String,
    "product_code": fields.String,
        'product_count': fields.Float,
    "sku_id": fields.String,
     "description": fields.String,
     "uom": fields.String,
       'uom_id': fields.Integer,
'material_cost': fields.String,
       'bom_id': fields.Integer,
       'allocated_quantity': fields.String,
       'is_serializable': fields.Boolean,
       'serialization_params': fields.List(fields.Raw)
     },
    **{
        'data':fields.List(fields.Nested(bulk_get_response))
     }
})

product_drop_down = {
    'product_id': fields.Integer,
    'product_group_id': fields.Integer,
    'group_name': fields.String,
    'product_name': fields.String,
    'product_code': fields.String,
    'sku_id': fields.String,
    'bom_id': fields.Integer,
    'uom_id': fields.Integer,
    'uom': fields.String,
    'is_serializable': fields.Boolean,
    'serialization_params': fields.List(fields.Raw)
}

product_drop_down_model = products_api_route.model('product_drop_down_model', product_drop_down)

products_variant_field_model = products_api_route.model('products_variant_field_model',product_variant_fields)
products_list_response = products_api_route.model('productss_list_response', {
    **list_response_model,

    **{
        'results': fields.List(fields.Nested(products_model))
    }
})

products_drop_down_list_response = products_api_route.model('products_drop_down_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(product_drop_down_model))
    }
})

create_products_model = products_api_route.model('create_productss_model', products_fields)
create_products_response = products_api_route.model('create_productss_response', create_record_response)
bulk_post_model=products_api_route.model('bulk_post_product_model',{
    **products_fields,
    "data":fields.List(fields.Nested(products_variant_field_model))
})

# Get productss records model
get_products_response = products_api_route.model('get_productss_response', products_fields)

# Update user record
update_products_fields = products_fields
update_products_model = products_api_route.model('update_productss_model', update_products_fields)
update_products_response = products_api_route.model('update_productss_response', update_record_response)


file_upload_parser = products_api_route.parser()

file_upload_parser.add_argument(
    'excel',
    type='FileStorage',  # Correct type for file uploads
    location='files',  # Specifies this is a file upload
    required=True,
    help='Upload the Excel file to update the cost'
)

    
