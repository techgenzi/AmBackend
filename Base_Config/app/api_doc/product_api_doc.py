from flask_restx import fields
from flask_restx.fields import List

products_fields={
"product_id": fields.Integer,
 "product_group_id": fields.Integer,
 "product_code": fields.String,
 "product_name": fields.String,
"product_count": fields.Integer,
"cost": fields.Integer,
'effective_date': fields.String,
"sku_id": fields.String,
 "description": fields.String,
"type":fields.String,
 "is_configurable": fields.Boolean,
 "is_active": fields.Boolean,
 "base_uom": fields.String,
    "is_serializable": fields.Boolean,
    "serialization_params": fields.List(fields.Raw),
    "deleted": fields.String
}


product_variant_fields={
 "product_variant_id": fields.Integer,
 "product_id": fields.Integer,
"variant_value_id": fields.Integer,
 "sku": fields.String,
 # "variant_name": fields.String,
 "is_active": fields.Boolean,
"deleted":fields.String
}

product_variant_get = {
 "product_variant_id": fields.Integer,
"variant_attribute_id": fields.Integer,
"variant_attribute_name": fields.String,
"variant_value_id": fields.Integer,
"variant_value": fields.String,
"deleted":fields.String
}

search_filters={
  'product_id':{
   "type":str,
   "description":"Search by product_id"
  },
  'product_group_id': {
   "type": str,
   "description": "Search by product_group_id"
  },
  'is_configurable': {
   "type": bool,
   "description": "Search by is_configurable"
  },
  'is_active': {
   "type": bool,
   "description": "Search by is_active"
  }
 }

form_fields = {
    "File": {
        "name": "file",
        "in": "formData",
        "description": "file to upload",
        "required": False,
        "type": "file"
    }}
