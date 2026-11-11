from flask_restx import Namespace, Resource, fields
from ..line_process_api_doc import line_process, process_field, stage_field
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

line_process_api_route = Namespace('line_process', path='/line')

line_process_get_model = line_process_api_route.model('line_map_data_model', process_field)

line_stage_model = line_process_api_route.model('line Stage', {
    **{
        'stage_id': fields.Integer,
        'stage_name': fields.String
    },
    'process': fields.List(fields.Nested(line_process_get_model))
})
line_get_model = line_process_api_route.model('inventoryBulk_model',{
    **line_process,
    'stages': fields.List(fields.Nested(line_stage_model))
})


line_process_list_response = line_process_api_route.model('inventoryRegistry_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(line_get_model))
    }
})

post = line_process_api_route.model('post_model', line_process)

post_model = line_process_api_route.model('multiple post model', {
    'data':  fields.List(fields.Nested(post))
})


create_record_response_model = line_process_api_route.model('post response model', create_record_response)

process_model = line_process_api_route.model('process Model', process_field)

stage_model = line_process_api_route.model('stage_model', {
    **stage_field,
    'process': fields.List(fields.Nested(process_model))
})

line_stage_process_model = line_process_api_route.model('line stage process model', {
    **line_process,
    'stages': fields.List(fields.Nested(stage_model))
})

##############################################

