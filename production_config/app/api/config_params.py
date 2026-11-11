# from production_config.app.routes.stage import stage_api_route
import datetime

from flask import request
from flask_restx import Resource
from ipss_utils.decorators import login_required
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import mapper

from ..routes.stage import stage_api_route, param_config_post_model, param_config_list_response_model, \
    create_stage_response
from ..models.satge import Params
from ipss_utils.ipss_api_doc import list_api_params
from .. import db_client,ipss_db
from .errorhandling import map_sqlalchemy_error_to_http_status
from ..stage_api_doc import params_filters

primary_key='parameter_id'
@stage_api_route.route('/ConfigParams')
class ConfigStageParams(Resource):
    @login_required()
    @stage_api_route.expect(param_config_post_model)
    @stage_api_route.marshal_with(create_stage_response)
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
            if not data[i].get('parameter_id')
        ]
        error = ''
        success = False
        try:
            with db_client.session.begin():
                    db_client.session.bulk_insert_mappings(mapper=Params, mappings=postData)
                    db_client.session.bulk_update_mappings(mapper=Params,mappings=data)
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

    @stage_api_route.marshal_with(param_config_list_response_model)
    @stage_api_route.doc(params={**list_api_params,**params_filters})
    @login_required()
    def get(self):
        """
        List of variant_attribute with pagination
        TODO: Search
        :return:
        """
        query = Params.query.order_by(Params.parameter_id.desc())
        # Filtering by parent id (Primary Table ID)
        if request.args.get('parameter_id', None):
            query = query.filter_by(parameter_id=request.args.get('parameter_id'))
        if request.args.get('parameter_type'):
            query=query.filter_by(parameter_type=request.args.get('parameter_type'))


        response = ipss_db.paginated_results(
            model=Params,
            query=query,
            primary_key=primary_key
        )
        return response
@stage_api_route.route('/ConfigParams/<parameter_id>/')
class ConfigStageParamsDelete(Resource):
    @login_required()
    def delete(self,parameter_id):
        """
                Soft delete Products record
                TODO: Make soft delete
                :return:
                """

        result = ipss_db.update_record(
            model=Params,
            condition=Params.parameter_id == parameter_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result