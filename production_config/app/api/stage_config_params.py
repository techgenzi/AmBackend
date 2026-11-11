# from production_config.app.routes.stage import stage_api_route
import datetime

from dns.e164 import query
from flask import request
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import mapper

from ..routes.stage import stage_api_route, param_config_stage_post_model, param_config_stage_list_response_model, \
    create_stage_response, param_config_stage_model_main
from ..models.satge import StageParams
from ipss_utils.ipss_api_doc import list_api_params
from .. import db_client,ipss_db
from .errorhandling import map_sqlalchemy_error_to_http_status
from ..stage_api_doc import params_filters

primary_key='stage_param_id'
@stage_api_route.route('/StageParams')
class ConfigParams(Resource):
    @login_required()
    @stage_api_route.expect(param_config_stage_model_main)
    @stage_api_route.marshal_with(create_stage_response)
    def post(self):
        data=request.json
        stage_id=data.get('stage_id',None)
        is_serialization = data.get('is_serialization', False)
        data=[{**i,**{'stage_id':stage_id}} for i in data.get('params_data')]
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now(),
              # "product_id": pkey if pkey else result.get('primary_key_id')[0]
              }
        postData = [
            {**data.pop(i), **cc} for i in range(len(data) - 1, -1, -1)
            if not data[i].get('stage_param_id')
        ]
        error = ''
        success = False
        try:
            with db_client.session.begin():
                    db_client.session.bulk_insert_mappings(mapper=StageParams, mappings=postData)
                    db_client.session.bulk_update_mappings(mapper=StageParams,mappings=data)
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

    @login_required()
    def put(self):
        data = request.json
        stage_id = data.get('stage_id', None)
        is_serialization = data.get('is_serialization', False)
        data = [{**i, **{'stage_id': stage_id}} for i in data.get('params_data')]
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now(),
              # "product_id": pkey if pkey else result.get('primary_key_id')[0]
              }
        ids = set()
        postData = []
        for i in range(len(data) - 1, -1, -1):
            if data[i].get('stage_param_id'):
                ids.add(data[i].get('stage_param_id'))
            else:
                postData.append({**data.pop(i), **cc})

        ids_tuple = tuple(ids)

        sql_query = text(f'''
        update stage_params 
        set deleted = true
        where stage_id = :stage_id and stage_param_id not in :ids
        ''')

        s = db_client.session
        try:
            with s.begin():
                s.execute(sql_query, {'stage_id': stage_id, 'ids': ids_tuple})
                s.bulk_insert_mappings(mapper=StageParams, mappings=postData)
                s.bulk_update_mappings(mapper=StageParams, mappings=data)


        except SQLAlchemyError as e:
            s.flush()
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': "Records update Successfully"
        }


    per_page = 20

    @stage_api_route.marshal_with(param_config_stage_list_response_model)
    @stage_api_route.doc(params={**list_api_params,**params_filters})
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
        if request.args.get('stage_param_id'):
            sql_con+=' and sp.stage_param_id=:stage_param_id '
        if request.args.get('stage_id'):
            sql_con+=' and sp.stage_id=:stage_id '
        if request.args.get('parameter_id'):
            sql_con+=' and sp.parameter_id=:parameter_id '
        if request.args.get('parameter_type'):
            sql_con += ' and cp.parameter_type=:parameter_type '
        sql_query=text(f'''
        select s.stage_id,s.stage_name,s.is_serialization,json_agg(
        json_build_object(
        'stage_param_id',sp.stage_param_id ,
        'parameter_id',sp.parameter_id,
        'stage_param_value',sp.stage_param_value ,
        'is_eval',sp.is_eval ,
        'description',sp.description,
        'additional',sp.additional,
        'parameter_name',cp.parameter_name,
        'parameter_type',cp.parameter_type
        ) 
        ) params_data from stage_params as sp
        join stage s on s.stage_id =sp.stage_id 
        join config_params as cp on cp.parameter_id=sp.parameter_id
        where sp.deleted is not true and sp.compcode=:ccode {sql_con}
        group by s.stage_id,s.stage_name,s.is_serialization
        limit :limit offset :offset
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,
                                                         limit=results_per_page,
                                                         offset=offset,
                                                         ccode=ccode,
                                                         stage_param_id=request.args.get('stage_param_id'),
                                                         stage_id=request.args.get('stage_id'),
                                                         parameter_id=request.args.get('parameter_id'),
                                                         parameter_type=request.args.get('parameter_type')
                                                         ))
        
        # Populate serialization_params based on is_serialization flag
        for row in sql_query:
            if row.get('is_serialization'):
                row['serialization_params'] = row.get('params_data', [])
            else:
                row['serialization_params'] = []
        sql_count=text(f''' select count(distinct s.stage_id)
        from stage_params as sp
        join stage s on s.stage_id =sp.stage_id 
        join config_params as cp on cp.parameter_id=sp.parameter_id
        where sp.deleted is not true and sp.compcode=:ccode {sql_con}
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,ccode=ccode,
                                                         stage_param_id=request.args.get('stage_param_id'),
                                                         stage_id=request.args.get('stage_id'),
                                                         parameter_id=request.args.get('parameter_id'),
                                                         parameter_type=request.args.get('parameter_type')
                                                         ))
        print("Sdfaede",sql_query)
        return {
            "total_results": sql_count[0].get('count', 0) if len(sql_count) else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query
        }
@stage_api_route.route('/StageParams/<stage_param_id>/')
class ConfigParamsDelete(Resource):
    @login_required()
    def delete(self,stage_param_id):
        """
                Soft delete Products record
                TODO: Make soft delete
                :return:
                """

        result = ipss_db.update_record(
            model=StageParams,
            condition=StageParams.stage_param_id == stage_param_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result
@stage_api_route.route('/StageParams/DeleteByStage/<stage_id>/')
class ConfigParamsDelete(Resource):
    @login_required()
    def delete(self,stage_id):
        """
                Soft delete Products record
                TODO: Make soft delete
                :return:
                """

        result = ipss_db.update_record(
            model=StageParams,
            condition=StageParams.stage_id == stage_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result