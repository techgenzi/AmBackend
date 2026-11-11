from flask_restx import Namespace, Resource, fields

from ..stage_api_doc import satge_fields, params_config_fields, stage_param_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model

# Initialize API routes

stage_api_route = Namespace('stage', path='/production_config/stage')

single_stage_model = stage_api_route.model('create_stage_model', satge_fields)

create_stage_response = stage_api_route.model('create_stage_response', create_record_response)

stage_list_response = stage_api_route.model('stage_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(single_stage_model))
    }
})

# Update user record
update_stage_fields = satge_fields
update_stage_model = stage_api_route.model('update_stage_model', update_stage_fields)
update_stage_response = stage_api_route.model('update_stage_response', update_record_response)

######################
param_config_model=stage_api_route.model('param_config_model',params_config_fields)
param_config_post_model=stage_api_route.model('param_config_post_model',{
    "data":fields.List(fields.Nested(param_config_model))
})
param_config_list_response_model=stage_api_route.model('param_config_list_response_model',{
    **list_response_model,
    **{"results":fields.List(fields.Nested(param_config_model))}
})
#######################

param_config_stage_model=stage_api_route.model('param_config_stage_model',stage_param_fields)
param_config_stage_model_main=stage_api_route.model('param_config_stage_model_main',{
    **{"stage_id":fields.Integer,
       "stage_name":fields.String},
    "params_data":fields.List(fields.Nested(param_config_stage_model))
})
param_config_stage_post_model=stage_api_route.model('param_config_stage_post_model',{
    "data":fields.List(fields.Nested(param_config_stage_model_main))
})

param_stage_model_get=stage_api_route.model('param_stage_model_get',{**stage_param_fields,
                                                                     **{"parameter_name":fields.String,
                                                                        "parameter_type":fields.String,
                                                                        "stage_name":fields.String
                                                                        }})
param_config_stage_model_get_main=stage_api_route.model('param_config_stage_model_get_main',{
    **{"stage_id":fields.Integer,
       "stage_name":fields.String,
       "is_serialization":fields.Boolean},
    "params_data":fields.List(fields.Nested(param_stage_model_get)),
    "serialization_params": fields.List(fields.Nested(param_stage_model_get))
})
param_config_stage_list_response_model=stage_api_route.model('param_config_stage_list_response_model',{
    **list_response_model,
    **{"results":fields.List(fields.Nested(param_config_stage_model_get_main))}
})



