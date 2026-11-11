
from flask_restx import Namespace, Resource, fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model
from ..api_doc import delivery_fields, workOrderItems, report_fields, report_line

delivery_api_route = Namespace('delivery Api', path='/am-delivery')

items_model = delivery_api_route.model('items_model', workOrderItems)

delivery_post_model = delivery_api_route.model('job_order_fields', {
            'items': fields.List(fields.Nested(items_model)),
            **delivery_fields,
            'deleted': fields.Boolean,
            'created_on': fields.String,
            'modified_on': fields.String
        })


delivery_get_model = delivery_api_route.model('delivery_fields', {
            **delivery_fields,
            'deleted': fields.Boolean,
            'created_on': fields.String,
            'modified_on': fields.String
        })

delivery_get_all_model = delivery_api_route.model('delivery_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(delivery_post_model))
    }
})

create_delivery_response = delivery_api_route.model('create_job_order_response', create_record_response)

update_delivery_response = delivery_api_route.model('update_job_order_response', update_record_response)

report_line_model = delivery_api_route.model('report line model', report_line)

report_model = delivery_api_route.model('report model', {
    **report_fields,
    'data': fields.List(fields.Nested(report_line_model))
})

delivery_report_list = delivery_api_route.model(' list_response_report', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(report_model))
    }
})



