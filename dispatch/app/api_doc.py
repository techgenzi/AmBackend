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
    "ref_id": fields.String,
    'type': fields.String,
    "is_returned":fields.Boolean,
    "status": fields.String,
    "grn_item_id":fields.Integer,
    "issued_date": fields.String,
    "prod_plan_id":fields.Integer,
    "invoice_id":fields.String,
    "compcode": fields.Integer,
    "created_on": fields.String,
    "modified_on": fields.String,
    "modified_by": fields.String,
    "deleted_at": fields.String,
    "deleted": fields.Boolean,
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
    'type': {
        'type': str,
        'description': 'search by type'
    }
}


dispatch_header = {
    'ref_id': fields.String,
    'plan_unique': fields.String,
    'package_unique': fields.String,
    'type': fields.String,
    'req': fields.String,
    'created_on': fields.String,
    'apr': fields.String,
    'approval_date': fields.String,
    'order_unique': fields.String,
    'data': fields.Raw
}

dispatch_post = {
'releseid': fields.Integer,
'store_id': fields.Integer,
'dispatch_amount': fields.String,
'action':  fields.String
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
    },
    'product_id': {
        'type': int,
        'description': 'filter by product_id'
    },
    'start_date': {
        'type': str,
        'description': 'filter by start date'
    },
    'end_date': {
        'type': str,
        'description': 'filter by end date'
    }
}


dispatch_get = {
    'prod_plan_id': fields.Integer,
    'packing_process_id': fields.Integer,
    'plan_unique': fields.String,
    'package_unique': fields.String,
    'product_id': fields.String,
    'product_name': fields.String,
    'product_code': fields.String,
    'sku_id': fields.String,
    'requested_amount': fields.Integer,
    'approved_amount': fields.Integer,
    'dispatch_amount': fields.Integer
}

plan_to_report = {
    'production_plan_id': fields.Integer,
    'plan_unique': fields.String,
    'order_unique': fields.String,
    'products': fields.Raw
}
report_filters={
'dispatch_material_id': 'Filter by dispatch material product ID',
    'planned_productid': 'Filter by planned product ID',
    'ref_id': 'Filter by reference ID',
    'production_plan_id': 'Filter by production plan ID',
    'releseid': 'Filter by release ID',
    'dispatch_id': 'Filter by dispatch ID',
    'dispatch_start_date': 'Filter by dispatch start date ',
    'dispatch_end_date':'Filter by dispatch dispatch_end_date date '
}