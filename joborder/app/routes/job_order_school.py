
from flask_restx import Namespace, Resource, fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model
from ..api_doc import job_order_fields, items, product_price, amendment_log

job_order_api_route = Namespace('Job Order Api', path='/am-job_order')


items_model = job_order_api_route.model('items_model', {**items,"uom":fields.String})

# List skills API docs
job_order_model = job_order_api_route.model('job_order_model', {
            'items': fields.List(fields.Nested(items_model)),
            **job_order_fields,
            'gstno': fields.String,
            'bill_addline1': fields.String,
            'is_amendment': fields.Boolean,
            'deleted': fields.Boolean,
            'created_on': fields.String,
            'modified_on': fields.String
        })

job_order_report_model = job_order_api_route.model('job_order_report_model', {
    **list_response_model,
    'results': fields.List(fields.Nested(job_order_model))
})

job_order_get_model = job_order_api_route.model('job_order_fields', {
            **job_order_fields,
            'deleted': fields.Boolean,
            'created_on': fields.String,
            'modified_on': fields.String
        })

job_order_get_all_model = job_order_api_route.model('job_order_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(job_order_get_model))
    }
})

# Create skill model
create_job_order_model = job_order_api_route.model('create_skill', job_order_model)
create_job_order_response = job_order_api_route.model('create_job_order_response', create_record_response)

# Get skill records model
get_job_order_response = job_order_api_route.model('get_job_order_response', job_order_model)


# Update user record
update_job_order_fields = job_order_fields
update_job_order_model = job_order_api_route.model('update_skill', update_job_order_fields)

update_job_order_response = job_order_api_route.model('update_job_order_response', update_record_response)

product_price_model = job_order_api_route.model('product_price_model', product_price)

product_price_list_response = job_order_api_route.model('product_price_list_response', {
    **list_response_model,
    'results': fields.List(fields.Nested(product_price_model))
})

amendment_log_model = job_order_api_route.model('amendment_log_model', amendment_log)

amendment_log_response = job_order_api_route.model('amendment_log_resposne', {
    **list_response_model,
    'results': fields.List(fields.Nested(amendment_log_model))
})

