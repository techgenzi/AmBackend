from flask_restx import fields

floor_fields = {
    "floor_id": fields.Integer,
    'floor_name': fields.String
}

stages = {
    "floor_stage_id": fields.Integer,
    "stage_id": fields.Integer,
    'stage_name': fields.String
}

search_filters={
  'floor_stage_id':{
   "type": int,
   "description": "Search by floor_stage_id"
  },
'floor_id':{
   "type": int,
   "description": "Search by floor_id"
  },
'stage_id':{
   "type": int,
   "description": "Search by stage_id"
  }
 }