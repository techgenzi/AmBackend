from flask_restx import Namespace, Resource, fields
# from ..api_doc import invRegistryFields, return_header, return_post, return_get,
from ..api_doc import return_data, return_amount, dispatch_drop_down, return_post, report, report_data
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

return_api_route = Namespace('ReturnMaterial', path='/am-returnMaterial')

return_data_model = return_api_route.model('return_data_model', {**return_data,
                                                                 "uom":fields.String,
                                                                 'uom_id': fields.Integer})

return_model = return_api_route.model('inventoryBulk_model',{
    **return_amount,
    'data': fields.List(fields.Nested(return_data_model))
})


return_list_response = return_api_route.model('inventoryRegistry_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(return_model))
    }
})

dispatch_drop_get_model = return_api_route.model('dipatch_drop_down_get', dispatch_drop_down)

dispatch_drop_get_list = return_api_route.model('dispatch_drop_down', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(dispatch_drop_get_model))
    }
})
post_model = return_api_route.model('post_model', return_post)
retrurn_post_model = return_api_route.model('return_post_model',{
    'data':fields.List(fields.Nested(post_model))
})
post_reponse = return_api_route.model('post_response', create_record_response)

report_data_model = return_api_route.model('report_data_model', {**report_data,"uom":fields.String})
single_get_report = return_api_route.model('single_report_get',
                                           {
                                               **report,
                                               'data': fields.List(fields.Nested(report_data_model))
                                           })

report_list_response = return_api_route.model('report_list_response',{
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(single_get_report))
    }
})
##############################################

