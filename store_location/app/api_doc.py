from flask_restx import fields

store_list = {
    'store_id': fields.Integer,
    'store_name': fields.String,
    'location': fields.String,
    'description': fields.String
}

store_product = {
    'store_product_id': fields.Integer,
    'store_id': fields.Integer,
    'product_id': fields.Integer,
    'product_count': fields.String,
    'sub_location': fields.String
}

store_material = {
    'store_id': fields.Integer,
    'store_name': fields.String,
    'description': fields.String,
    'location': fields.String,
    'data': fields.Raw
}

product_filter = {
        'product_id':{
            'type': int,
            'descritpion': 'product id filter'
        }
    }

store_transfer_post = {
    'from_store_id': fields.Integer,
    'to_store_id': fields.Integer,
    'transfer_date': fields.String,
    'release_status': fields.String,
    'receive_status': fields.String,
    'status': fields.String,
    'request_id': fields.String,
}

store_transfer_items = {
    'store_transfer_item_id': fields.Integer,
    'store_transfer_id': fields.Integer,
    'product_id': fields.Integer,
    'quantity': fields.String,
    'approved_qty': fields.String
}

store_transfer_get = {
    'store_transfer_id': fields.Integer,
    'from_store_id': fields.Integer,
    'to_store_id': fields.Integer,
    'from_store_name': fields.String,
    'to_store_name': fields.String,
    'transfer_date': fields.String,
    'status': fields.String,
    'release_status': fields.String,
    'receive_status': fields.String,
    'request_id': fields.String,
    'data': fields.Raw
}

role_map = {
    'role_id': fields.Integer,
    'store_id': fields.Integer
}