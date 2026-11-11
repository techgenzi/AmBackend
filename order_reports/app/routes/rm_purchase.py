from flask_restx import Namespace, fields
from ipss_utils.ipss_api_doc import list_response_model

# from return_material.app.api.return_material import ReportApiroute
from ..api_doc import orderPlanSubFields, orderPlanFeields, del_fields, delivery_sub_fields, delivery_fields, \
    requestPlanReport, requestPlanReportModel, report_order, report_field

# from rank.app.api_doc import list_response_model


orderReportsAPIRoutes = Namespace('orderReportsAPIRoutes', path='/am-order-reports')

orderReportSubModel=orderReportsAPIRoutes.model('orderReportSubModel',orderPlanSubFields)
orderPlanReportModel=orderReportsAPIRoutes.model('orderPlanReportModel',{
    **orderPlanFeields,
    "plan_details":fields.List(fields.Nested(orderReportSubModel))
})
orderPlanReportModelResponse=orderReportsAPIRoutes.model('orderPlanReportModelResponse',{
    **list_response_model,
    "results":fields.List(fields.Nested(orderPlanReportModel))
})

######################

del_model=orderReportsAPIRoutes.model('del_model',del_fields)
del_model_response=orderReportsAPIRoutes.model('del_model_response',{
    **list_response_model,
    "results":fields.List(fields.Nested(del_model))
})

#################
delivery_model=orderReportsAPIRoutes.model('deleivery_model',delivery_sub_fields)
delivery_model_response=orderReportsAPIRoutes.model('delivery_model_response',{
    **delivery_fields,
    "products":fields.List(fields.Nested(delivery_model))
})
delivery_model_list_response=orderReportsAPIRoutes.model('delivery_model_list_response',{
    **list_response_model,
    "results":fields.List(fields.Nested(delivery_model_response))
})
###########################
planBasedreportModel=orderReportsAPIRoutes.model('planBasedreportModel',requestPlanReport)
planBasedNestedModel=orderReportsAPIRoutes.model('planBasedNestedModel',{
    **requestPlanReportModel,
    "plan_details":fields.List(fields.Nested(planBasedreportModel))
})
planBasedNestedModelResponse=orderReportsAPIRoutes.model('planBasedNestedModelResponse',{
    **list_response_model,
    "results":fields.List(fields.Nested(planBasedNestedModel))
})

report_order_model = orderReportsAPIRoutes.model('order report model', report_order)

report_order_list_response = orderReportsAPIRoutes.model('report_order_list_response',{
    **list_response_model,
    "results": fields.List(fields.Nested(report_order_model))
})

report_order_plan_model = orderReportsAPIRoutes.model('order report plan model', report_field)

report_order_plan_list_response = orderReportsAPIRoutes.model('report_order_plan_list_response',{
    **list_response_model,
    "results": fields.List(fields.Nested(report_order_plan_model))
})

