from flask_restx import fields

line_process = {
    'line_config_id': fields.Integer,
    'line_name': fields.String,
}

stage_field = {
    'stage_id': fields.Integer,
    'stage_name': fields.String
}

process_field = {
    'line_process_id': fields.Integer,
    'process_id': fields.Integer,
    'process_name': fields.String
}

