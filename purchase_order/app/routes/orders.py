from flask_restx import Namespace, Resource, fields
from ..api_doc import job_dc_order_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

job_dc_order_api_route = Namespace('job_dc_order', path='/job_dc_order')

# List job_dc_orders API docs
job_dc_order_model = job_dc_order_api_route.model('job_dc_orders_model', {
            **job_dc_order_fields
        })

job_dc_order_list_response = job_dc_order_api_route.model('job_dc_orders_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(job_dc_order_model))
    }
})


create_job_dc_order_model = job_dc_order_api_route.model('create_job_dc_orders_model', job_dc_order_model)
create_job_dc_order_response = job_dc_order_api_route.model('create_job_dc_orders_response', create_record_response)

# Get job_dc_orders records model
get_job_dc_order_response = job_dc_order_api_route.model('get_job_dc_orders_response', job_dc_order_fields)

# Update user record
update_job_dc_order_fields = job_dc_order_fields
update_job_dc_order_model = job_dc_order_api_route.model('update_job_dc_orders_model', update_job_dc_order_fields)
update_job_dc_order_response = job_dc_order_api_route.model('update_job_dc_orders_response', update_record_response)
    
