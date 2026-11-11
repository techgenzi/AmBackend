from flask_restx import fields

satge_fields={
"stage_id": fields.Integer,
"stage_name": fields.String,
"description": fields.String,
"created_by": fields.String,
"is_serialization": fields.Boolean,
"deleted": fields.String,
"serialization_params": fields.List(fields.Raw)
}


search_filters={
  'stage_id':{
   "type": int,
   "description": "Search by stage_id"
  }
 }


params_config_fields={
"parameter_id":fields.Integer,
"parameter_name":fields.String,
"parameter_type":fields.String,
"description":fields.String,
"additional":fields.Raw
}

params_filters={
  'parameter_id':{
   "type": int,
   "description": "Search by parameter_id"
  },
    'parameter_type':{
        "type": str,
        "description": "Search by parameter_type"
    },
    "stage_id":{
"type": int,
        "description": "Search by stage_id"
},
    "stage_param_id":{
"type": int,
        "description": "Search by stage_param_id"
    }
 }

stage_param_fields={
"stage_param_id":fields.Integer,
    "stage_id":fields.Integer,
    "is_eval":fields.Boolean,
    "parameter_id":fields.Integer,
    "stage_param_value":fields.String,
    "description":fields.String,
    "additional":fields.Raw
}

stage_param_filters={
    'stage_param_id': {
        "type": int,
        "description": "Search by stage_param_id"
    },
    'stage_id': {
        "type": int,
        "description": "Search by stage_id"
    },
    **params_filters
}

