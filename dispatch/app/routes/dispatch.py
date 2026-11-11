from flask_restx import Namespace, Resource, fields
from ..api_doc import invRegistryFields, dispatch_header, dispatch_post, dispatch_get, plan_to_report
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

dispatch_api_route = Namespace('Dispatch', path='/am-dispatch-module')

dispatch_list_model = dispatch_api_route.model('dispatch_list_model', {**dispatch_header
                                                                       })

dispatch_list_response = dispatch_api_route.model('stock list  model', {
    **list_response_model,
    'results': fields.List(fields.Nested(dispatch_list_model))
})

# List inventoryRegistry API docs
inventoryRegistry_model = dispatch_api_route.model('inventoryRegistry_model', {
            **invRegistryFields ,**{"sku_id":fields.String,
                                    "product_count":fields.String,
                                    "product_name":fields.String,
                                    'allocated_quantity': fields.String,
                                    "rawmaterialsid":fields.String,
                                    "asset_attributes":fields.Raw}
        })
inventoryBulk_model=dispatch_api_route.model('inventoryBulk_model',{
    'data':fields.List(fields.Nested(inventoryRegistry_model))
})

inven_res = dispatch_api_route.model('model',{
    'prod_plan_id':fields.Integer,
    'ref_id': fields.String,
    'requested_by': fields.String,
    'requested_on': fields.String,
    'status': fields.String,
    'data': fields.List(fields.Nested(inventoryRegistry_model))
})


inventoryRegistry_list_response = dispatch_api_route.model('inventoryRegistry_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(inven_res))
    }
})

create_inventoryRegistry_model = dispatch_api_route.model('create_inventoryRegistry_model', inventoryRegistry_model)
create_inventoryRegistry_response = dispatch_api_route.model('create_inventoryRegistry_response', create_record_response)

# Get inventoryRegistry records model
get_inventoryRegistry_response = dispatch_api_route.model('get_inventoryRegistry_response', invRegistryFields)

# Update user record
update_inventoryRegistry_fields = invRegistryFields
update_inventoryRegistry_model = dispatch_api_route.model('update_inventoryRegistry_model', invRegistryFields)
update_inventoryRegistry_response = dispatch_api_route.model('update_inventoryRegistry_response', update_record_response)
post_model = dispatch_api_route.model('post_model', dispatch_post)
dispatch_post_model = dispatch_api_route.model('dispatch_post_model', {
    'data':fields.List(fields.Nested(post_model))
})

dispatch_get_model = dispatch_api_route.model('dispatch_get_model', dispatch_get)

dispatch_get_list_model = dispatch_api_route.model('dispatch_list_get_model', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(dispatch_get_model))
    }
})


plan_to_dispatch = dispatch_api_route.model('dispatch_to_plan', plan_to_report)


plan_to_dispatch_model = dispatch_api_route.model('dispatch_list_get_model', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(plan_to_dispatch))
    }
})
##############################################

from flask_restx import fields
dispatch_data_model = dispatch_api_route.model('DispatchData', {
    'dispatch_amount': fields.Float,
    'action': fields.String,
    'product_name': fields.String,
    'sku_id': fields.String,
    "product_code":fields.String,
    'approved_amount': fields.Float,
    'requested_amount': fields.Float,
    'request_status': fields.String,
    'approval_date': fields.String,  # ISO format assumed
})

order_date_model = dispatch_api_route.model('OrderDate', {
    'dispatch_date': fields.String,
    'distpatch_data': fields.List(fields.Nested(dispatch_data_model))
})

request_data_model = dispatch_api_route.model('RequestData', {
    'request_id': fields.String,
    'product_count': fields.Float,
    'order_date': fields.List(fields.Nested(order_date_model))
})

plan_data_model = dispatch_api_route.model('PlanData', {
    'plan_unique': fields.String,
    'order_unique': fields.String,
    'total_value': fields.Float,
    'planned_wastage': fields.Float,
    'planned_wastage_per': fields.Float,
    'status': fields.String,
    'plan_date': fields.String,
    'planed_quantity': fields.Float,
    'planned_product': fields.String,
    'planned_product_sku': fields.String,
"planned_product_code":fields.String,
    'request_data': fields.List(fields.Nested(request_data_model))
})
plan_response_model=dispatch_api_route.model('plan_response_model',{
    "data":fields.List(fields.Nested(plan_data_model))
})
# dispatch_model = dispatch_api_route.model('Dispatch', {
#     'dispatch_amount': fields.Float,
#     'action': fields.String,
#     'dispatch_date': fields.String,
#     'product_name': fields.String,
#     'sku_id': fields.String,
# 'request_status': fields.String,
#     'approval_date': fields.String,
#     'approved_amount': fields.Float,
#     'requested_amount': fields.Float,
# })
#
# request_model = dispatch_api_route.model('Request', {
#     'request_id': fields.String,
#     'distpatch_data': fields.List(fields.Nested(dispatch_model)),
# })
#
# plan_model = dispatch_api_route.model('Plan', {
#     'plan_unique': fields.String,
#     'planned_wastage': fields.Float,
#     'planned_wastage_per': fields.Float,
#     'status': fields.String,
#     'plan_date': fields.String,
#     'planed_quantity': fields.Float,
#     'planned_product': fields.String,
#     'planned_product_sku': fields.String,
#     'request_data': fields.List(fields.Nested(request_model)),
# })
# plan_response_model=dispatch_api_route.model('plan_response_model',{
#     **list_response_model,
#     "data":fields.List(fields.Nested(plan_model))
# })
