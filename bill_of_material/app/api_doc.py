from flask_restx import fields


bom_fields={
 "bom_id": fields.Integer,
 "product_id": fields.Integer,
 "product_name": fields.String,
 "uom": fields.String,
 "description": fields.String,
}

bom_get_fields = {
 "bom_id": fields.Integer,
 "bom_product_id": fields.Integer,
 "bom_product_name": fields.String,
 "bom_product_code": fields.String,
 'uom_id': fields.Integer,
 "uom": fields.String,
 "description": fields.String,
}


bom_det_fields={
 "bom_component_id": fields.Integer,
 "bom_id": fields.Integer,
 "product_id": fields.Integer,
 'product_group_id': fields.Integer,
 'product_group_name': fields.String,
 "product_name": fields.String,
 "product_code": fields.String,
 'is_mark_data': fields.Boolean,
 'uom_id': fields.Integer,
 "uom": fields.String,
 "quantity": fields.String,
 "notes":fields.String,
 "stage_id": fields.Integer,
 "stage_name": fields.String
}

search_filters={
 "bom_id":{
  "type":int,
  "description":"Search by Product"
 }
 ,
"product_id":{
  "type":int,
  "description":"Search by Primary_id"
 }

}
det_filter={
 "data_master_id": {
  "type": int,
  "description": "Search by det_id)"
 },
}


product_filter={
 'production_id':{
  "type":int,
  "description":"Sercah by finshed product"
 }
}

product_service = {
 'sku_id': fields.String,
 'raw_id': fields.Integer,
 'product_code': fields.String,
 'quantity': fields.String,
 'cost': fields.String
}
