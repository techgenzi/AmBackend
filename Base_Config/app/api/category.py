import datetime
from flask import request
from flask_restx import Resource

from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, and_
from ..models.category import Category, StyleCategory
from ..api.errorhandling import map_sqlalchemy_error_to_http_status
from ipss_utils.decorators import login_required

from ..routes.category import category_api_route, single_category_model, create_category_response, \
    category_list_response, \
    update_category_response, style_category_api_route, style_category_list_response, single_category_product_model
from .. import ipss_db, db_client
from ..api_doc.category_api_doc import search_filters


@category_api_route.route('/')
class CategoryApi(Resource):

    @category_api_route.marshal_with(category_list_response)
    @category_api_route.doc(params={**list_api_params, **search_filters})
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
        id = request.args.get('category_id', None)
        if id:
            sql_con += ' and category_id=:id '
        sql_query = text(f'''
               select *,count(*) over() as total_results from category
               where deleted is not true and compcode=:ccode {sql_con}
               order by category_id desc
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
    @category_api_route.expect(single_category_model)
    @category_api_route.marshal_with(create_category_response)
    def post(self):
        """
        Create Products record and return inserted id
        :return:
        """
        data = request.json
        category_name = data.get('category_name', None)
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        try:
            val = Category.query.filter_by(category_name=category_name, compcode=compcode, deleted=False).first()
            if val:
                return {
                    "success": False,
                    "message": "Duplicate value"
                }, 409
            result = ipss_db.insert_record(model=Category, values=data)
            return result

        except Exception as e:
            return map_sqlalchemy_error_to_http_status(e)


@category_api_route.route('/<category_id>/')
class CategoryUpdateApi(Resource):
    @staticmethod
    def update_record(data, category_id):
        data.pop('category_id', None)
        category_name = data.get('category_name', None)
        # value = {'category_name': category_name}
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        val = Category.query.filter(
            and_(Category.category_name == category_name, Category.compcode == compcode, Category.deleted == False, Category.category_id != category_id)).first()
        if val:
            return {
                "success": False,
                "message": "Duplicate value"
            }, 409

        result = ipss_db.update_record(
            model=Category,
            condition=Category.category_id == category_id,
            values=data
        )
        return result

    @category_api_route.marshal_with(single_category_model)
    @login_required()
    def get(self, category_id):
        user = Category.query.filter_by(category_id=int(category_id)).first()
        return user

    @category_api_route.expect(single_category_model)
    @category_api_route.marshal_with(update_category_response)
    @login_required()
    def put(self, category_id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, category_id)
        return response

    @category_api_route.expect(single_category_model)
    @category_api_route.marshal_with(update_category_response)
    @login_required()
    def patch(self, category_id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, category_id)
        return response

    @category_api_route.marshal_with(update_category_response)
    @login_required()
    def delete(self, category_id):
        """
        Soft delete Products record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=Category,
            condition=Category.category_id == category_id,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result


@style_category_api_route.route('/')
class StyleCategoryApi(Resource):

    @style_category_api_route.marshal_with(style_category_list_response)
    @style_category_api_route.doc(params={**list_api_params, **search_filters})
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
        category_id = request.args.get('category_id', None)
        sql_con = ''

        if category_id:
            sql_con += ' and sc.category_id=:category_id '

        query = text(f'''
        select sc.category_id,c.category_name,count(*) over() as total_results,
         json_agg(
         json_build_object(
            'style_category_id', sc.style_category_id,
            'style_id', sc.style_id,
            'style_code', s.style_code,
            'deleted', sc.deleted
        )) as data
        from style_category sc
        left join category c on c.category_id = sc.category_id
        left join style s on sc.style_id = s.style_id
        where sc.deleted is not true and sc.compcode=:company_id {sql_con}
        group by sc.category_id,c.category_name
        limit :limit offset :offset
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        company_id=company_id,
                                                        category_id=category_id,
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
    @style_category_api_route.expect(single_category_product_model)
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
            category = {'category_id': data.get('category_id')}
            for record in records:
                if record.get('style_category_id', None):
                    update_data.append({**record, **category, **updated_cc})
                else:
                    post_data.append({**record, **category, **cc})
            if post_data:
                s.bulk_insert_mappings(StyleCategory, post_data)
            if update_data:
                s.bulk_update_mappings(StyleCategory, update_data)
            s.commit()
            return {
                "success": True,
                "message": "Records inserted successfully"
            }, 201

        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

#
# @style_category_api_route.route('/<int:category_id>/')
# class StyleCategoryUpdateApi(Resource):
#
#     @style_category_api_route.expect(style_category_bulk_post_fields)
#     @login_required()
#     def put(self, category_id):
#
#         data = request.json
#
#         data = data.get('data')
#
#         cur = request.args.get('current_user', {})
#
#         compcode = cur.get('company_id', None)
#         s = db_client.session
#
#         try:
#             style_ids = [record['style_id'] for record in data]
#             # Step 1: Fetch existing records
#             existing_qs = s.query(StyleCategory).filter(
#                 StyleCategory.category_id == category_id,
#                 StyleCategory.compcode == compcode,
#                 StyleCategory.deleted == False
#             )
#
#             # Step 2: Delete records NOT in product_ids
#             existing_qs.filter(~StyleCategory.style_id.in_(style_ids)).delete(
#                 synchronize_session=False
#             )
#
#             # Step 3: Upsert / fresh insert new records
#             for record in data:
#                 record['category_id'] = category_id
#                 record['compcode'] = compcode
#                 record['created_by'] = cur.get('username')
#
#             s.bulk_insert_mappings(StyleCategory, data)
#             s.commit()
#
#         except Exception as e:
#             s.rollback()
#             return map_sqlalchemy_error_to_http_status(e)
######################################################################



