from flask_restx import fields 
prod_stages_fields={"id": fields.Integer,
 # "rank_id": fields.Integer,
 "product_id": fields.Integer,
 # "stage_name": fields.String,
 "description": fields.String,
                    "is_config":fields.Boolean,
                    # "ref_id":fields.String,
                    "product_name":fields.String,
"stage_name": fields.String,
 "additional": fields.Raw,
 "compcode": fields.Integer,
 "created_on": fields.String,
 "modified_on": fields.String,
 "modified_by": fields.String,
 "deleted_at": fields.String,
 "deleted": fields.Boolean}

det_fields={
 "stage_name": fields.String,
 "stage_id":fields.Integer,
 'target_per_hour': fields.String,
 'required_quantity_per_unit': fields.String,
 'rank_id':fields.String,
 "id":fields.String,
 "is_serialization": fields.Boolean,
 "serialization_params": fields.List(fields.Raw)
}

search_fields={
 "id":{
  "type":int,
  "description":"Search by record_id"
 },
 'is_config':{
  "type":bool,
    "description":"Search by status"
 },
 "product_id": {
  "type": int,
  "description": "Search by product_id"
 },
 "is_static":{
"type": bool,
  "description": "Search by product_id"
 },
 "rank_id": {
  "type": int,
  "description": "Search by rank_id"
 }
}

activities={
"activity_stage_map_id": fields.Integer,
 "config_id": fields.Integer,
 "production_stage_id": fields.Integer,
 "target_per_hour":fields.String,
 "config_name":fields.String,
 "is_final_process":fields.Boolean
}