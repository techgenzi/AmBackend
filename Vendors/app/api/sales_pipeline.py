import datetime
import uuid
from flask import request, abort
from flask_restx import Resource
from ipss_utils.decorators import login_required

from .. import ipss_db, db_client
from ..models.sales_pipeline import PipelineStages, SalesLeadPipelines
from ..models.vendors import Vendors
from ..routes.sales_pipeline import (
    sales_pipeline_route,
    pipeline_stage_list_response,
    pipeline_stage_model,
    sales_lead_list_response,
    sales_lead_model
)

DEFAULT_PIPELINE_STAGES = [
    {"name": "Order Placed", "key": "order_placed", "sequence_order": 10, "is_system": True, "color_code": "#EC4899"},
    {"name": "Dispatched", "key": "dispatched", "sequence_order": 20, "is_system": True, "color_code": "#F43F5E"},
    {"name": "Completed", "key": "completed", "sequence_order": 30, "is_system": True, "color_code": "#059669"},
]


def get_active_compcode():
    """Extract numeric company_id (compcode) from current_user session"""
    current_user = request.args.get('current_user') or {}
    compcode = current_user.get('company_id')
    if compcode is not None and str(compcode).isdigit():
        return int(compcode)
    req_comp = request.args.get('compcode') or (request.json or {}).get('compcode') if request.is_json else request.args.get('compcode')
    if req_comp is not None and str(req_comp).isdigit():
        return int(req_comp)
    return 1


def ensure_default_stages_for_compcode(compcode):
    """Auto-seed default milestone stages for a compcode if none exist yet"""
    existing_count = PipelineStages.query.filter_by(compcode=compcode).count()
    if existing_count == 0:
        try:
            for st in DEFAULT_PIPELINE_STAGES:
                stage = PipelineStages(
                    compcode=compcode,
                    name=st["name"],
                    key=st["key"],
                    sequence_order=st["sequence_order"],
                    is_system=st["is_system"],
                    color_code=st["color_code"]
                )
                db_client.session.add(stage)
            db_client.session.commit()
        except Exception:
            db_client.session.rollback()


@sales_pipeline_route.route('/stages')
class PipelineStagesApi(Resource):
    @login_required()
    @sales_pipeline_route.marshal_with(pipeline_stage_list_response)
    def get(self):
        """List all pipeline stages for the active compcode ordered by sequence_order"""
        compcode = get_active_compcode()
        ensure_default_stages_for_compcode(compcode)

        query = PipelineStages.query.filter_by(compcode=compcode).order_by(PipelineStages.sequence_order.asc())
        response = ipss_db.paginated_results(
            model=PipelineStages,
            query=query,
            primary_key='id'
        )
        return response

    @login_required()
    @sales_pipeline_route.expect(pipeline_stage_model)
    @sales_pipeline_route.marshal_with(pipeline_stage_model)
    def post(self):
        """Create a custom pipeline stage for the active compcode"""
        data = request.json
        if not data or not data.get('name') or not data.get('key'):
            abort(400, "Bad Request: 'name' and 'key' are required.")

        compcode = get_active_compcode()

        # Ensure key is unique within this compcode
        existing = PipelineStages.query.filter_by(compcode=compcode, key=data['key']).first()
        if existing:
            abort(400, f"Stage key '{data['key']}' already exists in this company.")

        new_stage = PipelineStages(
            compcode=compcode,
            name=data['name'],
            key=data['key'],
            sequence_order=data.get('sequence_order', 100),
            is_system=False,
            color_code=data.get('color_code', '#6B7280')
        )
        db_client.session.add(new_stage)
        db_client.session.commit()
        return new_stage


