import datetime
from flask import request
from flask_restx import Resource, abort

from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text
from ..models.floor_stage import FloorStageMap
from ipss_utils.decorators import login_required

from ..routes.floor_stage import floor_stage_api_route, single_floor_stage_model, create_floor_stage_response, \
    floor_stage_list_response, \
    update_floor_stage_response, floor_stage_post
from .. import ipss_db, db_client
from ..floor_stage_api_doc import search_filters
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError
from .errorhandling import map_sqlalchemy_error_to_http_status, update_local

primary_key = 'floor_id'

@floor_stage_api_route.route('/')
class StageApi(Resource):
    per_page = 20

    @floor_stage_api_route.marshal_with(floor_stage_list_response)
    @floor_stage_api_route.doc(params={**list_api_params, **search_filters})
    @login_required()
    def get(self):
        """
        List of Products with pagination
        TODO: Search
        :return:
        """
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page if (paged - 1) * results_per_page else 0
        sql_con = ''
        floor_stage_id = request.args.get('floor_stage_id', None)
        floor_id = request.args.get('floor_id', None)
        stage_id = request.args.get('stage_id', None)
        if floor_stage_id:
            sql_con += ' and fsm.floor_stage_id=:floor_stage_id '
        if stage_id:
            sql_con += ' and fsm.stage_id=:stage_id '
        if floor_id:
            sql_con += ' and fsm.floor_id=:floor_id '

        sql_query = text(f'''
                    select 
                    fsm.floor_id,
                    f.floor_name,
                    JSON_AGG(
                        JSON_BUILD_OBJECT(
                            'floor_stage_id', fsm.floor_stage_id,
                            'stage_id', fsm.stage_id,
                            'stage_name', s.stage_name
                        )
                    ) AS stages
                FROM 
                    floor_stage_map AS fsm
                LEFT JOIN 
                    floor AS f ON fsm.floor_id = f.floor_id
                LEFT JOIN 
                    stage AS s ON s.stage_id = fsm.stage_id
                WHERE 
                    fsm.deleted IS NOT TRUE 
                    AND f.deleted IS NOT TRUE 
                    AND s.deleted IS NOT TRUE 
                    AND fsm.compcode = :compcode 
                    {sql_con}
                GROUP BY 
                    fsm.floor_id, f.floor_name
                ORDER BY 
                    fsm.floor_id desc
                LIMIT :limit 
                OFFSET :offset;
               ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           compcode=compcode,
                                                           floor_stage_id=floor_stage_id,
                                                           stage_id=stage_id,
                                                           floor_id=floor_id
                                                           ))
        sql_count = text(f'''
                select count( distinct fsm.floor_id) from floor_stage_map as fsm
                LEFT JOIN 
                    floor AS f ON fsm.floor_id = f.floor_id
                LEFT JOIN 
                    stage AS s ON s.stage_id = fsm.stage_id
                WHERE 
                    fsm.deleted IS NOT TRUE 
                    AND f.deleted IS NOT TRUE 
                    AND s.deleted IS NOT TRUE 
                    AND fsm.compcode = :compcode  {sql_con}
               ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           compcode=compcode,
                                                           floor_stage_id=floor_stage_id,
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           stage_id=stage_id,
                                                           floor_id=floor_id
                                                           ))

        print(sql_query)
        return {
            "total_results": sql_count[0].get('count', 0) if sql_count else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query
        }
    @floor_stage_api_route.expect(floor_stage_post)
    @floor_stage_api_route.marshal_with(create_floor_stage_response)
    @login_required(permissions='floorstage.add')
    def post(self):
        data = request.json
        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id')
        items = data.pop('stages', [])
        floor_id = data.get('floor_id', None)
        cc = {
            'compcode':  compcode,
            'created_on': datetime.datetime.now(),
            'floor_id': floor_id
        }
        if items and floor_id:
            for i in items:
                i.update(cc)
        else:
            return {
                'success': False,
                'message': 'Value required to bind data'
            }, 400
        s = db_client.session
        try:
            s.bulk_insert_mappings(mapper=FloorStageMap, mappings=items)
            s.commit()
        except SQLAlchemyError as e:
            s.rollback()
            s.flush()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': 'craeted successfully'
        }




@floor_stage_api_route.route('/<floor_id>/')
class StageUpdateApi(Resource):
    @staticmethod
    def update_record(data, floor_id):
        data.pop('floor_stage_id', None)
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        data['compcode'] = compcode
        result = update_local(
            model=FloorStageMap,
            condition=FloorStageMap.floor_id == floor_id,
            values=data
        )
        return result

    @staticmethod
    def put_method(data, floor_id):
        floor_id = data.pop('floor_id', None)
        items = data.pop('stages', [])
        success = False
        error = ''
        s = db_client.session
        try:
            with s.begin():
                compcode = request.args.get('current_user', {})
                cc = {
                    "compcode": compcode.get('company_id'),
                    "modified_on": datetime.datetime.now()
                }
                new_cc = {
                    "compcode": compcode.get('company_id'),
                    "created_on": datetime.datetime.now()
                }

                updateitemData = []
                itemdata = []
                current_ids = set()

                for item in items:
                    if item.get('floor_stage_id'):
                        updateitemData.append({**item, **cc, 'deleted': False})
                    else:
                        itemdata.append({**item, **new_cc, "floor_id": floor_id, "deleted": False})
                    if item.get('floor_stage_id'):
                        current_ids.add(item.get('floor_stage_id'))
                existing_records = s.query(FloorStageMap).filter(
                    FloorStageMap.floor_id == floor_id,
                    FloorStageMap.deleted != True
                ).all()

                existing_ids = {record.floor_stage_id for record in existing_records}

                to_delete_ids = existing_ids - current_ids

                print(to_delete_ids)

                if to_delete_ids:
                    s.query(FloorStageMap).filter(
                        FloorStageMap.floor_stage_id.in_(to_delete_ids)
                    ).update({"deleted": True}, synchronize_session=False)

                if updateitemData:
                    s.bulk_update_mappings(mapper=FloorStageMap, mappings=updateitemData)
                if itemdata:
                    s.bulk_insert_mappings(mapper=FloorStageMap, mappings=itemdata)

                success = True

        except SQLAlchemyError as e:
            s.flush()
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': success,
            'message': "Update successful" if success else "Error in update",
            'error': error
        }

    @floor_stage_api_route.marshal_with(single_floor_stage_model)
    @login_required(permissions='floorstage.view')
    def get(self, floor_id):
        """
        Read user record / single record
        :param id:
        :return:
        """

        user = FloorStageMap.query.filter_by(floor_id=int(floor_id)).all()
        return user

    @floor_stage_api_route.expect(single_floor_stage_model)
    @floor_stage_api_route.marshal_with(update_floor_stage_response)
    @login_required(permissions='floorstage.edit')
    # @login_required()
    def put(self, floor_id):

        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.put_method(data,floor_id)
        return response

    @floor_stage_api_route.expect(single_floor_stage_model)
    @floor_stage_api_route.marshal_with(update_floor_stage_response)
    @login_required(permissions='floorstage.edit')
    def patch(self, floor_id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, floor_id)
        return response

    @floor_stage_api_route.marshal_with(update_floor_stage_response)
    @login_required(permissions='floorstage.edit')
    # @login_required()
    def delete(self, floor_id):
        """
        Soft delete Products record
        TODO: Make soft delete
        :return:
        """

        result = update_local(
            model=FloorStageMap,
            condition=FloorStageMap.floor_id == floor_id,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################



