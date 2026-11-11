from flask_restx import fields

labour = {
    'labour_cost_id': fields.Integer,
    'product_id': fields.Integer,
    'product_code': fields.String,
    'sku_id': fields.String,
    'stage_count': fields.Integer,
    'rate_per_piece': fields.String,
    'rate_per_box': fields.String,
    'add_attribute': fields.Raw
}


product_filter = {
        'product_id':{
            'type': int,
            'descritpion': 'product id filter'
        }
    }


labour_cost_response = {
    'production_plan_id': fields.Integer,
    'product_id': fields.Integer,
    'product_name': fields.String,
    'product_code': fields.String,
    'sku_id': fields.String,
    'labour_cost': fields.Float,
    'estimated_cost': fields.String,
    'is_done': fields.Boolean,
    'moved_quantity': fields.Float,
    'uom': fields.String,
    'plan_unique': fields.String,
    'data': fields.Raw,
    'order_details': fields.Raw
}

labour_cost_search = {
    'product_id':{
        'type': int,
        'description': 'Filter by product id'
    },
    'production_plan_id':{
        'type': int,
        'description': 'Filter by production plan id'
    },
    'start_date':{
        'type': 'string',
        'description': 'Filter by start date (YYYY-MM-DD)'
    },
    'end_date':{
        'type': 'string',
        'description': 'Filter by end date (YYYY-MM-DD)'
    },
    'is_done': {
        'type': 'boolean',
        'description': 'Filter by completion status'
    }
}

