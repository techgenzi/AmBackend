import datetime
from pprint import pprint

from flask import request, session
from flask_restx import Resource, abort

from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger, bindparam, NUMERIC, Integer, DateTime, String, insert
from sqlalchemy.exc import SQLAlchemyError

from .bulk_insert import inventory_ops, inventory_inv, get_product_sequence
from .. import ipss_db, db_client
from ..api_doc import product_filter
from ..models.storelocation import StoreTransfer, Location, LocationProduct, StoreTransferItems
from ipss_utils.decorators import login_required
from ..routes.storelocation import store_api_route, store_list_response, store_post_model, create_record_response_model, \
    store_product_list_response, store_transfer_post_model, store_transfer_list_resposne
from .errorhandling import map_sqlalchemy_error_to_http_status, update_local



@store_api_route.route('/')
class StoreApi(Resource):

    @store_api_route.marshal_with(store_list_response)
    @store_api_route.doc(params=list_api_params)
    # @login_required(permissions='store_location.list')
    @login_required()
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
        sql_con = ''

        sql_query = text(f'''
                select 
                    sl.store_id,sl.store_name,
                    sl.location,sl.description
                 from store_location as sl
                 where sl.deleted is not true and sl.compcode=:compcode
                order by  sl.store_id DESC
                limit :limit offset :offset
        ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           compcode=compcode,
                                                           limit=results_per_page,
                                                           offset=offset))
        sql_count = text(f'''
        select 
        count(*)
        from store_location as sl
        where sl.deleted is not true and sl.compcode=:compcode
        ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count, compcode=compcode))

        return {
            'total_results': sql_count[0].get('count') if sql_count else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }

    @login_required(permissions='store_location.add')
    # @login_required()
    @store_api_route.expect(store_post_model)
    @store_api_route.marshal_with(create_record_response_model)
    def post(self):
        data = request.json
        items = data.pop('data', None)
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        username = cur.get('username', None)
        cc = {
                "compcode": compcode,
                'created_by': username,
                "created_on": datetime.datetime.now()
        }
        error = ''
        s = db_client.session
        try:
            with s.begin():
                data.update(**cc)
                stmt = insert(Location).values(data).returning(Location.store_id)
                result = s.execute(stmt)
                if items:
                    primary_key = result.scalar()
                    for i in items:
                        i.update(**{**cc, 'store_id': primary_key})
                    s.bulk_insert_mappings(mapper=LocationProduct, mappings=items)

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


@store_api_route.route('/<store_id>')
class StoreUpdate(Resource):

    # @login_required()
    @login_required(permissions='store_location.edit')
    @store_api_route.expect(store_post_model)
    def patch(self, store_id):
        data = request.json

        result = update_local(model=Location,
                              condition= Location.store_id==store_id,
                              values=data)

        return result

    # @login_required()
    @login_required(permissions='store_location.delete')
    def delete(self, store_id):

        result = update_local(model=Location,
                              condition=Location.store_id==store_id,
                              values={
                                  'deleted': True,
                                  'deleted_at': datetime.datetime.now()
                              })

        return result


@store_api_route.route('/products/')
class StoreProduct(Resource):

    @login_required()
    @store_api_route.marshal_with(store_product_list_response)
    @store_api_route.doc(params=product_filter)
    def get(self):
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        compcode = request.args.get('current_user',{}).get('company_id', None)
        # compcode = 33
        product_id = request.args.get('product_id', None)
        sql_con = ''
        if product_id:
            sql_con += ' and sp.product_id=:product_id '

        query = text(f'''
            select sl.store_id,sl.store_name,sl.location,sl.description,
            json_agg(
                json_build_object(
            'product_id',sp.product_id,
                'product_code', p.product_code,
                    'sub_location', sp.sub_location,
                    'product_count', p.product_count,
                    'allocated_quantity', p.allocated_quantity,
                'uom', u.uom,
                'uom_id', p.uom_id
            )
            ) as data,
            count(*) over() as total_count
            from store_location as sl
            left join store_product as sp on sl.store_id = sp.store_id
            left join products as p on p.product_id = sp.product_id
            left join uom as u on u.id = p.uom_id
            where sl.compcode=:compcode and sl.deleted is not true 
            and sp.deleted is not true {sql_con}
            group by sl.store_id,sl.store_name,sl.location,sl.description
            order by store_id desc
            limit :limit offset :offset
        ''')
        results = query_to_dict(db_client.engine.execute(query,
                                                         compcode=compcode,
                                                         limit=results_per_page,
                                                         offset=offset,
                                                         product_id=product_id))

        return {
            'total_results': results[0].get('total_count') if results else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': results
        }


