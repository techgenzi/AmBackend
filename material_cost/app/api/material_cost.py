import datetime
from pprint import pprint

from flask import request, session
from flask_restx import Resource, abort

from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, insert
from .. import ipss_db, db_client
from ..api_doc import product_filter, bulk_product, actual_material_filter
from ..models.material_cost import MaterialCost, MaterialCostLog
from ipss_utils.decorators import login_required
from ..routes.material_cost import create_record_response_model, material_cost_list_response, material_cost_api_route, \
    material_cost_model, product_service_list_model, material_cost_bulk_upload_model, actual_material_cost_list_response
from .errorhandling import map_sqlalchemy_error_to_http_status, update_local



@material_cost_api_route.route('/')
class MaterialCostApi(Resource):

    @material_cost_api_route.marshal_with(material_cost_list_response)
    @material_cost_api_route.doc(params=list_api_params)
    @login_required(permissions='material_cost.list')
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
        product_group_id = request.args.get('product_group_id', None)

        sql_con = ''

        if product_id:
            sql_con += 'and p.product_id =:product_id '
        if product_group_id:
            sql_con += 'and p.product_group_id =:product_group_id '
        sql_query = text(f'''
        with cte as(
            select distinct on(p.product_id)
            mc.material_cost_id,p.product_id,p.product_group_id,mc.created_by,mc.created_on,mc.modified_by,
            p.product_code,p.sku_id,uom.uom,
            mc.modified_on,gli.grnotesid,grn.grn_no,mc.cost,
            gli.rate_per_item::numeric  as rate_per_item
            from products p  
            left join material_cost mc on mc.product_id = p.product_id
            left join grnlineitems gli on p.product_id = gli.product_id
            left join grnotes grn on grn.grnotesid = gli.grnotesid
            left join uom on p.uom_id = uom.id
            where p.compcode =:compcode and p.deleted is not true {sql_con}
            order by p.product_id,gli.grnotesid desc
        )
        select cte.*,
         count(*) over() as total_results
         from cte
        order by cte.material_cost_id
        limit :limit offset :offset
        ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           product_id=product_id,
                                                           product_group_id=product_group_id,
                                                           compcode=compcode,
                                                           limit=results_per_page,
                                                           offset=offset))


        return {
            'total_results': sql_query[0].get('total_results') if sql_query else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }

    @login_required(permissions='material_cost.add')
    # @login_required()
    @material_cost_api_route.expect(material_cost_model)
    @material_cost_api_route.marshal_with(create_record_response_model)
    def post(self):
        data = request.json
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        username = cur.get('username', None)
        s = db_client.session
        try:
            with s.begin():
                primary_key = None
                material_cost_id = data.get('material_cost_id', None)
                if material_cost_id:
                    result = update_local(model=MaterialCost,
                                          condition=MaterialCost.material_cost_id == material_cost_id,
                                          values=data,
                                          commit=False,
                                          s=s)
                    if result['success']:
                        data.pop('modified_by', None)
                        data['material_cost_id'] = material_cost_id
                        data['created_by'] = username
                        data['created_on'] = datetime.datetime.now()
                        data['compcode'] = compcode
                        data.pop('modified_on', None)
                    else:
                        raise Exception('Error')
                else:
                    data['compcode'] = compcode
                    data['created_by'] = username
                    data['created_on'] = datetime.datetime.now()
                    stmt = insert(MaterialCost).values(data).returning(MaterialCost.material_cost_id)
                    result = s.execute(stmt)
                    primary_key = result.scalar()
                    data['material_cost_id'] = primary_key

                stmt2 = insert(MaterialCostLog).values(data)
                s.execute(stmt2)

        except Exception as e:
            s.rollback()
            s.flush()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': "Record Created Successfully",
            'inserted_id': primary_key,
            'primary_key': 'material_cost_id'
        }, 200


@material_cost_api_route.route('/<int:material_cost_id>')
class MaterialCostUpdate(Resource):

    # @login_required()
    @login_required(permissions='material_cost.edit')
    @material_cost_api_route.expect(material_cost_model)
    def put(self, material_cost_id):
        data = request.json
        s = db_client.session
        error = ''
        try:
            result = update_local(model=MaterialCost,
                                  condition=MaterialCost.material_cost_id == material_cost_id,
                                  values=data,
                                  commit=False,
                                  s=s)
            if result['success']:
                data['material_cost_id'] = material_cost_id
                data['created_by'] = data.pop('modified_by', None)
                data['created_on'] = datetime.datetime.now()
                data.pop('modified_on', None)
                stmt2 = insert(MaterialCostLog).values(data)
                s.execute(stmt2)
                s.commit()
            else:
                raise Exception('updation Failed')

        except Exception as e:
            s.rollback()
            s.flush()
            return map_sqlalchemy_error_to_http_status(e)

        return result

    @login_required()
    # @login_required(permissions='material_cost.delete')
    def delete(self, material_cost_id):

        result = update_local(model=MaterialCost,
                              condition=MaterialCost.material_cost_id == material_cost_id,
                              values={
                                  'deleted': True,
                                  'deleted_at': datetime.datetime.now()
                              })

        return result

@material_cost_api_route.route('/products')
class MaterialCostGet(Resource):

    @login_required(permissions='material_cost.list')
    @material_cost_api_route.marshal_with(product_service_list_model)
    @material_cost_api_route.doc(params=list_api_params)
    @material_cost_api_route.doc(params=bulk_product)
    def get(self):
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        compcode = request.args.get('current_user', {}).get('company_id', None)
        product_id = request.args.get('product_id', None)
        product_group_id = request.args.get('product_group_id', None)

        sql_con = ''
        ids = None
        if product_id:
            ids = tuple(map(int,product_id.split(',')))
            sql_con += ' and p.product_id in :product_id'
        if product_group_id:
            sql_con += ' and p.product_group_id=:product_group_id '
        query1 = text(f'''
        select mc.material_cost_id,p.product_group_id,p.product_id,p.product_code,u.uom,mc.cost
        from products as p
        left join material_cost as mc on mc.product_id = p.product_id
        left join uom as u on u.id = p.uom_id
        where p.compcode=:compcode and p.deleted is not true {sql_con}
        order by p.product_id desc
        limit :limit offset :offset
        ''')

        query1 = query_to_dict(db_client.engine.execute(query1,
                                                           product_id=ids,
                                                        product_group_id=product_group_id,
                                                           compcode=compcode,
                                                           limit=results_per_page,
                                                           offset=offset))
        sql_count = text(f'''
              select count(p.*)
            from products as p
            where p.compcode=:compcode and p.deleted is not true {sql_con}
              ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           product_id=ids,
                                                           product_group_id=product_group_id,
                                                           compcode=compcode))

        return {
            'total_results': sql_count[0].get('count') if sql_count else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': query1
        }


