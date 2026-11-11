import datetime

from flask import request
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import insert, update, text, func, and_
from sqlalchemy.exc import SQLAlchemyError
from ..models.paking_process import PackingProcess,PackingMaterials
from ..routes.paking_process import paking_process_api_route, paking_process_model, create_response_model, \
    packing_list_response, bulk_post_model, final_response_model
from .. import db_client,ipss_db
from .errorhandling import map_sqlalchemy_error_to_http_status
from ..api_doc import paking_searches
from ipss_utils.ipss_api_doc import list_api_params
@paking_process_api_route.route('/')
class Packing(Resource):
    @login_required()
    @paking_process_api_route.expect(paking_process_model)
    @paking_process_api_route.marshal_with(create_response_model)
    def post(self):
        data = request.json
        items = data.pop('items', None)
        data.pop('packing_process_id', None)
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now()
              }
        error = ''
        success = False
        total_count = db_client.session.query(func.count(PackingProcess.packing_process_id)) \
                          .filter(and_(
            PackingProcess.compcode == compcode.get('company_id'))) \
                          .scalar() + 1
        db_client.session.close()
        data['package_unique'] = 'SPPLN-' + str(total_count).zfill(6)
        try:
            with db_client.session.begin():
                stmt = (
                    insert(PackingProcess).values(**data, **cc).returning(PackingProcess.packing_process_id)
                )
                result = db_client.session.execute(stmt)
                primary_key_id = result.scalar()
                if primary_key_id:
                    if items:
                        items = [{**i, **{"packing_process_id": primary_key_id},**cc} for i in items]
                        db_client.session.bulk_insert_mappings(mapper=PackingMaterials, mappings=items)

                success = True

        except SQLAlchemyError as e:
            error = str(e)
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
    @paking_process_api_route.expect(paking_process_model)
    @paking_process_api_route.marshal_with(create_response_model)
    def patch(self):
        data = request.json
        items = data.pop('items', None)
        pkey=data.pop('packing_process_id', None)
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now()
              }
        error = ''
        success = False
        updateData = [{**data.pop(i), **cc} for i in range(len(data) - 1, -1, -1) if
                      data[i].get('meterials_id')]
        try:
            with db_client.session.begin():

                stmt = (
                    update(PackingProcess)
                    .where(PackingProcess.packing_process_id==pkey)
                    .values(**data)
                )
                result = db_client.session.execute(stmt)
                # db_client.session.commit()


                if pkey:
                    if items:
                        items = [{**i, **{"packing_process_id": pkey}, **cc} for i in items]
                        db_client.session.bulk_insert_mappings(mapper=PackingMaterials, mappings=items)
                    if updateData:
                        db_client.session.bulk_update_mappings(mapper=PackingMaterials, mappings=updateData)
                success = True

        except SQLAlchemyError as e:
            error = str(e)
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
    @paking_process_api_route.marshal_with(packing_list_response)
    @paking_process_api_route.doc(params={**list_api_params,**paking_searches})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con=''
        if request.args.get('packing_process_id'):
            sql_con+=' and pp.packing_process_id=:packing_process_id '
        if request.args.get('order_items_id'):
            sql_con+=' and pp.order_items_id=:order_items_id '
        if request.args.get('packing_date'):
            sql_con+=' and pp.packing_date::date=cast(:packing_date as date) '
        if request.args.get('is_done'):
            sql_con+=' and pp.is_done=:is_done '
        if request.args.get('product_id'):
            sql_con += ' and p.product_id=:product_id '
        sql_query=text(f'''
        select pp.packing_process_id,pp.package_unique,pp.order_items_id,
        pp.packing_date,pp.quantity,cp.order_unique,p.product_code,p.product_name,p.sku_id,
        jsonb_agg(json_build_object(
        'meterials_id',pm.meterials_id ,'packing_process_id',pm.packing_process_id,
        'product_id',pm.product_id,
        'is_packing_materials',pm.is_packing_materials,'quantity',pm.quantity,
        'product_code',p.product_code,'product_name',p.product_name,
        'sku_id',p.sku_id
        )) items
        from packing_plan as pp
        join customer_purchase_items cpi on cpi.items_id =pp.packing_process_id 
        join customer_purchase cp on  cp.customer_purchase_id =cpi.customer_purchase_id 
        join products p on p.product_id =cpi.product_id 
        left join packing_materials pm on pm.packing_process_id =pp.packing_process_id and pm.deleted is not true
        left join products p2 on p2.product_id =pm.product_id 
        where pp.deleted is not true and pp.compcode=:ccode {sql_con}
        group by pp.packing_process_id,pp.package_unique,pp.order_items_id,
        pp.packing_date,pp.quantity,cp.order_unique,p.product_code,p.product_name,p.sku_id
        order by packing_process_id desc
        limit :limit offset :offset
        ''')

        sql_query=query_to_dict(db_client.engine.execute(sql_query,
                                                         is_done=request.args.get('is_done'),
                                                         packing_date=request.args.get('packing_date'),
                                                         order_items_id=request.args.get('order_items_id'),
                                                         packing_process_id=request.args.get('packing_process_id'),
                                                         product_id=request.args.get('product_id'),
                                                         limit=results_per_page,
                                                         offset=offset,
                                                         ccode=ccode))
        sql_count = text(f'''select count(distinct pp.packing_process_id)
                from packing_plan as pp
                join customer_purchase_items cpi on cpi.items_id =pp.packing_process_id 
                join customer_purchase cp on  cp.customer_purchase_id =cpi.customer_purchase_id 
                join products p on p.product_id =cpi.product_id 
                left join packing_materials pm on pm.packing_process_id =pp.packing_process_id and pm.deleted is not true
                left join products p2 on p2.product_id =pm.product_id 
                where pp.deleted is not true and pp.compcode=:ccode {sql_con}
                ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,ccode=ccode,
                                                         is_done=request.args.get('is_done'),
                                                         packing_date=request.args.get('packing_date'),
                                                         order_items_id=request.args.get('order_items_id'),
                                                         packing_process_id=request.args.get('packing_process_id'),
                                                         product_id=request.args.get('product_id'),
                                                         ))
        return {
            'total_results': sql_count[0].get('count', 0) if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }
@paking_process_api_route.route('/<packing_process_id>/')
class DeleteProcess(Resource):
    @login_required()
    def delete(self, packing_process_id):
        result = ipss_db.update_record(
            model=PackingProcess,
            condition=PackingProcess.packing_process_id == packing_process_id,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result
@paking_process_api_route.route('/packing_materials/<meterials_id>/')
class DeleteRank(Resource):
    @login_required()
    def delete(self, meterials_id):
        result = ipss_db.update_record(
            model=PackingMaterials,
            condition=PackingMaterials.meterials_id == meterials_id,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result
@paking_process_api_route.route('/bulk_post')
class DeleteRank(Resource):
    @login_required()
    @paking_process_api_route.expect(bulk_post_model)
    @paking_process_api_route.marshal_with(create_response_model)
    def post(self):
        data = request.json
        data = data.get('data')
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now(),
              # "product_id": pkey if pkey else result.get('primary_key_id')[0]
              }
        total_count = db_client.session.query(func.count(PackingProcess.packing_process_id)) \
                          .filter(and_(
            PackingProcess.compcode == compcode.get('company_id'))) \
                          .scalar() + 1
        db_client.session.close()
        # data['package_unique'] = 'SPPLN-' + str(total_count).zfill(6)
        updateData = [{**item, **cc} for item in data if item.get('packing_process_id')]
        updateData = [{**data.pop(i), **cc} for i in range(len(data) - 1, -1, -1) if
                      data[i].get('packing_process_id')]
        # Then update `data` with the 'package_unique' field
        for i in range(len(data)):
            data[i] = {**data[i], **{"package_unique": 'SPPLN-' + str(total_count + i).zfill(6)}}

        # Finally, merge the `cc` values with the updated `data`
        data = [{**item, **cc} for item in data]
        error = ''
        try:
            with db_client.session.begin():
                if updateData:
                    db_client.session.bulk_update_mappings(mapper=PackingProcess, mappings=updateData)
                if data:
                    db_client.session.bulk_insert_mappings(mapper=PackingProcess, mappings=data)
        except SQLAlchemyError as e:
            error = str(e)
            db_client.session.rollback()

            db_client.session.flush()
        success = False if error else True
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
    @paking_process_api_route.marshal_with(final_response_model)
    @paking_process_api_route.doc(params={**list_api_params, **paking_searches})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con =''
        end_date=request.args.get('end_date') if request.args.get('end_date') else request.args.get('packing_date')
        if request.args.get('packing_process_id'):
            sql_con += ' and pp.packing_process_id=:packing_process_id '
        if request.args.get('order_items_id'):
            sql_con += ' and pp.order_items_id=:order_items_id '
        if request.args.get('packing_date'):
            sql_con += ' and pp.packing_date::date>=cast(:packing_date as date) '
        if end_date:
            sql_con+=' and pp.packing_date::date<=cast(:end_date as date) '
        if request.args.get('is_done'):
            sql_con += ' and pp.is_done=:is_done '
        if request.args.get('product_id'):
            sql_con += ' and p.product_id=:product_id '
        if request.args.get('in_started')=='true':
            sql_con += ' and pp.quantity is not null and pp.packed_quantity <> 0  '
        if request.args.get('in_started')=='false':
            sql_con += ' and (pp.quantity is null or pp.packed_quantity = 0)  '
        sql_query = text(f'''
            select pp.packing_process_id,pp.package_unique,pp.order_items_id,pp.packing_date,pp.is_done,
            pp.packing_date,pp.quantity,cp.order_unique,p.product_code,p.product_name,p.sku_id,pp.end_date,p.product_count,
            p.product_id,pp.packed_quantity,cpi.quantity_ordered,
            (select sum(pp2.quantity) from packing_plan pp2 
            where pp2.order_items_id=pp.order_items_id and deleted is not true
            ) as planned_quantity
            from packing_plan as pp
            join customer_purchase_items cpi on cpi.items_id =pp.order_items_id 
            join customer_purchase cp on  cp.customer_purchase_id =cpi.customer_purchase_id 
            join products p on p.product_id =cpi.product_id 
            where pp.deleted is not true and pp.compcode=:ccode {sql_con}
            --group by pp.packing_process_id,pp.package_unique,pp.order_items_id,
            --pp.packing_date,pp.quantity,cp.order_unique,p.product_code,p.product_name,p.sku_id,p.product_id
            order by packing_process_id desc
            limit :limit offset :offset
            ''')

        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           is_done=request.args.get('is_done'),
                                                           end_date=end_date,
                                                           packing_date=request.args.get('packing_date'),
                                                           order_items_id=request.args.get('order_items_id'),
                                                           packing_process_id=request.args.get('packing_process_id'),
                                                           product_id=request.args.get('product_id'),
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           ccode=ccode))
        sql_count = text(f'''select count(distinct pp.packing_process_id)
                    from packing_plan as pp
            join customer_purchase_items cpi on cpi.items_id =pp.order_items_id 
            join customer_purchase cp on  cp.customer_purchase_id =cpi.customer_purchase_id 
            join products p on p.product_id =cpi.product_id 
                    where pp.deleted is not true and pp.compcode=:ccode {sql_con}
                    ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count, ccode=ccode,
                                                           is_done=request.args.get('is_done'),
                                                           end_date=end_date,
                                                           packing_date=request.args.get('packing_date'),
                                                           order_items_id=request.args.get('order_items_id'),
                                                           packing_process_id=request.args.get('packing_process_id'),
                                                           product_id=request.args.get('product_id'),
                                                           ))
        return {
            'total_results': sql_count[0].get('count', 0) if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }


