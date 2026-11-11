from flask_restx import fields

product_group = {
    "product_group_id": fields.Integer
}

product_group_name = {
"product_group_id": fields.Integer,
"group_name": fields.String
}


attribute_ids = {
    'attribute_id': fields.Integer,
    'rank': fields.Integer,
    'is_product': fields.Boolean
}

attribute_ids_name = {
    'attribute_id': fields.Integer,
    'product_group_seq_id': fields.Integer,
    'variant_attribute_name': fields.String,
    'rank': fields.Integer,
    'isproduct': fields.Boolean
}


search_filters={
    "product_group_seq_id": {
        "type": int,
        "description": "Search by product_group_seq_id"
    }}