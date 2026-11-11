from flask_restx import fields


process_fields = {
 "process_id": fields.Integer,
 "process_name": fields.String,
 "description": fields.String
 }

process_filter = {
 'process_id': {
  'type': int,
  'description': 'filter by process id'
 }
}
