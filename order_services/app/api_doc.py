

from flask_restx import fields

total_order_products={
    "rawmaterialsid":fields.Integer,
    "quantity_ordered":fields.String,
    "product_count":fields.String,
    "quantity_planned":fields.String,
    "productcode":fields.String,
    "product_name":fields.String,
    "sku_id":fields.String,
}

overAllOrders={"customer_purchase_id":fields.Integer,
               "order_unique":fields.String,
               'companyname':fields.String,
               'contactname':fields.String
               }

search_filters={
    "product_group_id":{
    "type":int,
            "description":"serch by product_id"
    },
    "product_id":{
        "type":int,
        "description":"serch by product_id"
    },
    "customer_purchase_id":{
        "type": int,
        "description": "serch by customer_purchase_id"
    }
}

orderBasedReportFields={
"product_id":fields.Integer,
    'bom_id': fields.Integer,
"quantity_ordered":fields.String,
"quantity_planned":fields.String,
"product_code":fields.String,
"product_name":fields.String,
"product_count":fields.String,
"production_stages":fields.String,
    "sku_id":fields.String,
"bom_config":fields.String
}
orderBasedReportFieldsNested={
    'customer_purchase_id': fields.Integer,
    "extract_id":fields.String,
    "quantity_ordered":fields.String,
    "quantity_planned":fields.String,
    "order_unique":fields.String,
    "description":fields.String
}

productBasedReportss={
    "extract_id":fields.Integer,
    "sku_id":fields.String,
    # "product_count":fields.String,
    "order_items_id":fields.Integer,
    'bom_id': fields.Integer,
    "product_id":fields.Integer,
    "quantity_ordered":fields.String,
    "quantity_planned":fields.String,
    "product_count":fields.String,
    "product_name":fields.String,
    "product_code":fields.String,
    'uom': fields.String,
    "order_date":fields.String,
    "expected_receiving_date":fields.String,
    "order_unique":fields.String,
    "order_type":fields.String,
    "production_stages":fields.String,
    "bom_config":fields.String,
    "description":fields.String,
    "lot_breakdown":fields.Raw,
}

all_plan_fields={
    "production_plan_id":fields.Integer,
    "product_id":fields.Integer,
    "is_hourly":fields.Boolean,
    "planed_quantity":fields.String,
    "plan_unique":fields.String,
    "wastage":fields.String,
    "wastage_per":fields.String,
    "sku_id":fields.String,
    "product_code":fields.String,
    "product_name":fields.String,
    "product_count":fields.String
}

all_plan_details={
    "stage_id":fields.Integer,
    "process_name":fields.String,
    "stage_name":fields.String,
    "target_per_hour":fields.String,
    "achieved_quantity_per_hour":fields.String,
    "day_target":fields.String,
    "plan_target_id":fields.Integer,
    "achieved_quantity_day": fields.String,
    "created_on": fields.String
}

all_plan_filters={
    "is_hourly":{
      "type":bool,
        "description":"Search by hourly production or not"
    },
    "product_id":{
        "type":int,
        "description":"Searh by the product_id"
    },
    "production_plan_id":{
        "type": int,
        "description": "Searh by the production_plan_id"
    },
    'end_date':{
        "type": str,
        "description": "Searh by the end_date"
    },
    'start_date':{
        "type": str,
        "description": "Searh by the start_date"
    },
}

bom_fields={
    "product_id": fields.Integer,
    "quantity": fields.String,
    "product_code": fields.String,
    "product_name": fields.String,
    "sku_id": fields.String,
    'uom': fields.String,
    "product_count": fields.String,
    "allocated_quantity": fields.String
}


material_fields={
    'production_plan_id': fields.String,
    'plan_unique': fields.String,
    "product_id": fields.Integer,
    "product_code": fields.String,
    "product_name": fields.String,
    "sku_id": fields.String,
    'uom': fields.String,
    "requested_amount": fields.String,
    "approved_amount": fields.String
}

material_filter = {
    'production_plan_id': {
        'type': int,
        'description': 'Search by plan id'
    },
    'status': {
        'type': str,
        'description': 'Filter by status'
    }
}


execution_previous_stage_fields={
"production_stage_id":fields.Integer,
    "current_stage_outward":fields.String,
"rank_id":fields.Integer,
"product_id":fields.Integer,
"stage_id":fields.Integer,
"stage_name":fields.String,
"id":fields.Integer,
"outward_qty":fields.String,
"process_id":fields.Integer,
"process_name":fields.String
}
exec_prev_filtes={
'plan_target_id': {
        'type': int,
        'description': 'Search by plan_target_id'
    },
    'stage_id': {
        'type': int,
        'description': 'Filter by stage_id'
    }
}

stage_wise_production_fields={
    'product_id': fields.Integer,
    'sku_id': fields.String,
    'product_code': fields.String,
    'product_name': fields.String,
    'data': fields.Raw
}