from flask_restx import fields 
uom_fields={
"id": fields.Integer,
 "uom": fields.String,
 "description": fields.String,
"created_by": fields.String,
"deleted": fields.String
}




search_filters={
  'id': {
   "type": int,
   "description": "Search by floor_id"
  }
 }
