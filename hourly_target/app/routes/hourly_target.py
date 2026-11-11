from flask_restx import Namespace, Resource, fields
from ..api_doc import hourly_target_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

hourly_target_api_route = Namespace('hourly_target', path='/hourly_target')

# List hourly_targets API docs
hourly_target_model = hourly_target_api_route.model('hourly_targets_model', {
            **hourly_target_fields,**{ "compcode": fields.Integer,
                                       "doc_id":fields.String,
                                       "plan_unique":fields.String,
 "created_on": fields.String,
 "modified_on": fields.String,
 "modified_by": fields.String,
 "deleted_at": fields.String,
 "deleted": fields.Boolean}
        })

hourly_target_list_response = hourly_target_api_route.model('hourly_targets_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(hourly_target_model))
    }
})


create_hourly_target_model = hourly_target_api_route.model('create_hourly_targets_model', hourly_target_fields)
bulk_hourly_model=hourly_target_api_route.model('bulk_hourly_model',{
    "data":fields.List(fields.Nested(create_hourly_target_model))
})
create_hourly_target_response = hourly_target_api_route.model('create_hourly_targets_response', create_record_response)

# Get hourly_targets records model
get_hourly_target_response = hourly_target_api_route.model('get_hourly_targets_response', hourly_target_fields)

# Update user record
update_hourly_target_fields = hourly_target_fields
update_hourly_target_model = hourly_target_api_route.model('update_hourly_targets_model', update_hourly_target_fields)
update_hourly_target_response = hourly_target_api_route.model('update_hourly_targets_response', update_record_response)
    
