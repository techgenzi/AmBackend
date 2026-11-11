
from flask_restx import Namespace, Resource, fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model
from ..api_doc import inv_summary, plan_summary, wastage, top_card, plan_cost_vs_actual_cost, loss, update_dashboard, \
    order_result

dashboard_api_route = Namespace('AM Dashboard Api', path='/am-dashboard')

#
# dashboard_model = dashboard_api_route.model('dashboard_model', inv_summary)
#
# dashboard_report_model = dashboard_api_route.model('dashboard_report_model', {
#     **list_response_model,
#     'results': fields.List(fields.Nested(dashboard_model))
# })

plan_model = dashboard_api_route.model('plan_single_model', plan_summary)

inv_model = dashboard_api_route.model('inv model', inv_summary)

wastage_model = dashboard_api_route.model('wastage_model', wastage)

plan_vs_actual_cost_model = dashboard_api_route.model('plan_cost_vs_actual_cost_model', plan_cost_vs_actual_cost)

top_card_model = dashboard_api_route.model('top card model', top_card)

margin_loss = dashboard_api_route.model('margin loss', loss)

planvact_model = dashboard_api_route.model('planvsact_model',{
            'planed_quantity': fields.Integer,
            'actual_quantity': fields.Integer
        })
result_model = dashboard_api_route.model('result_model', {
        'top_card': fields.Nested(top_card_model),
        'inv_summary': fields.List(fields.Nested(inv_model)),
        'wastage': fields.List(fields.Nested(wastage_model)),
        'plan_vs_actual': fields.Nested(planvact_model),
        'plan_cost_vs_actual_cost': fields.List(fields.Nested(plan_vs_actual_cost_model)),
        'margin_loss': fields.List(fields.Nested(margin_loss))
    })
plan_dashboard_report_model = dashboard_api_route.model('plan_dashboard', {
    **list_response_model,
    'results': fields.Raw
})

# dashboard_get_model = dashboard_api_route.model('dashboard_fields', {
#             **dashboard_fields,
#             'deleted': fields.Boolean,
#             'created_on': fields.String,
#             'modified_on': fields.String
#         })
#
# dashboard_get_all_model = dashboard_api_route.model('dashboard_list_response', {
#     **list_response_model,
#     **{
#         'results': fields.List(fields.Nested(dashboard_get_model))
#     }
# })
#
# # Create skill model
# create_dashboard_model = dashboard_api_route.model('create_skill', dashboard_model)
# create_dashboard_response = dashboard_api_route.model('create_dashboard_response', create_record_response)
#
# # Get skill records model
# get_dashboard_response = dashboard_api_route.model('get_dashboard_response', dashboard_model)
#
#
# # Update user record
# update_dashboard_fields = dashboard_fields
# update_dashboard_model = dashboard_api_route.model('update_skill', update_dashboard_fields)
#
# update_dashboard_response = dashboard_api_route.model('update_dashboard_response', update_record_response)
efficiency_model=dashboard_api_route.model('efficiency_model',{'plan_unique':fields.String,
                                                               'wastage_per':fields.String,
                                                               'actual_wastage':fields.String,
                                                               'wastage':fields.String})
update_dashboard_model = dashboard_api_route.model('update_dashboard', {**update_dashboard,
                                                                        'wastage_eff':fields.List(fields.Nested(efficiency_model))})

order_result_model = dashboard_api_route.model('order result model', order_result)

order_list_response = dashboard_api_route.model('order list response', {
    **list_response_model,
    'results': fields.List(fields.Nested(order_result_model))
})
