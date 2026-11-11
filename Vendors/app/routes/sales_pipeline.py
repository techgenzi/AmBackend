from flask_restx import Namespace, fields
from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model

# Initialize API routes
sales_pipeline_route = Namespace('sales_pipeline', path='/am-vendors/pipeline')

# Pipeline Stages models
pipeline_stage_fields = {
    'id': fields.String(description='UUID of the stage'),
    'compcode': fields.Integer(description='Company code ID (gtcompmastid)'),
    'name': fields.String(required=True, description='Name of the stage'),
    'key': fields.String(required=True, description='Unique key slug'),
    'sequence_order': fields.Integer(required=True, description='Display order'),
    'is_system': fields.Boolean(description='True if it is a system stage'),
    'color_code': fields.String(description='Hex code representation'),
    'created_at': fields.String,
    'updated_at': fields.String
}

pipeline_stage_model = sales_pipeline_route.model('PipelineStage', pipeline_stage_fields)

pipeline_stage_list_response = sales_pipeline_route.model('PipelineStageListResponse', {
    **list_response_model,
    'results': fields.List(fields.Nested(pipeline_stage_model))
})

# Sales Lead Models
sales_lead_fields = {
    'id': fields.String(description='UUID of the lead'),
    'compcode': fields.Integer(description='Company code ID (gtcompmastid)'),
    'customer_type': fields.String(required=True, description='NEW or EXISTING'),
    'customer_id': fields.Integer(description='Vendor/Customer database ID'),
    'new_customer_name': fields.String,
    'new_customer_contact': fields.String,
    'new_customer_email': fields.String,
    'new_customer_address': fields.String,
    'stage_id': fields.String(required=True, description='UUID of current stage'),
    'tally_invoice_number': fields.String,
    'delivery_method': fields.String,
    'created_by': fields.String,
    'created_at': fields.String,
    'updated_at': fields.String
}

sales_lead_model = sales_pipeline_route.model('SalesLead', sales_lead_fields)

sales_lead_list_response = sales_pipeline_route.model('SalesLeadListResponse', {
    **list_response_model,
    'results': fields.List(fields.Nested(sales_lead_model))
})
