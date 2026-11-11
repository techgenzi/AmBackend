from flask_restx import Namespace, Resource, fields

from ..api_doc import bom_fields, bom_det_fields, bom_get_fields, product_service
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model

# Initialize API routes

bom_api_route = Namespace('bom', path='/am-bom')

bom_det_model = bom_api_route.model('bom_det_model', {**bom_det_fields,
                                                      "sku_id":fields.String})
# List production_requirmentss API docs

bom_single_get_model = bom_api_route.model('bom_model', {
    **bom_get_fields,"sku_id":fields.String,
    'data': fields.List(fields.Nested(bom_det_model))
})

bom_patch_model = bom_api_route.model('bom_model', {
    **bom_fields,
    'data': fields.List(fields.Nested(bom_det_model))
})

bom_get_all_model = bom_api_route.model('bom_get_all_model', {
    **list_response_model,
    'results': fields.List(fields.Nested(bom_single_get_model))
})


create_bom_response = bom_api_route.model(
    'create_production_requirmentss_response', create_record_response)


update_bom_response = bom_api_route.model('update_bom_response', update_record_response)

product_service_model = bom_api_route.model('product service model', product_service)

product_service_list_response = bom_api_route.model('list response on product service', {
    **list_response_model,
    'grant_cost': fields.String,
    'results': fields.List(fields.Nested(product_service_model))
})


lot_option_model = bom_api_route.model('lot_option_model', {
    'lot_id': fields.Integer,
    'lot_number': fields.String,
    'lot_qty': fields.Float,
    'required_quantity': fields.Float,
    'procured_quantity': fields.Float,
    'is_procured': fields.Boolean
})

multi_bom_get_model = bom_api_route.model('bom_model', {
    'product_id': fields.Integer,
    'product_name': fields.String,
    'product_code': fields.String,
    'product_count': fields.Integer,
    'product_group_id': fields.Integer,
    'sku_id': fields.String,
    'uom': fields.String,
    'allocated_quantity': fields.String,
    'total_required_quantity': fields.String,
    'already_procured_quantity': fields.String,
    'bom_status': fields.String,
    'lot_options': fields.List(fields.Nested(lot_option_model))
})


multiple_bom_get_model = bom_api_route.model('multiple_bom_model', {
    'results': fields.List(fields.Nested(multi_bom_get_model))
})
