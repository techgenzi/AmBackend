from flask_restx import fields 
paking_process_fields={"packing_process_id": fields.Integer,
 "package_unique": fields.String,
 "order_items_id": fields.Integer,
 "is_done":fields.Boolean,
 "packing_date":fields.String,
                       "end_date":fields.String,
 "quantity": fields.String,
                       "packed_quantity":fields.String
}

packing_materials_fields={
 "meterials_id":fields.Integer,
 "packing_process_id":fields.Integer,
 "product_id":fields.Integer,
 "is_packing_materials":fields.Boolean,
 "quantity":fields.Float
}

paking_searches={
 "in_started":{
  "type": bool,
  "description": "search by is_done"
 },
"end_date":{
 "type": str,
 "description": "search by is_done"
},
 "is_done":{
  "type":bool,
  "description":"search by is_done"
 },
 "packing_date": {
  "type": str,
  "description": "search by packing_date"
 },
 "order_items_id": {
  "type": int,
  "description": "search by order_items_id"
 },
 "packing_process_id": {
  "type": int,
  "description": "search by packing_process_id"
 },
 "product_id": {
  "type": int,
  "description": "search by product_id"
 }
}
