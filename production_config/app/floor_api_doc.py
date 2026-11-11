from flask_restx import fields 
floor_fields={
"floor_id": fields.Integer,
 "floor_name": fields.String,
 "description": fields.String,
"created_by": fields.String,
"deleted": fields.String
}




search_filters={
  'floor_id':{
   "type": int,
   "description": "Search by floor_id"
  }
 }
