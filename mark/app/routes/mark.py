from flask_restx import Namespace, Resource, fields
from ..api_doc import mark, mark_line, mark_report
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

mark_api_route = Namespace('AM mark', path='/am-mark')


mark_model = mark_api_route.model('mark_model', mark)

mark_line_model = mark_api_route.model('mark line model', {**mark_line,
                                                           **{"product_name": fields.String,
                                                              "product_code": fields.String,
                                                              "sku_id": fields.String}
                                                           })

mark_update_model=mark_api_route.model('mark_update_model',mark_line)
nested_mark_update_model=mark_api_route.model('nested_mark_update_model',{
    "data":fields.List(fields.Nested(mark_update_model))
})

mark_list_model = mark_api_route.model('mark list response model', {
    **mark_model,
    **{"product_name":fields.String,
       "product_code":fields.String,
       "sku_id":fields.String},
    'data': fields.List(fields.Nested(mark_line_model))
})

mark_list_response = mark_api_route.model('mark list model', {
    **list_response_model,
    'results': fields.List(fields.Nested(mark_list_model))
})

create_record_response_model = mark_api_route.model('post response model', create_record_response)

mark_report_model = mark_api_route.model('mark report', mark_report)

mark_report_list_response = mark_api_route.model('mark report list model', {
    **list_response_model,
    'results': fields.List(fields.Nested(mark_report_model))
})