@sales_pipeline_route.route('/stages/<string:id>')
class PipelineStageDetailApi(Resource):
    @login_required()
    @sales_pipeline_route.expect(pipeline_stage_model)
    @sales_pipeline_route.marshal_with(pipeline_stage_model)
    def patch(self, id):
        """Edit a pipeline stage within the active compcode"""
        compcode = get_active_compcode()
        stage = PipelineStages.query.filter_by(id=id, compcode=compcode).first()
        if not stage:
            abort(404, "Stage not found for this company.")

        data = request.json
        if not data:
            abort(400, "No patch payload provided.")

        # System stages can be modified (name, sequence_order, color_code)
        if 'name' in data:
            stage.name = data['name']
        if 'sequence_order' in data:
            stage.sequence_order = data['sequence_order']
        if 'color_code' in data:
            stage.color_code = data['color_code']

        db_client.session.commit()
        return stage

    @login_required()
    def delete(self, id):
        """Delete a pipeline stage within the active compcode"""
        compcode = get_active_compcode()
        stage = PipelineStages.query.filter_by(id=id, compcode=compcode).first()
        if not stage:
            abort(404, "Stage not found for this company.")

        # Safeguard: 'completed' is required internally if convert-to-customer is used
        if stage.key == 'completed':
            abort(403, "Forbidden: The 'Completed' system milestone stage is required for customer conversions and cannot be deleted.")

        # Ensure no active leads in this compcode are referencing this stage
        has_leads = SalesLeadPipelines.query.filter_by(stage_id=id, compcode=compcode).first()
        if has_leads:
            abort(400, "Bad Request: Cannot delete stage with active leads.")

        db_client.session.delete(stage)
        db_client.session.commit()
        return {"message": "Stage deleted successfully"}, 200


@sales_pipeline_route.route('/leads')
class SalesLeadsApi(Resource):
    @login_required()
    @sales_pipeline_route.marshal_with(sales_lead_list_response)
    def get(self):
        """List sales/lead pipelines for the active compcode with pagination"""
        compcode = get_active_compcode()
        query = SalesLeadPipelines.query.filter_by(compcode=compcode).order_by(SalesLeadPipelines.created_at.desc())
        
        stage_id = request.args.get('stage_id')
        if stage_id:
            query = query.filter_by(stage_id=stage_id)
            
        customer_type = request.args.get('customer_type')
        if customer_type:
            query = query.filter_by(customer_type=customer_type)

        response = ipss_db.paginated_results(
            model=SalesLeadPipelines,
            query=query,
            primary_key='id'
        )
        return response

    @login_required()
    @sales_pipeline_route.expect(sales_lead_model)
    @sales_pipeline_route.marshal_with(sales_lead_model)
    def post(self):
        """Create a new sales/lead pipeline for the active compcode"""
        data = request.json
        if not data or not data.get('customer_type') or not data.get('stage_id'):
            abort(400, "Bad Request: 'customer_type' and 'stage_id' are required.")

        compcode = get_active_compcode()

        # Verify stage exists in active compcode
        stage = PipelineStages.query.filter_by(id=data['stage_id'], compcode=compcode).first()
        if not stage:
            abort(400, "Invalid stage_id for this company.")

        cust_type = data['customer_type']
        if cust_type not in ('NEW', 'EXISTING'):
            abort(400, "Bad Request: customer_type must be either 'NEW' or 'EXISTING'.")

        customer_id = data.get('customer_id')
        if cust_type == 'EXISTING':
            if not customer_id:
                abort(400, "Bad Request: 'customer_id' is required for existing customers.")
            # Verify customer exists in active compcode
            cust = Vendors.query.filter_by(vendorid=customer_id, compcode=compcode).first()
            if not cust:
                abort(400, f"Customer with id {customer_id} does not exist in this company.")

        delivery_method = data.get('delivery_method')
        if delivery_method and delivery_method not in ('PICKUP', 'SUPPLIER_DELIVERED'):
            abort(400, "Bad Request: delivery_method must be either 'PICKUP' or 'SUPPLIER_DELIVERED'.")

        # Resolve current user from session
        current_user = request.args.get('current_user', {})
        raw_user_id = current_user.get('user_id') or current_user.get('userid')
        user_uuid = None
        if raw_user_id:
            try:
                user_uuid = uuid.UUID(str(raw_user_id))
            except ValueError:
                pass

        new_lead = SalesLeadPipelines(
            compcode=compcode,
            customer_type=cust_type,
            customer_id=customer_id if cust_type == 'EXISTING' else None,
            new_customer_name=data.get('new_customer_name'),
            new_customer_contact=data.get('new_customer_contact'),
            new_customer_email=data.get('new_customer_email'),
            new_customer_address=data.get('new_customer_address'),
            stage_id=data['stage_id'],
            tally_invoice_number=data.get('tally_invoice_number'),
            delivery_method=delivery_method,
            created_by=user_uuid
        )
        db_client.session.add(new_lead)
        db_client.session.commit()
        return new_lead


