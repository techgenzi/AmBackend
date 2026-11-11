from flask_restx import fields

line_config_fields = {
    'line_config_id': fields.Integer,
    'line_name': fields.String,
    'description': fields.String
}

line_config_filters = {
    'line_config_id': {
        'type': int,
        'description': 'Enter the line config id'
    }
}