import datetime
from pprint import pprint

from flask import request, session
from flask_restx import Resource, abort

from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger, bindparam, NUMERIC, Integer, DateTime, String
from sqlalchemy.exc import SQLAlchemyError

from .bulk_insert import inventory_ops
from .. import ipss_db, db_client
from ..api_doc import search_filters, stock_search, dispatch_search, report_filter
from ..models.return_material import DispatchRegistry
from ipss_utils.decorators import login_required
from ..routes.return_material import return_list_response, return_api_route, dispatch_drop_get_list, retrurn_post_model, \
    post_reponse, post_model, report_list_response
from .errorhandling import map_sqlalchemy_error_to_http_status, update_local

primary_key = 'releseid'


@return_api_route.route('/')
class ReturnApiroute(Resource):
    per_page = 20

    @return_api_route.marshal_with(return_list_response)
    @return_api_route.doc(params=list_api_params)
    @return_api_route.doc(params=search_filters)
    @login_required(permissions='return_material.list')
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
        compcode = request.args.get('current_user', {}).get('company_id', None)
        print(compcode, 'QWE')
        prod_plan_id = request.args.get('prod_plan_id', None)
        product_id = request.args.get('product_id', None)
        status = request.args.get('status', None)
        unique_id = request.args.get('unique_id', None)
        sql_con = ''
        if product_id:
            sql_con += ' and rm.product_id=:product_id '
        if status:
            sql_con += ' and rm.status=:status '
        if prod_plan_id:
            sql_con += 'and rm.prod_plan_id=:prod_plan_id '
        if unique_id:
            sql_con += 'and rm.unique_id=:unique_id '

        sql_query = text(f'''
		select rm.prod_plan_id,rm.packing_process_id,
		pp.plan_unique,pp1.package_unique,
		rm.unique_id,
		rm.created_on::date as requested_date,rm.created_by as requested_by,
		max(return_material_id) as max_id,
		case 
		    when bool_and(rm.status='Moved') then True
		    else False
		end as status,
		max(cp.order_unique) as order_unique,
		json_agg(
		json_build_object(
		'return_material_id', rm.return_material_id,
		'product_id', rm.product_id,
		'sku_id', p.sku_id,
		'product_name', COALESCE(NULLIF(p.product_name, ''), p.product_code, p.sku_id),
		'product_code', COALESCE(NULLIF(p.product_code, ''), p.product_name, p.sku_id),
		'return_request_amount', rm.return_request_amount,
		'return_amount', rm.return_amount,
		'status', rm.status,
		'remarks', rm.remarks,
		'description', rm.description,
		'uom',uom.uom,
		'uom_id', p.uom_id,
		'moved_date', rm.moved_date::date,
		'is_rejected', rm.is_rejected,
		'rejection_action', rm.rejection_action,
		'rejection_store_id', rm.rejection_store_id,
		'store_id', rm.store_id,
		'lot_no', rm.lot_no,
		'store_name', sl.store_name
		)
		) as data
		from return_material as rm
		left join production_plan as pp on rm.prod_plan_id = pp.production_plan_id
		left join plan_details as pd on pd.production_plan_id = pp.production_plan_id
		left join order_items_extract as oie on oie.extract_id = pd.order_extract_id
		left join customer_purchase_items as cpi on cpi.items_id = oie.order_items_id
		left join customer_purchase as cp on cp.customer_purchase_id = cpi.customer_purchase_id
		left join packing_plan as pp1 on rm.packing_process_id = pp1.packing_process_id
		left join products as p on rm.product_id = p.product_id
		left join uom on uom.id =p.uom_id 
		left join store_location as sl on sl.store_id = COALESCE(rm.rejection_store_id, rm.store_id)
		where rm.deleted is not true and rm.compcode =:compcode {sql_con}
		group by rm.prod_plan_id,rm.packing_process_id,pp.plan_unique,pp1.package_unique,rm.unique_id,rm.created_on::date,rm.created_by
		order by max_id desc
        limit :limit offset :offset
        ''')
        result = query_to_dict(db_client.engine.execute(sql_query,
                                                        compcode=compcode,
                                                        prod_plan_id=prod_plan_id,
                                                        limit=results_per_page,
                                                        offset=offset,
                                                        status=status,
                                                        product_id=product_id,
                                                        unique_id=unique_id
                                                        ))
        sql_count_query = text(f'''   
        select count(distinct unique_id) from
        (
        select rm.prod_plan_id,rm.unique_id,pp.plan_unique,
        json_agg(
            json_build_object(
                'return_material_id', rm.return_material_id,
                'product_name', COALESCE(NULLIF(p.product_name, ''), p.product_code, p.sku_id),
                'sku_id', p.sku_id,
                'request_return_amount', rm.return_request_amount,
                'return_amount', rm.return_amount
            )
        ) AS data
         from return_material as rm 
        left join production_plan as pp on pp.production_plan_id = rm.prod_plan_id
        left join products as p on p.product_id = rm.product_id
        where rm.compcode=:compcode and rm.deleted is not true {sql_con}
        group by rm.prod_plan_id,rm.unique_id,pp.plan_unique
        ) as cte
        ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count_query, compcode=compcode,
                                                           prod_plan_id=prod_plan_id,
                                                           status=status,
                                                           product_id=product_id,
                                                           unique_id=unique_id))
        return {
            'total_results': sql_count[0].get('count') if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }

    @login_required(permissions='return_material.add')
    @return_api_route.expect(retrurn_post_model)
    @return_api_route.marshal_with(post_reponse)
    def post(self):
        """
        Create inventoryRegistry record and return inserted id
        :return:
        """
        data = request.json
        data = data.get('data')
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        query = text('''
                        select count(distinct return_material.unique_id) from return_material where compcode=:compcode
                        ''')
        result = query_to_dict(db_client.engine.execute(query, compcode=compcode))
        count = result[0].get('count', 0) if len(result) else 0
        next_no = int(count) + 1
        formatnum = str(int(next_no)).zfill(6)
        sequenc_num = f"RET-{formatnum}"
        print(sequenc_num)
        cc = {
            "compcode": compcode,
            'unique_id': sequenc_num,
            "created_on": datetime.datetime.now(),
            'created_by': cur.get('username', None),
            "userid": cur.get('userid')
        }
        data = [{**i, **cc} for i in data]
        error = ''
        s = db_client.session
        try:
            with s.begin():
                s.bulk_insert_mappings(mapper=DispatchRegistry, mappings=data)
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

    @return_api_route.marshal_with(post_reponse)
    @return_api_route.expect(retrurn_post_model)
    @login_required(permissions='return_material.edit')
    def patch(self):
        """
        List of inventoryRegistry with pagination
        TODO: Search Notification_manage
        :return:
        """
        data = request.json
        data = data.get('data')
        cur = request.args.get('current_user', {})
        s = db_client.session
        try:
            with s.begin():
                s.bulk_update_mappings(mapper=DispatchRegistry, mappings=data)
                for i in data:
                    return_material_id = i.get('return_material_id', None)
                    if not return_material_id:
                        continue
                    rm_record = s.query(DispatchRegistry).get(return_material_id)
                    if not rm_record:
                        continue
                    
                    status = rm_record.status
                    return_amount = rm_record.return_amount
                    product_id = rm_record.product_id
                    store_id = rm_record.store_id
                    is_rejected = rm_record.is_rejected
                    rejection_action = rm_record.rejection_action
                    rejection_store_id = rm_record.rejection_store_id
                    compcode = rm_record.compcode
                    created_by = rm_record.created_by
                    
                    if status and return_amount and product_id:
                        if status == 'Moved':
                            if is_rejected:
                                # Count current sequences to make a unique RJT ID
                                count_q = text('select count(*) as cnt from rejected_material')
                                count_res = s.execute(count_q).fetchone()
                                next_seq = int(count_res.cnt if count_res else 0) + 1
                                unique_id = f"RJT-{str(next_seq).zfill(6)}"
                                
                                insert_q = text('''
                                    INSERT INTO rejected_material (
                                        unique_id, product_id, rejected_quantity,
                                        action, store_id, status, compcode,
                                        created_on, created_by
                                    )
                                    VALUES (
                                        :unique_id, :product_id, :rejected_quantity,
                                        :action, :store_id, 'Pending', :compcode,
                                        NOW(), :created_by
                                    )
                                ''')
                                s.execute(insert_q, {
                                    'unique_id': unique_id,
                                    'product_id': product_id,
                                    'rejected_quantity': float(return_amount),
                                    'action': rejection_action or 'Return to Store',
                                    'store_id': rejection_store_id or store_id,
                                    'compcode': cur.get('company_id', compcode),
                                    'created_by': cur.get('username', created_by),
                                })
                            else:
                                # Normal return: Add back to normal stock count
                                query = text('''UPDATE products 
                                    SET product_count = 
                                        CASE 
                                            WHEN :status = 'Moved' THEN COALESCE(product_count, 0) + COALESCE(CAST(:return_amount AS NUMERIC), 0)
                                            WHEN COALESCE(:status, 'Rejected') = 'Approved' THEN product_count
                                            ELSE product_count
                                        END
                                    WHERE product_id = :product_id
                                ''')
                                s.execute(query, {'status': status, 'return_amount': return_amount, 'product_id': product_id})
                                if store_id:
                                    check_store = text('''
                                        SELECT EXISTS (
                                            SELECT 1 FROM store_product 
                                            WHERE product_id = :product_id AND store_id = :store_id 
                                              AND COALESCE(lot_no, '') = COALESCE(:lot_no, '')
                                              AND COALESCE(sub_location, '') = '' 
                                              AND deleted IS NOT TRUE
                                        )
                                    ''')
                                    exists = s.execute(check_store, {'product_id': product_id, 'store_id': store_id, 'lot_no': rm_record.lot_no}).scalar()

                                    if exists:
                                        store_query = text('''
                                            UPDATE store_product 
                                            SET product_count = 
                                                CASE 
                                                    WHEN :status = 'Moved' THEN COALESCE(product_count, 0) + COALESCE(CAST(:return_amount AS NUMERIC), 0)
                                                    WHEN COALESCE(:status, 'Rejected') = 'Approved' THEN product_count
                                                    ELSE product_count
                                                END,
                                                modified_by = :created_by,
                                                modified_on = NOW()
                                            WHERE product_id = :product_id AND store_id = :store_id AND COALESCE(lot_no, '') = COALESCE(:lot_no, '')
                                              AND COALESCE(sub_location, '') = ''
                                              AND deleted IS NOT TRUE
                                        ''')
                                        s.execute(store_query, {'status': status, 'return_amount': return_amount, 'product_id': product_id, 'store_id': store_id, 'lot_no': rm_record.lot_no, 'created_by': cur.get('username', created_by)})
                                    else:
                                        ins_store_product = text('''
                                            INSERT INTO store_product (product_id, store_id, lot_no, sub_location, product_count, compcode, created_on, created_by, deleted)
                                            VALUES (:product_id, :store_id, :lot_no, '', 
                                                CASE 
                                                    WHEN :status = 'Moved' THEN COALESCE(CAST(:return_amount AS NUMERIC), 0)
                                                    ELSE 0
                                                END,
                                                :compcode, NOW(), :created_by, FALSE)
                                        ''')
                                        s.execute(ins_store_product, {
                                            'product_id': product_id,
                                            'store_id': store_id,
                                            'lot_no': rm_record.lot_no,
                                            'status': status,
                                            'return_amount': return_amount,
                                            'compcode': compcode,
                                            'created_by': cur.get('username', created_by)
                                        })

                                # Insert inward ledger record into invregistry
                                ins_registry = text('''
                                    INSERT INTO invregistry (
                                        product_id, requested_amount, approved_amount, action, ref_id, 
                                        status, is_dispatch, store_id, lot_no, compcode, userid, approval_id, 
                                        approval_date, created_on, created_by, type, deleted
                                    ) VALUES (
                                        :product_id, :requested_amount, :approved_amount, 'Inward', :ref_id, 
                                        'Approved', false, :store_id, :lot_no, :compcode, :userid, :userid, 
                                        NOW(), NOW(), :username, 'Return', false
                                    )
                                ''')
                                s.execute(ins_registry, {
                                    'product_id': product_id,
                                    'requested_amount': rm_record.return_request_amount,
                                    'approved_amount': return_amount,
                                    'ref_id': rm_record.unique_id,
                                    'store_id': store_id,
                                    'lot_no': rm_record.lot_no,
                                    'compcode': compcode,
                                    'userid': rm_record.user_id,
                                    'username': cur.get('username', created_by)
                                })
                            
        except SQLAlchemyError as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': "Update successful"
        }


@return_api_route.route('/dispatchget')
class Dispatch(Resource):
    @login_required(permissions='return_material.list')
    @return_api_route.doc(params=list_api_params)
    @return_api_route.doc(params=dispatch_search)
    @return_api_route.marshal_with(dispatch_drop_get_list)
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
select 
    inv.prod_plan_id,
	inv.packing_process_id,
	pp2.package_unique,
    pp.plan_unique,
--	max(inv.releseid),
    JSON_AGG(
        JSON_BUILD_OBJECT(
            'product_id', inv.product_id,
            'product_name', COALESCE(NULLIF(p.product_name, ''), p.product_code, p.sku_id),
            'product_code', COALESCE(NULLIF(p.product_code, ''), p.product_name, p.sku_id),
            'uom_id', p.uom_id,
            'uom', u.uom,
            'sku_id', p.sku_id,
            'requested_amount', inv.request_amount,
            'approved_amount', inv.approve_amount,
            'dispatch_amount', inv.dispatch_amount,
            'return_amount', inv.return_amount,
            'store_id', inv.store_id,
            'store_name', sl.store_name
        )
    ) AS data
FROM (
				select 
					inv.prod_plan_id,
					inv.packing_process_id,
					inv.product_id,
					-- inv.releseid,
					sum(inv.requested_amount) as request_amount,
					sum(inv.approved_amount) as approve_amount,
					sum(dp.dispatch_amount) as dispatch_amount,
					sum(rm.return_amount) as return_amount,
                    max(dp.store_id) as store_id
					from invregistry as inv
				LEFT JOIN 
					(
						select releseid,compcode,sum(dispatch_amount::numeric) as dispatch_amount, max(store_id) as store_id
						from dispatch group by releseid,compcode
					) as dp
				 ON dp.releseid = inv.releseid
				 left join 
					(
						select prod_plan_id,product_id,sum(return_amount) as return_amount
						from return_material group by prod_plan_id,product_id
					) as rm
					on inv.prod_plan_id = rm.prod_plan_id and inv.product_id = rm.product_id
				left join 
					(
						select packing_process_id,product_id,sum(return_amount) as return_amount
						from return_material group by packing_process_id,product_id
					) as rm2
					on inv.packing_process_id = rm2.packing_process_id and inv.product_id = rm2.product_id
					WHERE 
					inv.deleted is not true and inv.compcode=:compcode and inv.action='Outward'
					and (inv.prod_plan_id is not null or inv.packing_process_id is not null)
					group by 
					-- inv.releseid,
					inv.prod_plan_id,inv.packing_process_id,inv.product_id
        ) as inv
left join 
    products AS p ON p.product_id = inv.product_id
left join 
    uom as u on u.id = p.uom_id
left join
    production_plan AS pp ON inv.prod_plan_id = pp.production_plan_id
left join 
	packing_plan as pp2 on inv.packing_process_id = pp2.packing_process_id
left join 
    store_location sl on sl.store_id = inv.store_id
    where 1=1 {sql_con}
group by
    inv.prod_plan_id,inv.packing_process_id, pp.plan_unique,pp2.package_unique
order by inv.prod_plan_id desc
    limit :limit offset :offset
        ''')
        result = query_to_dict(
            db_client.engine.execute(query, compcode=compcode, prod_plan_id=prod_plan_id, limit=results_per_page,
                                     offset=offset))
        count_query = text(f'''
        select count(*)
        from (
            select inv.prod_plan_id, inv.packing_process_id
            from invregistry as inv
            where inv.deleted is not true and inv.compcode=:compcode and inv.action='Outward'
            and (inv.prod_plan_id is not null or inv.packing_process_id is not null)
            {sql_con}
            group by inv.prod_plan_id, inv.packing_process_id
        ) as c
        ''')

        sql_count = query_to_dict(db_client.engine.execute(count_query, compcode=compcode, prod_plan_id=prod_plan_id))

        return {
            'total_results': sql_count[0].get('count') if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }



