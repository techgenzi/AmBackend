from flask_restx import Namespace, fields
from ..api_doc import employee_line, line_model, delete, employee_report_field
from ipss_utils.ipss_api_doc import create_record_response, list_response_model


employee_line_api_route = Namespace('employee_line_map', path='/line')

employee_line_model = employee_line_api_route.model('post model', employee_line)

employee_lineitems_model = employee_line_api_route.model('line model', line_model)
employee_response = employee_line_api_route.model('list response', {
    'line_name': fields.String,
    'data': fields.List(fields.Nested(employee_lineitems_model))
})

employee_list_response = employee_line_api_route.model('get list response', {
    **list_response_model,
    'results': fields.List(fields.Nested(employee_response))
})

employee_model = employee_line_api_route.model('employee model', employee_line)
employee_response = employee_line_api_route.model('', {
    **list_response_model,
    'results': fields.List(fields.Nested(employee_model))
})
employee_post_model = employee_line_api_route.model('post Model', {
    'data': fields.List(fields.Nested(employee_line_model))
})

create_record_response_model = employee_line_api_route.model('create record', create_record_response)

delete_model = employee_line_api_route.model('delete Model', delete)

employee_report_model = employee_line_api_route.model('employee_report_field', employee_report_field)

employee_resport_list = employee_line_api_route.model('', {
    **list_response_model,
    'results': fields.List(fields.Nested(employee_report_model))
})





