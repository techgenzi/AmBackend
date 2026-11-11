import datetime
from flask import request
from flask_restx import Resource

from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, and_
from ..models.uom import UOM
from ipss_utils.decorators import login_required

from ..routes.uom import uom_api_route, single_uom_model, create_uom_response, uom_list_response, \
    update_uom_response
from .. import ipss_db, db_client
from ..api_doc.api_doc import search_filters


primary_key = 'id'


@uom_api_route.route('/')
class UomApi(Resource):
    per_page = 20
    @uom_api_route.marshal_with(uom_list_response)
    @uom_api_route.doc(params={**list_api_params,**search_filters})
    @login_required(permissions='uom.list')
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
        id = request.args.get('id', None)
        if id:
            sql_con += ' and id=:id '
        sql_query = text(f'''
               select * from uom
               where deleted is not true and compcode=:ccode {sql_con}
               order by id desc
               limit :limit offset :offset
               ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           ccode=ccode,
                                                           id=id
                                                           ))
        sql_count = text(f'''
               select count(*) from uom
               where deleted is not true and compcode=:ccode {sql_con}
               ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           ccode=ccode,
                                                           id=id
                                                           ))
        return {
            "total_results": sql_count[0].get('count', 0) if sql_count else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query
        }

    @login_required(permissions='uom.add')
    @uom_api_route.expect(single_uom_model)
    @uom_api_route.marshal_with(create_uom_response)
    def post(self):
        """
        Create Products record and return inserted id
        :return:
        """
        data = request.json
        uom = data.get('uom', None)
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        val = UOM.query.filter_by(uom=uom, compcode=compcode, deleted=False).first()
        if val:
            return {
                "success": False,
                "message": "Duplicate value"
            }, 409
        result = ipss_db.insert_record(model=UOM, values=data)
        return result


@uom_api_route.route('/<id>/')
class UOMUpdateApi(Resource):
    @staticmethod
    def update_record(data, id):
        data.pop('id', None)
        uom = data.get('uom', None)
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        val = UOM.query.filter(and_(UOM.uom==uom, UOM.compcode==compcode, UOM.deleted==False, UOM.id!=id)).first()
        if val:
            return {
                "success": False,
                "message": "Duplicate value"
            }, 409
        result = ipss_db.update_record(
            model=UOM,
            condition=UOM.id == id,
            values=data
        )
        return result

    @uom_api_route.marshal_with(single_uom_model)
    @login_required(permissions='uom.view')
    def get(self, id):
        user = UOM.query.filter_by(id=int(id)).first()
        return user

    @uom_api_route.expect(single_uom_model)
    @uom_api_route.marshal_with(update_uom_response)
    @login_required(permissions='uom.edit')
    def put(self, id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, id)
        return response

    @uom_api_route.expect(single_uom_model)
    @uom_api_route.marshal_with(update_uom_response)
    @login_required(permissions='uom.edit')
    def patch(self, id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, id)
        return response

    @uom_api_route.marshal_with(update_uom_response)
    @login_required(permissions='uom.delete')
    def delete(self, id):
        """
        Soft delete Products record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=UOM,
            condition=UOM.id == id,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################

    
    
