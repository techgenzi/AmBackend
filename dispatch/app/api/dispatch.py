import datetime
from pprint import pprint

from flask import request, session
from flask_restx import Resource, abort
from werkzeug.exceptions import HTTPException

from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger, bindparam, NUMERIC, Integer, DateTime, String, Numeric
from sqlalchemy.exc import SQLAlchemyError

from .bulk_insert import inventory_ops
from .. import ipss_db, db_client
from ..api_doc import invRegistryFields, search_filters, stock_search, dispatch_search
from ..models.dispatch import DispatchRegistry
from ipss_utils.decorators import login_required
from ..routes.dispatch import dispatch_api_route, inventoryRegistry_list_response, \
    create_inventoryRegistry_response, dispatch_list_response, \
    update_inventoryRegistry_model, update_inventoryRegistry_response, inventoryBulk_model, dispatch_post_model, \
    dispatch_get_list_model, plan_to_dispatch_model
from ..routes.dispatch import create_inventoryRegistry_model, get_inventoryRegistry_response
from .errorhandling import map_sqlalchemy_error_to_http_status, update_local

primary_key = 'releseid'


@dispatch_api_route.route('/')
class DispatchApi(Resource):
    per_page = 20

    @dispatch_api_route.marshal_with(dispatch_list_response)
    @dispatch_api_route.doc(params=list_api_params)
    @dispatch_api_route.doc(params=search_filters)
    # @user_verify(permission='InventoryRegistry.list', db_client=db_client)
    @login_required(permissions='dispatch.list')
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
        print(compcode ,'QWE')
        prod_plan_id = request.args.get('prod_plan_id', None)
        type = request.args.get('type', None)
        sql_con = ''
        if request.args.get('releseid', None):
            sql_con += ' and inv.releseid=:releseid '
        if request.args.get('is_from', None):
            sql_con += ' and inv.is_from=:is_from '
        if request.args.get('product_id', None):
            sql_con += ' and inv.product_id=:product_id '
        if request.args.get('action', None):
            sql_con += ' and inv.action=:action '
        is_dispatch_condition = " AND inv.is_dispatch IS NOT TRUE "
        if request.args.get('ref_id', None):
            sql_con += ' and inv.ref_id=:ref_id '
            is_dispatch_condition = " AND (inv.is_dispatch IS NOT TRUE OR inv.status = 'Short Closed') "
        if request.args.get('status', None):
            sql_con += ' and inv.status=:status '
        if request.args.get('is_returned', None):
            sql_con += 'and inv.is_returned=:is_returned '
        if prod_plan_id:
            sql_con += 'and inv.prod_plan_id=:prod_plan_id '
        if type:
            sql_con += 'and inv.type=:type '
        sql_query = text(f'''
		WITH inv_aggregated AS (
    SELECT 
        inv.releseid, 
        inv.ref_id, 
        inv.prod_plan_id, 
        inv.packing_process_id,
        inv.userid, 
        inv.approval_id, 
        inv.product_id, 
        inv.type, 
        inv.created_on, 
        inv.approval_date, 
        inv.approved_amount, 
		inv.store_id,
        inv.status,
        SUM(CAST(d.dispatch_amount AS NUMERIC)) AS dispatch_amount
    FROM 
        invregistry AS inv
    LEFT JOIN 
        dispatch AS d ON inv.releseid = d.releseid
    WHERE 
        inv.action = 'Outward' 
        AND inv.status IN ('Approved', 'Short Closed') 
        AND inv.deleted IS NOT TRUE 
        {is_dispatch_condition} 
        AND inv.compcode =:compcode
        {sql_con}
    GROUP BY 
        inv.releseid, inv.ref_id, inv.prod_plan_id, inv.packing_process_id,inv.userid, inv.approval_id, inv.product_id, 
        inv.type, inv.created_on, inv.approval_date, inv.approved_amount, inv.store_id, inv.status
)
SELECT 
    inv.ref_id,
    STRING_AGG(DISTINCT pp.plan_unique, ', ') AS plan_unique,
    STRING_AGG(DISTINCT pp1.package_unique, ', ') AS package_unique,
    inv.type,
    CONCAT(e.firstname, e.lastname) AS req,
    inv.created_on,
    STRING_AGG(DISTINCT NULLIF(CONCAT_WS(' ', p.firstname, p.lastname), ''), ', ') AS apr,
    MAX(inv.approval_date::DATE) AS approval_date,
    max(inv.releseid) as order_ref,
    STRING_AGG(DISTINCT cp.order_unique, ', ') as order_unique,
    count(*) over() AS total_results,
    JSON_AGG(
        JSON_BUILD_OBJECT(
            'releseid', unique_data.releseid,
            'sku_id', unique_data.sku_id,
            'uom',unique_data.uom,
            'product_id', unique_data.product_id,
            'product_name', unique_data.product_name,
            'product_code', unique_data.product_code,
            'product_count', unique_data.product_count,
			'store_id', unique_data.store_id,
			'store_name', unique_data.store_name,
            'allocated_quantity' , unique_data.allocated_quantity,
            'approved_amount', unique_data.approved_amount,
            'already_dispatch', unique_data.dispatch_amount,
            'status', unique_data.status,
            'available_lots', (
                SELECT JSON_AGG(DISTINCT COALESCE(NULLIF(gl.supplier_lot_no, ''), g.grn_no))
                FROM joborder j
                JOIN grnotes g ON g.joborderid = CAST(j.joborderid AS VARCHAR)
                JOIN grnlineitems gl ON gl.grnotesid = g.grnotesid
                WHERE j.customer_purchase_id = cp.customer_purchase_id
                AND gl.product_id = unique_data.product_id
            )
        )
    ) AS data
FROM 
    inv_aggregated AS inv
LEFT JOIN 
    production_plan AS pp ON inv.prod_plan_id = pp.production_plan_id
    left join 
    packing_plan as pp1 on pp1.packing_process_id = inv.packing_process_id
left join plan_details as pd on pd.production_plan_id = pp.production_plan_id
left join order_items_extract as oie on oie.extract_id = pd.order_extract_id
left join customer_purchase_items as cpi on cpi.items_id = oie.order_items_id
left join customer_purchase as cp on cp.customer_purchase_id = cpi.customer_purchase_id
LEFT JOIN 
    euser AS e ON e.userid = inv.userid
LEFT JOIN 
    euser AS p ON p.userid = inv.approval_id
LEFT JOIN (
    SELECT DISTINCT ON (inv.releseid)
        inv.releseid,
        po.product_id,
        po.sku_id,
        po.product_name,
        po.product_code,
        sp.product_count,
		inv.store_id,
		st.store_name,
		pa.allocated_amount as allocated_quantity,
        uom.uom,
        inv.approved_amount,
        inv.dispatch_amount,
        inv.status
    FROM 
        inv_aggregated AS inv
    LEFT JOIN 
        products AS po ON po.product_id = inv.product_id
		left join plan_allocation pa on inv.prod_plan_id = pa.prod_plan_id 
		and inv.store_id = pa.store_id and pa.product_id = inv.product_id and pa.deleted is not true
		left join store_product sp on sp.product_id = po.product_id and sp.store_id = inv.store_id
		left join store_location st on st.store_id = inv.store_id
    left join uom on uom.id =uom_id 
    ORDER BY inv.releseid, pa.plan_allocation_id DESC
) AS unique_data ON inv.releseid = unique_data.releseid
GROUP BY 
    inv.ref_id, inv.type,
    CONCAT(e.firstname, e.lastname),
    inv.created_on
    order by order_ref desc
    limit :limit offset :offset
        ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           compcode=compcode,
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           prod_plan_id=prod_plan_id,
                                                            ref_id= request.args.get('ref_id', None)))
        return {
            'total_results': sql_query[0].get('total_results') if sql_query else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }

    @login_required(permissions='dispatch.add')
    @dispatch_api_route.expect(dispatch_post_model)
    @dispatch_api_route.marshal_with(create_inventoryRegistry_response)
    def post(self):
        """
        Create inventoryRegistry record and return inserted id
        :return:
        """
        data = request.json
        data = data.get('data')
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        cc = {
            "compcode": compcode,
              "created_on": datetime.datetime.now(),
            'issued_date': datetime.datetime.now(),
              "created_by": cur.get('username')
        }
        relese_ids = set()
        update_product = text('''
        update products set 
        allocated_quantity = cast(coalesce(allocated_quantity,0) as numeric) - :dispatch_amount,
        product_count = coalesce(product_count,0) - cast(:dispatch_amount as numeric)
        where product_id=:product_id
        ''').bindparams(
            product_id=bindparam('product_id', type_=Integer),
            dispatch_amount=bindparam('dispatch_amount', type_=NUMERIC)
        )

        product_id_query = text('''
        select product_id,prod_plan_id,store_id,sub_location from invregistry 
        where releseid=:releseid
        ''').bindparams(
            releseid=bindparam('releseid', type_=NUMERIC)
        )


        update_store = text('''
        update store_product
        set product_count = coalesce(product_count,0) - cast(:dispatch_amount as numeric)
        where store_product_id = (
            SELECT store_product_id FROM store_product 
            WHERE store_id=:store_id and product_id =:product_id and deleted is not true
            and compcode=:compcode
            and COALESCE(sub_location, '') = COALESCE(:sub_location, '')
            and (COALESCE(lot_no, '') = COALESCE(:supplier_lot_no, '') OR lot_no IS NULL)
            ORDER BY CASE WHEN COALESCE(lot_no, '') = COALESCE(:supplier_lot_no, '') THEN 0 ELSE 1 END
            LIMIT 1
        )
        ''').bindparams(
            dispatch_amount = bindparam('dispatch_amount', type_=NUMERIC),
            store_id = bindparam('store_id', type_=Integer),
            product_id = bindparam('product_id', type_=Integer),
            compcode = bindparam('compcode', type_=Integer),
            sub_location = bindparam('sub_location', type_=String),
            supplier_lot_no = bindparam('supplier_lot_no', type_=String)
        )
        # print("SDffdsf", data)

        for i in data:
            i.update(**cc)
            relese_ids.add(i.get('releseid'))
        # db_client.engine.execute(query, relese_ids=relese_ids)
        error = ''
        s = db_client.session
        dispatch_cost_query = text(f'''
            select cost from material_cost
            where product_id =:product_id
        ''').bindparams(
            product_id=bindparam('product_id', type_=Integer)
        )

        allocated_amount_query = text(f'''
        select plan_allocation_id, allocated_amount, store_id from plan_allocation
        where product_id=:product_id and prod_plan_id=:prod_plan_id
        and compcode=:compcode and (store_id=:store_id or store_id is null) and deleted is not true
        order by store_id nulls last
        for update
        ''').bindparams(
            product_id=bindparam('product_id', type_=Integer),
            prod_plan_id=bindparam('prod_plan_id', type_=Integer),
            compcode=bindparam('compcode', type_=Integer),
            store_id=bindparam('store_id', type_=Integer)
        )
        try:
            with s.begin():
                for i in data:
                    # print(i)
                    pro = s.execute(product_id_query, {'releseid': i.get('releseid')}).mappings().all()
                    if not pro or len(pro) == 0:
                        s.rollback()
                        abort(400, message=f"Invalid releseid {i.get('releseid')}")
                    # print(pro[0])
                    product_id = pro[0].get('product_id', None)
                    prod_plan_id = pro[0].get('prod_plan_id', None)
                    store_id = i.get('store_id') or pro[0].get('store_id', None)
                    if not store_id and product_id:
                        store_record = s.execute(
                            text("""
                                SELECT store_id FROM store_product 
                                WHERE product_id = :product_id 
                                  AND compcode = :compcode 
                                  AND deleted IS NOT TRUE 
                                ORDER BY product_count DESC 
                                LIMIT 1
                            """),
                            {"product_id": product_id, "compcode": compcode}
                        ).fetchone()
                        if store_record:
                            store_id = store_record[0]
                    # print(i)
                    allocated_records = s.execute(allocated_amount_query, {'product_id': product_id,
                                                                          'prod_plan_id': prod_plan_id,
                                                                          'compcode': compcode,
                                                                          'store_id': store_id}).mappings().all()
                    if allocated_records:
                        allocated_amount = float(allocated_records[0].get('allocated_amount', 0))
                        plan_allocation_id = allocated_records[0].get('plan_allocation_id')
                    else:
                        allocated_amount = float(i.get('dispatch_amount'))
                        plan_allocation_id = None
                    reduced_allocation_amount = min(allocated_amount, float(i.get('dispatch_amount')))
                    s.execute(update_product, {'dispatch_amount': reduced_allocation_amount, 'product_id': product_id})
                    if plan_allocation_id:
                        # Check if a plan_allocation record with target store_id already exists
                        existing_target_alloc = None
                        if store_id:
                            existing_target_alloc = s.execute(text("""
                                SELECT plan_allocation_id FROM plan_allocation
                                WHERE product_id = :product_id 
                                  AND prod_plan_id = :prod_plan_id 
                                  AND store_id = :store_id
                                  AND plan_allocation_id != :plan_allocation_id
                                LIMIT 1
                            """), {
                                'product_id': product_id,
                                'prod_plan_id': prod_plan_id,
                                'store_id': store_id,
                                'plan_allocation_id': plan_allocation_id
                            }).fetchone()

                        # If target store already has a row (e.g., deleted or active), do not overwrite store_id to avoid uq_plan_alloc violation
                        if existing_target_alloc:
                            s.execute(text("""
                                UPDATE plan_allocation
                                SET allocated_amount = GREATEST(0, allocated_amount - :qty),
                                    deleted = CASE WHEN (allocated_amount - :qty) <= 0 THEN TRUE ELSE deleted END,
                                    modified_on = NOW(),
                                    modified_by = :user
                                WHERE plan_allocation_id = :plan_allocation_id
                            """), {
                                'qty': reduced_allocation_amount,
                                'user': cur.get('username'),
                                'plan_allocation_id': plan_allocation_id
                            })
                        else:
                            s.execute(text("""
                                UPDATE plan_allocation
                                SET allocated_amount = GREATEST(0, allocated_amount - :qty),
                                    deleted = CASE WHEN (allocated_amount - :qty) <= 0 THEN TRUE ELSE deleted END,
                                    store_id = COALESCE(store_id, :store_id),
                                    modified_on = NOW(),
                                    modified_by = :user
                                WHERE plan_allocation_id = :plan_allocation_id
                            """), {
                                'qty': reduced_allocation_amount,
                                'store_id': store_id,
                                'user': cur.get('username'),
                                'plan_allocation_id': plan_allocation_id
                            })
                    
                    actual_dispatch = float(i.get('dispatch_amount') or 0)
                    if actual_dispatch > allocated_amount:
                        over_dispatched_qty = actual_dispatch - allocated_amount
                        s.execute(text("""
                            UPDATE invregistry
                            SET description = COALESCE(description, '') || :warning,
                                modified_on = NOW(),
                                modified_by = :user
                            WHERE releseid = :releseid
                        """), {
                            'warning': f" [Over-dispatched: {actual_dispatch} units dispatched against allocation of {allocated_amount}. Over-dispatched by {over_dispatched_qty}]",
                            'user': cur.get('username'),
                            'releseid': i.get('releseid')
                        })
                    cost = s.execute(dispatch_cost_query, {'product_id': product_id}).fetchone()
                    if cost:
                        i['dispatch_cost'] = float(cost['cost'] or 0) * float(i.get('dispatch_amount') or 0)
                    else:
                        i['dispatch_cost'] = 0.0

                    val = {**i, 'product_id':product_id, 'store_id': store_id, 'compcode': compcode, 'sub_location': pro[0].get('sub_location'), 'supplier_lot_no': i.get('supplier_lot_no') or ''}
                    pprint(val)
                    if store_id:
                        s.execute(update_store, val)

                # Add lot_no mapping and clean up extra fields for bulk insert
                clean_data = []
                for i in data:
                    i_copy = i.copy()
                    i_copy['lot_no'] = i_copy.pop('supplier_lot_no', None)
                    i_copy.pop('status', None)
                    clean_data.append(i_copy)

                s.bulk_insert_mappings(mapper=DispatchRegistry, mappings=clean_data)


        except HTTPException as e:
            s.rollback()
            raise e
        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': "Records created Successfully"
        }, 200


@dispatch_api_route.route('/dispatchget')
class Dispatch(Resource):
    @login_required(permissions='dispatch.list')
    @dispatch_api_route.doc(params=list_api_params)
    @dispatch_api_route.doc(params=dispatch_search)
    @dispatch_api_route.marshal_with(dispatch_get_list_model)
    def get(self):
        cur = request.args.get('current_user')
        compcode = cur.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page

        prod_plan_id = request.args.get('prod_plan_id', None)
        sql_con = ''
        if prod_plan_id:
            sql_con += 'and inv.prod_plan_id=:prod_plan_id '
        query = text(f'''
        select inv.prod_plan_id,inv.packing_process_id,
        pp.plan_unique,pp1.package_unique,
        inv.product_id,p.product_name,p.product_code,p.sku_id,
        sum(inv.requested_amount::integer) as requested_amount
        ,sum(inv.approved_amount::integer) as approved_amount,
        sum(dp.dispatch_amount::integer) as dispatch_amount 
        from dispatch as dp
        left join invregistry as inv on dp.releseid = inv.releseid
        left join products as p on p.product_id = inv.product_id 
        left join production_plan as pp on inv.prod_plan_id = pp.production_plan_id
        left join packing_plan as pp1 on pp1.packing_process_id = inv.packing_process_id
        where dp.compcode=:compcode {sql_con}
        group by inv.prod_plan_id,inv.packing_process_id, pp.plan_unique,pp1.package_unique,inv.product_id,p.product_name,p.product_code,p.sku_id
        ''')
        result = query_to_dict(db_client.engine.execute(query, compcode=compcode, prod_plan_id=prod_plan_id, limit=results_per_page, offset=offset))
        count_query = text(f'''
        with cte as(
        select count(*)
        from dispatch as dp
        left join invregistry as inv on dp.releseid = inv.releseid
        left join products as p on p.product_id = inv.product_id 
        left join production_plan as pp on inv.prod_plan_id = pp.production_plan_id
        left join packing_plan as pp1 on pp1.packing_process_id = inv.packing_process_id
        where dp.compcode=:compcode {sql_con}
        group by inv.prod_plan_id,inv.packing_process_id,pp.plan_unique,pp1.package_unique,inv.product_id,p.product_name
        ) select count(*) from cte
        ''')

        sql_count = query_to_dict(db_client.engine.execute(count_query, compcode=compcode, prod_plan_id=prod_plan_id))

        return {
            'total_results': sql_count[0].get('count') if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }


@dispatch_api_route.route('/plantodispatch')
class PlanToReturn(Resource):

    @login_required()
    @dispatch_api_route.marshal_with(plan_to_dispatch_model)
    @dispatch_api_route.doc(params=dispatch_search)
    def get(self):
        cur = request.args.get('current_user')
        compcode = cur.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page', '20'))
        offset = (paged - 1) * results_per_page

        start_date = request.args.get('start_date', None)

        end_date = request.args.get('end_date', None)

        prod_plan_id = request.args.get('prod_plan_id', None)

        product_id = request.args.get('product_id', None)

        sql_con = ''
        if prod_plan_id:
            sql_con += ' and t1.production_plan_id=:prod_plan_id '
        if product_id:
            sql_con += ' and t1.product_id=:product_id '

        date_con = ''
        if start_date:
            date_con += ' and d.created_on::date between :start_date '

            if end_date:

                date_con += ' and :end_date '

            else:

                date_con += ' and :start_date'

        query = text(f'''
        with cp_data as (
            select pd.production_plan_id, max(cp.order_unique) as order_unique
            from plan_details as pd
            left join order_items_extract as oie on oie.extract_id = pd.order_extract_id
            left join customer_purchase_items as cpi on cpi.items_id = oie.order_items_id
            left join customer_purchase as cp on cp.customer_purchase_id = cpi.customer_purchase_id
            group by pd.production_plan_id
        ),
        t1 as (
			SELECT 
    pp.production_plan_id,
    pp.plan_unique,
    cp_data.order_unique,
    inv.product_id,
    inv.ref_id,
    inv.requested_amount,
    inv.approved_amount,
	SUM(d.dispatch_amount::numeric) as dispatch_amount
FROM production_plan AS pp
left join cp_data on cp_data.production_plan_id = pp.production_plan_id
left join invregistry AS inv ON inv.prod_plan_id = pp.production_plan_id
left join dispatch as d ON d.releseid = inv.releseid 
		where d.deleted is not true and pp.production_plan_id is not null and d.dispatch_amount IS NOT NULL and d.compcode=:compcode {date_con}
			group by  pp.production_plan_id,pp.plan_unique,cp_data.order_unique,inv.product_id,inv.ref_id,inv.requested_amount,inv.approved_amount
		),
		t2 as (
		select rm.prod_plan_id,rm.product_id as p2_id,sum(rm.return_request_amount) as return_requested_amount, sum(rm.return_amount) as return_amount
		from return_material as rm
		where rm.compcode=:compcode
		group by rm.prod_plan_id,rm.product_id
		),
		t3 as(
		select t1.*,t2.*,p.product_code,p.product_name,p.sku_id,u.uom
		 from t1
		left join t2 on t1.production_plan_id = t2.prod_plan_id and t1.product_id = t2.p2_id
		left join products as p on p.product_id = t1.product_id 
		left join uom as u on u.id = p.uom_id
		where 1=1 {sql_con}
		),
		product_level as (
		select 
    t3.production_plan_id,
    t3.plan_unique,
    max(t3.order_unique) as order_unique,
    t3.product_id,
    t3.product_code,
    t3.product_name,
    t3.sku_id,
    t3.uom,
    sum(t3.requested_amount) as requested_amount,
    sum(t3.approved_amount) as approved_amount,
    sum(t3.dispatch_amount) as dispatch_amount,
    sum(coalesce(t3.return_requested_amount, 0)) as return_requested_amount,
    sum(coalesce(t3.return_amount, 0)) as return_amount,
    json_agg(
        json_build_object(
            'ref_id', t3.ref_id,
            'requested_amount', t3.requested_amount,
            'approved_amount', t3.approved_amount,
            'dispatch_amount', t3.dispatch_amount,
            'return_requested_amount', coalesce(t3.return_requested_amount, 0),
            'return_amount', coalesce(t3.return_amount, 0),
            'product_code', t3.product_code,
            'product_name', t3.product_name,
            'sku_id', t3.sku_id,
            'uom', t3.uom
        )
    ) as transactions
from 
    t3
group by 
    t3.production_plan_id,
    t3.plan_unique,
    t3.product_id,
    t3.product_code,
    t3.product_name,
    t3.sku_id,
    t3.uom
    )
    select 
    p.production_plan_id,
    p.plan_unique,
    max(p.order_unique) as order_unique,
    count(*) over() as total_results,
    json_agg(
        json_build_object(
            'product_id', p.product_id,
            'product_code', p.product_code,
            'product_name', p.product_name,
            'sku_id', p.sku_id,
            'uom', p.uom,
            'total_requested_amount', p.requested_amount,
            'total_approved_amount', p.approved_amount,
            'total_dispatch_amount', p.dispatch_amount,
            'total_return_requested_amount', p.return_requested_amount,
            'total_return_amount', p.return_amount,
            'transactions', p.transactions
        )
    ) as products
from 
    product_level p
group by 
    p.production_plan_id,
    p.plan_unique
   order by 
    p.production_plan_id desc
limit :limit offset :offset
                ''')
        result = query_to_dict(
            db_client.engine.execute(query,
                                     compcode=compcode,
                                     prod_plan_id=prod_plan_id,
                                     product_id=product_id,
                                     start_date=start_date,
                                     end_date=end_date,
                                     limit=results_per_page,
                                     offset=offset))

        return {
            'total_results': result[0].get('total_results') if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }


@dispatch_api_route.route('/fast_track_dispatch/')
class FastTrackDispatchApi(Resource):

    @login_required(permissions='dispatch.add')
    def post(self):
        """
        FastTrack Dispatch (Direct Material Issue)
        - Generates FT-XXXXXX ref_id
        - Inserts records in invregistry
        - Inserts records in dispatch
        - Deducts stock from products and store_product
        """
        data = request.json
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        userid = cur.get('userid', None)
        username = cur.get('username', None)

        store_id = data.get('store_id')
        prod_plan_id = data.get('prod_plan_id')
        packing_process_id = data.get('packing_process_id')
        materials = data.get('materials', [])

        if not store_id or not materials:
            return abort(400, "Store ID and materials list are required")

        # Generate unique FT ref_id
        query = text('''
                select max(nullif(regexp_replace(ref_id, '^FT-', ''), '')::integer) as max_no from invregistry where compcode=:compcode and action='Outward' and ref_id like 'FT-%'
                ''')
        result = query_to_dict(db_client.engine.execute(query, compcode=compcode))
        max_no = result[0].get('max_no') if (result and result[0].get('max_no') is not None) else 0
        next_no = int(max_no) + 1
        formatnum = str(int(next_no)).zfill(6)
        ref_id = f"FT-{formatnum}"

        update_product = text('''
        update products set 
        product_count = coalesce(product_count,0) - cast(:dispatch_amount as numeric)
        where product_id=:product_id
        ''').bindparams(
            product_id=bindparam('product_id', type_=Integer),
            dispatch_amount=bindparam('dispatch_amount', type_=NUMERIC)
        )

        update_store = text('''
        update store_product
        set product_count = coalesce(product_count,0) - cast(:dispatch_amount as numeric)
        where store_id=:store_id and product_id =:product_id and deleted is not true
        and compcode=:compcode
        and COALESCE(sub_location, '') = COALESCE(:sub_location, '')
        ''').bindparams(
            dispatch_amount = bindparam('dispatch_amount', type_=NUMERIC),
            store_id = bindparam('store_id', type_=Integer),
            product_id = bindparam('product_id', type_=Integer),
            compcode = bindparam('compcode', type_=Integer),
            sub_location = bindparam('sub_location', type_=String)
        )

        check_store_stock = text('''
        select product_count from store_product
        where store_id=:store_id and product_id =:product_id and deleted is not true
        and compcode=:compcode
        and COALESCE(sub_location, '') = COALESCE(:sub_location, '')
        for update
        ''').bindparams(
            store_id = bindparam('store_id', type_=Integer),
            product_id = bindparam('product_id', type_=Integer),
            compcode = bindparam('compcode', type_=Integer),
            sub_location = bindparam('sub_location', type_=String)
        )

        dispatch_cost_query = text('''
            select cost from material_cost
            where product_id =:product_id
        ''').bindparams(
            product_id=bindparam('product_id', type_=Integer)
        )

        insert_invregistry = text('''
        INSERT INTO invregistry (
            product_id, requested_amount, approved_amount, action, ref_id, 
            prod_plan_id, packing_process_id, status, is_dispatch, store_id, 
            sub_location, compcode, userid, approval_id, approval_date, created_on, created_by, type, deleted
        ) VALUES (
            :product_id, :quantity, :quantity, 'Outward', :ref_id, 
            :prod_plan_id, :packing_process_id, 'Approved', true, :store_id, 
            :sub_location, :compcode, :userid, :userid, NOW(), NOW(), :username, 'FastTrack', false
        ) RETURNING releseid
        ''')

        s = db_client.session
        try:
            with s.begin():
                for item in materials:
                    prod_id = item.get('product_id')
                    qty = float(item.get('quantity', 0))
                    sub_loc = item.get('sub_location')
                    if qty.is_integer():
                        qty = int(qty)

                    if not prod_id or qty <= 0:
                        continue

                    # 0. Validate stock in store
                    stock_res = s.execute(check_store_stock, {
                        'store_id': store_id,
                        'product_id': prod_id,
                        'compcode': compcode,
                        'sub_location': sub_loc
                    }).fetchone()

                    if not stock_res:
                        s.rollback()
                        abort(400, message=f"Product with ID {prod_id} is not available in the specified store/sub-location.")

                    available_qty = float(stock_res['product_count'] or 0)
                    if available_qty < qty:
                        s.rollback()
                        abort(400, message=f"Insufficient stock for Product ID {prod_id}. Available: {available_qty}, Requested: {qty}")

                    item_prod_plan_id = item.get('prod_plan_id', prod_plan_id)
                    item_packing_process_id = item.get('packing_process_id', packing_process_id)

                    # 1. Insert into invregistry and get releseid
                    res = s.execute(insert_invregistry, {
                        'product_id': prod_id,
                        'quantity': qty,
                        'ref_id': ref_id,
                        'prod_plan_id': item_prod_plan_id,
                        'packing_process_id': item_packing_process_id,
                        'store_id': store_id,
                        'sub_location': sub_loc,
                        'compcode': compcode,
                        'userid': userid,
                        'username': username
                    })
                    row = res.fetchone()
                    releseid = row[0]

                    # 2. Get cost and compute dispatch cost
                    cost_res = s.execute(dispatch_cost_query, {'product_id': prod_id}).fetchone()
                    cost = float(cost_res['cost'] or 0) if cost_res else 0.0
                    dispatch_cost = cost * qty
                    if isinstance(dispatch_cost, float) and dispatch_cost.is_integer():
                        dispatch_cost = int(dispatch_cost)

                    # 3. Insert into dispatch
                    dispatch_entry = DispatchRegistry(
                        releseid=releseid,
                        user_id=userid,
                        action='Outward',
                        dispatch_amount=qty,
                        dispatch_cost=dispatch_cost,
                        store_id=store_id,
                        compcode=compcode,
                        created_on=datetime.datetime.now(),
                        created_by=username,
                        deleted=False
                    )
                    s.add(dispatch_entry)

                    # 4. Update stock in products and store_product
                    s.execute(update_product, {'dispatch_amount': qty, 'product_id': prod_id})
                    s.execute(update_store, {
                        'dispatch_amount': qty,
                        'store_id': store_id,
                        'product_id': prod_id,
                        'compcode': compcode,
                        'sub_location': sub_loc
                    })
        except HTTPException as e:
            s.rollback()
            raise e
        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': "FastTrack Dispatch created successfully",
            'ref_id': ref_id
        }, 200

@dispatch_api_route.route('/short_close')
class ShortCloseApi(Resource):
    @login_required(permissions='dispatch.add')
    def post(self):
        data = request.json
        releseids = data.get('releseids', [])
        cur = request.args.get('current_user', {})
        username = cur.get('username')
        compcode = cur.get('company_id')

        s = db_client.session
        try:
            with s.begin():
                for releseid in releseids:
                    # 1. Update invregistry status to 'Short Closed' and is_dispatch = TRUE
                    s.execute(text("""
                        UPDATE invregistry
                        SET status = 'Short Closed',
                            is_dispatch = TRUE,
                            modified_by = :username,
                            modified_on = NOW()
                        WHERE releseid = :releseid
                          AND (:compcode IS NULL OR compcode = :compcode)
                    """), {"username": username, "releseid": releseid, "compcode": compcode})
                    
                    # 2. Get details to release allocation
                    inv = s.execute(text("""
                        SELECT prod_plan_id, product_id, store_id, approved_amount, requested_amount
                        FROM invregistry 
                        WHERE releseid = :releseid
                          AND (:compcode IS NULL OR compcode = :compcode)
                    """), {"releseid": releseid, "compcode": compcode}).fetchone()
                    
                    if inv and inv.prod_plan_id:
                        # Find total dispatched
                        disp = s.execute(text("""
                            SELECT SUM(dispatch_amount::numeric) as total_dispatch 
                            FROM dispatch 
                            WHERE releseid = :releseid 
                              AND deleted IS NOT TRUE
                              AND (:compcode IS NULL OR compcode = :compcode)
                        """), {"releseid": releseid, "compcode": compcode}).fetchone()
                        
                        total_disp = float(disp.total_dispatch or 0)
                        approved = float(inv.approved_amount or 0)
                        remaining = max(0, approved - total_disp)
                        
                        if remaining > 0:
                            # 1) Release allocation in plan_allocation table
                            alloc_records = s.execute(text("""
                                SELECT plan_allocation_id, allocated_amount, store_id 
                                FROM plan_allocation
                                WHERE prod_plan_id = :prod_plan_id 
                                  AND product_id = :product_id 
                                  AND (:compcode IS NULL OR compcode = :compcode)
                                  AND (store_id = :store_id OR store_id IS NULL)
                                  AND deleted IS NOT TRUE
                                ORDER BY store_id NULLS LAST
                                FOR UPDATE
                            """), {
                                "prod_plan_id": inv.prod_plan_id, 
                                "product_id": inv.product_id, 
                                "store_id": inv.store_id,
                                "compcode": compcode
                            }).fetchall()

                            remaining_to_release = remaining
                            for alloc in alloc_records:
                                if remaining_to_release <= 0:
                                    break
                                alloc_amount = float(alloc.allocated_amount or 0)
                                release_qty = min(alloc_amount, remaining_to_release)
                                if release_qty > 0:
                                    s.execute(text("""
                                        UPDATE plan_allocation
                                        SET allocated_amount = GREATEST(0, allocated_amount - :qty),
                                            deleted = CASE WHEN (allocated_amount - :qty) <= 0 THEN TRUE ELSE deleted END,
                                            modified_on = NOW(),
                                            modified_by = :username
                                        WHERE plan_allocation_id = :plan_allocation_id
                                    """), {
                                        "qty": release_qty,
                                        "username": username,
                                        "plan_allocation_id": alloc.plan_allocation_id
                                    })
                                    remaining_to_release -= release_qty

                            # 2) Release allocation in products table
                            s.execute(text("""
                                UPDATE products
                                SET allocated_quantity = GREATEST(0, COALESCE(allocated_quantity, 0) - :remaining)
                                WHERE product_id = :product_id
                            """), {
                                "remaining": remaining,
                                "product_id": inv.product_id
                            })
        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)
            
        return {"success": True, "message": "Items short closed successfully"}, 200

@dispatch_api_route.route('/reopen')
class ReopenApi(Resource):
    @login_required(permissions='dispatch.add')
    def post(self):
        data = request.json
        releseids = data.get('releseids', [])
        cur = request.args.get('current_user', {})
        username = cur.get('username')
        compcode = cur.get('company_id')

        s = db_client.session
        try:
            with s.begin():
                for releseid in releseids:
                    inv = s.execute(text("""
                        SELECT prod_plan_id, product_id, store_id, approved_amount
                        FROM invregistry 
                        WHERE releseid = :releseid
                          AND (:compcode IS NULL OR compcode = :compcode)
                    """), {"releseid": releseid, "compcode": compcode}).fetchone()
                    
                    if inv and inv.prod_plan_id:
                        disp = s.execute(text("""
                            SELECT SUM(dispatch_amount::numeric) as total_dispatch 
                            FROM dispatch 
                            WHERE releseid = :releseid 
                              AND deleted IS NOT TRUE
                              AND (:compcode IS NULL OR compcode = :compcode)
                        """), {"releseid": releseid, "compcode": compcode}).fetchone()
                        
                        total_disp = float(disp.total_dispatch or 0)
                        approved = float(inv.approved_amount or 0)
                        remaining = max(0, approved - total_disp)
                        
                        if remaining > 0:
                            alloc = s.execute(text("""
                                SELECT plan_allocation_id FROM plan_allocation
                                WHERE prod_plan_id = :prod_plan_id 
                                  AND product_id = :product_id 
                                  AND (:compcode IS NULL OR compcode = :compcode)
                                  AND (store_id = :store_id OR store_id IS NULL)
                                ORDER BY store_id NULLS LAST
                                LIMIT 1
                            """), {
                                "prod_plan_id": inv.prod_plan_id, 
                                "product_id": inv.product_id, 
                                "store_id": inv.store_id,
                                "compcode": compcode
                            }).fetchone()
                            
                            if alloc:
                                s.execute(text("""
                                    UPDATE plan_allocation
                                    SET allocated_amount = allocated_amount + :remaining,
                                        deleted = FALSE,
                                        modified_on = NOW(),
                                        modified_by = :username
                                    WHERE plan_allocation_id = :plan_allocation_id
                                """), {"remaining": remaining, "username": username, "plan_allocation_id": alloc.plan_allocation_id})
                            else:
                                s.execute(text("""
                                    INSERT INTO plan_allocation (
                                        product_id, prod_plan_id, store_id, allocated_amount, compcode, created_by, created_on
                                    ) VALUES (
                                        :product_id, :prod_plan_id, :store_id, :remaining, :compcode, :username, NOW()
                                    )
                                """), {
                                    "product_id": inv.product_id, "prod_plan_id": inv.prod_plan_id, "store_id": inv.store_id,
                                    "remaining": remaining, "compcode": compcode, "username": username
                                })

                            # Update products allocated_quantity
                            s.execute(text("""
                                UPDATE products
                                SET allocated_quantity = COALESCE(allocated_quantity, 0) + :remaining
                                WHERE product_id = :product_id
                            """), {
                                "remaining": remaining,
                                "product_id": inv.product_id
                            })

                    # Finally, revert status
                    s.execute(text("""
                        UPDATE invregistry
                        SET status = 'Approved',
                            is_dispatch = FALSE,
                            modified_by = :username,
                            modified_on = NOW()
                        WHERE releseid = :releseid
                          AND (:compcode IS NULL OR compcode = :compcode)
                    """), {"username": username, "releseid": releseid, "compcode": compcode})
                    
        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)
            
        return {"success": True, "message": "Items reopened successfully"}, 200
