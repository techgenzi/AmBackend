from flask_restx import fields

material_cost = {
    'material_cost_id': fields.Integer,
    'product_group_id': fields.Integer,
    'product_id': fields.Integer,
    'product_code': fields.String,
    'sku_id': fields.String,
    'uom': fields.String,
    'cost': fields.String,
    'created_by': fields.String,
    'created_on': fields.String,
    'modified_on': fields.String,
    'modified_by': fields.String,
    'grn_no': fields.String,
    'grnotesid': fields.String,
    'rate_per_item': fields.String,
}


product_filter = {
        'product_id':{
            'type': int,
            'descritpion': 'product id filter'
        }
    }

bulk_product = {
    'product_id': {
        'type': str,
        'description': 'get the product with comma separated value'
    },
    'product_group_id': {
        'type': int,
        'description': 'filter the product based on the product group'
    }
}

product_service = {
    'material_cost_id': fields.Integer,
    'product_group_id': fields.Integer,
    'product_id': fields.Integer,
    'product_code': fields.String,
    'uom': fields.String,
    'cost': fields.String
}

bulk_post_upload = {
    'material_cost_id': fields.Integer,
    'product_id': fields.Integer,
    'cost': fields.Integer
}

actual_material_cost = {
    'production_plan_id': fields.Integer,
    'plan_unique': fields.String,
    'total': fields.String,
    'data': fields.Raw
}

actual_material_filter = {
    'production_plan_id': {
        'type': int,
        'description': 'Filter by production plan id'
    },
    'product_id': {
        'type': int,
        'description': 'Filter by product id'
    },
    'start_date': {
        'type': 'string',
        'description': 'Filter by start date (YYYY-MM-DD)'
    },
    'end_date': {
        'type': 'string',
        'description': 'Filter by end date (YYYY-MM-DD)'
    }
}


