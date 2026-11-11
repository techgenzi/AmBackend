import datetime
from pprint import pprint

from flask import request, session
from flask_restx import Resource, abort

from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, insert, select, exists
from .. import ipss_db, db_client
from ..api_doc import mark_search
from ..models.mark import Mark, MarkLine, MarkLineLog
from ipss_utils.decorators import login_required
from ..routes.mark import create_record_response_model, mark_list_response, mark_api_route, mark_model, mark_list_model, \
    mark_line_model, nested_mark_update_model, mark_report_list_response
from .errorhandling import map_sqlalchemy_error_to_http_status, update_local


@mark_api_route.route('/')
class MarkApi(Resource):

    @mark_api_route.marshal_with(mark_list_response)
    @mark_api_route.doc(params=list_api_params)
    @mark_api_route.doc(params=mark_search)
    @login_required(permissions='marks.list')
    # @login_required()
    def get(self):
        """
        List of inventoryRegistry with pagination
        TODO: Search Notification_manage
        :return:
        """
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        compcode = request.args.get('current_user',{}).get('company_id', None)
        product_id = request.args.get('product_id', None)
        raw_product_id = request.args.get('raw_product_id', None)
        mark_id = request.args.get('mark_id', None)

        sql_con = ''

        if product_id:
            sql_con += 'and m.product_id =:product_id '
        if mark_id:
            sql_con += ' and m.mark_id =:mark_id '
        if raw_product_id:
            sql_con += ' and ml.product_id=:raw_product_id '

        sql_query = text(f'''
            select m.mark_id,m.product_id, p.product_name,p.product_code,p.sku_id,
            json_agg(
            json_build_object(
            'mark_line_id',ml.mark_line_id,
                'mark_id', ml.mark_id,
                'product_id', p1.product_id,
                'total_weight', ml.total_weight,
                'add_attribute', ml.add_attribute,
                'product_name',p1.product_name,
                'product_code',p1.product_code,
                'sku_id',p1.sku_id
            ) order by ml.mark_line_id asc
            ) as data,
            count(*) over() as total_results
            from mark as m 
            left join mark_line as ml on m.mark_id = ml.mark_id
            left join products as p on m.product_id = p.product_id
            left join products as p1 on ml.product_id = p1.product_id
            where m.deleted is not true and ml.deleted is not true and m.compcode=:compcode {sql_con}
            group by m.mark_id,m.product_id,p.product_id
            order by m.mark_id desc
            limit :limit offset :offset
        ''')
        result = query_to_dict(db_client.engine.execute(sql_query,
                                                        product_id=product_id,
                                                        raw_product_id=raw_product_id,
                                                        mark_id=mark_id,
                                                        compcode=compcode,
                                                        limit=results_per_page,
                                                        offset=offset))

        pprint(result)

        return {
            'total_results': result[0].get('total_results') if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }

    @login_required(permissions='marks.add')
    # @login_required()
    @mark_api_route.expect(mark_list_model)
    @mark_api_route.marshal_with(create_record_response_model)
    def post(self):
        data = request.json
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        username = cur.get('username', None)
        error = ''
        items = data.pop('data', None)
        s = db_client.session
        try:
            with s.begin():
                data['compcode'] = compcode
                data['created_by'] = username
                data['created_on'] = datetime.datetime.now()
                data.pop('product_code', None)
                stmt = insert(Mark).values(data).returning(Mark.mark_id)
                result = s.execute(stmt)
                primary_key = result.scalar()
                for i in items:
                    i['mark_id'] = primary_key
                    stmt2 = insert(MarkLine).values(i)
                    s.execute(stmt2)
                    stmt3 = insert(MarkLineLog).values(i)
                    s.execute(stmt3)

        except Exception as e:
            s.rollback()
            s.flush()
            return map_sqlalchemy_error_to_http_status(e)

        success = False if error else True
        if success:
            message = "Records created Successfully"
        else:
            message = "There is an Error"
        return {
            'success': success,
            'message': message,
            'error': error,
        }, 200 if success else 500


@mark_api_route.route('/<int:mark_line_id>')
class MarkLineUpdate(Resource):

    # @login_required()
    @login_required(permissions='marks.edit')
    @mark_api_route.expect(nested_mark_update_model)
    def put(self, mark_line_id):
        items = request.json
        items= items.get('data')
        postData = [
            {**items.pop(i), **{}} for i in range(len(items) - 1, -1, -1)
            if not items[i].get('mark_line_id')
        ]
        # s = db_client.session
        error = ''

        try:
            with db_client.session.begin():
             # Context manager ensures proper resource management
                db_client.session.bulk_update_mappings(mapper=MarkLine, mappings=items)
                db_client.session.bulk_insert_mappings(mapper=MarkLine, mappings=postData)
                # s.commit()
            # result = update_local(model=MarkLine,
            #                       condition=MarkLine.mark_line_id == mark_line_id,
            #                       values=data,
            #                       commit=False,
            #                       s=s)
            # if result['success']:
            #     data['mark_line_id'] = mark_line_id
            #     data['created_by'] = request.args.get('current_user', {}).get('username', None)
            #     data['created_on'] = datetime.datetime.now()
            #     data.pop('modified_on', None)
            #     stmt2 = insert(MarkLineLog).values(data)
            #     s.execute(stmt2)
            #     s.commit()
            # else:
            #     raise Exception('updation Failed')

        except Exception as e:
            db_client.session.rollback()
            db_client.session.flush()
            return map_sqlalchemy_error_to_http_status(e)

        return {
          "success": True,
          "message": "Records Updated Successfully",
          "error": ""
        }

    # @login_required()
    @login_required(permissions='marks.delete')
    def delete(self, mark_line_id):

        result = update_local(model=MarkLine,
                              condition=MarkLine.mark_line_id == mark_line_id,
                              values={
                                  'deleted': True,
                                  'deleted_at': datetime.datetime.now()
                              })

        return result

