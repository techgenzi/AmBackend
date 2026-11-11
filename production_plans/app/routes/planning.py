from flask_restx import Namespace, fields

from ..api_doc import plan_target_fields, plan_details_fields, prod_plan_fields, hourly_target_fields, report_fields, \
    moved_quantity, plan_stock, plan_datewise_outward, plan_wise_outward, production_plan_cost, plan_to_store
from ipss_utils.ipss_api_doc import list_response_model
class NullField(fields.Raw):
    def format(self, value):
        if value == [None]:
            return None
        return super().format(value)
# report_det_resp=production_details_api_route.model('report_det_resp',{
# **production_fields,**{
#     # 'details':fields.List(fields.Nested(production_details_model),default=N)
# "details":NullField(attribute='details', nested=fields.Nested(production_details_model))
#
#     }
#
# })
prod_plan_api_route = Namespace('prod_plans', path='/am-prod_plans')

#post and update
plan_target_model=prod_plan_api_route.model('plan_target_model',plan_target_fields)

plan_details_model=prod_plan_api_route.model('plan_details_fields',plan_details_fields)

hourly_target_model=prod_plan_api_route.model('hourly_target_model',hourly_target_fields)
prod_plan_model=prod_plan_api_route.model('prod_plan_model', {
    **prod_plan_fields,
    "targets":fields.List(fields.Nested(plan_target_model)),
    "details":fields.List(fields.Nested(plan_details_model)),
    "hourly_target":fields.List(fields.Nested(hourly_target_model)),

})
prod_plan_bulk_model=prod_plan_api_route.model('prod_plan_bulk_model',{
    "data":fields.List(fields.Nested(prod_plan_model))
})
post_response_model=prod_plan_api_route.model('post_response_model',list_response_model)
##################################################################
#get

plan_nestedmodel=prod_plan_api_route.model('plan_nestedmodel',{"stage_name":fields.String,
                                                                "rank_id":fields.Integer,
                                                                "is_final_process":fields.Boolean,
                                                                "target_per_hour":fields.String,
                                                                "config_name":fields.String,
                                                                "config_id":fields.Integer,
                                                                "stage_id":fields.String,
                                                                "product_id":fields.Integer,
                                                                "product_name":fields.String,
                                                                "product_code":fields.String})
plan_deltailed_model=prod_plan_api_route.model('plan_deltailed_model',{
    "all_stages":fields.List(fields.Nested(plan_nestedmodel))
})

plan_details_get_model=prod_plan_api_route.model('plan_details_get_model',{**plan_details_model,
                                                                           **{"order_unique":fields.String,
                                                                            "order_type":fields.String,
                                                                            "status":fields.String,
                                                                              'ordered_quantity': fields.String,
                                                                              'product_name': fields.String,
                                                                              'product_code': fields.String,
                                                                              'sku_id': fields.String,
                                                                              'product_id': fields.Integer,
                                                                              'cumulative_planned_quantity': fields.Integer
                                                                            }})
plan_target_get_model=prod_plan_api_route.model('plan_target_get_model', {**plan_target_fields,
                                                                           'product_id': fields.Integer,
                                                                           'product_name': fields.String,
                                                                           'product_code': fields.String
                                                                           })
hourly_target_get_model=prod_plan_api_route.model('hourly_target_get_model', {**hourly_target_fields,
                                                                              **{
                                                                                  "stage_name":fields.String,
                                                                                  "rank_id":fields.String,
                                                                                  'product_id': fields.Integer,
                                                                                  'product_name': fields.String,
                                                                                  'product_code': fields.String
                                                                              }})
# hourly_target_respnse_model=prod_plan_api_route.model('hourly_target_respnse_model',{
#     "hourly_target":fields.List(fields.Nested(hourly_target_get_model))
# })
prod_plan_get_model=prod_plan_api_route.model('prod_plan_get_model',{

    **prod_plan_fields,
    "is_rawmaterials_received":fields.Boolean,
    **plan_deltailed_model,
    **{"product_name":fields.String,
       "floor_id":fields.String,
       "floor_name":fields.String,
       "sku_id":fields.String,
       "uom":fields.String,
       "product_code":fields.String,
       "is_serializable":fields.Boolean,
       "serialization_params":fields.Raw},
    "targets": fields.List(fields.Nested(plan_target_get_model)),
    "details": fields.List(fields.Nested(plan_details_get_model)),
    "hourly_target": fields.List(fields.Nested(hourly_target_get_model))
})