@material_cost_api_route.route('/bulk_upload')
class BulkUpload(Resource):

    @login_required()
    @material_cost_api_route.expect(material_cost_bulk_upload_model)
    def post(self):

        data = request.json

        data = data.get('data', None)
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id', None)
        username = current_user.get('username', None)
        s= db_client.session
        cc= {
            'created_by': username,
            'created_on': datetime.datetime.now(),
            'compcode': compcode
        }
        updated_cc = {
            'modified_by': username,
            'modified_on': datetime.datetime.now()
        }
        log_data = []
        try:

            post_data = []
            update_data = []

            for i in data:

                if i.get('material_cost_id'):
                    update_data.append({**i, **updated_cc})
                    log_data.append({
                        "material_cost_id": i.get("material_cost_id"),
                        "product_id": i.get("product_id"),
                        "cost": i.get("cost"),
                        "effective_date": i.get("effective_date", None),
                        "add_attribute": i.get("add_attribute", None),
                        "compcode": compcode,
                        "created_by": username,
                        "created_on": datetime.datetime.now()
                    })
                else:
                    obj = MaterialCost(**i, **cc)
                    post_data.append(obj)

            if post_data:
                s.add_all(post_data)
                s.flush()
                for obj in post_data:
                    log_data.append({
                        "material_cost_id": obj.material_cost_id,
                        "product_id": obj.product_id,
                        "cost": obj.cost,
                        "effective_date": obj.effective_date,
                        "add_attribute": obj.add_attribute,
                        "compcode": compcode,
                        "created_by": username,
                        "created_on": datetime.datetime.now()
                    })
            if update_data:
                s.bulk_update_mappings(MaterialCost, update_data)
            if log_data:
                s.bulk_insert_mappings(MaterialCostLog, log_data)

            s.commit()

        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': 'Bulk data upload Successfully'
        }


