from flask_restx import fields
from ipss_utils.ipss_api_doc import list_api_params


delivery_fields = {
    "deliveryid": fields.Integer,
    "deliveryno": fields.String,
    "userid": fields.Integer,
    "compcode": fields.Integer,
    "vendorid": fields.Integer,
    "type": fields.String,
    "vehicle_number":fields.String,
    "driver_name":fields.String,
    "driver_number":fields.String,
    "status":fields.String,
    "is_drafted":fields.Boolean,

    "delivery_date": fields.String,
    "customerid": fields.Integer,
    "contactname":fields.String,
    "companyname":fields.String,
    "emailid": fields.String,
    "mobileno": fields.String,
    "description": fields.String,
    "termsand_condition": fields.String,
    "modified_by": fields.String,
    "modified_on": fields.String,
    "created_by": fields.String,
    "created_on": fields.String
}
search_types = {
    **list_api_params,
    'deliveryid':{
        'type':int,
        'description':'Filter based on deliveryid'
    },
    'vendorid':{
        'type':'int',
        'description':'Filter based on the vendorid'
    },
    "status":{
'type':'int',
        'description':'Filter based on the status'
    },
    "is_drafted":{
        "type":bool,
        'description': 'Filter based on the is_drafted'
    },
    "delivery_date":{
        "type": str,
        'description': 'Filter based on the delivery_date'
    },
    "id":{
        "type": int,
        'description': 'Filter based on the delivery_date'
    },
    "workOrderLineId":{
        "type": int,
        'description': 'Filter based on the delivery_date'
    },
    "customerid": {
        "type": int,
        'description': 'Filter based on the customerid'
    }
}

workOrderItems = {
    'id': fields.Integer,
    'deliveryid': fields.Integer,
    # "is_drafted":fields.Boolean,
    'workOrderLineId': fields.Integer,
    'quantity': fields.Integer,
    'store_id': fields.Integer,
    'production_lot_no': fields.String,
    'serial_numbers': fields.List(fields.String, description="List of scanned serial numbers for this item"),
    'created_by':fields.String,
    'created_on': fields.String,
    'deleted': fields.Boolean
}

report_fields = {
    'customer_purchase_id': fields.Integer,
    'order_unique': fields.String,
    'companyname': fields.String,
    'expected_receiving_date': fields.String,
    'customer_id': fields.Integer,
    'status': fields.String,
    'sku_id': fields.String,
    'data': fields.Raw
}

report_line = {
    'product_id': fields.Integer,
    'product_name': fields.String,
    'product_code': fields.String,
    'sku_id': fields.String,
    'quantity_ordered': fields.String,
    'quantity_delivered': fields.String,
    'quantity_produced': fields.String,
    'delivery': fields.Raw
}

report_filter = {
    'results_per_page': {
        'type': int,
        'description': 'result per page'
    },
    'paged': {
        'type': int,
        'description': 'no of page'
    },
    'customer_id': {
        'type': int,
        'description': 'no of page'
    },
    'customer_purchase_id': {
        'type': int,
        'description': 'no of page'
    },
    'start_date': {
        'type': str,
        'description': 'no of page'
    },
    'end_date': {
        'type': str,
        'description': 'no of page'
    },
    'product_id': {
        'type': int,
        'description': 'Filter by product'
    }
}
