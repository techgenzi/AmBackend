from flask_restx import Namespace, fields
from ipss_utils.ipss_api_doc import list_response_model, create_record_response, update_record_response

from ..api_doc.hour_config import hour_fields
line_config_api_route = Namespace('Hour configuration', path='/baseConfig/hour-config')
hours_data_model=line_config_api_route.model('hours_data_model',hour_fields)
bulk_post_hour_model=line_config_api_route.model('bulk_post_hour_model',{
    "data":fields.List(fields.Nested(hours_data_model))
})
list_response_model=line_config_api_route.model('list_response_model',{
    **list_response_model,
    "results":fields.List(fields.Nested(hours_data_model))
})

create_record_response_data=line_config_api_route.model('create_record_response_data',create_record_response)
update_line_config_response = line_config_api_route.model('Update Line response',
                                                                update_record_response)
