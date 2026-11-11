from flask_restx import fields 
hourly_target_fields={"hourly_target_id": fields.Integer,
 "plan_id": fields.Integer,
 "hour_estimate_quantity": fields.String,
 "alter_hours": fields.String,

}


search_filters={
 "hourly_target_id":{
  "type":int,
  "description":"Search by Traget Id"
 },
 "plan_id": {
  "type": int,
  "description": "Search by plan_id"
 }
}