from flask_restx import fields 

custom_config_fields = {
    "id": fields.Integer,
    "compcode": fields.Integer,
    "module_name": fields.String,
    "config_type": fields.String,
    "config_data": fields.Raw,
    "created_on": fields.String,
    "created_by": fields.String,
    "deleted": fields.Boolean
}
