from flask_restx import Namespace, Resource, fields
from ..api_doc import line_map, line_get, line_get_list
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

line_map_api_route = Namespace('line_map', path='/line')

line_get_model = line_map_api_route.model('line_map_data_model', line_get_list)


line_get_model = line_map_api_route.model('inventoryBulk_model',{
    **line_get,
    'data': fields.List(fields.Nested(line_get_model))
})


line_map_list_response = line_map_api_route.model('inventoryRegistry_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(line_get_model))
    }
})

post = line_map_api_route.model('post_model', line_map)

post_model = line_map_api_route.model('multiple post model', {
    'data':  fields.List(fields.Nested(post))
})


create_record_response_model = line_map_api_route.model('post response model', create_record_response)
##############################################

