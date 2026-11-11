import datetime
from flask import request
from flask_restx import Resource

from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, and_
from ..models.style import Style, StyleProduct
from ..api.errorhandling import map_sqlalchemy_error_to_http_status
from ipss_utils.decorators import login_required

from ..routes.style import style_api_route, single_style_model, create_style_response, style_list_response, \
    update_style_response, style_product_api_route, style_product_list_response, single_style_product_model
from .. import ipss_db, db_client
from ..api_doc.style_api_doc import search_filters, style_product_bulk_post_fields


@style_api_route.route('/')
class StyleApi(Resource):

    @style_api_route.marshal_with(style_list_response)
    @style_api_route.doc(params={**list_api_params, **search_filters})
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
        id = request.args.get('style_id', None)
        if id:
            sql_con += ' and style_id=:id '
        sql_query = text(f'''
               select s.*,va.variant_attribute_name as attribute_name,count(*) over() as total_results from style s
               left join variant_attribute va on s.attribute_id=va.variant_attribute_id
               where s.deleted is not true and s.compcode=:ccode {sql_con}
               order by s.style_id desc
               limit :limit offset :offset
               ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           ccode=ccode,
                                                           id=id
                                                           ))
        return {
            "total_results": sql_query[0].get('total_results', 0) if sql_query else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query
        }

    @login_required(permissions='uom.add')
    @style_api_route.expect(single_style_model)
    @style_api_route.marshal_with(create_style_response)
    def post(self):
        """
        Create Products record and return inserted id
        :return:
        """
        data = request.json
        style_code = data.get('style_code', None)
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        try:
            val = Style.query.filter_by(style_code=style_code, compcode=compcode, deleted=False).first()
            if val:
                return {
                    "success": False,
                    "message": "Duplicate value"
                }, 409
            result = ipss_db.insert_record(model=Style, values=data)
            return result

        except Exception as e:
            return map_sqlalchemy_error_to_http_status(e)


@style_api_route.route('/<id>/')
class StyleUpdateApi(Resource):
    @staticmethod
    def update_record(data, id):
        data.pop('id', None)
        style_code = data.get('style_code', None)
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        val = Style.query.filter(
            and_(Style.style_code == style_code, Style.compcode == compcode, Style.deleted == False, Style.style_id != id)).first()
        if val:
            return {
                "success": False,
                "message": "Duplicate value"
            }, 409

        result = ipss_db.update_record(
            model=Style,
            condition=Style.style_id == id,
            values=data
        )
        return result

    @style_api_route.marshal_with(single_style_model)
    @login_required()
    def get(self, id):
        user = Style.query.filter_by(style_id=int(id)).first()
        return user

    @style_api_route.expect(single_style_model)
    @style_api_route.marshal_with(update_style_response)
    @login_required()
    def put(self, id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, id)
        return response

    @style_api_route.expect(single_style_model)
    @style_api_route.marshal_with(update_style_response)
    @login_required()
    def patch(self, id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, id)
        return response

    @style_api_route.marshal_with(update_style_response)
    @login_required()
    def delete(self, id):
        """
        Soft delete Products record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=Style,
            condition=Style.style_id == id,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result


@style_product_api_route.route('/')
class StyleProductApi(Resource):

    @style_product_api_route.marshal_with(style_product_list_response)
    @style_product_api_route.doc(params={**list_api_params, **search_filters})
    @login_required()
    def get(self):
        """
        List of Products with pagination
        """
        current_user = request.args.get('current_user', {})
        company_id = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        style_id = request.args.get('style_id', None)
        sql_con = ''

        if style_id:
            sql_con += ' and sp.style_id=:style_id '

        query = text(f'''
        select sp.style_id,s.style_code,count(*) over() as total_results,
        json_agg(
        json_build_object(
            'style_product_id', sp.style_product_id,
            'product_id', sp.product_id,
            'product_code', p.product_code,
            'product_name', p.product_name,
            'sku_id', p.sku_id,
            'deleted', sp.deleted
        )) as data
        from style_product sp
        left join style s on sp.style_id = s.style_id
        left join products p on sp.product_id = p.product_id
        where sp.deleted is not true and sp.compcode=:company_id {sql_con}
        group by sp.style_id,s.style_code
        order by sp.style_id desc
        limit :limit offset :offset
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        company_id=company_id,
                                                        style_id=style_id,
                                                        limit=results_per_page,
                                                        offset=offset
                                                        ))

        return {
            "total_results": result[0].get('total_results', 0) if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            "results": result
        }

    @login_required()
    @style_product_api_route.expect(single_style_product_model)
    def post(self):

        """
        Bulk insert style products
        :return:
        """
        data = request.json
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        s = db_client.session
        try:
            post_data = []
            update_data = []
            cc = {
                'compcode': compcode,
                'created_by': cur.get('username')
            }
            updated_cc = {
                'modified_by': cur.get('username'),
                'modified_on': datetime.datetime.now()
            }
            records = data.get('data')
            style = {'style_id': data.get('style_id')}
            for record in records:
                if record.get('style_product_id', None):
                    update_data.append({**record, **style, **updated_cc})
                else:
                    post_data.append({**record, **style, **cc})
            if post_data:
                s.bulk_insert_mappings(StyleProduct, post_data)
            if update_data:
                s.bulk_update_mappings(StyleProduct, update_data)
            s.commit()
            return {
                "success": True,
                "message": "Records inserted successfully"
            }, 201

        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)
######################################################################



