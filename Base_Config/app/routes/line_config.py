from flask_restx import Namespace, fields
from ipss_utils.ipss_api_doc import list_response_model, create_record_response, update_record_response

from ..api_doc.line_config import line_config_fields

line_config_api_route = Namespace('Line configuration', path='/baseConfig/line-config')

line_config_model = line_config_api_route.model('Line config model', line_config_fields)

line_config_list_response = line_config_api_route.model('Line config list response', {
    **list_response_model,
    'results': fields.List(fields.Nested(line_config_model))
})

# Create Line Configuration model

create_line_config_model = line_config_api_route.model('Create Line model', line_config_model)
create_line_config_response = line_config_api_route.model('Create Line response', create_record_response)

# Get Line config records model
get_line_config_response = line_config_api_route.model('Get Line response', line_config_model)

# Update Line configure record model
update_line_config_model = line_config_api_route.model('Update Line model',
                                                             line_config_model)
update_line_config_response = line_config_api_route.model('Update Line response',
                                                                update_record_response)