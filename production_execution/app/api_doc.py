from flask_restx import fields

prod_exe_fields = {
    "id": fields.Integer,
    "map_id": fields.Integer,
    "prod_plan_id": fields.String,
    "is_material_recieved":fields.Boolean,
    "stage_id": fields.String,
    "stage_name": fields.String,
    "wastage": fields.String,
    "product_id": fields.String,
    "inward_qty": fields.Float,
    "outward_qty": fields.Float,
    "operation_date": fields.String,
    "description": fields.String,
    "additional": fields.Raw,
    "status": fields.String(default="Pending"),
    "compcode": fields.Integer,
    "product_name": fields.String,
    "sku_id": fields.String,
    "prod_color": fields.String,
    "prod_size": fields.String,
    "gender": fields.String,
    "plan_date": fields.String,
    "total_qty": fields.Float
}
# "sku_id": fields.List(fields.Raw)

searc_filters = {
    'is_material_recieved':{
        'type': bool,
        "description": "Search by Request"
    },
    'operation_date': {
        'type': str,
        "description": "Search by date"
    },
    'prod_plan_id': {
        'type': int,
        'description': "Search By prod_plan_id"
    },
    'stage_id': {
        'type': int,
        'description': "Search By stage_id"
    },
    "status": {
        'type': str,
        "description": "Search By status"
    },
    'id': {
        'type': int,
        'description': "Search By id"
    }
}
