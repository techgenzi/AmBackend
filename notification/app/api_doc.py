from flask_restx import fields 

notification_company = {
 'id': fields.Integer,
    'action_id': fields.Integer,
    'action_name': fields.String,
 'deleted': fields.Boolean
}

notification_user = {
'id': fields.Integer,
 'action_id': fields.Integer,
 'action_name': fields.String,
 'user_id': fields.Integer,
 'username': fields.String,
 'email': fields.String,
 'deleted': fields.Boolean
}

notification_user_message = {
 'id': fields.Integer,
 'action_id': fields.Integer,
 'action_name': fields.String,
 'message': fields.String,
    'is_read': fields.Boolean
}
