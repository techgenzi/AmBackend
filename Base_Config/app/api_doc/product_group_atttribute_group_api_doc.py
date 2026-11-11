from flask_restx import fields 
product_group_attributes_group_fields={
 "product_group_attributes_group_id": fields.Integer,
 "product_group_id": fields.Integer,
 "attribute_group_id": fields.Integer,
 "is_required": fields.Boolean,
 "display_order": fields.Integer
}

search_filters={
 'attribute_group_id':{
  'type':int,
  "description":"Search by attribute_group_id"
 },
 'product_group_id': {
  'type': int,
  "description": "Search by product_group_id"
 },
 'product_group_attributes_group_id': {
  'type': int,
  "description": "Search by product_group_attributes_group_id"
 }
}