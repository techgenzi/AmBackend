import calendar
import datetime

from flask import request
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import and_, text

from ..api_doc import apk_upload_filter
from ..models.apk_upload import APKUpload
from ..routes.apk_upload import apk_upload_api_route, apk_upload_list_response, get_apk_upload_response, \
    create_apk_upload_model, update_apk_upload_model, update_apk_upload_response
from .. import ipss_db, db_client

# Primary key
primary_key = 'apk_upload_id'


def update_active_apk():
    update_query = text(f"""UPDATE apk_upload
                            SET active = false
                        """)
    db_client.engine.execute(update_query)


@apk_upload_api_route.route('/')
class ColorConfigApi(Resource):
    per_page = 1500

    @apk_upload_api_route.marshal_with(apk_upload_list_response)
    @apk_upload_api_route.doc(params=list_api_params)
    @apk_upload_api_route.doc(params=apk_upload_filter)
    @login_required(permissions='mobileapp_download.list')
    def get(self):
        active = request.args.get('active')
        app_id = request.args.get('app_id')
        compcode = request.args.get('current_user', {}).get('company_id')
        version_name = request.args.get('version_name')
        version_no = request.args.get('version_no')
        apk_query = APKUpload.query.filter_by(deleted=False).order_by(APKUpload.apk_upload_id.desc())
        apk_query = apk_query.filter_by(compcode=compcode)
        if active:
            is_active = active.lower() == 'true'
            apk_query = apk_query.filter_by(active=is_active)
        if app_id:
            apk_query = apk_query.filter_by(app_id=app_id)
        if version_name:
            apk_query = apk_query.filter_by(version_name=version_name)
        if version_no:
            apk_query = apk_query.filter_by(version_no=version_no)
        response = ipss_db.paginated_results(
            model=APKUpload,
            query=apk_query,
            primary_key=primary_key
        )
        return response

    @apk_upload_api_route.expect(create_apk_upload_model)
    @login_required(permissions='mobileapp_download.add')
    def post(self):
        data = request.json
        data.pop(primary_key, None)
        if data.get('active'):
            update_active_apk()

        response = ipss_db.insert_record(model=APKUpload,
                                         values=data)
        return {
            'success': True if response['primary_key_id'] else False,
            'error': response['error'],
            'primary_key_id': response['primary_key_id'][0]
        }


@apk_upload_api_route.route('/<apk_upload_id>')
class ColorConfigUpdateApi(Resource):

    @staticmethod
    def update_record(data, apk_upload_id):
        data.pop('color_id', None)

        if data.get('active'):
            update_active_apk()

        result = ipss_db.update_record(
            model=APKUpload,
            condition=APKUpload.apk_upload_id == apk_upload_id,
            values=data
        )
        return result

    @apk_upload_api_route.marshal_with(get_apk_upload_response)
    # @user_verify(permission='mobileapp_download.view',db_client=db_client)
    @login_required(permissions='mobileapp_download.view')
    def get(self, apk_upload_id):
        response = APKUpload.query.filter_by(apk_upload_id=apk_upload_id).first()
        return response

    @apk_upload_api_route.expect(update_apk_upload_model)
    @apk_upload_api_route.marshal_with(update_apk_upload_response)
    # @user_verify(permission='mobileapp_download.edit',db_client=db_client)
    @login_required(permissions='mobileapp_download.edit')
    def put(self, apk_upload_id):
        data = request.json
        response = self.update_record(data=data, apk_upload_id=apk_upload_id)
        return response

    @apk_upload_api_route.expect(update_apk_upload_model)
    @apk_upload_api_route.marshal_with(update_apk_upload_response)
    @login_required(permissions='mobileapp_download.edit')
    # @user_verify(permission='mobileapp_download.edit',db_client=db_client)
    def patch(self, apk_upload_id):
        data = request.json
        response = self.update_record(data=data, apk_upload_id=apk_upload_id)
        return response

    @apk_upload_api_route.marshal_with(update_apk_upload_response)
    # @user_verify(permission='mobileapp_download.delete',db_client=db_client)
    @login_required(permissions='mobileapp_download.delete')
    def delete(self, apk_upload_id):
        data = {
            'deleted': True,
            'deleted_at': datetime.datetime.now()
        }
        response = self.update_record(data=data, apk_upload_id=apk_upload_id)

        return response