@sales_pipeline_route.route('/leads/<string:id>')
class SalesLeadDetailApi(Resource):
    @login_required()
    @sales_pipeline_route.expect(sales_lead_model)
    @sales_pipeline_route.marshal_with(sales_lead_model)
    def patch(self, id):
        """Update fields/stages of an active sales/lead pipeline within the active compcode"""
        compcode = get_active_compcode()
        lead = SalesLeadPipelines.query.filter_by(id=id, compcode=compcode).first()
        if not lead:
            abort(404, "Lead not found for this company.")

        data = request.json
        if not data:
            abort(400, "No patch payload provided.")

        if 'stage_id' in data:
            # Verify stage exists in this compcode
            stage = PipelineStages.query.filter_by(id=data['stage_id'], compcode=compcode).first()
            if not stage:
                abort(400, "Invalid stage_id for this company.")
            lead.stage_id = data['stage_id']

        if 'tally_invoice_number' in data:
            lead.tally_invoice_number = data['tally_invoice_number']
        if 'delivery_method' in data:
            delivery_method = data['delivery_method']
            if delivery_method and delivery_method not in ('PICKUP', 'SUPPLIER_DELIVERED'):
                abort(400, "Bad Request: delivery_method must be either 'PICKUP' or 'SUPPLIER_DELIVERED'.")
            lead.delivery_method = delivery_method
        if 'new_customer_name' in data:
            lead.new_customer_name = data['new_customer_name']
        if 'new_customer_contact' in data:
            lead.new_customer_contact = data['new_customer_contact']
        if 'new_customer_email' in data:
            lead.new_customer_email = data['new_customer_email']
        if 'new_customer_address' in data:
            lead.new_customer_address = data['new_customer_address']

        db_client.session.commit()
        return lead


@sales_pipeline_route.route('/leads/<string:id>/convert')
class SalesLeadConvertApi(Resource):
    @login_required()
    def post(self, id):
        """Convert a NEW customer lead into the main customer (vendor) table for the active compcode"""
        compcode = get_active_compcode()
        lead = SalesLeadPipelines.query.filter_by(id=id, compcode=compcode).first()
        if not lead:
            abort(404, "Lead not found for this company.")

        if lead.customer_type != 'NEW':
            abort(400, "Bad Request: Lead is already linked to an existing customer.")

        if not lead.new_customer_name:
            abort(400, "Bad Request: New customer name is missing.")

        # Ensure default stages exist and find the 'completed' stage for this compcode
        ensure_default_stages_for_compcode(compcode)
        completed_stage = PipelineStages.query.filter_by(compcode=compcode, key='completed').first()
        if not completed_stage:
            abort(500, "Internal Server Error: System 'completed' stage config is missing for this company.")

        current_user = request.args.get('current_user', {})

        try:
            # Promote to active vendor table
            new_customer = Vendors(
                type='Customer',
                companyname=lead.new_customer_name,
                contactname=lead.new_customer_name,
                emailid=lead.new_customer_email or '',
                mobileno=lead.new_customer_contact or '',
                bill_addline1=lead.new_customer_address or '',
                compcode=compcode,
                created_by=str(current_user.get('userid') or current_user.get('user_id') or 'System'),
                created_on=datetime.datetime.utcnow()
            )
            db_client.session.add(new_customer)
            db_client.session.flush() # Flush to populate new_customer.vendorid

            # Update lead mapping
            lead.customer_id = new_customer.vendorid
            lead.customer_type = 'EXISTING'
            lead.stage_id = completed_stage.id

            db_client.session.commit()
            return {
                "message": "Lead converted successfully to customer",
                "vendorid": new_customer.vendorid,
                "companyname": new_customer.companyname
            }, 200

        except Exception as e:
            db_client.session.rollback()
            abort(500, f"Database transaction failed: {str(e)}")
