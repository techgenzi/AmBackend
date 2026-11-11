from flask_restx import fields 
execution_log_fields={"id": fields.Integer,
 # "execution_id": fields.Integer,
                      "stage_id":fields.String,
                      "target_id":fields.String,
                      "process_id":fields.String,
                      "hour_config_id":fields.String,
                      "machine_id":fields.Integer,
                      "activity_id":fields.Integer,
                      "time_value":fields.String,
 "wastage": fields.String,
 "inward_qty": fields.String,
 "outward_qty": fields.String,
                      "is_outsource":fields.String,
 "opertaion_start_date": fields.String,
                      "opertaion_end_date":fields.String,
                      "emp_id":fields.String,
                      'line_id': fields.Integer,
                      "description": fields.String,
                      "additional": fields.Raw,
                      "serialized_units": fields.List(fields.Raw),
                      "supplier_lot_no": fields.String,
                      "production_lot_no": fields.String
                      ,"job_order_id": fields.Integer,
                      "vendor_id": fields.Integer
                      }


execution_capture_fields={
"capture_id":fields.Integer,
"rawmaterials_id":fields.Integer,
"stage_id":fields.Integer,
"is_eval":fields.Boolean,
"parameter_id":fields.Integer,
"stage_param_value":fields.String,
"description":fields.String,
"prod_plan_id":fields.Integer,
"operation_date":fields.String,
"additional":fields.Raw
}

report_fields={
    "stage_id":fields.Integer,
    "prod_plan_id":fields.Integer,
    "operation_date":fields.String,
    "stage_name":fields.String,
    "captured_parameters":fields.List(fields.Raw)
}

# is_outsource=request.args.get('is_outsource'),
#                                                            target_id=request.args.get('target_id'),
#                                                            stage_id=request.args.get('stage_id'),
#                                                            production_plan_id=request.args.get('production_plan_id')

log_filters={
    "operation_date":{
"type":str,
        "description":"Search by out source operation or not"
    },
    "is_outsource":{
        "type":bool,
        "description":"Search by out source operation or not"
    },
    "target_id": {
        "type": int,
        "description": "Search by target_id"
    },
    "stage_id": {
        "type": int,
        "description": "Search by stage_id"
    },
    "production_plan_id": {
        "type": int,
        "description": "Search by production_plan_id"
    },
    "product_id":{
        "type": int,
        "description": "Search by product_id"
    },
    'hour_config_id':{
        "type": int,
        "description": "Search by hour_config_id"
    }
}


exeraw_fields={
    "record_id":fields.Integer,
    "execution_id":fields.Integer,
    "parameter_id":fields.Integer,
    "operation_date":fields.String,
    "stage_param_value":fields.String,
    "is_eval":fields.Boolean,
    "description":fields.String,
    "additional":fields.Raw,
    "rawmaterials_id":fields.Integer,
    "supplier_lot_no": fields.String,
    "production_lot_no": fields.String
}


execution_report_fields={
    "id": fields.Integer,
    "target_id": fields.Integer,
    "plan_unique": fields.String,
    "stage_id": fields.Integer,
    "stage_name": fields.String,
    "inward_qty": fields.Integer,
    "outward_qty": fields.Integer,
    'wastage': fields.String,
    "opertaion_start_date": fields.String,
    "opertaion_end_date": fields.String,
    "is_outsource": fields.Boolean,
    "process_id": fields.Integer,
    "config_name": fields.String,
    "emp_id": fields.Integer,
    "emp_name": fields.String,
    "line_id": fields.Integer,
    "line_name": fields.String,
    "time_value":fields.String,
    "hour_config_id":fields.String,
    "serialized_units": fields.List(fields.Raw),
    "supplier_lot_no": fields.String,
    "production_lot_no": fields.String,
    "job_order_id": fields.Integer,
    "vendor_id": fields.Integer,
    "job_order_no": fields.String,
    "vendor_name": fields.String
}
report_rawmat={
    'parameter_id': fields.Integer,
"parameter_name": fields.String,
    "stage_param_value": fields.String,  # Assuming it's numeric, change if needed
    "is_eval": fields.Boolean,
    "record_id": fields.Integer,
    "rawmaterials_id": fields.Integer,
    "product_name": fields.String,
    "product_code": fields.String,
    "sku_id": fields.String,
    "supplier_lot_no": fields.String,
    "production_lot_no": fields.String
}

execution_report_filters={
    "activity_id":{
"type":int,
        "description":"search by activity_id"
    },
 "machine_id":{
"type":int,
        "description":"search by machine_id"
    },
    "line_id":{
"type":int,
        "description":"search by line_id"
    },
    "hour_config_id":{"type":int,
        "description":"search by hour_config_id"},
    "id":{
        "type":int,
        "description":"search by id"
    },
"record_id":{
        "type":int,
        "description":"search by record_id"
    },
    'stage_id': {
        "type": int,
        "description": "search by record_id"
    },
    'process_id': {
        "type": int,
        "description": "search by record_id"
    },
    'production_plan_id': {
        "type": int,
        "description": "search by record_id"
    },
    "operation_date":{
        "type": str,
        "description": "search by record_id"
    }
}

employee_filter={
    "end_date": {
        "type": str,
        "description": "search by record_id"
    },
    'start_date':{ "type": str,
        "description": "search by record_id"},
    "line_id":{
"type":int,
        "description":"search by line_id"
    },
    "emp_id":{
"type":int,
        "description":"search by emp_id"
    },    "product_id":{
"type":int,
        "description":"search by product_id"
    },
}



list_response = {
    'total_results': fields.Integer,
    'page':  fields.Integer,
    'results_per_page':  fields.Integer,
}

employe_report={
    # "opertaion_start_date":fields.String,
    # "employee_name":fields.String,
    # "idcardno":fields.String,
    "product_name":fields.String,
    "product_code":fields.String,
    "sku_id":fields.String,
    'line_name':fields.String,
    'plan_unique':fields.String,
    'order_unique': fields.String,
    "process_name":fields.String,
    "stage_name":fields.String,
    "total_outward":fields.String,
    "sec_per_pcs":fields.String,
    "production":fields.Raw,
   "efficiency":fields.Raw,
   "remarks":fields.Raw
}

head_fields={
    "opertaion_start_date":fields.String,
    "employee_name":fields.String,
    "idcardno":fields.String,
    "average_efficiency":fields.Raw,
    "overall_efficiency":fields.String
}