@store_api_route.route('/transfer/')
class StoreTransferApi(Resource):

    @login_required()
    @store_api_route.marshal_with(store_transfer_list_resposne)
    @store_api_route.doc(params={**product_filter,**{
        'status': {
            'type': 'str',
            'description': "Filter by status"
        }
    }})
    def get(self):
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get(
            'results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        compcode = request.args.get('current_user',{}).get('company_id', None)
        store_id = request.args.get('store_id')
        sql_con = ''
        # print("Current_User", request.args.get('current_user', {}))
        store_ids = store_id.split(',') if store_id else []
        store_transfer_id = request.args.get('store_transfer_id')
        status = request.args.get('status')
        if status:
            sql_con += ' and st.status = :status '
        if store_transfer_id:
            sql_con += ' and st.store_transfer_id = :store_transfer_id '
        if store_ids:
            sql_con += ' and (st.from_store_id = any(:store_ids) or st.to_store_id = any(:store_ids)) '
        query = text(f'''
            select st.store_transfer_id,st.from_store_id,st.to_store_id,
            fs.store_name as from_store_name,
            ts.store_name as to_store_name,
            st.transfer_date,st.status,st.release_status,st.receive_status,st.request_id,
            count(*) over() as total_count,
            json_agg(
                json_build_object(
                'store_transfer_item_id', sti.store_transfer_item_id,
                'store_transfer_id', sti.store_transfer_id,
                'product_id', sti.product_id,
                'product_code', p.product_code,
                'sku_id', p.sku_id,
                'uom', u.uom,
                'quantity', sti.quantity,
                'approved_qty', sti.approved_qty
            )
            ) as data
            from store_transfer as st
            left join store_location as fs on fs.store_id = st.from_store_id
            left join store_location as ts on ts.store_id = st.to_store_id
            left join store_transfer_items as sti on sti.store_transfer_id = st.store_transfer_id
            left join products as p on p.product_id = sti.product_id
            left join uom u on u.id= p.uom_id
            where st.compcode=:compcode and st.deleted is not true {sql_con}
            group by st.store_transfer_id,st.from_store_id,st.to_store_id,
            fs.store_name,ts.store_name,
            st.transfer_date,st.status,st.release_status,st.receive_status,st.request_id
            order by st.store_transfer_id desc
            limit :limit offset :offset
        ''')
        results = query_to_dict(db_client.engine.execute(query,
                                                         compcode=compcode,
                                                         status=status,
                                                         store_transfer_id=store_transfer_id,
                                                         limit=results_per_page,
                                                         store_ids=store_ids,
                                                         offset=offset))

        return {
            'total_results': results[0].get('total_count') if results else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': results
        }

    @login_required()
    @store_api_route.expect(store_transfer_post_model)
    @store_api_route.marshal_with(create_record_response_model)
    def post(self):
        data = request.json
        items = data.pop('data', None)
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        username = cur.get('username', None)
        cc = {
                "compcode": compcode,
                'created_by': username,
                "created_on": datetime.datetime.now()
        }
        s = db_client.session
        try:
            with s.begin():
                data.update(**cc)
                data['request_id'] = get_product_sequence(s)
                stmt = insert(StoreTransfer).values(data).returning(StoreTransfer.store_transfer_id)
                result = s.execute(stmt)
                if items:
                    primary_key = result.scalar()
                    for i in items:
                        i.update(**{**cc, 'store_transfer_id': primary_key})
                    s.bulk_insert_mappings(mapper=StoreTransferItems, mappings=items)

        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': "Records created Successfully"
        }, 200


