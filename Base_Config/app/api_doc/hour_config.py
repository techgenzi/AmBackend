from flask_restx import fields
# class TimeField(fields.String):
#     def format(self, value):
#         if isinstance(value, str) and len(value) == 8:  # Example validation
#             return value
#         raise ValueError("Invalid time format. Use HH:MM:SS.")
hour_fields={
"record_id" :fields.Integer,
    # "hour_starts": fields.String(description="Start time in HH:MM:SS format"),
    # "end_time": fields.String(description="End time in HH:MM:SS format"),
    "hour_starts":fields.String,
    "hour_ends":fields.String,
    "time_value":fields.String,
    "description":fields.String,
    "is_active":fields.Boolean
}