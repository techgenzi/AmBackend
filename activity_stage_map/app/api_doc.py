

from flask_restx import fields
activity_stage_map_fields={"activity_stage_map_id": fields.Integer,
 "config_id": fields.Integer,
 "production_stage_id": fields.Integer,
                           "target_per_hour":fields.String,
 "is_final_process":fields.Boolean
}


activity_filters={
 "activity_stage_map_id":{
  "type":int,
  "description":"Search by activity_stage_map_id"
 },
 "config_id": {
  "type": int,
  "description": "Search by config_id"
 },
 "production_stage_id": {
  "type": int,
  "description": "Search by production_stage_id"
 },
 "product_id": {
  "type": int,
  "description": "Search by product_id"
 },
 "is_final_process":{
  "type":bool,
"description": "Search by is_final_process"
 }
}


product_data={
"product_id":fields.Integer,
 "product_code": fields.String
 ,"product_name": fields.String,
 "sku_id": fields.String,
}
sub_data={
 "stage_name":fields.String,
 "stage_id":fields.Integer,
 "config_name":fields.String,
 "config_id":fields.Integer,
 "target_per_hour":fields.String,
 "production_stage_id":fields.Integer,
 "is_final_process":fields.Boolean
}