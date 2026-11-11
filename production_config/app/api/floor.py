import datetime
from flask import request
from flask_restx import Resource

from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text
from ..models.floor import Floor
from ipss_utils.decorators import login_required

from ..routes.floor import floor_api_route, single_floor_model, create_floor_response, floor_list_response, \
    update_floor_response
from .. import ipss_db, db_client
from ..floor_api_doc import search_filters
from .stage import duplicate


primary_key = 'floor_id'


@floor_api_route.route('/')
class FloorApi(Resource):
    per_page = 20
    @floor_api_route.marshal_with(floor_list_response)
    @floor_api_route.doc(params={**list_api_params,**search_filters})
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
        floor_id = request.args.get('floor_id', None)
        if floor_id:
            sql_con += ' and floor_id=:floor_id '
        sql_query = text(f'''
               select * from floor
               where deleted is not true and compcode=:ccode {sql_con}
               order by floor_id desc
               limit :limit offset :offset
               ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           ccode=ccode,
                                                           floor_id=floor_id
                                                           ))
        sql_count = text(f'''
               select count(*) from floor
               where deleted is not true and compcode=:ccode {sql_con}
               ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           ccode=ccode,
                                                           floor_id=floor_id
                                                           ))
        return {
            "total_results": sql_count[0].get('count', 0) if len(sql_count) else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query
        }

    @login_required(permissions='floor.add')
    @floor_api_route.expect(single_floor_model)
    @floor_api_route.marshal_with(create_floor_response)
    def post(self):
        """
        Create Products record and return inserted id
        :return:
        """
        data = request.json
        floor_name = data.get('floor_name', None)
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        # val = Floor.query.filter_by(floor_name=floor_name,compcode=compcode).first()
        # if val:
        #     return {
        #         "success":False,
        #         "message": "Duplicate value"
        #     },409
        duplicate(table_name='floor', data={'floor_name':floor_name, 'compcode':compcode})
        result = ipss_db.insert_record(model=Floor, values=data)
        return result


@floor_api_route.route('/<floor_id>/')
class FloorUpdateApi(Resource):
    @staticmethod
    def update_record(data, floor_id):
        data.pop('floor_id', None)
        floor_name = data.get('floor_name', None)
        data['compcode'] = request.args.get('current_user',{}).get('company_id', None)
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        duplicate(table_name='floor', data={'floor_name':floor_name, 'compcode':compcode}, pkey={'floor_id': floor_id})
        result = ipss_db.update_record(
            model=Floor,
            condition=Floor.floor_id == floor_id,
            values=data
        )
        return result

    @floor_api_route.marshal_with(single_floor_model)
    @login_required(permissions='floor.view')
    def get(self, floor_id):
        """
        Read user record / single record
        :param id:
        :return:
        """

        user = Floor.query.filter_by(floor_id=int(floor_id)).first()
        return user

    @floor_api_route.expect(single_floor_model)
    @floor_api_route.marshal_with(update_floor_response)
    @login_required(permissions='floor.edit')
    def put(self, floor_id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, floor_id)
        return response

    @floor_api_route.expect(single_floor_model)
    @floor_api_route.marshal_with(update_floor_response)
    @login_required(permissions='floor.edit')
    def patch(self, floor_id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, floor_id)
        return response

    @floor_api_route.marshal_with(update_floor_response)
    @login_required(permissions='floor.delete')
    def delete(self, floor_id):
        """
        Soft delete Products record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=Floor,
            condition=Floor.floor_id == floor_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################

    
    
