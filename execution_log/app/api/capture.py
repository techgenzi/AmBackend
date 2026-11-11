# from production_config.app.routes.stage import execution_log_api_route
import datetime

from flask import request
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..routes.logs import execution_log_api_route, param_config_stage_post_model, \
    param_config_stage_list_response_model, \
    create_execution_log_response, capture_report_model_response
from ..models.logs import ExecutionCaptures
from ipss_utils.ipss_api_doc import list_api_params
from .. import db_client,ipss_db
from .errorhandling import map_sqlalchemy_error_to_http_status


primary_key='capture_id'
@execution_log_api_route.route('/ExecutionCaptures')
class ConfigParams(Resource):
    @login_required()
    @execution_log_api_route.expect(param_config_stage_post_model)
    @execution_log_api_route.marshal_with(create_execution_log_response)
    def post(self):
        data=request.json
        data=data.get('data',[])
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now(),
              # "product_id": pkey if pkey else result.get('primary_key_id')[0]
              }
        postData = [
            {**data.pop(i), **cc} for i in range(len(data) - 1, -1, -1)
            if not data[i].get('capture_id')
        ]
        error = ''
        success = False
        try:
            with db_client.session.begin():
                    db_client.session.bulk_insert_mappings(mapper=ExecutionCaptures, mappings=postData)
                    db_client.session.bulk_update_mappings(mapper=ExecutionCaptures,mappings=data)
                    success = True

        except SQLAlchemyError as e:
            db_client.session.flush()
            db_client.session.rollback()
            return map_sqlalchemy_error_to_http_status(e)
        if success:
            message = "Records created Successfully"
        else:
            message = "There is an Error"
        return {
            'success': success,
            'message': message,
            'error': error,
        }

    per_page = 20

    @execution_log_api_route.marshal_with(param_config_stage_list_response_model)
    @execution_log_api_route.doc(params={**list_api_params,**{}})
    @login_required()
    def get(self):
        """
        List of variant_attribute with pagination
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
        if request.args.get('capture_id'):
            sql_con+=' and sp.capture_id=:capture_id '
        if request.args.get('stage_id'):
            sql_con+=' and sp.stage_id=:stage_id '
        if request.args.get('parameter_id'):
            sql_con+=' and sp.parameter_id=:parameter_id '
        if request.args.get('parameter_type'):
            sql_con += ' and cp.parameter_type=:parameter_type '
        sql_query=text(f'''
        select sp.*,cp.parameter_name,cp.parameter_type,
        s.stage_name,
        p.product_name,p.product_code,p.sku_id
        from execution_captures as sp
        join config_params as cp on cp.parameter_id=sp.parameter_id
        join stage s on s.stage_id=sp.stage_id
        join products p on p.product_id =sp.rawmaterials_id
        where sp.deleted is not true and sp.compcode=:ccode {sql_con}
        order by sp.capture_id desc
        limit :limit offset :offset
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,
                                                         limit=results_per_page,
                                                         offset=offset,
                                                         ccode=ccode,
                                                         capture_id=request.args.get('capture_id'),
                                                         stage_id=request.args.get('stage_id'),
                                                         parameter_id=request.args.get('parameter_id'),
                                                         parameter_type=request.args.get('parameter_type')
                                                         ))
        sql_count=text(f''' select count(*)
         from execution_captures as sp
        join config_params as cp on cp.parameter_id=sp.parameter_id
        join stage s on s.stage_id=sp.stage_id
        join products p on p.product_id =sp.rawmaterials_id
        where sp.deleted is not true and sp.compcode=:ccode {sql_con}
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,ccode=ccode,
                                                         capture_id=request.args.get('capture_id'),
                                                         stage_id=request.args.get('stage_id'),
                                                         parameter_id=request.args.get('parameter_id'),
                                                         parameter_type=request.args.get('parameter_type')
                                                         ))
        return {
            "total_results": sql_count[0].get('count', 0) if len(sql_count) else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query
        }
@execution_log_api_route.route('/ExecutionCaptures/<capture_id>/')
class ConfigParamsDelete(Resource):
    @login_required()
    def delete(self,capture_id):
        """
                Soft delete Products record
                TODO: Make soft delete
                :return:
                """

        result = ipss_db.update_record(
            model=ExecutionCaptures,
            condition=ExecutionCaptures.capture_id == capture_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result
@execution_log_api_route.route('/ExecutionCaptures/Report')
class Report(Resource):
    @login_required()
    @execution_log_api_route.marshal_with(capture_report_model_response)
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con=''
        if request.args.get('stage_id'):
            sql_con+=' and ec.stage_id=:stage_id '
        if request.args.get('prod_plan_id'):
            sql_con+=' and ec.prod_plan_id=:prod_plan_id '
        if request.args.get('operation_date'):
            sql_con+=' and ec.operation_date=cast(:operation_date as date) '
        sql_query=text(f'''
             select ec.stage_id,ec.prod_plan_id,ec.operation_date::date,s.stage_name,
            jsonb_agg(json_build_object(
            cp.parameter_name,ec.stage_param_value,
            'is_eval',ec.is_eval
            )) as captured_parameters
            from execution_captures as ec
            join config_params as cp on cp.parameter_id=ec.parameter_id
            join stage s on s.stage_id=ec.stage_id
            where ec.deleted is not true and ec.compcode=:ccode {sql_con}
            group by  ec.stage_id,ec.prod_plan_id,ec.operation_date::date,s.stage_name
            limit :limit offset :offset
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,
                                                         ccode=ccode,
                                                         stage_id=request.args.get('stage_id'),
                                                         prod_plan_id=request.args.get('prod_plan_id'),
                                                         operation_date=request.args.get('operation_date'),
                                                         limit=results_per_page,
                                                         offset=offset))
        sql_count=text(f'''
        select count(*)
        from execution_captures as ec
            join config_params as cp on cp.parameter_id=ec.parameter_id
            join stage s on s.stage_id=ec.stage_id
            where ec.deleted is not true and ec.compcode=:ccode {sql_con}
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,ccode=ccode,
                                                         stage_id=request.args.get('stage_id'),
                                                         prod_plan_id=request.args.get('prod_plan_id'),
                                                         operation_date=request.args.get('operation_date'),))
        return {
            "total_results": sql_count[0].get('count', 0) if len(sql_count) else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query
        }