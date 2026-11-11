from flask_restx import fields

product_group_fields={
 "product_group_id": fields.Integer,
 "group_name": fields.String,
 "description": fields.String,
 'product_group_attribute_id': fields.Integer,
'variant_attribute_name':fields.String,
 'deleted':fields.String
}

product_variant_fields={
 "product_variant_id": fields.Integer,
 "product_id": fields.Integer,
"variant_value_id": fields.Integer,
 "sku": fields.String,
 "variant_name": fields.String,
 "is_active": fields.Boolean,
"deleted":fields.String
}

product_group = {
 "product_group_id": fields.Integer,
 "group_name": fields.String,
 "description": fields.String
}


variant_att = {
    'product_group_attribute_id': fields.Integer,
    'product_group_id': fields.Integer,
    'attribute_id':fields.Integer,
    'variant_attribute_name': fields.String,
    'deleted': fields.String
}

