from flask_restx import fields

bom_config_fields={
    "bom_config_id": fields.Integer,
    "maper_id": fields.List(fields.Integer),
    "mapping_id": fields.List(fields.Integer),
    "child_id": fields.List(fields.Integer),
    "map_type": fields.String
}


search_filters={
  'bom_config_id':{
   "type": int,
   "description": "Search by stage_id"
  },
'type':{
   "type": str,
   "description": "Search by type"
  }
 }