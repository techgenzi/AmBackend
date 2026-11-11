from flask_restx import fields

# inRegistry list response
invRegistryFields = {
    "releseid": fields.Integer,
    "product_id": fields.Integer,
    "doc_id":fields.String,
    "lot_no":fields.String,
    "roll_id":fields.String,
    "userid": fields.Integer,
    "username": fields.String,
    "requested_amount": fields.String,
    "approved_amount": fields.String,
    "is_from": fields.String,
    "action": fields.String,
    'reason': fields.String,
    "ref_id": fields.String,
    'type': fields.String,
    "is_returned": fields.Boolean,
    'description': fields.String,
    'is_dispatch': fields.Boolean,
    'manual_count': fields.String,
    "status": fields.String,
    'approved_by': fields.String,
    'approval_date': fields.String,
    "grn_item_id":fields.Integer,
    "issued_date": fields.String,
    "prod_plan_id":fields.Integer,
    'packing_process_id': fields.Integer,
    "invoice_id":fields.String,
    "compcode": fields.Integer,
    "created_on": fields.String,
    'created_by': fields.String,
    "modified_on": fields.String,
    "modified_by": fields.String,
    "deleted_at": fields.String,
    "deleted": fields.Boolean,
    "sub_location": fields.String,
}

search_filters = {
    "is_returned":{
        "type": bool,
        "description": "Serch by record Id"
    },
    "releseid": {
        "type": int,
        "description": "Serch by record Id"
    },
    "is_from": {
        "type": str,
        "description": "Serch by records"
    },
    "product_id": {
        "type": int,
        "description": "Serch by product_id"
    },
    "action": {
        "type": str,
        "description": "Serch by action"
    },
    "ref_id": {
        "type": str,
        "description": "Serch by ref_id"
    },
    "status": {
        "type": str,
        "description": "Serch by status"
    },
    "rawmaterials_id": {
        "type": str,
        "description": "Search by rm_id"
    },
    'prod_plan_id':{
        'type': int,
        'description': 'search by prod plan id'
    },
    'packing_process_id': {
        'type': int,
        'description': 'search by order id'
    },
    'type': {
        'type': str,
        'description': 'search by type'
    },
    'start_date': {
        'type': str,
        'description': 'search by start date'
    },
    'end_date': {
        'type': str,
        'description': 'search by end date'
    }
}


stock_list = {
    'product_id': fields.Integer,
    "store_name":fields.String,
    "sub_location": fields.String,
    "lot_no": fields.String,
    'product_code': fields.String,
    'product_name': fields.String,
    'product_count': fields.Integer,
    'uom': fields.String,
    "allocated_quantity":fields.String,
    'sku_id': fields.String,
    "roql":fields.String,
    'unit_cost': fields.Float,
    'last_grn_rate': fields.Float,
    'weighted_avg_rate': fields.Float,
    'total_valuation': fields.Float,
    'product_group': fields.String,
    'group_name': fields.String,
    'product_group_name': fields.String,
    'details': fields.Raw
}

stock_search = {
    'product_id': {
        'type': str,
        'description': 'search by product id'
    },
    'product_group_id':{
        'type':int,
        'description': 'search by product_group_id'
    },
    'store_id':{
        'type':int,
        'description': 'search by store_id'
    },
    'lot_no': {
        'type': str,
        'description': 'search by lot_no'
    }
}

stock_movement_report = {
    'product_id': fields.Integer,
    'product_code': fields.String,
    'product_name': fields.String,
    'store_name': fields.String,
    'sub_location': fields.String,
    'current_stock': fields.Float,
    'open_stock': fields.Float,
    'inward_transactions': fields.Float,
    'outward_transactions': fields.Float,
    'close_stock': fields.Float,
    'weighted_avg_rate': fields.Float,
    'unit_cost': fields.Float,
    'total_valuation': fields.Float,
    'open_valuation': fields.Float,
    'close_valuation': fields.Float,
    'uom': fields.String,
    'sku_id': fields.String,
    'details': fields.Raw
}

report_date_params = {
    'start_date': {
        'type': str,
        'description': 'report start date (YYYY-MM-DD)'
    },
    'end_date': {
        'type': str,
        'description': 'report end date (YYYY-MM-DD)'
    }
}

manual_addition = {
    'product_id': fields.Integer,
    "approved_amount": fields.String
}

store_product = {
    'product_id': fields.Integer,
    'product_code': fields.String,
    'product_name': fields.String,
    'product_count': fields.Integer,
    'sku_id': fields.String,
    'overall_count': fields.Integer,
    'data': fields.Raw
    }


transfer_log = {
    'store_id': fields.Integer,
    'approved_amount': fields.String,
    'is_dispatch': fields.Boolean,
    'product_id': fields.Integer,
    'ref_id': fields.String
}

transfer_get_log = {
    'sku_id': fields.String,
    'uom': fields.String,
    'uom_id': fields.Integer,
    'is_dispatch': fields.Boolean,
    'store_name': fields.String,
    'product_id': fields.Integer,
    'product_code': fields.String,
    'product_name': fields.String,
    'approved_amount': fields.String,
    'created_on': fields.String,
    'ref_id': fields.String,
    'ref_name': fields.String,
    'created_by': fields.String
}

inventory_action = {
    'prod_plan_id': fields.Integer,
    'data': fields.Raw
}