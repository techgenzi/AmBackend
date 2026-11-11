from flask_restx import fields



style_fields ={
    "style_id": fields.Integer,
    "style_code": fields.String,
    "description": fields.String,
    'allowed_wastage': fields.String,
    'attribute_id': fields.Integer,
    'attribute_name': fields.String,
    "created_by": fields.String,
    "deleted": fields.String
}


search_filters={
  'id': {
   "type": int,
   "description": "Search by floor_id"
  }
 }

style_product_fields = {
    "style_id": fields.Integer,
    'style_code': fields.String,
    'data': fields.Raw
}

style_product_bulk_post_fields = {
    'data': fields.List(fields.Nested(style_product_fields))
}