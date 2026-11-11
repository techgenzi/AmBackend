from flask_restx import Namespace, Resource, fields
from ..api_doc import vendors_fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model

# Initialize API routes
vendors_api_route = Namespace('vendors API', path='/am-vendors')

# List vendors API docs
vendors_model = vendors_api_route.model('vendors', {
    **vendors_fields,
    'deleted': fields.Boolean,
    'created_on': fields.String,
    'modified_on': fields.String
})

vendors_list_response = vendors_api_route.model('vendors_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(vendors_model))
    }
})

# Create Vendors model
create_vendors_model = vendors_api_route.model('create_vendors', vendors_fields)
create_vendors_response = vendors_api_route.model('create_vendors_response', create_record_response)

# Get vendors records model
get_vendors_response = vendors_api_route.model('get_vendors_response', vendors_fields)

# Update user record
update_vendors_fields = vendors_fields
update_vendors_model = vendors_api_route.model('update_vendors', update_vendors_fields)
update_vendors_response = vendors_api_route.model('update_vendors_response', update_record_response)

###################################

# # Initialize API routes
# vendor_detail_api_route = Namespace('vendor_detail', path='/am-vendor_mange/vendor_detail')
#
# # List vendors API docs
# vendor_det_model = vendor_detail_api_route.model('vendor_det', {
#             **vendor_det_fields,
#             'deleted': fields.Boolean,
#             'created_on': fields.String,
#             'modified_on': fields.String
#         })
#
# vendors_list_response = vendor_detail_api_route.model('vendors_list_response', {
#     **list_response_model,
#     **{
#         'results': fields.List(fields.Nested(vendor_det_model))
#     }
# })
#
# # Create Vendors model
# create_vendors_model = vendor_detail_api_route.model('create_vendors', vendors_fields)
# create_vendors_response = vendor_detail_api_route.model('create_vendors_response', create_record_response)
#
# # Get vendors records model
# get_vendors_response = vendor_detail_api_route.model('get_vendors_response', vendors_fields)
#
# # Update user record
# update_vendors_fields = vendors_fields
# update_vendors_model = vendor_detail_api_route.model('update_vendors', update_vendors_fields)
# update_vendors_response = vendor_detail_api_route.model('update_vendors_response', update_record_response)


# Initialize API routes

# vendor_detail_api_route = Namespace('vendor_detail', path='/am-vendors/vendor_detail')
#
# # List vendor_detail API docs
# vendor_det_model = vendor_detail_api_route.model('vendor_det_model', {
#     **vendor_det_fields,
#     'deleted': fields.Boolean,
#     'created_on': fields.String,
#     'modified_on': fields.String
# })
#
# vendor_det_list_response = vendor_detail_api_route.model('vendor_det_list_response', {
#     **list_response_model,
#     'results': fields.List(fields.Nested(vendor_det_model))
# })
#
# # Create vendor_detail model
#
# create_vendor_det_model = vendor_detail_api_route.model('create_vendor_det_model', vendor_det_fields)
# create_vendor_det_response = vendor_detail_api_route.model('create_notification_response', create_record_response)
#
# # Get notification records model
# get_vendor_det_response = vendor_detail_api_route.model('get_vendor_det_response', vendor_det_fields)
#
# # Update user record
# update_vendor_det_fields = vendor_det_fields
# update_vendor_det_model = vendor_detail_api_route.model('update_vendor_det_model', update_vendor_det_fields)
# update_vendor_det_response = vendor_detail_api_route.model('update_vendor_det_response', update_record_response)
