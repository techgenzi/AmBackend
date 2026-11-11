
from flask_restx import fields

plan_target_fields={
"plan_target_id":fields.Integer,
"production_plan_id": fields.Integer,
    "is_outsource": fields.Boolean,
"target_quantity": fields.String,
"is_hourly_target": fields.Boolean (default=False),
"stage_id": fields.Integer,
#     "process_id":fields.Integer,
#     'config_id':fields.String,
# 'config_name':fields.String,
"start_date" :fields.String,
"end_date": fields.String,
}
hourly_target_fields={
"plan_target_id":fields.Integer,
    "is_outsource":fields.Boolean,
"production_plan_id": fields.Integer,
"target_quantity": fields.String,
"is_hourly_target":fields.Boolean (default=True),
"stage_id": fields.Integer,
"day_target":fields.String,
"start_date" :fields.String,
"end_date": fields.String,
"alter_hours":fields.String,
"process_id":fields.Integer,
# 'config_id':fields.String,
'config_name':fields.String,
}

plan_details_fields={
"plan_details_id" :fields.Integer,
"production_plan_id" :fields.Integer,
"plan_quantity": fields.String,
"wastage": fields.String,
"wastage_per": fields.String,
"order_extract_id" :fields.Integer,
"is_done" :fields.Boolean
}
prod_plan_fields={
"production_plan_id" :fields.Integer,
    "dispatch_status":fields.Boolean,
    "end_date":fields.String,
    "floor_id":fields.String,
    "is_hourly":fields.Boolean,
    "wastage_per":fields.String,
    "product_id":fields.Integer,
    "planed_quantity":fields.String,
    'moved_quantity': fields.String,
    "wastage":fields.String,
    "plan_unique":fields.String,
    "plan_date":fields.String,
    "execution_start_date":fields.String,
    "execution_end_date":fields.String,
    "is_emergency_plan":fields.Boolean,
    "is_done":fields.Boolean,
    "status":fields.String,
    "additional" :fields.Raw,
    'product_code': fields.String,
    'product_name': fields.String,
    'sku_id': fields.String,
    'uom': fields.String,
    'produced_qty': fields.String,
    "is_multi_product":fields.Boolean,
    "products":fields.List(fields.Raw),
}

delete_fields={
    "production_plan_id":{
        "type":int,
        "description":"For delete a Production Plan"
    },
    "plan_details_id":{
            "type":int,
            "description":"For delete a Production Details"
        },
    "plan_target_id":{
            "type":int,
            "description":"For delete a Production Target"
        }
}
plan_fields={
    "status": {
        "type": str,
        "description": "Search By status"
    },
    "is_rawmaterials_received":{
        "type": bool,
        "description": "Search By status"
    },
    "is_done": {
        "type": bool,
        "description": "Search By is_done"
    },
    "is_closed": {
        "type": bool,
        "description": "Search By is_closed"
    },
    "is_emergency_plan": {
        "type": bool,
        "description": "Search By is_emergency_plan"
    },
    "plan_date": {
        "type": str,
        "description": "Search By plan_date"
    },
    "product_id": {
        "type": int,
        "description": "Search By product_id"
    },
    "production_plan_id": {
        "type": int,
        "description": "Search By production_plan_id"
    },
    "target_date":{
"type": str,
        "description": "Search By target_date"
    }
}

report_fields = {
    'customer_purchase_id': fields.Integer,
    'order_unique': fields.String,
    'production_plan_id': fields.Integer,
    'product_id': fields.Integer,
    'planed_quantity': fields.String,
    'moved_quantity': fields.String,
    'plan_date': fields.String,
    'plan_unique': fields.String,
    'product_code': fields.String,
    'product_name': fields.String,
    'sku_id': fields.String,
    'target_details': fields.Raw
}

report_filter = {
    'production_plan_id': {
        'type': int,
        'description': 'filter by production_plan_id '
    },
    'customer_purchase_id': {
        'type': int,
        'description': 'filter by customer_purchase_id '
    },
    'end_date': {
        'type': str,
        'description': 'filter by end_date '
    },
    'start_date': {
        'type': str,
        'description': 'filter by start_date '
    }
}

plan_stock = {
    'production_plan_id': fields.Integer,
    'plan_unique': fields.String,
    'planed_quantity': fields.String,
    'moved_quantity': fields.String,
    'outward_qty': fields.String,
    'product_id': fields.Integer,
    'product_code': fields.String,
    'product_name': fields.String,
    'sku_id': fields.String,
    'production_lot_no': fields.String,
    'available_lot_numbers': fields.Raw
}

moved_quantity = {
    'is_done': fields.Boolean,
    'moved_quantity': fields.String,
    'moved_date': fields.String,
    'store_id':fields.String,
    'product_id':fields.String,
}

plan_to_outward_filter = {
    'production_plan_id': {
        'type': int,
        'description': 'filter by production_plan_id '
    },
    'start_date': {
        'type': str,
        'description': 'filter by start_date '
    },
    'end_date': {
        'type': str,
        'description': 'filter by end_date '
    },
    'status': {
        'type': str,
        'description': 'filter by status '
    },
    'product_id': {
        'type': int,
        'description': 'filter by product_id '
    },
    'customer_purchase_id': {
        'type': int,
        'description': 'filter by customer_purchase_id '
    }
}

plan_datewise_outward = {
    'production_plan_id': fields.Integer,
    'plan_unique': fields.String,
    'data': fields.Raw
}

drop_down_get_all_filter = {
    'status': {
        'type': str,
        'description': 'filter by status'
    },
    'is_done': {
        'type': bool,
        'description': 'filter by finished plan'
    },
    'is_closed': {
        'type': bool,
        'description': 'filter by closed/active plans'
    },
    'is_rawmaterials_received': {
        'type': bool,
        'description': 'filter by rawmaterial received plan'
    }
}

plan_wise_outward = {
    'production_plan_id': fields.Integer,
    'product_id': fields.Integer,
    'stage_id': fields.Integer,
    'process_id': fields.Integer,
    'planed_quantity': fields.String,
    'required_quantity_per_unit': fields.String,
    'total': fields.String
}

production_plan_cost = {
    'production_plan_id': fields.Integer,
    'data': fields.Raw
}

plan_to_store = {
    'production_plan_id': fields.Integer,
    'plan_unique': fields.String,
    'planed_quantity': fields.String,
    'moved_quantity': fields.String,
    'product_id': fields.Integer,
    'product_code': fields.String,
    'product_name': fields.String,
    'sku_id': fields.String,
    'uom': fields.String,
    'produced_qty': fields.String,
    'plan_date': fields.String,
    'end_date': fields.String,
    'moved_date': fields.String,
    'plan_type': fields.String,
    'status': fields.String,
    'is_emergency_plan': fields.Boolean,
    'is_done': fields.Boolean,
    'is_rawmaterials_received': fields.Boolean,
    'details': fields.Raw
}