@material_cost_api_route.route('/actual_material_cost_report')
class ActualMaterialCostReport(Resource):
    @login_required()
    @material_cost_api_route.marshal_with(actual_material_cost_list_response)
    @material_cost_api_route.doc(params={**list_api_params,**actual_material_filter})
    def get(self):

        sql_con = ''
        production_plan_id = request.args.get('production_plan_id', None)
        product_id = request.args.get('product_id', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', start_date)

        if production_plan_id:
            sql_con += ' and mv.production_plan_id = :production_plan_id '
        if product_id:
            sql_con += ' and mv.material_id = :product_id '
        if start_date:
            sql_con += ' and mv.execution_date >= cast(:start_date as date) and mv.execution_date <= cast(:end_date as date) '
        compcode = request.args.get('current_user', {}).get('company_id', None)
        if compcode:
            sql_con += ' and mv.compcode = :compcode '

        raw_rpp = request.args.get('results_per_page')
        result_per_page = int(raw_rpp) if raw_rpp is not None and raw_rpp != '' else 20
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1

        pagination_clause = ''
        exec_params = {
            'compcode': compcode,
            'production_plan_id': production_plan_id,
            'product_id': product_id,
            'start_date': start_date,
            'end_date': end_date
        }
        if result_per_page > 0:
            offset = (paged - 1) * result_per_page
            pagination_clause = ' limit :limit offset :offset '
            exec_params['limit'] = result_per_page
            exec_params['offset'] = offset

        # Uses Unified Daily Manufacturing Fact table (mv_daily_manufacturing_fact) to align
        # with Consolidated Dashboard, WIP execution logs, and daily material consumption
        query = text(f'''
        with date_filtered_mv as (
            select 
                mv.production_plan_id,
                pp.plan_unique,
                mv.material_id as product_id,
                p.product_code,
                p.sku_id,
                u.uom,
                0::numeric as dispatch_amount,
                0::numeric as return_amount,
                case 
                    when coalesce(mc.cost, 0) > 0 then round((sum(mv.actual_material_cost) / mc.cost), 2)
                    else 0::numeric 
                end as consumed,
                sum(mv.actual_material_cost) as total_cost
            from mv_daily_manufacturing_fact mv
            join production_plan pp on pp.production_plan_id = mv.production_plan_id
            join products p on p.product_id = mv.material_id
            left join uom u on u.id = p.uom_id
            left join material_cost mc on mc.product_id = mv.material_id 
                and mc.deleted is not true 
                and (:compcode is null or mc.compcode = :compcode or mc.compcode is null)
            where mv.material_id > 0
              {sql_con}
            group by mv.production_plan_id, pp.plan_unique, mv.material_id, p.product_code, p.sku_id, u.uom, mc.cost
        )
        select 
            production_plan_id,
            plan_unique,
            sum(total_cost) as total,
            json_agg(
                json_build_object(
                    'product_code', product_code,
                    'product_id', product_id,
                    'uom', uom,
                    'sku_id', sku_id,
                    'dispatch_amount', dispatch_amount,
                    'return_amount', return_amount,
                    'consumed', consumed,
                    'total_cost', total_cost
                )
            ) as data,
            count(*) over() as total_results
        from date_filtered_mv
        group by production_plan_id, plan_unique
        order by plan_unique, production_plan_id
        {pagination_clause}
        ''')

        result = query_to_dict(db_client.engine.execute(query, **exec_params))

        return {
            'total_results': result[0].get('total_results') if result else 0,
            'page': paged,
            'results_per_page': result_per_page,
            'results': result
        }