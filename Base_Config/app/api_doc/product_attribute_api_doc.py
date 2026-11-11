from flask_restx import fields 
product_attribute_fields={"product_attribute_id": fields.Integer,
 "product_id": fields.Integer,
 "attribute_meta_data_id": fields.Integer,
 "product_attribute_value": fields.String,
}
