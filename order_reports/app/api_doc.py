from flask import request
from flask_restx import fields

orderPlanFeields={
"customer_purchase_id":fields.Integer,
"order_date":fields.String,
"expected_receiving_date":fields.String,
"order_unique":fields.String
}

orderPlanSubFields={
    "quantity_ordered":fields.String,
    "product_id":fields.String,
    # "quantity_ordered":fields.NumberMixin,
    "product_code":fields.String,
    "product_name":fields.String,
    "product_count":fields.String,
    "sku_id":fields.String,
    "planed_qty":fields.String
}
search_filters={
    "product_id":{
"type":int,
      "description":"Seacrh by product_id"
    },
    "production_plan_id":{
"type":int,
      "description":"Seacrh by production_plan_id"
    },
  "customer_purchase_id":{
      "type":int,
      "description":"Seacrh by customer_purchase_id"
  }  ,
"status":{
      "type":str,
      "description":"Seacrh by status"
  }  ,
"start_date":{
      "type":str,
      "description":"Seacrh by start_date"
  }  ,
"end_date":{
      "type":str,
      "description":"Seacrh by end_date"
  }
}

del_fields={
    "plan_unique":fields.String,
    "product_id":fields.Integer,
    "allowed_wastage":fields.String,
    "product_code":fields.String,
    "product_name":fields.String,
    "planed_quantity":fields.String,
    'quantity_ordered': fields.String,
    "production_plan_id":fields.Integer,
    'uom_id': fields.Integer,
    'uom': fields.String,
    'order_unique': fields.String,
    "outward_qty":fields.String,
    "actual_wastage":fields.String,
    "sku_id":fields.String,
    "stage_name":fields.String
}
################
delivery_fields={
"deliveryno":fields.String,
"delivery_date":fields.String,
"driver_name":fields.String,
"driver_number":fields.String,
"vehicle_number":fields.String,
"customer_name":fields.String,
"order_unique":fields.String,
    "customer_purchase_id":fields.String,
    "number_of_products":fields.String,
    "created_on":fields.String
}
delivery_sub_fields={
    "product_code":fields.String,
    "product_name":fields.String,
    "sku_id":fields.String,
    "delivered_qty":fields.String,
    'quantity_ordered': fields.String,
    'serial_numbers': fields.List(fields.String),
    'rejected_qty': fields.String,
    'is_rejected': fields.Boolean,
    'rejection_action': fields.String,
    'rejection_store_id': fields.String,
    'rejection_store_name': fields.String
}

deleivery_filters={
    "deliveryid":{
        "type":int,
        "description":"Search by deliveryid"
    },
    "product_id":{
"type":int,
        "description":"Search by product_id"
    },
    "customer_id":{
        "type":int,
        "description":"Search by customer_id"
    }
}

paln_filterss={
    "product_id":{
"type":int,
        "description":"Search by product_id"
    },
"production_plan_id":{
"type":int,
        "description":"Search by production_plan_id"
    },
"status":{
"type":str,
        "description":"Search by status"
    },
"start_date":{
"type":str,
        "description":"Search by start_date"
    },
"end_date":{
"type":str,
        "description":"Search by end_date"
    },
}

##########################
requestPlanReport={
"doc_id": fields.String,
"plan_unique": fields.String,
"order_unique": fields.String,
    "releseid":fields.Integer,
"approved_amount": fields.String,
"planed_quantity": fields.String,
"required_quantity": fields.String,
"production_plan_id": fields.String
}
requestPlanReportModel={
"product_id": fields.String,
      "product_name": fields.String,
      "product_code": fields.String,
      "sku_id": fields.String,
    'uom': fields.String
}
requestPlanFilter={
    "production_plan_id":{
"type":str,
        "description":"Search by production_plan_id"
    },

    "start_date":{
"type":str,
        "description":"Search by start_date"
    },
    "end_date":{
"type":str,
        "description":"Search by end_date"
    },
    "product_id":{
"type":str,
        "description":"Search by product_id"
    }
}


report_order = {
    'customer_purchase_id': fields.Integer,
    'order_unique': fields.String,
    'order_date': fields.String,
    'expected_receiving_date': fields.String,
    'customer_id': fields.Integer,
    'companyname': fields.String,
    'product_details': fields.Raw
}

report_filter = {
    'product_id': {
        'type': int,
        'description': 'filter based on product_id'
    },
    'customer_purchase_id': {
        'type': int,
        'description': 'filter based on customer_purchase_id'
    },
    'customer_id': {
        'type': int,
        'description': 'filter based on customer_id'
    },
    'start_date': {
        'type': str,
        'description': 'filter by start_date'
    },
    'end_date': {
        'type': str,
        'description': 'filter based on end_date'
    }
}


report_field = {
    'product_id': fields.Integer,
    'product_code': fields.String,
    'product_name': fields.String,
    'sku_id': fields.String,
    'data': fields.Raw
}

materialProductionFilter = {
    "production_plan_id": {
        "type": int,
        "description": "Search by production_plan_id"
    },
    "start_date": {
        "type": str,
        "description": "Search by start_date"
    },
    "end_date": {
        "type": str,
        "description": "Search by end_date"
    },
    "product_id": {
        "type": int,
        "description": "Search by product_id"
    }
}