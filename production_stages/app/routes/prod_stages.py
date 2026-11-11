from flask_restx import Namespace, Resource, fields
from ..api_doc import prod_stages_fields, det_fields, activities
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes

prod_stages_api_route = Namespace('prod_stages', path='/am-prod_stages')

# List prod_stagess API docs
det_model = prod_stages_api_route.model('prod_stagess_model', {
            **prod_stages_fields
        })
activities_model=prod_stages_api_route.model('activities_model',activities)

stages_mode=prod_stages_api_route.model('stages_mode', {**det_fields,
                                "activities":fields.List(fields.Nested(activities_model))})

prod_stages_model=prod_stages_api_route.model('det_model',{
    **{'product_id': fields.Integer,
       'product_code': fields.String,
       "sku_id":fields.String,
       'product_name': fields.String},
        "stages":fields.List(fields.Nested(stages_mode))
})

prod_stages_list_response = prod_stages_api_route.model('prod_stagess_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(prod_stages_model))
    }
})
# bulk_post=prod_stages_api_route.model("bulk_post",{
#     "data":fields.List(fields.Nested(prod_stages_model))
# })

create_prod_stages_model = prod_stages_api_route.model('create_prod_stagess_model', prod_stages_model)
create_prod_stages_response = prod_stages_api_route.model('create_prod_stagess_response', create_record_response)

# Get prod_stagess records model
get_prod_stages_response = prod_stages_api_route.model('get_prod_stagess_response', prod_stages_fields)

# Update user record
update_prod_stages_fields = prod_stages_fields
update_prod_stages_model = prod_stages_api_route.model('update_prod_stagess_model', update_prod_stages_fields)
update_prod_stages_response = prod_stages_api_route.model('update_prod_stagess_response', update_record_response)



########################
config_model=prod_stages_api_route.model('configs',{'id':fields.String,
                                       "stage_name":fields.String})
config_resposne=prod_stages_api_route.model("",{**list_response_model,
    **{
        'results': fields.List(fields.Nested(config_model))
    }
})

    