@mark_api_route.route('/mark_id/<int:mark_id>')
class MarkUpdate(Resource):

    @login_required(permissions='marks.delete')
    def delete(self, mark_id):

        result = update_local(model=Mark,
                              condition=Mark.mark_id == mark_id,
                              values={
                                  'deleted': True,
                                  'deleted_at': datetime.datetime.now()
                              })

        return result


@mark_api_route.route('/update')
class MarkModifiedPost(Resource):

    @login_required()
    @mark_api_route.expect()
    def post(self):
        data = request.json
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        username = cur.get('username', None)
        error = ''
        items = data.pop('data', None)
        s = db_client.session

        try:
            with s.begin():
                data['compcode'] = compcode
                data['created_by'] = username
                data['created_on'] = datetime.datetime.now()
                data.pop('product_code', None)

                # Check if the parent product already exists in Mark
                existing_mark_stmt = select(Mark.mark_id).where(
                    (Mark.product_id == data['product_id']) & (Mark.compcode == compcode) & (Mark.deleted.is_(False))
                )
                existing_mark_id = s.execute(existing_mark_stmt).scalar()

                if existing_mark_id:
                    primary_key = existing_mark_id  # Use the existing mark_id
                else:
                    # Insert the new parent product into Mark
                    stmt = insert(Mark).values(data).returning(Mark.mark_id)
                    result = s.execute(stmt)
                    primary_key = result.scalar()

                for i in items:
                    i['mark_id'] = primary_key
                    i.pop('product_code', None)
                    duplicate_check_stmt = select(exists().where(
                        (MarkLine.mark_id == primary_key) &
                        (MarkLine.product_id == i['product_id']) &
                        (MarkLine.deleted.is_(False))
                    ))

                    duplicate_exists = s.execute(duplicate_check_stmt).scalar()

                    if duplicate_exists:
                        s.rollback()
                        error = f"Duplicate entry found for product_id {i['product_id']} under mark_id {primary_key}."
                        return {
                            'success': False,
                            'message': "Duplicate entry detected",
                            'error': error,
                        }, 400  # Bad Request

                    # Insert into MarkLine
                    stmt2 = insert(MarkLine).values(i)
                    s.execute(stmt2)

                    # Insert into MarkLineLog
                    stmt3 = insert(MarkLineLog).values(i)
                    s.execute(stmt3)

        except Exception as e:
            s.rollback()
            s.flush()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': "Records created Successfully",
            'error': error,
        }, 200


@mark_api_route.route('/report')
class MarkReport(Resource):

    @login_required()
    @mark_api_route.doc(params={**list_api_params, **mark_search})
    @mark_api_route.marshal_with(mark_report_list_response)
    def get(self):


        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        compcode = request.args.get('current_user',{}).get('company_id', None)
        product_id = request.args.get('product_id', None)
        raw_product_id = request.args.get('raw_product_id', None)

        sql_con = ''

        if product_id:
            sql_con += 'and m.product_id =:product_id '
        # if mark_id:
        #     sql_con += ' and m.mark_id =:mark_id '
        if raw_product_id:
            sql_con += ' and ml.product_id=:raw_product_id '


        query = text(f'''
        select m.product_id,p.product_code,p.sku_id,u.uom,m.mark_id,
        count(*) over() as total_results,
        json_agg(
        json_build_object(
        'product_id', ml.product_id,
        'product_code', p1.product_code,
            'sku_id', p1.sku_id,
            'uom', u1.uom,
            'add_attributes', ml.add_attribute
        )
        ) as data
        from mark as m
        left join mark_line as ml on ml.mark_id = m.mark_id
        left join products as p on m.product_id = p.product_id
        left  join products as p1 on ml.product_id =p1.product_id
        left join uom as u on u.id = p.uom_id
        left join uom u1 on u1.id = p1.uom_id
        where m.deleted is not true and m.compcode=:compcode {sql_con}
        group by m.product_id,p.product_code,p.sku_id,u.uom,m.mark_id
        order by m.mark_id desc nulls last
        limit :limit offset :offset''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        compcode=compcode,
                                                        limit=results_per_page,
                                                        offset=offset,
                                                        product_id=product_id,
                                                        raw_product_id=raw_product_id))

        return {
            'total_results': result[0].get('total_results') if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }







