from flask_restx import Namespace, Resource, fields
from ..floor_stage_api_doc import floor_fields, stages
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model

# Initialize API routes

floor_stage_api_route = Namespace('floor_stage', path='/am-floor_stage_config')

single_satge_model = floor_stage_api_route.model('stages_model', stages)

single_floor_stage_model = floor_stage_api_route.model('get floor_satge model',{
    **floor_fields,
    'stages': fields.List(fields.Nested(single_satge_model))
})

create_floor_stage_response = floor_stage_api_route.model('create_floor_stage_response', create_record_response)
stage = {
    'stage_id': fields.Integer
}

satges_model = floor_stage_api_route.model('stages_model', stage)
floor_stage_post = floor_stage_api_route.model('post_model',{
    **{'floor_id':fields.Integer},
    'stages': fields.List(fields.Nested(satges_model))
})
floor_stage_list_response = floor_stage_api_route.model('floor_stage_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(single_floor_stage_model))
    }
})

# Update user record
update_floor_stage_model = single_floor_stage_model
update_floor_stage_response = floor_stage_api_route.model('update_floor_stage_response', update_record_response)

