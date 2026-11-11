from flask_restx import Namespace, Resource, fields
from ..api_doc import labour, labour_cost_response
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

labour_api_route = Namespace('AM Labour', path='/am-labour')


labour_model = labour_api_route.model('labour_model', labour)

labour_list_response = labour_api_route.model('labour list model', {
    **list_response_model,
    'results': fields.List(fields.Nested(labour_model))
})


create_record_response_model = labour_api_route.model('post response model', create_record_response)


labour_cost_model = labour_api_route.model('labour_cost_model', labour_cost_response)

labour_cost_list_response = labour_api_route.model('labour_cost list model', {
    **list_response_model,
    'results': fields.List(fields.Nested(labour_cost_model))
})