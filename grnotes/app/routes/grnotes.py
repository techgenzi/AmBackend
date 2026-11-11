from flask_restx import Namespace, Resource, fields
from ..api_doc import grnotes_fields, grnotes_get_fields, grnline_items
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model


# Initialize API routes
grnotes_api_route = Namespace('Goods Recive notes Api', path='/am-grnotes')

# List skills API docs
grnotes_model = grnotes_api_route.model('grnotes_fields', {
            **grnotes_fields,
            'deleted': fields.Boolean,
            'created_on': fields.String,
            'modified_on': fields.String
        })

grnotes_list_response = grnotes_api_route.model('grnotes_list_response', {
    **list_response_model,
    **{
        'results': fields.List(fields.Nested(grnotes_model))
    }
})
grnotes_bulk_list_response = grnotes_api_route.model('grnotes_bulk_list_response', {
    **{
        'results': fields.List(fields.Nested(grnotes_model))
    }
})

####
grnotes_get_model = grnotes_api_route.model('grnotes_get_fields', grnotes_get_fields)
grnotes_get_response = grnotes_api_route.model('grnotes_get_response', {
**list_response_model,
    'results': fields.List(fields.Nested(grnotes_get_model))
})

# Create skill model
create_grnotes_model = grnotes_api_route.model('grnotes_fields', grnotes_fields)
grnline_model = grnotes_api_route.model('grnline_model', {**grnline_items,
                                                          "joborderno":fields.String,
                                                          "product_code":fields.String,
                                                          "uom":fields.String,
                                                          'uom_id': fields.Integer})
items_model = grnotes_api_route.model('items_model',{**grnotes_fields, 'items': fields.List(fields.Nested(grnline_model))})
# create_grn_items_model = grnotes_api_route.model('grn_postmodel',{grnotes_fields,items_model})
response_model_grn=grnotes_api_route.model('response_model_grn',{

**list_response_model,
    "data":fields.List(fields.Nested(items_model))
})
create_grnotes_response = grnotes_api_route.model('create_grnotes_response', create_record_response)

# Get skill records model
get_grnotes_response = grnotes_api_route.model('get_grnotes_response', grnotes_fields)

# Update user record
update_grnotes_fields = grnotes_fields
update_grnotes_model = grnotes_api_route.model('update_skill', update_grnotes_fields)
update_grnotes_response = grnotes_api_route.model('update_grnotes_response', update_record_response)

##################################################################################

product_model = grnotes_api_route.model('Product', {
    'product_code': fields.String,
    'product_name': fields.String,
    'sku_id': fields.String,
    'received_quantity': fields.String,
    'damaged_quantity': fields.String,
    'non_damaged_quantity': fields.String,
    'grn_no': fields.String,
})
joborder_model = grnotes_api_route.model('JobOrder', {
    'joborderid': fields.String,
    'joborderno': fields.String,
    'vendorid': fields.String,
    'companyname': fields.String,
    'jo_date': fields.String,  # Or fields.DateTime
    'is_done': fields.Boolean,
    'jo_status': fields.String,
    'ordercompletiondate': fields.String,  # Or fields.DateTime
    'products': fields.List(fields.Nested(product_model)),
})
joborder_model_list_response=grnotes_api_route.model('ListResponse',{
    **list_response_model,
    "data":fields.List(fields.Nested(joborder_model))
})


