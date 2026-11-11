from flask_restx import fields 


cost_estimation = {
 'cost_estimation_id': fields.Integer,
 'estimation_code': fields.String,
 'customer_id': fields.Integer,
 'companyname': fields.String,
 'emailid': fields.String,
 'mobileno': fields.String,
 'marketing_person': fields.String,
 'estimate_date': fields.String,
 'description': fields.String
}


estimation_line = {
 'estimation_product_id': fields.Integer,
 'cost_estimation_id': fields.Integer,
 'product_id': fields.Integer,
 'product_code': fields.String,
 'sku_id': fields.String,
 'uom': fields.String,
 'quantity': fields.String,
 'admin_cost': fields.String,
 'margin_cost': fields.String,
 'transport_cost_per_piece': fields.String,
 'material_cost': fields.String,
 'miscellaneous_cost': fields.String,
 'labour_cost': fields.String,
 'eto_cost': fields.String,
 'packing_material_cost': fields.String,
 'cost_definition': fields.Raw,
 'final_cost': fields.String,
 'description': fields.String
}

search_filter = {
 'cost_estimation_id': {
  'type': int,
  'descrition': 'serach by cost_estimation_id'
 },
 'estimation_product_id': {
   'type': int,
   'description': 'search by estimation_product_id'
 }
}