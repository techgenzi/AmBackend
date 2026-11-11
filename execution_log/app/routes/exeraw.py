from flask_restx import Namespace
from flask_restx import fields
from ipss_utils.ipss_api_doc import create_record_response

from ..api_doc import list_response
from ..api_doc import exeraw_fields, execution_log_fields, report_rawmat, execution_report_fields

execution_log_api_route = Namespace('execution_log', path='/execution_log/rawmaterials')

exeraw_model=execution_log_api_route.model('exeraw_model',exeraw_fields)

serialized_unit_model = execution_log_api_route.model('serialized_unit_model', {
    "*": fields.Raw(description="Dynamic unit-level parameters (e.g., serial_number, Voltage, Watts, etc.)")
})

execution_model_rawmaterials=execution_log_api_route.model('execution_model_rawmaterials',{
    **execution_log_fields,
    "captured_parameters":fields.List(fields.Nested(exeraw_model)),
    "serialized_units": fields.List(fields.Nested(serialized_unit_model))
})
execution_model_rawmaterials_bulk=execution_log_api_route.model('execution_model_rawmaterials_bulk',{
    "data":fields.List(fields.Nested(execution_model_rawmaterials))
})

create_execution_log_response = execution_log_api_route.model('create_execution_logs_response', create_record_response)

#################################
exec_raw_model=execution_log_api_route.model('exec_raw_model',report_rawmat)
execution_nested_raw_model=execution_log_api_route.model('execution_nested_raw_model',{
    **execution_report_fields,
"machine_id":fields.Integer,
                      "activity_id":fields.Integer,
    "machine_name":fields.String,
    "activity_name":fields.String,
    "captured_parameters":fields.List(fields.Nested(exec_raw_model))
})
list_exec_report_response=execution_log_api_route.model('list_exec_report_response',
                                                        {**list_response,
                    "data":fields.List(fields.Nested(execution_nested_raw_model))})
