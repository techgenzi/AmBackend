import datetime
from flask import request
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_api_doc import list_api_params
from ..models.tenant_config import TenantConfiguration
from ..routes.tenant_config import (
    custom_config_api_route,
    custom_config_list_response,
    create_custom_config_model,
    create_custom_config_response
)
from .. import ipss_db

primary_key = 'id'

@custom_config_api_route.route('/')
class CustomConfigApi(Resource):
    @custom_config_api_route.marshal_with(custom_config_list_response)
    @custom_config_api_route.doc(params={
        **list_api_params,
        'module_name': 'Module name (e.g. PO)',
        'config_type': 'Configuration type (e.g. Fields, Print)'
    })
    @login_required()
    def get(self):
        """
        List or retrieve tenant configurations by module_name and config_type
        """
        current_user = request.args.get('current_user') or {}
        compcode = current_user.get('company_id', None)
        module_name = request.args.get('module_name')
        config_type = request.args.get('config_type')

        query = TenantConfiguration.query.filter_by(deleted=False)
        if compcode:
            query = query.filter_by(compcode=compcode)
        if module_name:
            query = query.filter_by(module_name=module_name)
        if config_type:
            query = query.filter_by(config_type=config_type)

        query = query.order_by(TenantConfiguration.id.desc())

        response = ipss_db.paginated_results(
            model=TenantConfiguration,
            query=query,
            primary_key=primary_key
        )
        return response

    @login_required()
    @custom_config_api_route.expect(create_custom_config_model)
    @custom_config_api_route.marshal_with(create_custom_config_response)
    def post(self):
        """
        Create or Update tenant configuration (Upsert)
        """
        current_user = request.args.get('current_user') or {}
        compcode = current_user.get('company_id', None)
        username = current_user.get('username', 'system')

        data = request.json
        data.pop(primary_key, None)

        module_name = data.get('module_name')
        config_type = data.get('config_type')

        # Check if configuration already exists for this tenant
        existing = TenantConfiguration.query.filter_by(
            compcode=compcode,
            module_name=module_name,
            config_type=config_type,
            deleted=False
        ).first()

        if existing:
            # Upsert: Update existing record's config_data and author
            result = ipss_db.update_record(
                model=TenantConfiguration,
                condition=TenantConfiguration.id == existing.id,
                values={
                    'config_data': data.get('config_data'),
                    'created_by': username
                }
            )
            return {
                "success": True,
                "message": "Configuration has been updated successfully",
                "id": existing.id
            }

        # Insert a new record if it doesn't exist
        data['compcode'] = compcode
        data['created_by'] = username
        result = ipss_db.insert_record(
            model=TenantConfiguration,
            values=data
        )

        return ipss_db.created_response(
            result=result,
            message="Configuration has been created successfully",
            primary_key=primary_key
        )
