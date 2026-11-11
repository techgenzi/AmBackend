from flask_restx import Namespace, Resource, fields
from ..api_doc.category_api_doc import category_fields, style_category_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

category_api_route = Namespace('Category', path='/baseConfig/group/category')


single_category_model = category_api_route.model('create_category_model', category_fields)

create_category_response = category_api_route.model('create_category_response', create_record_response)

category_list_response = category_api_route.model('category_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(single_category_model))
    }
})

# Update user record
update_category_fields = category_fields
update_category_model = category_api_route.model('update_category_model', update_category_fields)
update_category_response = category_api_route.model('update_category_response', update_record_response)

style_category_api_route = Namespace('Style_Category', path='/baseConfig/group/category_product')


single_category_product_model = style_category_api_route.model('create_category_product_model', style_category_fields)

create_category_product_response = style_category_api_route.model('create_category_product_response', create_record_response)

style_category_list_response = style_category_api_route.model('category_product_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(single_category_product_model))
    }
})

# Update user record
update_style_category_fields = category_fields
update_style_category_model = style_category_api_route.model('update_category_product_model', update_style_category_fields)
update_style_category_response = style_category_api_route.model('update_category_product_response', update_record_response)

