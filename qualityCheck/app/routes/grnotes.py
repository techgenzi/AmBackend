from flask_restx import Namespace, Resource, fields
from ..api_doc import grnotes_fields, grnotes_get_fields, grnline_items, qc_items
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes
qc_api_route = Namespace('Quality Check Api', path='/am-qualitycheck')

# List skills API docs
grnotes_model = qc_api_route.model('grnotes_fields', {
            **grnotes_fields,
            'deleted': fields.Boolean,
            'created_on': fields.String,
            'modified_on': fields.String
        })

grnotes_list_response = qc_api_route.model('grnotes_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(grnotes_model))
    }
})

grnotes_bulk_list_response = qc_api_route.model('grnotes_bulk_list_response', {
    **{
        'results': fields.List(fields.Nested(grnotes_model))
    }
})

####
grnotes_get_model = qc_api_route.model('grnotes_get_fields', grnotes_get_fields)
grnotes_get_response = qc_api_route.model('grnotes_get_response', {
**list_response_model,
    'results': fields.List(fields.Nested(grnotes_get_model))
})
report_items = qc_api_route.model('report_items', {**qc_items,
                                                   "uom":fields.String})

qc_model = qc_api_route.model('qc_model', {
    'grnotesid': fields.Integer,
    'grn_no': fields.String,
    'grndate': fields.String,
    'created_on': fields.String,
    'companyname': fields.String,
    'joborderno': fields.String,
    'items': fields.List(fields.Nested(report_items))
})

qc_get_model = qc_api_route.model('qc_report_model', {
    **list_response_model,
    'results': fields.List(fields.Nested(qc_model))
})
# Create skill model
create_grnotes_model = qc_api_route.model('grnotes_fields', grnotes_fields)
grnline_model = qc_api_route.model('grnline_model', grnline_items)
items_model = qc_api_route.model('items_model',{**grnotes_fields, 'items': fields.List(fields.Nested(grnline_model))})
# create_grn_items_model = qc_api_route.model('grn_postmodel',{grnotes_fields,items_model})
create_grnotes_response = qc_api_route.model('create_grnotes_response', create_record_response)

# Get skill records model
get_grnotes_response = qc_api_route.model('get_grnotes_response', grnotes_fields)

# Update user record
update_grnotes_fields = grnotes_fields
update_grnotes_model = qc_api_route.model('update_skill', update_grnotes_fields)
update_grnotes_response = qc_api_route.model('update_grnotes_response', update_record_response)

##################################################################################


