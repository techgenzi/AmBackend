from flask_restx import Namespace, Resource, fields
from ..api_doc import store_list, store_product, store_material, store_transfer_post, store_transfer_items, \
    store_transfer_get
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

store_api_route = Namespace('Store Location', path='/am-store')


store_list_model = store_api_route.model('store_list_model', store_list)

store_list_response = store_api_route.model('store list model', {
    **list_response_model,
    'results': fields.List(fields.Nested(store_list_model))
})

store_product_model = store_api_route.model('store product model', store_product)
store_post_model = store_api_route.model('store product post model', {
    **store_list,
    'data': fields.List(fields.Nested(store_product_model))
})


create_record_response_model = store_api_route.model('post response model', create_record_response)

store_material_model = store_api_route.model('store material product model', store_material)

store_product_list_response = store_api_route.model('store list response', {
    **list_response_model,
    'results': fields.List(fields.Nested(store_material_model))
})

store_transfer_items_model = store_api_route.model('store transfer items model', store_transfer_items)

store_transfer_post_model = store_api_route.model('store transfer post model', {
    **store_transfer_post,
    'data': fields.List(fields.Nested(store_transfer_items_model))
})

store_transfer_get_model = store_api_route.model('store transfer get model', store_transfer_get)

store_transfer_list_resposne = store_api_route.model('store transfer list response model', {
    **list_response_model,
    'results': fields.List(fields.Nested(store_transfer_get_model))
})