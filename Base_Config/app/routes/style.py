from flask_restx import Namespace, Resource, fields
from ..api_doc.style_api_doc import style_fields, style_product_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

style_api_route = Namespace('Style', path='/baseConfig/group/style')


single_style_model = style_api_route.model('create_uom_model', style_fields)

create_style_response = style_api_route.model('create_uom_response', create_record_response)

style_list_response = style_api_route.model('uom_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(single_style_model))
    }
})

# Update user record
update_style_fields = style_fields
update_style_model = style_api_route.model('update_floor_model', update_style_fields)
update_style_response = style_api_route.model('update_floor_response', update_record_response)

style_product_api_route = Namespace('Style_Product', path='/baseConfig/group/style_product')


single_style_product_model = style_product_api_route.model('create_style_product_model', style_product_fields)

create_style_product_response = style_product_api_route.model('create_style_product_response', create_record_response)

style_product_list_response = style_product_api_route.model('style_product_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(single_style_product_model))
    }
})

# Update user record
update_style_product_fields = style_fields
update_style_product_model = style_product_api_route.model('update_style_product_model', update_style_product_fields)
update_style_product_response = style_product_api_route.model('update_style_product_response', update_record_response)

