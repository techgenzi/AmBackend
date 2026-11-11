from flask_restx import fields

mark = {
    'mark_id': fields.Integer,
    'product_id': fields.Integer
}

mark_line = {
    'mark_line_id': fields.Integer,
    'mark_id': fields.Integer,
    'product_id': fields.Integer,
    'total_weight': fields.Integer,
    'add_attribute': fields.Raw
}


mark_search = {
        'product_id': {
            'type': int,
            'descritpion': 'product id filter'
        },
        'mark_id': {
            'type': int,
            'description': 'mark id filter'
        },
        'raw_product_id': {
            'type': int,
            'descritpion': 'product id filter'
        }
}


mark_report = {
 'product_id': fields.Integer,
 'product_code': fields.String,
 'sku_id': fields.String,
 'uom': fields.String,
 'data': fields.Raw
}
