from flask_restx import fields

# Job Orderlist response
from ipss_utils.ipss_api_doc import list_api_params


items ={
    'id': fields.Integer,
    'sku_id':fields.String,
    'vendorid': fields.Integer,
    'rawmaterialsid': fields.Integer,
    'product_name': fields.String,
    'product_code': fields.String,
    'quandity':fields.String,
    "quantity_delivered":fields.String,
    'rate_per_item':fields.String,
    'type': fields.String,
    'gst': fields.Integer,
    'hsn': fields.String,
    'cgst':fields.Integer,
    'sgst':fields.Integer,
    "product_details":fields.Raw,
    "notes":fields.String,
    "description":fields.String,
    'total_price':fields.String
}

job_order_fields = {
    "joborderid": fields.Integer,
    "joborderproposalid": fields.Integer,
    "total_value": fields.Float,
    "joborderno": fields.String,
    "customer_details":fields.Raw,
    "vendor_details":fields.Raw,
    "add_attribute": fields.Raw,
    "is_done": fields.Boolean,
    # "user_id": fields.Integer,
    # 'emp_id': fields.Integer,
    "compcode": fields.Integer,
    "jo_status": fields.String,
    "type": fields.String,
    "rawmaterials_id": fields.Integer,
    "jo_doc": fields.String,  # date of complition
    "jo_valid_date": fields.String,
    "purchase_orderno": fields.String,
    "jo_date": fields.String,
    'ordercompletiondate': fields.String,
    "customer_po_no": fields.String,
    # "jo_unitofmeasure": fields.String,
    # "jo_quantity": fields.String,  # jobOrder Quantity
    # "rateper_item": fields.String,
    # "gst": fields.String,
    # "amount": fields.String,
    "gst_type": fields.String,
    "notes": fields.String,  # -----------------> New
    "payment_time": fields.String,  # -----------------> New
    "with_in_day": fields.String,  # -----------------> New
    "vendorid": fields.Integer,
    "contactname":fields.String,
    "companyname":fields.String,
    "emailid": fields.String,
    "mobileno": fields.String,
    'customer_purchase_id': fields.Integer,
    "order_unique": fields.String,
    "ship_addline1": fields.String,
    "ship_addline2": fields.String,
    "ship_district": fields.String,
    "ship_pincode": fields.String,
    "ship_city": fields.String,
    "ship_state": fields.String,
    "ship_country": fields.String,
    "jo_aql": fields.Float,
    "description": fields.String,
    "jo_reason": fields.String,
    "termsand_condition": fields.String,
    "modified_by": fields.String,
    "modified_on": fields.String,
    "created_by": fields.String
}
#
log_search ={
**list_api_params,
    'joborderid':{
        'type':'int',
        'description':'To filter based on the joborderid'
    },
    'status':{
        'type':'str',
        'description':'To filter based on the status'
    },
    'userid':{
        'type':'int',
        'description':'To filter based on the userid'
    }
}
search_types = {
    **list_api_params,
    'is_delivered':{
        'type':bool,
        'description':'Filter based on is_delivered'

    },
    'is_done': {
        'type': bool,
        'dscription': 'filter based on the is_done field '
    },
    'joborderno':{
        'type':'str',
        'description':'Filter based on joborderno'
    },
    'joborderid':{
        'type':'int',
        'description':'Filter based on the joborderid'
    },
    'vendorid':{
        'type':'int',
        'description':'Filter based on the vendorid'
    },
    # },
    'type': {
        'type': "str",
        'description': "use type based filtering record "
    },
    'status': {
        'type': "str",
        'description': "use filtering the status "
    }
}

joborder_report = {
    'start_date':{
        'type': 'str',
        'description': 'search from start date'
    },
    'end_date':{
        'type': 'str',
        'description': 'search from end date'
    },
    'product_id':{
        'type': int,
        'description': 'search by product id'
    }
}

product_price = {
    'product_id': fields.Integer,
    'rate_per_item': fields.String,
    'gst': fields.Integer,
    'created_on': fields.String,
    'vendorid': fields.Integer,
    'hsn': fields.String
}

product_price_filter = {
    'vendorid':{
        'type': int,
        'description': 'Filter based on vendorid',
        'required': True
    },
    'product_id':{
        'type': int,
        'description': 'Filter based on product id',
        'required': True
    }
}


amendment_log = {
    'id': fields.Integer,
    'joborderid': fields.Integer,
    'created_by': fields.String,
    'created_on': fields.String,
    'changed_data': fields.Raw
}
