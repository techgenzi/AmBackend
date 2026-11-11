from flask_restx import Namespace, Resource, fields
from ..api_doc import material_cost, product_service, bulk_post_upload, actual_material_cost
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model

# Initialize API routes

material_cost_api_route = Namespace('AM Material Cost', path='/am-material_cost')

material_cost_model = material_cost_api_route.model('material_cost_model', material_cost)

product_service_model = material_cost_api_route.model('product service', product_service)

product_service_list_model = material_cost_api_route.model('list product service', {
    **list_response_model,
    'results': fields.List(fields.Nested(product_service_model))
})
material_cost_list_response = material_cost_api_route.model('material_cost list model', {
    **list_response_model,
    'results': fields.List(fields.Nested(material_cost_model))
})

bulk_post_upload_model = material_cost_api_route.model('bulk_post_upload_model', bulk_post_upload)
material_cost_bulk_upload_model = material_cost_api_route.model('material_cost_bulk_upload_model', {
    'data': fields.List(fields.Nested(bulk_post_upload_model))
})


create_record_response_model = material_cost_api_route.model('post response model', create_record_response)

actual_material_model = material_cost_api_route.model('actual_material_model', actual_material_cost)

actual_material_cost_list_response = material_cost_api_route.model('actual_material_cost list model', {
    **list_response_model,
    'results': fields.List(fields.Nested(actual_material_model))
})
