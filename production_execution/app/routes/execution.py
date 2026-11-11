from flask_restx import Namespace, Resource, fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model

from ..api_doc import prod_exe_fields

# Initialize API routes

prod_exe_api_route = Namespace('prod_exe', path='/am-prod_exe')

# List prod_exes API docs
prod_exe_model = prod_exe_api_route.model('prod_exes_model', {
    **prod_exe_fields,**{"product_code":fields.String,
                         "rank_id":fields.Integer,
                         # "product_name":fields.String,
                         "attributes":fields.Raw,
                         }
})

prod_exe_list_response = prod_exe_api_route.model('prod_exes_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(prod_exe_model))
    }
})
bulk_data_post = prod_exe_api_route.model('bulk_data', {
    "data": fields.List(fields.Nested(prod_exe_model))})

create_prod_exe_model = prod_exe_api_route.model('create_prod_exes_model', prod_exe_model)
create_prod_exe_response = prod_exe_api_route.model('create_prod_exes_response', create_record_response)

# Get prod_exes records model
get_prod_exe_response = prod_exe_api_route.model('get_prod_exes_response', prod_exe_fields)

# Update user record
update_prod_exe_fields = prod_exe_fields
update_prod_exe_model = prod_exe_api_route.model('update_prod_exes_model', update_prod_exe_fields)
update_prod_exe_response = prod_exe_api_route.model('update_prod_exes_response', update_record_response)
#######################

data_move_model = prod_exe_api_route.model('data_move_model', {
    "id": fields.String,
    "prod_plan_id": fields.String,
    "product_id":fields.String,
    # "rank_id":fields.Integer,
    "stage_id": fields.String,
    "inward_qty": fields.String,
    "wastage": fields.String,
    "outward_qty": fields.String,
    "opertaion_date": fields.String,
})