@store_api_route.route('/transfer/<store_transfer_id>')
class StoreTransferUpdate(Resource):

    @login_required()
    @store_api_route.expect(store_transfer_post_model)
    def put(self, store_transfer_id):
        data = request.json
        items = data.pop('data', None)
        s = db_client.session
        try:
            with s.begin():
                result = update_local(model=StoreTransfer,
                                      condition=StoreTransfer.store_transfer_id==store_transfer_id,
                                      values=data, s=s, commit=False)
                if items:
                    existing_items = s.query(StoreTransferItems).filter(
                        StoreTransferItems.store_transfer_id == store_transfer_id
                    ).all()
                    existing_item_ids = {item.store_transfer_item_id for item in existing_items}
                    new_item_ids = {item.get('store_transfer_item_id') for item in items if item.get('store_transfer_item_id')}
                    # Delete items that are not in the new list
                    items_to_delete = existing_item_ids - new_item_ids
                    if items_to_delete:
                        s.query(StoreTransferItems).filter(
                            StoreTransferItems.store_transfer_item_id.in_(items_to_delete)
                        ).delete(synchronize_session=False)
                    # Update existing items and add new ones
                    for item in items:
                        if item.get('store_transfer_item_id') in existing_item_ids:
                            s.query(StoreTransferItems).filter(
                                StoreTransferItems.store_transfer_item_id == item.get('store_transfer_item_id')
                            ).update(item)
                        else:
                            item.update({
                                'store_transfer_id': store_transfer_id,
                                'compcode': data.get('compcode'),
                                'created_by': data.get('created_by'),
                                'created_on': data.get('created_on')
                            })
                            s.add(StoreTransferItems(**item))
        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': "Records updated Successfully"
        }


@store_api_route.route('/role-map/')
class StoreRoleMapApi(Resource):


    @login_required()
    def get(self):

        current_user = request.args.get('current_user', {})
        company_id = current_user.get('company_id', None)

        query = text('''
            select srm.store_id,srm.role_id,ar.role_name from store_role_map srm
            join auth_roles ar on ar.role_id = srm.role_id
            where srm.compcode = :compcode and srm.deleted is not true
        ''')

        results = query_to_dict(db_client.engine.execute(query,
                                                         compcode=company_id))
        return {
            'results': results
        }

    @login_required()
    def post(self):
        pass


@store_api_route.route('/role-map/get_stores')
class StoreRoleMapGetStores(Resource):


    @login_required()
    def get(self):

        current_user = request.args.get('current_user', {})
        company_id = current_user.get('company_id', None)

        print("Current User:", current_user)
        flag = True if current_user.get('user_permissions', {}).get('org_admin', []).__contains__('admin') else False
        query = None
        if not flag:
            query = text('''
                select distinct sl.store_id, sl.store_name from store_location sl
                join store_role_map srm on srm.store_id = sl.store_id
                join auth_roles ar on ar.role_id = srm.role_id
                join user_roles ur on ur.role_id = ar.role_id
                where sl.compcode = :compcode and sl.deleted is not true and ur.user_id = :user_id
            ''')
        else:
            query = text('''
                select sl.store_id, sl.store_name from store_location sl
                where sl.compcode = :compcode and sl.deleted is not true
            ''')

        results = query_to_dict(db_client.engine.execute(query,
                                                         compcode=company_id,
                                                         user_id=current_user.get('user_id')))
        return {
            'results': results
        }


@store_api_route.route('/sub-locations/')
class StoreSubLocations(Resource):

    @login_required()
    def get(self):
        store_id = request.args.get('store_id')
        compcode = request.args.get('current_user', {}).get('company_id')
        if not store_id:
            return {'message': 'store_id is required'}, 400

        query = text('''
            select distinct sub_location from store_product
            where store_id = :store_id
              and sub_location is not null
              and sub_location != ''
              and deleted is not true
              and compcode = :compcode
            order by sub_location asc
        ''')
        results = query_to_dict(db_client.engine.execute(query, store_id=store_id, compcode=compcode))
        return {
            'results': [r.get('sub_location') for r in results]
        }