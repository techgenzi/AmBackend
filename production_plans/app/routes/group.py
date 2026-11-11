from flask_restx import Namespace, fields

from ..api_doc import plan_target_fields, plan_details_fields, prod_plan_fields, hourly_target_fields, report_fields, \
    moved_quantity, plan_stock
from ipss_utils.ipss_api_doc import list_response_model


group_api_route = Namespace('group_report', path='/am-prod_plans/report_group')
