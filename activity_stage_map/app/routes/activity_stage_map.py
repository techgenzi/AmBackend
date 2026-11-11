from flask_restx import Namespace, Resource, fields
from ..api_doc import activity_stage_map_fields, sub_data, product_data
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

activity_stage_map_api_route = Namespace('activity_stage_map', path='/activity_stage_map')

# List activity_stage_maps API docs
activity_stage_map_model = activity_stage_map_api_route.model('activity_stage_maps_model', {
            **activity_stage_map_fields,
            "product_id":fields.Integer,
            "product_code":fields.String,
            "product_name":fields.String,
            "sku_id":fields.String,
            "config_name":fields.String,
            "stage_name":fields.String,
            "stage_id":fields.String,
            "compcode": fields.Integer,
            "created_on": fields.String,
            "modified_on": fields.String,
            "modified_by": fields.String,
            "deleted_at": fields.String,
            "deleted": fields.Boolean
        })

activity_stage_map_list_response = activity_stage_map_api_route.model('activity_stage_maps_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(activity_stage_map_model))
    }
})


create_activity_stage_map_model = activity_stage_map_api_route.model('create_activity_stage_maps_model', activity_stage_map_fields)
bulk_create_activity_stage_map_model=activity_stage_map_api_route.model('bulk_create_activity_stage_map_model',
                                    {"data":fields.List(fields.Nested(create_activity_stage_map_model))})
create_activity_stage_map_response = activity_stage_map_api_route.model('create_activity_stage_maps_response', create_record_response)

# Get activity_stage_maps records model
# get_activity_stage_map_response = activity_stage_map_api_route.model('get_activity_stage_maps_response', activity_stage_map_fields)

# Update user record
update_activity_stage_map_response = activity_stage_map_api_route.model('update_activity_stage_maps_response', update_record_response)

##############
sub_data_model=activity_stage_map_api_route.model('sub_data_model',sub_data)
product_model=activity_stage_map_api_route.model('product_model',{
    **product_data,
    "stage_data":fields.List(fields.Nested(sub_data_model))
})
nested_product_model=activity_stage_map_api_route.model('nested_product_model',{
    **list_response_model,
    "results":fields.List(fields.Nested(product_model))
})
    
