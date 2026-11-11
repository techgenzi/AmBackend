from flask_restx import fields

# Job Orderlist response
from ipss_utils.ipss_api_doc import list_api_params


inv_summary = {
    'sku_id': fields.String,
    'planed_quantity': fields.Integer,
    'actual_quantity': fields.Integer,
    'efficiency': fields.String
}

plan_summary = {
    'product_id': fields.Integer,
    'sku_id': fields.String,
    'planed_quantity': fields.Integer,
    'all_wastage': fields.Integer,
    'actual_quantity': fields.Integer,
    'act_wastage': fields.Integer
}

top_card = {
    'total_orders': fields.Integer,
    'total_dispatch': fields.Integer,
    'production_complete': fields.Integer,
    'production_pending': fields.Integer
}

wastage = {
    'month': fields.String,
    'allowed_wastage': fields.Integer,
    'act_wastage': fields.Integer
}
plan_cost_vs_actual_cost = {
    'month': fields.String,
    'total_planned_cost': fields.Integer,
    'total_actual_cost': fields.Integer
}

loss = {
    'month': fields.String,
    'loss': fields.String
}

search_filter = {
    'product_id': {
        'type': int,
        'description': 'filter by product id'
    },
    'customer_id': {
        'type': int,
        'description': 'filter by customer id'
    },
    'customer_purchase_id': {
        'type': int,
        'description': 'filter by customer purchase id'
    },
    'start_date':{
        'type': str,
        'description': 'filter by start date'
    },
    'end_date': {
        'type': str,
        'description': 'filter by end date'
    }
}

product_based_filter={
    'product_id': {
        'type': int,
        'description': 'filter by product id'
    },
    'customer_id': {
        'type': int,
        'description': 'filter by customer id'
    },
    'customer_purchase_id': {
        'type': int,
        'description': 'filter by customer purchase id'
    },
}

update_dashboard = {
    'order_status_overview': fields.Raw,
    'deliver_efficiency': fields.Raw,

    'performance': fields.Raw,
    'order_efficiency': fields.Raw,
    'daily_efficiency': fields.Raw,
    'employee_efficiency': fields.Raw
}

order_result = {
    'order_type': fields.String,
    'order_unique': fields.String,
    'order_date': fields.String,
    'companyname': fields.String,
    'emailid': fields.String,
    'mobileno': fields.String,
    'no_of_products': fields.String,
    'calculated_status': fields.String
}

order_filter = {
    'calculated_status': {
        'type': str,
        'description': 'filter based on status',
        'enum': ['Closed', 'Pending', 'Completed', 'In Progress']
    },
    'order_type': {
        'type': str,
        'description': 'filter based on order_type',
        'enum': ['Customer', 'Internal']
    }
}

date_filter = {
    'start_date': {
        'type': str,
        'description': 'filter by start date'
    },
    'end_date': {
        'type': str,
        'description': 'filter by end date'
    }
}