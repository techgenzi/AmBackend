from flask_restx import fields


search_filters = {
    "product_id": {
        "type": int,
        "description": "Serch by product_id"
    },
    "status": {
        "type": str,
        "description": "Serch by status"
    },
    'prod_plan_id':{
        'type': int,
        'description': 'search by prod plan id'
    },
    'unique_id':{
        'type':str,
        'description': 'search by unique_id'
    }
}

report_filter = {
    'start_date': {
        'type': str,
        'description': 'search by start date'
    },
    'end_date': {
        'type': str,
        'description': 'search by end date'
    }
}


dispatch_header = {
    'ref_id': fields.String,
    'plan_unique': fields.String,
    'type': fields.String,
    'req': fields.String,
    'created_on': fields.String,
    'apr': fields.String,
    'approval_date': fields.String,
    'data': fields.Raw
}

dispatch_post = {
'releseid': fields.Integer,
'dispatch_amount': fields.String,
'action':  fields.String,
}

stock_search = {
    'product_id': {
        'type': str,
        'description': 'search by product id'
    },
    'product_group_id':{
        'type':int,
        'description': 'search by product_group_id'
    }
}

dispatch_search = {
    'prod_plan_id': {
        'type': int,
        'description': 'search by prod_plan_id'
    }
}


dispatch_get = {
    'prod_plan_id': fields.Integer,
    'plan_unique': fields.String,
    'product_id': fields.String,
    'product_name': fields.String,
    'product_code': fields.String,
    'requested_amount': fields.Float,
    'approved_amount': fields.Float,
    'dispatch_amount': fields.Float,
    'return_amount': fields.Float
}


return_amount = {
    'prod_plan_id': fields.Integer,
    'packing_process_id': fields.Integer,
    'plan_unique': fields.String,
    'package_unique': fields.String,
    'unique_id': fields.String,
    'requested_date': fields.String,
    'requested_by': fields.String,
    'status': fields.Boolean,
    'order_unique': fields.String
}


dispatch_drop_down = {
    'prod_plan_id': fields.Integer,
    'packing_process_id': fields.Integer,
    'plan_unique': fields.String,
    'package_unique': fields.String,
    'unique_id': fields.String,
    'data': fields.Raw
}

return_data = {
    'return_material_id': fields.Integer,
    'product_id': fields.Integer,
    'sku_id': fields.String,
    'product_name': fields.String,
    'product_code': fields.String,
    'return_request_amount': fields.Float,
    'return_amount': fields.Float,
    'moved_date': fields.String,
    'status': fields.String,
    'description': fields.String,
    'remarks': fields.String,
    'is_rejected': fields.Boolean,
    'rejection_action': fields.String,
    'rejection_store_id': fields.Integer,
    'store_name': fields.String
}


return_post = {
    'return_material_id': fields.Integer,
    'product_id': fields.Integer,
    'prod_plan_id': fields.Integer,
    'packing_process_id': fields.Integer,
    'return_request_amount': fields.Float,
    'return_amount': fields.String,
    'status': fields.String,
    'description': fields.String,
    'is_rejected': fields.Boolean,
    'rejection_action': fields.String,
    'rejection_store_id': fields.Integer
}


report = {
    'prod_plan_id': fields.Integer,
    'plan_unique': fields.String,
    'order_unique': fields.String
}

report_data = {
    'product_id': fields.Integer,
    'sku_id': fields.String,
    'product_code': fields.String,
    'product_name': fields.String,
    'dispatch_amount': fields.Integer,
    'return_amount': fields.Integer,
    'return_date': fields.String
}