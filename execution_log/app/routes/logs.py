from flask_restx import Namespace, Resource, fields
from ..api_doc import execution_log_fields, execution_capture_fields, report_fields, employe_report, head_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

execution_log_api_route = Namespace('execution_log', path='/execution_log')

# List execution_logs API docs
execution_log_model = execution_log_api_route.model('execution_logs_model', {
            **execution_log_fields,**{"plan_unique":fields.String,
                                      "emp_name":fields.String,
                                      'line_name': fields.String,
                                      "stage_name":fields.String,
                                      "config_name":fields.String,
                                      "job_order_no": fields.String,
                                      "vendor_name": fields.String}
        })

execution_log_list_response = execution_log_api_route.model('execution_logs_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(execution_log_model))
    }
})


create_execution_log_model = execution_log_api_route.model('create_execution_logs_model', execution_log_model)
bulk_post_log_model=execution_log_api_route.model('bulk_post_log_model',{
    "data":fields.List(fields.Nested(create_execution_log_model))})
create_execution_log_response = execution_log_api_route.model('create_execution_logs_response', create_record_response)

# Get execution_logs records model
get_execution_log_response = execution_log_api_route.model('get_execution_logs_response', execution_log_fields)

# Update user record
update_execution_log_fields = execution_log_fields
update_execution_log_model = execution_log_api_route.model('update_execution_logs_model', update_execution_log_fields)
update_execution_log_response = execution_log_api_route.model('update_execution_logs_response', update_record_response)
bulk_update=execution_log_api_route.model('bulk_update',{
    "data":fields.List(fields.Nested(update_execution_log_model))
})
############################################

param_config_stage_model=execution_log_api_route.model('param_config_stage_model',execution_capture_fields)
param_config_stage_post_model=execution_log_api_route.model('param_config_stage_post_model',{
    "data":fields.List(fields.Nested(param_config_stage_model))
})

param_stage_model_get=execution_log_api_route.model('param_stage_model_get',{**execution_capture_fields,
                                                                     **{"parameter_name":fields.String,
                                                                        "parameter_type":fields.String,
                                                                        "stage_name":fields.String
                                                                        }})

param_config_stage_list_response_model=execution_log_api_route.model('param_config_stage_list_response_model',{
    **list_response_model,
    **{"results":fields.List(fields.Nested(param_stage_model_get))}
})
#######################################
capture_report_model=execution_log_api_route.model('capture_report_model',report_fields)
capture_report_model_response=execution_log_api_route.model('capture_report_model_response',{
    **list_response_model,
    **{"results":fields.List(fields.Nested(capture_report_model))}
})

##############################
employee_report_model=execution_log_api_route.model('employee_report_model',employe_report)
employee_report_model_response=execution_log_api_route.model('employee_report_model_response',{
                                                             # **list_response_model,
    **head_fields,
                                                             "products":fields.List(fields.Nested(employee_report_model))})
nested_head_fields_model=execution_log_api_route.model('nested_head_fields_model',{
    **list_response_model,
    "results":fields.List(fields.Nested(employee_report_model_response))
})