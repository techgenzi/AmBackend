from flask_restx import fields



category_fields ={
    "category_id": fields.Integer,
    "category_name": fields.String,
    "created_by": fields.String,
    "deleted": fields.String
}


search_filters={
  'category_id': {
   "type": int,
   "description": "Search by category_id"
  }
 }

style_category_fields = {
    "category_id": fields.Integer,
    'category_name': fields.String,
    'data': fields.Raw
}

# style_category_bulk_post_fields = {
#     'data': fields.List(fields.Nested(style_category_fields))
# }