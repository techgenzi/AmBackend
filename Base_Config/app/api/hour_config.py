import datetime

from flask import request
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from ..models.line_config import HourConfig
from ..routes.hour_config import line_config_api_route,bulk_post_hour_model,list_response_model,create_record_response_data,update_line_config_response
from .. import db_client,ipss_db
from .errorhandling import map_sqlalchemy_error_to_http_status
primary_key='record_id'
@line_config_api_route.route('/')
class HourManagement(Resource):
    @line_config_api_route.marshal_with(list_response_model)
    @line_config_api_route.doc(params={**list_api_params})
    @login_required()
    def get(self):
        """
        List of Products with pagination
        TODO: Search
        :return:
        """
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con = ''
        record_id = request.args.get('record_id', None)
        if record_id:
            sql_con += ' and record_id=:record_id '
        active_only = request.args.get('active_only', None)
        if active_only == 'true':
            sql_con += ' and is_active is not false '
        sql_query = text(f'''
                       select * from hour_config
                       where deleted is not true and compcode=:ccode {sql_con}
                       order by record_id desc
                       limit :limit offset :offset
                       ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           ccode=ccode,
                                                           record_id=record_id
                                                           ))
        sql_count = text(f'''
                       select count(*) from hour_config
                       where deleted is not true and compcode=:ccode {sql_con}
                       ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           ccode=ccode,
                                                           record_id=record_id
                                                           ))
        return {
            "total_results": sql_count[0].get('count', 0) if sql_count else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query
        }


    @login_required(permissions='production_hours.add')
    @line_config_api_route.expect(bulk_post_hour_model)
    @line_config_api_route.marshal_with(create_record_response_data)
    def post(self):
        """
        Create variant_attribute record and return inserted id
        :return:
        """
        data = request.json
        data = data.get('data', None)
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": str(datetime.datetime.now()),
              "created_by": compcode.get('username')
              # "product_id": pkey if pkey else result.get('primary_key_id')[0]
              }
        updateData = [{**data.pop(i), **cc} for i in range(len(data) - 1, -1, -1) if
                      data[i].get('record_id')]
        data = [{**i, **cc} for i in data]
        error = ''
        message = None
        print("Dfsdfsdfd",data,updateData)
        try:
            with db_client.session.begin():

                if updateData:
                    db_client.session.bulk_update_mappings(mapper=HourConfig, mappings=updateData)
                if data:
                    db_client.session.bulk_insert_mappings(mapper=HourConfig, mappings=data)
        except SQLAlchemyError as e:
            # error = str(e)
            db_client.session.rollback()
            db_client.session.flush()
            res = map_sqlalchemy_error_to_http_status(e)
            print("FGH", res)
            return res
        success = False if error else True
        if success:
            message = "Records created Successfully"
        return {
            'success': success,
            'message': message,
            'error': error,
        }



@line_config_api_route.route(f'/<{primary_key}>')
class LineConfigUpdateApi(Resource):

    @line_config_api_route.marshal_with(update_line_config_response)
    # @login_required(permissions='line.delete')
    @login_required()
    def delete(self, record_id):
        data = {
            'deleted': True,
            'deleted_at': datetime.datetime.now()
        }
        data.pop(primary_key, None)

        result = ipss_db.update_record(
            model=HourConfig,
            condition=HourConfig.record_id == record_id,
            values=data
        )

        return result