

from flask_restx import Namespace, fields
from ipss_utils.ipss_api_doc import list_response_model
# from rank.app.api_doc import list_response_model
from ..api_doc import total_order_products, overAllOrders, orderBasedReportFieldsNested, orderBasedReportFields, \
    productBasedReportss, all_plan_details, all_plan_fields, bom_fields, material_fields, \
    execution_previous_stage_fields, stage_wise_production_fields

orderServicesAPIRoutes = Namespace('orderServicesAPIRoutes', path='/am-order-Services')

bom_set_models=orderServicesAPIRoutes.model('bom_set_models',bom_fields)

#total_products on order
total_product_model=orderServicesAPIRoutes.model('total_product_model',total_order_products)
total_product_response=orderServicesAPIRoutes.model('total_product_response',{
    "data": fields.List(fields.Nested(total_product_model))})

#orderBased Products
order_based_products_model=orderServicesAPIRoutes.model('order_based_products_model',{**total_order_products,
                                                                                      **{
                                                                                          "extract_id":fields.Integer,
                                                                                          "order_unique":fields.String,
                                                                                          "items_id":fields.String,
                                                                                      }})
order_based_products_response=orderServicesAPIRoutes.model('order_based_products_response',{
    "data":fields.List(fields.Nested(order_based_products_model))
})

#Overall Orde
overAllOrderModel=orderServicesAPIRoutes.model('overAllOrderModel',overAllOrders)
overAllOrderModelResponse=orderServicesAPIRoutes.model('overAllOrderModelResponse',
                                                       {"data":fields.List(fields.Nested(overAllOrderModel))})

#orderBasedReports
orderBasedReportModel=orderServicesAPIRoutes.model('orderBasedReportModel',orderBasedReportFieldsNested)
orderBasedReportOrderModel=orderServicesAPIRoutes.model('orderBasedReportOrderModel', {**orderBasedReportFields,
                                        "bom_sets":fields.List(fields.Nested(bom_set_models))   ,
                                        "orders":fields.List(fields.Nested(orderBasedReportModel))})
orderBasedReportOrderModelResponse=orderServicesAPIRoutes.model('orderBasedReportOrderModelResponse',
                                                                {**list_response_model,
                                                                 "data":fields.List(fields.Nested(orderBasedReportOrderModel))
                                                                 })

###productReports

productBasecResportsmodel=orderServicesAPIRoutes.model('productBasecResportsmodel', {**productBasedReportss,
                                                    "bom_sets":fields.List(fields.Nested(bom_set_models))})
porductBasedReportResponse=orderServicesAPIRoutes.model('porductBasedReportResponses',{
    **list_response_model,
    **{"data":fields.List(fields.Nested(productBasecResportsmodel))}
})

###################overall_production
over_all_prod_sub_model=orderServicesAPIRoutes.model('over_all_prod_sub_model',all_plan_details)
over_all_prod_model=orderServicesAPIRoutes.model('over_all_prod_model',{
    **all_plan_fields,
    **{"plan_details":fields.List(fields.Nested(over_all_prod_sub_model))}
})
over_all_prod_model_list=orderServicesAPIRoutes.model('over_all_prod_model_list',{
    **list_response_model,
    **{"results":fields.List(fields.Nested(over_all_prod_model))}
})


material_model = orderServicesAPIRoutes.model('material model', material_fields)

material_list_response = orderServicesAPIRoutes.model('material list response', {
    **list_response_model,
    'results': fields.List(fields.Nested(material_model))
})


##############################
exe_prev_model=orderServicesAPIRoutes.model('exe_prev_model',execution_previous_stage_fields)
exe_nexted_prev_model=orderServicesAPIRoutes.model('exe_nexted_prev_model',{
    **list_response_model,
    "data":fields.List(fields.Nested(exe_prev_model))
})

stage_wise_production_model = orderServicesAPIRoutes.model('stage_wise_production_model', stage_wise_production_fields)

stage_wise_production_response = orderServicesAPIRoutes.model('stage_wise_production_response', {
    **list_response_model,
    'results': fields.List(fields.Nested(stage_wise_production_model))
})