@return_api_route.route('/report')
class ReportApiroute(Resource):
    per_page = 20

    @return_api_route.marshal_with(report_list_response)
    @return_api_route.doc(params=list_api_params)
    @return_api_route.doc(params=search_filters)
    @return_api_route.doc(params=report_filter)
    @login_required(permissions='return_report.list')
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
        compcode = request.args.get('current_user', {}).get('company_id', None)
        print(compcode, 'QWE')
        prod_plan_id = request.args.get('prod_plan_id', None)
        product_id = request.args.get('product_id', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)

        sql_con = ''


        if prod_plan_id:
            sql_con += ' and cte.prod_plan_id=:prod_plan_id '

        if product_id:
            sql_con += ' and cte.product_id=:product_id '

        if start_date:
            sql_con += ' and cte.return_date between :start_date '

            if end_date:
                sql_con += 'and :end_date'
            else:
                sql_con += 'and :start_date'

        query = text(f'''
        with cte as(
with t2 as (
        select pp.production_plan_id,
            pp.plan_unique,
            max(cp.order_unique) as order_unique,
            inv.product_id,
            p.sku_id,
            p.product_name,
            uom.uom,
            p.product_code,
            sum(dp.dispatch_amount::NUMERIC) as dispatch_amount 
            from dispatch as dp
        left join invregistry as inv on inv.releseid = dp.releseid
        left join production_plan as pp on inv.prod_plan_id = pp.production_plan_id
        left join plan_details as pd on pd.production_plan_id = pp.production_plan_id
        left join order_items_extract as oie on oie.extract_id = pd.order_extract_id
        left join customer_purchase_items as cpi on cpi.items_id = oie.order_items_id
        left join customer_purchase as cp on cp.customer_purchase_id = cpi.customer_purchase_id
        left join products as p on p.product_id = inv.product_id
left join uom on uom.id =uom_id 
        where inv.deleted is not true and inv.compcode =:compcode
        group by pp.production_plan_id,pp.plan_unique,inv.product_id,p.sku_id,p.product_name,p.product_code,uom.uom),
        t1 as (select prod_plan_id,
               product_id,
               sum(return_amount) as return_amount,
               moved_date::date as return_date from return_material 
        where deleted is not true and compcode =:compcode
		group by prod_plan_id,product_id,moved_date::date) 
		select t1.*,t2.plan_unique,t2.order_unique,t2.sku_id,t2.product_code,t2.product_name,t2.uom,t2.dispatch_amount from t1 
		left join t2 on t1.prod_plan_id = t2.production_plan_id and t1.product_id = t2.product_id
		)
		select cte.prod_plan_id,cte.plan_unique,max(cte.order_unique) as order_unique,
		json_agg(
		json_build_object(
		'product_id', cte.product_id,
			'sku_id', cte.sku_id,
			'product_code', COALESCE(NULLIF(cte.product_code, ''), cte.product_name, cte.sku_id),
			'product_name', COALESCE(NULLIF(cte.product_name, ''), cte.product_code, cte.sku_id),
			'dispatch_amount', cte.dispatch_amount,
			'return_amount', cte.return_amount,
			'return_date', cte.return_date,
			'uom', cte.uom
		)
		) as data
		from cte
		where 1=1 {sql_con}
		group by cte.prod_plan_id,cte.plan_unique
        limit :limit offset :offset
        ''')
        sql_count = text(f'''
        with con as(
            with cte as(
with t2 as (
        select pp.production_plan_id,
            pp.plan_unique,
            inv.product_id,
            p.sku_id,
            p.product_name,
            uom.uom,
            p.product_code,
            sum(dp.dispatch_amount::NUMERIC) as dispatch_amount 
            from dispatch as dp
        left join invregistry as inv on inv.releseid = dp.releseid
        left join production_plan as pp on inv.prod_plan_id = pp.production_plan_id
        left join products as p on p.product_id = inv.product_id
left join uom on uom.id =uom_id 
        where inv.deleted is not true and inv.compcode =:compcode
        group by pp.production_plan_id,pp.plan_unique,inv.product_id,p.sku_id,p.product_name,p.product_code,uom.uom),
        t1 as (select prod_plan_id,
               product_id,
               sum(return_amount) as return_amount,
               moved_date::date as return_date from return_material 
        where deleted is not true and compcode =:compcode
		group by prod_plan_id,product_id,moved_date::date) 
		select t1.*,t2.plan_unique,t2.sku_id,t2.product_code,t2.product_name,t2.uom,t2.dispatch_amount from t1 
		left join t2 on t1.prod_plan_id = t2.production_plan_id and t1.product_id = t2.product_id
		)
		select cte.prod_plan_id,cte.plan_unique,
		json_agg(
		json_build_object(
		'product_id', cte.product_id,
			'sku_id', cte.sku_id,
			'product_code', COALESCE(NULLIF(cte.product_code, ''), cte.product_name, cte.sku_id),
			'product_name', COALESCE(NULLIF(cte.product_name, ''), cte.product_code, cte.sku_id),
			'dispatch_amount', cte.dispatch_amount,
			'return_amount', cte.return_amount,
			'return_date', cte.return_date,
			'uom', cte.uom
		)
		) as data
		from cte
		where 1=1 {sql_con}
		group by cte.prod_plan_id,cte.plan_unique
            )
            select count(con.*) from con
        ''')
        result = query_to_dict(db_client.engine.execute(query, compcode=compcode,
                                                        limit=results_per_page,
                                                        offset=offset,
                                                        prod_plan_id=prod_plan_id,
                                                        product_id=product_id,
                                                        start_date=start_date,
                                                        end_date=end_date))

        sql_count = query_to_dict(db_client.engine.execute(sql_count, compcode=compcode,
                                                        prod_plan_id =prod_plan_id,
                                                        product_id =product_id,
                                                        start_date =start_date,
                                                        end_date =end_date))
        return {
            'total_results': sql_count[0].get('count') if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }
