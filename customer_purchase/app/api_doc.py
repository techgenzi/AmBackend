from flask_restx import fields
from ipss_utils.ipss_api_doc import list_api_params

cc_fields={
"compcode" : fields.Integer,
"created_on" : fields.String,
"modified_on" : fields.String,
"modified_by" : fields.String,
"deleted_at" : fields.String,
"deleted" : fields.Boolean, 
}

order_fields={
"customer_purchase_id":fields.Integer,
"order_date" :fields.String,
"expected_receiving_date":fields.String,
"order_unique":fields.String,
"billing_address":fields.String,
"shipping_address":fields.String,
"customer_id":fields.Integer,
    "order_type":fields.String,
"customer_details":fields.Raw,
"status":fields.String, # Approved ,Rejected ,Pending
"description":fields.String
}

item_fields={
"items_id":fields.Integer,
    "order_type":fields.String,
    "attachment":fields.String,
"customer_purchase_id":fields.Integer,
"product_id":fields.Integer,
"quantity_ordered":fields.String,
"quantity_delivered":fields.String,
"quantity_produced":fields.String,
"product_attributes":fields.Raw,
"delivery_product_code":fields.String,
"description":fields.String,
"status" : fields.String,
"lot_no": fields.String,
}

data_filters={
    **list_api_params,
    "order_type":{
        "type": str,
        "description": "serach by order_type"
    },
    "customer_purchase_id":{
        "type":int,
        "description":"serach by customer_purchase_id"
    },
    "order_date":{
        "type":str,
        "description":"serach by order_date"
    },
    "expected_receiving_date":{
        "type": str,
        "description": "serach by expected_receiving_date"
    },
    "customer_id":{
        "type": int,
        "description": "serach by customer_id"
    },
    "status":{
"type": str,
        "description": "serach by status"
    }
}

serach_filters={
    **list_api_params,
    # **data_filters.get('customer_purchase_id'),
    "items_id":{
        "type":int,
"description": "serach by items_id"
    },
    "product_id":{
 "type":int,
"description": "serach by product_id"
    },
    "order_type":{
        "type":str,
"description": "serach by order_type"
    },
    "customer_purchase_id":{
        "type":int,
"description": "serach by customer_purchase_id"
    }
}

plan_cost = {
    'customer_purchase_id': fields.Integer,
    'order_unique': fields.String,
    'data': fields.Raw
}
