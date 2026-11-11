import datetime
from pprint import pprint

from flask import request
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import insert, text

from .errorhandling import map_sqlalchemy_error_to_http_status
from ..models.line_config import LineConfig
from ..routes.line_config import line_config_api_route, line_config_list_response, \
    create_line_config_model, create_line_config_response, get_line_config_response, \
    update_line_config_model, update_line_config_response
from ..api_doc.line_config import line_config_filters
from .. import ipss_db, db_client

# Primary key
primary_key = 'line_config_id'


@line_config_api_route.route('/')
class LineConfigApi(Resource):
    per_page = 1500

    @line_config_api_route.marshal_with(line_config_list_response)
    @line_config_api_route.doc(params=list_api_params)
    @line_config_api_route.doc(params=line_config_filters)
    @login_required()
    def get(self):
        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id', None)
        page = int(request.args.get('paged')) if request.args.get('paged') else 1
        result_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0
        line_config_id = request.args.get('line_config_id', None)
        sql_con = ''
        if line_config_id:
            sql_con += ' and line_config.line_config_id=:line_config_id '
        query = text(f'''
        select * from line_config
        where deleted is not true and compcode=:compcode {sql_con}
        order by line_config_id desc
        limit :limit offset :offset
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        line_config_id=line_config_id,
                                                        compcode=compcode,
                                                        limit=result_per_page,
                                                        offset=offset))

        # pprint(result)

        count_query = text(f'''
        select count(*) from line_config
        where deleted is not true and compcode=:compcode {sql_con}
        ''')
        sql_count = query_to_dict(db_client.engine.execute(count_query,
                                                           compcode=compcode,
                                                           line_config_id=line_config_id))

        return {
            "total_results": sql_count[0].get('count', 0) if sql_count else 0,
            "page": page,
            "results_per_page": result_per_page,
            "results": result
        }

    @line_config_api_route.expect(create_line_config_model)
    @line_config_api_route.marshal_with(create_line_config_response)
    @login_required()
    def post(self):
        data = request.json
        # remove primary key if exists
        data.pop(primary_key, None)
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now(),
              "created_by": compcode.get('username')
              }
        s = db_client.session
        primary_key_id = None
        try:
            stmt = (
                insert(LineConfig).values(**data, **cc, **{"line_name_temp": data.get("line_name", "").replace(" ", "").lower()}).returning(LineConfig.line_config_id)
            )
            result = s.execute(stmt)
            primary_key_id = result.scalar()
            s.commit()
        except Exception as e:
            s.flush()
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'primary_key': 'line_config_id',
            'inserted_id': primary_key_id,
            'success': True,
            'message': "Records created Successfully"
        }


@line_config_api_route.route(f'/<{primary_key}>')
class LineConfigUpdateApi(Resource):

    @staticmethod
    def update_record(data, line_config_id):
        current_user = request.args.get('current_user')
        compcode = current_user.get('company_id')

        data.pop(primary_key, None)

        result = ipss_db.update_record(
            model=LineConfig,
            condition=LineConfig.line_config_id == line_config_id,
            values=data
        )
        return result

    @line_config_api_route.marshal_with(get_line_config_response)
    @login_required()
    def get(self, line_config_id):
        current_user = request.args.get('current_user')
        compcode = current_user.get('company_id')

        response = (LineConfig.query
                    .filter(line_config_id=line_config_id, compcode=compcode)
                    .first()
                    )
        return response

    @line_config_api_route.expect(update_line_config_model)
    @line_config_api_route.marshal_with(update_line_config_response)
    @login_required()
    def put(self, line_config_id):
        data = request.json
        response = self.update_record(data=data, line_config_id=line_config_id)
        return response

    @line_config_api_route.expect(update_line_config_model)
    @line_config_api_route.marshal_with(update_line_config_response)
    @login_required()
    def patch(self, line_config_id):
        data = request.json
        response = self.update_record(data=data, line_config_id=line_config_id)
        return response

    @line_config_api_route.marshal_with(update_line_config_response)
    # @login_required(permissions='line.delete')
    @login_required()
    def delete(self, line_config_id):
        data = {
            'deleted': True,
            'deleted_at': datetime.datetime.now()
        }
        response = self.update_record(data=data, line_config_id=line_config_id)

        return response

