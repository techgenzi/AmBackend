import datetime
from pprint import pprint

from flask import request
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import insert, text

from .errorhandling import map_sqlalchemy_error_to_http_status
from ..models.process_config import ProcessConfig
from ..routes.process_config import process_api_route, process_model, create_process_response, update_process_model, \
    process_list_response
from ..api_doc.process_config import process_filter
from .. import ipss_db, db_client

# Primary key
primary_key = 'process_id'


@process_api_route.route('/')
class ProcessApi(Resource):

    @process_api_route.marshal_with(process_list_response)
    @process_api_route.doc(params=list_api_params)
    @process_api_route.doc(params=process_filter)
    @login_required(permissions='process_config.list')
    def get(self):
        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id', None)
        page = int(request.args.get('paged')) if request.args.get('paged') else 1
        result_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0
        process_config_id = request.args.get('process_config_id', None)
        sql_con = ''
        if process_config_id:
            sql_con += ' and process_config.process_id=:process_id '
        query = text(f'''
        select *,count(*) over() AS total_count from process_config
        where deleted is not true and compcode=:compcode {sql_con}
        order by process_id desc
        limit :limit offset :offset
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        process_config_id=process_config_id,
                                                        compcode=compcode,
                                                        limit=result_per_page,
                                                        offset=offset))


        return {
            "total_results": result[0].get('total_count', 0) if result else 0,
            "page": page,
            "results_per_page": result_per_page,
            "results": result
        }

    @process_api_route.expect(process_model)
    @process_api_route.marshal_with(create_process_response)
    @login_required(permissions='process_config.add')
    def post(self):
        data = request.json
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now(),
              "created_by": compcode.get('username')
              }
        s = db_client.session
        primary_key_id = None
        try:
            stmt = (
                insert(ProcessConfig).values(**data, **cc, **{"process_temp": data.get("process_name", "").replace(" ", "").lower()}).returning(ProcessConfig.process_id)
            )
            result = s.execute(stmt)
            primary_key_id = result.scalar()
            s.commit()
        except Exception as e:
            s.flush()
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'primary_key': 'process_id',
            'inserted_id': primary_key_id,
            'success': True,
            'message': "Records created Successfully"
        }


@process_api_route.route(f'/<{primary_key}>')
class ProcessUpdateApi(Resource):

    @staticmethod
    def update_record(data, process_id):
        data.pop(primary_key, None)

        result = ipss_db.update_record(
            model=ProcessConfig,
            condition=ProcessConfig.process_id == process_id,
            values=data
        )
        return result

    @process_api_route.marshal_with(process_model)
    @login_required(permissions='process_config.view')
    def get(self, process_id):
        current_user = request.args.get('current_user')
        compcode = current_user.get('company_id')

        response = (ProcessConfig.query
                    .filter(process_id=process_id, compcode=compcode)
                    .first()
                    )
        return response

    @process_api_route.expect(process_model)
    @process_api_route.marshal_with(update_process_model)
    @login_required(permissions='process_config.edit')
    def put(self, process_id):
        data = request.json
        response = self.update_record(data=data, process_id=process_id)
        return response

    @process_api_route.expect(process_model)
    @process_api_route.marshal_with(update_process_model)
    @login_required(permissions='process_config.edit')
    def patch(self, process_id):
        data = request.json
        response = self.update_record(data=data, process_id=process_id)
        return response

    @process_api_route.marshal_with(update_process_model)
    @login_required(permissions='process_config.delete')
    def delete(self, process_id):
        data = {
            'deleted': True,
            'deleted_at': datetime.datetime.now()
        }
        response = self.update_record(data=data, process_id=process_id)

        return response

