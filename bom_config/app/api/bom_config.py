import datetime
from flask import request
from flask_restx import Resource, abort

from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text
from ..models.bom_config import BomConfig
from ipss_utils.decorators import login_required

from ..routes.bom_config import bom_config_api_route, single_bom_config_model, create_bom_config_response, bom_config_list_response, \
    update_bom_config_response
from .. import ipss_db, db_client
from ..bom_config_api_doc import search_filters

primary_key = 'floor_id'

# def duplicate(table_name='',pkey={} ,data={}):
#     sql_con = ''
#     if data:
#         for key, value in data.items():
#             sql_con += f"{key} = :{key} and "
#     if pkey:
#         for key, value in pkey.items():
#             sql_con += f"{key} != :{key} and "
#
#     sql_query = text(f'''
#     select * from {table_name} where {sql_con} deleted is not true
#     ''')
#     val = query_to_dict(db_client.engine.execute(sql_query, **data, **pkey))
#     if val:
#         abort(409, "Already exist")
#     return


@bom_config_api_route.route('/')
class StageApi(Resource):
    per_page = 20

    @bom_config_api_route.marshal_with(bom_config_list_response)
    @bom_config_api_route.doc(params={**list_api_params, **search_filters})
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
        offset = (paged - 1) * results_per_page if (paged - 1) * results_per_page else 0
        sql_con = ''
        bom_config_id = request.args.get('bom_config_id', None)
        map_type = request.args.get('map_type', None)
        if bom_config_id:
            sql_con += ' and bom_config_id=:bom_config_id '
        if map_type:
            sql_con += ' and map_type=:map_type '

        sql_query = text(f'''
                select * from bom_config where deleted is not true and compcode=:ccode {sql_con} and 1=1
                order by bom_config_id desc
                limit :limit offset :offset
               ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           ccode=ccode,
                                                           bom_config_id=bom_config_id,
                                                           map_type=map_type
                                                           ))
        sql_count = text(f'''
                select count(*) from bom_config where deleted is not true and compcode=:ccode {sql_con} and 1=1
               ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           ccode=ccode,
                                                           bom_config_id=bom_config_id,
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           map_type=map_type
                                                           ))
        return {
            "total_results": sql_count[0].get('count', 0) if sql_count else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query
        }

    @login_required()
    @bom_config_api_route.expect(single_bom_config_model)
    @bom_config_api_route.marshal_with(create_bom_config_response)
    def post(self):
        """
        Create Products record and return inserted id
        :return:
        """
        data = request.json
        product_id = data.get('product_id', None)
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now()
              }
        # duplicate(table_name='bom_config', data={'compcode': compcode, 'product_id': product_id})
        data = {**data, **cc}
        result = ipss_db.insert_record(model=BomConfig, values=data)
        return result



@bom_config_api_route.route('/<bom_config_id>/')
class StageUpdateApi(Resource):
    @staticmethod
    def update_record(data, bom_config_id):
        data.pop('bom_config_id', None)
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        data['compcode'] = compcode
        #duplicate(table_name='bom_config', data=data, pkey={'bom_config_id':bom_config_id})
        result = ipss_db.update_record(
            model=BomConfig,
            condition=BomConfig.bom_config_id == bom_config_id,
            values=data
        )
        return result

    @bom_config_api_route.marshal_with(single_bom_config_model)
    @login_required()
    def get(self, bom_config_id):
        """
        Read user record / single record
        :param id:
        :return:
        """

        user = BomConfig.query.filter_by(bom_config_id=int(bom_config_id)).first()
        return user

    @bom_config_api_route.expect(single_bom_config_model)
    @bom_config_api_route.marshal_with(update_bom_config_response)
    @login_required()
    def put(self, bom_config_id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, bom_config_id)
        return response

    @bom_config_api_route.expect(single_bom_config_model)
    @bom_config_api_route.marshal_with(update_bom_config_response)
    @login_required()
    def patch(self, bom_config_id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, bom_config_id)
        return response

    @bom_config_api_route.marshal_with(update_bom_config_response)
    @login_required()
    def delete(self, bom_config_id):
        """
        Soft delete Products record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=BomConfig,
            condition=BomConfig.bom_config_id == bom_config_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################



