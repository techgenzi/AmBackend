from flask_restx import fields

# vehicle list response
from ipss_utils.ipss_api_doc import list_api_params

vendors_fields = {
    'vendorid': fields.Integer,
    'user_id': fields.Integer,
    'compcode': fields.Integer,
    'asset_attributes':fields.Raw,
    'type': fields.String,
    'companyname': fields.String,
    'contactname': fields.String,
    'emailid': fields.String,
    'mobileno': fields.String,
    'gstno': fields.String,
    'panno': fields.String,
    'bill_addline1': fields.String,
    'bill_addline2': fields.String,
    'bill_district': fields.String,
    'bill_pincode': fields.Integer,
    'bill_city': fields.String,
    'bill_state': fields.String,
    'bill_country': fields.String,
    'same_as_add': fields.Boolean,
    'ship_addline1': fields.String,
    'ship_addline2': fields.String,
    'ship_district': fields.String,
    'ship_pincode': fields.Integer,
    'ship_city': fields.String,
    'ship_state': fields.String,
    'ship_country': fields.String,
    'discount_price': fields.String,
    'discount_percentage': fields.String,
    'credit_limit': fields.Integer,
    'modified_by': fields.String,
    'created_by': fields.String,
    'deleted': fields.Boolean,
    'deleted_at': fields.String
}

country_fields = {
    'countryid': fields.Integer,
    'state_name': fields.String,
    'district_name': fields.String,
    'city_name': fields.String,
    'post_name': fields.String,
    'pincode': fields.Integer
}
search_params1 = {
    'pincode': {
        'type': 'int',
        'description': 'enter the pincode'
    }
}

#
# vendor_det_fields = {
#     'vendor_det_id': fields.Integer,
#     'vendorid': fields.Integer,
#     'compcode': fields.Integer,
#     'sku_id': fields.Integer,
#     'product_name': fields.String,
#     'received_sku': fields.String,
#     'lead_time': fields.Integer,
#     'catogory_id': fields.Integer,
#     'category': fields.String,
#     'product_group': fields.Integer,
#     'group': fields.String,
#     'uom': fields.Integer,
#     'unit_of_measure': fields.String,
#     'productcode': fields.String,
#     'min_order_qty': fields.Integer,
#     "modified_by": fields.String,
#     "modified_on": fields.String,
#     "created_by": fields.String,
#     "created_on": fields.String,
#     "deleted": fields.Boolean,
#     "deleted_at": fields.String
#
# }

type_filter = {
    **list_api_params,
    'vendorid': {
        'type': 'int',
        'description': "Enter vendorid  "
    },
    'vendor_det_id': {
        'type': 'int',
        'description': "Enter vendor_det_id  "
    },
    'type':{
        'type':'str',
        'description': 'Enter the type customer/vendor'
    }
}
#
