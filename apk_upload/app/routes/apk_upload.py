from flask_restx import Namespace, fields
from ipss_utils.ipss_api_doc import list_response_model, create_record_response, update_record_response

from ..api_doc import list_response, apk_upload_fields

# Initialize API routes
# Initialize API routes
apk_upload_api_route = Namespace('APK Upload API', path='/am-apk_upload')

# List template API docs
apk_upload_model = apk_upload_api_route.model('apk_upload', apk_upload_fields)

apk_upload_list_response = apk_upload_api_route.model('apk_upload_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(apk_upload_model))
    }
})

# Create form template model
create_apk_upload_model = apk_upload_api_route.model('create_apk_upload_model', apk_upload_model)

get_apk_upload_response = apk_upload_api_route.model('get_apk_upload_response', apk_upload_fields)

update_apk_upload_model = apk_upload_api_route.model('update_apk_upload_model',
                                                     apk_upload_fields)
update_apk_upload_response = apk_upload_api_route.model('update_apk_upload_response',
                                                        update_record_response)
