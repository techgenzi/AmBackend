

from flask_restx import Namespace, fields
from ipss_utils.ipss_api_doc import list_api_params, list_response_model

from ..api_doc import item_fields, order_fields, plan_cost

customerPurchaseRoute = Namespace('customerPurchaseRoute', path='/am-customer-purchase-order')
itemsModel=customerPurchaseRoute.model('itemsModel', {**item_fields,
                                                      **{"product_code":fields.String,
                                                         "product_count":fields.String,
                                                       "product_name":fields.String,
                                                         'uom': fields.String,
                                                       "sku_id":fields.String,
                                                       "is_serialized":fields.Boolean,
                                                       "store_stocks":fields.Raw,
                                                       "lot_breakdown":fields.Raw}
                                                      })
aggricatedModel=customerPurchaseRoute.model('aggricatedModel',{
    **order_fields,
    "lineItems":fields.List(fields.Nested(itemsModel))
})
aggricatedListModel=customerPurchaseRoute.model('aggricatedListModel', {**list_api_params,
                                                    "results":fields.List(fields.Nested(aggricatedModel))})
orderModel=customerPurchaseRoute.model('orderModel', {**order_fields,
                                                      "total_items":fields.String})
orderModelResponse=customerPurchaseRoute.model('orderModelResponse',{**list_response_model,
                                                                     "results":fields.List(fields.Nested(orderModel))})

ItemModelResponse=customerPurchaseRoute.model('ItemModelResponse',{
    **list_response_model,
    "results":fields.List(fields.Nested(itemsModel))
})


plan_cost_model = customerPurchaseRoute.model('plan_cost_model', plan_cost)

plan_cost_response_model = customerPurchaseRoute.model('plan_cost_response_model', {
    **list_response_model,
    'results': fields.List(fields.Nested(plan_cost_model))
})

planed_qty_model = customerPurchaseRoute.model('planed_qty_model', {
    'product_id': fields.String,
    'total': fields.String,
    'data': fields.Raw
})

planed_qty_response_model = customerPurchaseRoute.model('planed_qty_response_model', {
    **list_response_model,
    'results': fields.List(fields.Nested(planed_qty_model))
})