prod_plan_list_response=prod_plan_api_route.model('prod_plan_list_response',
                                                  { **list_response_model,
                                                  **{"results":fields.List(fields.Nested(prod_plan_get_model))}}
                                                  )

prod_plan_report = prod_plan_api_route.model('report model', report_fields)

report_response = prod_plan_api_route.model('plan_list_report', {
    **list_response_model,
    'results': fields.List(fields.Nested(prod_plan_report))
})

moved_quantity_model = prod_plan_api_route.model('moved quantity Model', moved_quantity)

plan_stock_model = prod_plan_api_route.model('plan stock model', plan_stock)

plan_stock_list_response = prod_plan_api_route.model('plan stock list response', {
    **list_response_model,
    'results': fields.List(fields.Nested(plan_stock_model))
})

plan_to_outward_model = prod_plan_api_route.model('plan to outward model', {
                                                  "production_plan_id": fields.Integer,
                                                    "plan_unique": fields.String,
    'product_id': fields.Integer,
    'product_name': fields.String,
    'product_code': fields.String,
    'sku_id': fields.String,
    'status': fields.String,
    'sum': fields.String
})

plan_to_outward_list_response = prod_plan_api_route.model('plan to outward list response', {
    **list_response_model,
    'results': fields.List(fields.Nested(plan_to_outward_model))
})

plan_date_outward = {
    'product_id': fields.Integer,
    'product_name': fields.String,
    'product_code': fields.String,
    'sku_id': fields.String,
    'uom': fields.String,
    'details': fields.Raw
}

style_plan_outward = prod_plan_api_route.model('style plan outward', {
    'category_id': fields.Integer,
    'category_name': fields.String,
    'products': fields.Raw
})

plan_date_outward_model = prod_plan_api_route.model('plan date outward model', plan_date_outward)

plan_date_outward_list_response = prod_plan_api_route.model('plan date outward list response', {
    **list_response_model,
    'results': fields.List(fields.Nested(plan_date_outward_model))
})

style_plan_outward_list_response = prod_plan_api_route.model('style plan outward list response', {
    **list_response_model,
    'results': fields.List(fields.Nested(style_plan_outward))
})

plan_datewise_outward_model = prod_plan_api_route.model('plan datewise outward model', plan_datewise_outward)

plan_datewise_list_response = prod_plan_api_route.model('plan datewise list response', {
    **list_response_model,
    'results': fields.List(fields.Nested(plan_datewise_outward_model))
})

prod_plan_get_all_model = prod_plan_api_route.model('prod_plan_get_all_model', {**{
'is_rawmaterials_received':fields.Boolean,
    'details': fields.Raw
},
    **prod_plan_fields})

prod_plan_get_all_list_response = prod_plan_api_route.model('prod_plan_get_all_list_response', {
    **list_response_model,
    'results': fields.List(fields.Nested(prod_plan_get_all_model))
})

fg_report_model = prod_plan_api_route.model('fg_report_model', {
    "customer_purchase_id": fields.Integer,
    "order_unique": fields.String,
    'data': fields.Raw
})

fg_cost_report_list_response = prod_plan_api_route.model('fg_cost_report_list_response', {
    **list_response_model,
    'results': fields.List(fields.Nested(fg_report_model))
})

plan_wise_outward_get_model = prod_plan_api_route.model('plan_wise_outward_get_model', plan_wise_outward)

plan_wise_outward_resposne_model = prod_plan_api_route.model('plan_wise_outward_resposne_model', {
    **list_response_model,
    'results': fields.List(fields.Nested(plan_wise_outward_get_model))
})

production_plan_cost_model = prod_plan_api_route.model('production_plan_cost_model', production_plan_cost)

production_plan_cost_model_list_response = prod_plan_api_route.model('production_plan_cost_model_list_response', {
    **list_response_model,
    'results': fields.List(fields.Nested(production_plan_cost_model))
})


plan_to_store_model = prod_plan_api_route.model('plan_to_store_model', plan_to_store)

plan_to_store_response_model = prod_plan_api_route.model('plan_to_store_response_model', {
    **list_response_model,
    'results': fields.List(fields.Nested(plan_to_store_model))
})
