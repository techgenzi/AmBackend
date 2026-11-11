from flask_restx import fields
from ipss_utils.ipss_api_doc import list_api_params

search_params = {
    'search': {
        'type': 'str',
        'description': "Enter id here"
    },
    'moved_items': {
        'type': 'str',
        'description': "Enter MOVED to show moved items UNMOVED to show Un_moved items"
    },
    'grn_notes': {
        'type': 'str',
        'description': "TO find the type of the GRN"
    }
}
# Good Recive Notes
grnotes_fields = {
    "grnotesid": fields.Integer,
    "companyname":fields.String,"emailid":fields.String, "mobileno":fields.String,
    "grn_no": fields.String,
    "grn_type": fields.String,
    "is_moved": fields.Boolean,
    "total_item": fields.Integer,
    "total_price": fields.String,
    'grn_status': fields.String,
    "user_id": fields.Integer,
    "type": fields.String,
    "joborderid": fields.String,
    "joborderno": fields.String,
    "bommaster_id": fields.Integer,
    "grndate": fields.String,
    "vendorid": fields.Integer,
    "inviceno": fields.String,
    # "inviceid": fields.String,
    "invice_attach": fields.String,
    "deliverychallan_no": fields.String,
    "is_qc_done": fields.Boolean,
    "store_id": fields.Integer,
    "store_name": fields.String,
    "dc_attach": fields.String,
    "grn_description": fields.String,
    "grn_reason": fields.String
}

grnline_items = {
    'grnlineid': fields.Integer,
    'grnotesid': fields.Integer,
    'product_id': fields.Integer,
    'product_name': fields.String,
    'sku_id': fields.String,
    'additional_attributes': fields.Raw,
    'asset_attribute':fields.Raw,
    'grn_type': fields.String,
    'userid': fields.Integer,
    'received_quantity': fields.String,
    'rate_per_item': fields.String,
    'gst': fields.String,
    # "total_item":fields.String,
    'reason': fields.String,
    'quandity': fields.Integer,
    'quantity_delivered': fields.Integer,
    "purchase_items_id":fields.Integer,
    'non_damaged_quantity': fields.String,
    'damaged_quantity':fields.String,
    "uom":fields.String,
    'compcode': fields.String,
    'is_moved': fields.Boolean,
    'total_price': fields.Integer,
    'modified_by': fields.String,
    'modified_on': fields.String,
    'created_by': fields.String,
    'created_on': fields.String,
    'supplier_lot_no': fields.String,
    'lot_no': fields.String,
    'product_details': fields.Raw,
    'deleted': fields.Boolean,
    "deleted_at": fields.String

}


# Good Recive Notes
grnotes_get_fields = {
    "grnotesid": fields.Integer,
    "deliverychallan_no": fields.String,
    "invice_attach": fields.String,
    "dc_attach": fields.String,
    "grn_no": fields.String,
    "user_id": fields.Integer,
    "is_moved": fields.Boolean,
    "total_item": fields.Integer,
    "total_price": fields.String,
    "compcode": fields.Integer,
    "type": fields.String,
    "joborderid": fields.String,
    "joborderno": fields.String,
    "bommaster_id": fields.Integer,
    "bom_no": fields.String,
    "jo_doc": fields.String,  # date of complition
    "jo_valid_date": fields.String,
    "purchase_orderno": fields.String,
    "jo_date": fields.String,
    "vendorid": fields.Integer,
    "companyname": fields.String,
    "contactname": fields.String,
    "emailid": fields.String,
    "mobileno": fields.String,
    'status': fields.String,
    "is_qc_done": fields.Boolean,
    "store_id": fields.Integer,
    "store_name": fields.String,
    # "ship_addline1": fields.String,
    # "ship_addline2": fields.String,
    # "ship_district": fields.String,
    # "ship_pincode": fields.String,
    # "ship_city": fields.String,
    # "ship_state": fields.String,
    # "ship_country": fields.String,
    "jo_aql": fields.String,
    # "jo_description": fields.String,
    "jo_termsand_condition": fields.String,
    "grndate": fields.String,
    "inviceno": fields.String,
    "inviceid": fields.String,
    "grn_description": fields.String,
    "grn_reason": fields.String,
    "modified_by": fields.String,
    "modified_on": fields.String,
    "created_by": fields.String,
    "created_on": fields.String,
    "deleted": fields.Boolean,
    "deleted_at": fields.String,

}
# request
grnotes_list_request = {
    **list_api_params,
    'grnotesid': {
        'type': "int",
        'description': "grnotesid sigle record search"
    },
    'types': {
        'type': "str",
        'description': "use type based filtering record "
    }
}
####
doc_upload_fields = {

    "content_type": fields.String,
}


grn_bom_report_field = {
    "grn_no": fields.String,
    "po_quantity": fields.Integer,
    "received_quantity": fields.Integer,
    'rawmaterialsid': fields.Integer,
    "product_code": fields.String,
    "bom_no": fields.String,
    "bom_quantity": fields.Integer,
    "details": fields.Raw,
    "purchase_quantity": fields.Integer,
    "remaining_quantity": fields.Integer
}

grnotes_report_edit = {
    'rawmaterialsid': fields.Integer,
    'received_quantity': fields.Integer
}

grnotes_get_filter = {
    'rawmaterialsid': {
        'type': "int",
        'description': "use type based filtering record "
    }
}

report_filter={
    "product_id":{
        'type': "int",
        'description': "use type based filtering product_id "
    },

    "joborderid": {
        'type': "int",
        'description': "use type based filtering joborderid "
    },
    "grnotesid": {
        'type': "int",
        'description': "use type based filtering grnotesid "
    },
}

grn_report={
    "status":{ 'type': "str",
        'description': "use type based filtering status "},
"grnotesid": {
        'type': "int",
        'description': "use type based filtering grnotesid "
    },
"product_id":{
        'type': "int",
        'description': "use type based filtering product_id "
    },
"startdate":{
        'type': "int",
        'description': "use type based filtering startdate "
    },
"enddate":{
        'type': "int",
        'description': "use type based filtering enddate "
    },
"vendorid":{
'type': "int",
        'description': "use type based filtering enddate "
}
}