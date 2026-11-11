from flask_restx import fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model

# reuse existing namespace from return_material routes
from .return_material import return_api_route

# ── field definitions ────────────────────────────────────────────────────────

rejected_item_fields = {
    'rejected_material_id': fields.Integer,
    'unique_id':            fields.String,
    'grnotesid':            fields.Integer,
    'grnlineid':            fields.Integer,
    'product_id':           fields.Integer,
    'sku_id':               fields.String,
    'product_code':         fields.String,
    'product_name':         fields.String,
    'uom':                  fields.String,
    'rejected_quantity':    fields.Float,
    'rejection_reason':     fields.Raw,
    'rejection_remark':     fields.String,
    'image_attachment':     fields.Raw,
    'action':               fields.String,   # Return to Store | Write Off | Re-inspect | Return to Vendor | Rework
    'store_id':             fields.Integer,
    'store_name':           fields.String,
    'status':               fields.String,   # Pending | Completed
    'action_date':          fields.String,
    'grn_no':               fields.String,
    'created_on':           fields.String,
    'created_by':           fields.String,
}

rejected_header_fields = {
    'grnotesid':      fields.Integer,
    'grn_no':         fields.String,
    'created_on':     fields.String,
    'total_rejected': fields.Float,
    'items':          fields.List(fields.Raw),
}

# ── models ───────────────────────────────────────────────────────────────────

rejected_item_model = return_api_route.model(
    'RejectedMaterial_item', rejected_item_fields
)

rejected_list_model = return_api_route.model(
    'RejectedMaterial_list_response', {
        **list_response_model,
        'results': fields.List(fields.Nested(rejected_item_model)),
    }
)

rejected_patch_model = return_api_route.model(
    'RejectedMaterial_patch', {
        'status':      fields.String(description='Completed'),
        'action_date': fields.String,
    }
)

rejected_patch_response = return_api_route.model(
    'RejectedMaterial_patch_response', create_record_response
)
