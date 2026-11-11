from flask_restx import fields 
variant_value_fields={
 "variant_value_id": fields.Integer,
 "variant_attribute_id": fields.Integer,
"description": fields.String,
"variant_attribute_name":fields.String,
"variant_value":fields.String,
 "variant_value_temp": fields.String,
"add_att":fields.String,
"compcode": fields.Integer,
 "created_on": fields.String,
 "modified_on": fields.String,
 "modified_by": fields.String,
 "deleted_at": fields.String,
 "deleted": fields.Boolean
}



search_filters={
'variant_attribute_id':{
 'type':int,
 'description': 'filter based on the attribute'
}
}
