from flask_restx import fields

list_response = {
    'total_results': fields.Integer,
    'page':  fields.Integer,
    'results_per_page':  fields.Integer,
}

apk_upload_fields = {
    'apk_upload_id': fields.Integer,
    'title': fields.String,
    'media_key': fields.String,
    'form_type': fields.String,
    'description': fields.String,
    'upload_date': fields.String,
    'file_size': fields.String,
    'active': fields.Boolean(default=False),
    'app_id': fields.String,
    'version_name': fields.String,
    'version_no': fields.String,
    'created_on': fields.String,
    'created_by': fields.String,
    'modified_on': fields.String,
    'modified_by': fields.String,
    'deleted': fields.Boolean(default=False),
    'deleted_at': fields.String
}

apk_upload_filter = {
    'active': {
        'type': bool,
        'description': "Enter the active true (or) false"
    },
    'app_id': {
        'type': str,
        'description': "Enter the app_id"
    },
    'version_name': {
        'type': str,
        'description': "Enter the version_name"
    },
    'version_no': {
        'type': str,
        'description': "Enter the version_no"
    }
}
