import datetime
from pprint import pprint

from flask import request, session
from flask_restx import Resource, abort
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger, bindparam, NUMERIC, Integer, DateTime, String
from sqlalchemy.exc import SQLAlchemyError
from psycopg2.errors import CheckViolation

from .bulk_insert import inventory_ops, inventory_inv
from .. import ipss_db, db_client
from ..api_doc import invRegistryFields, search_filters, stock_search, report_date_params
from ..models.invregistry import InvRegistry, planAllocation
from ipss_utils.decorators import login_required
from ..routes.invregistry import invRegistry_api_route, inventoryRegistry_list_response, \
    create_inventoryRegistry_response, stockList_api_route, stock_list_response, \
    update_inventoryRegistry_model, update_inventoryRegistry_response, inventoryBulk_model, manual_list_response_model, \
    manual_post_model, store_product_list_model, transfer_log_model, transfer_post_model, transfer_get_list_response, \
    inventory_report_response, stock_movement_response, reconciliation_alerts_response, reconcile_post_model, reconcile_response, stock_audit_response, stock_audit_drilldown_response, stock_audit_reconcile_post_model
from ..routes.invregistry import create_inventoryRegistry_model, get_inventoryRegistry_response
from .errorhandling import map_sqlalchemy_error_to_http_status, update_local

primary_key = 'releseid'

@invRegistry_api_route.route('/')
class inventoryRegistryApi(Resource):
    per_page = 20

    @invRegistry_api_route.marshal_with(inventoryRegistry_list_response)
    @invRegistry_api_route.doc(params=list_api_params)
    @invRegistry_api_route.doc(params=search_filters)
    # @user_verify(permission='InventoryRegistry.list', db_client=db_client)
    @login_required()
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
        # print(compcode ,'QWE')
        prod_plan_id = request.args.get('prod_plan_id', None)
        packing_process_id = request.args.get('packing_process_id', None)
        type = request.args.get('type', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', start_date)
        sql_con = ''
        if request.args.get('releseid', None):
            sql_con += ' and iry.releseid=:releseid '
        if request.args.get('is_from', None):
            sql_con += ' and iry.is_from=:is_from '
        if request.args.get('product_id', None):
            sql_con += ' and iry.product_id=:product_id '
        if request.args.get('action', None):
            sql_con += ' and iry.action=:action '
        if request.args.get('ref_id', None):
            sql_con += ' and iry.ref_id=:ref_id '
        if request.args.get('status', None):
            sql_con += ' and iry.status=:status '
        if request.args.get('is_returned', None):
            sql_con += 'and iry.is_returned=:is_returned '
        if prod_plan_id:
            sql_con += 'and iry.prod_plan_id=:prod_plan_id '

        if packing_process_id:
            sql_con += ' and iry.packing_process_id=:packing_process_id '
        if type:
            sql_con += 'and iry.type=:type '
        if start_date:
            sql_con += ' and iry.created_on::date BETWEEN :start_date AND :end_date '
        lot_no = request.args.get('lot_no', None)
        if lot_no and lot_no not in ('--All--', 'ALL', 'null', ''):
            sql_con += ''' and (
                iry.lot_no = :lot_no 
                or pp.lot_number = :lot_no
                or EXISTS (
                    SELECT 1 FROM grnotes grn
                    JOIN grnlineitems gli ON gli.grnotesid = grn.grnotesid
                    JOIN joline_items jli ON gli.purchase_items_id = jli.id
                    WHERE grn.grn_no = iry.ref_id 
                      AND (trim(jli.lot_no) = :lot_no OR trim(jli.product_details->>'target_lot_number') = :lot_no)
                )
                or EXISTS (
                    SELECT 1 FROM plan_details pd
                    WHERE pd.production_plan_id = pp.production_plan_id
                      AND trim(pd.lot_number) = :lot_no
                )
            ) '''
        sql_query = text(f'''
    SELECT 
    iry.prod_plan_id,
    iry.packing_process_id,
    iry.ref_id,
    iry.type,
    pp.plan_unique,
    packing_plan.package_unique,
    concat(e.firstname, e.lastname) as requested_by,
    min(iry.created_on) as requested_on,
    (
        SELECT max(cp.order_unique)
        FROM plan_details pd
        LEFT JOIN order_items_extract oie ON oie.extract_id = pd.order_extract_id
        LEFT JOIN customer_purchase_items cpi ON cpi.items_id = oie.order_items_id
        LEFT JOIN customer_purchase cp ON cp.customer_purchase_id = cpi.customer_purchase_id
        WHERE pd.production_plan_id = pp.production_plan_id
    ) as order_unique,
    coalesce(
        nullif(trim(min(iry.lot_no)), ''),
        nullif(trim(min(pp.lot_number)), ''),
        (
            SELECT string_agg(DISTINCT coalesce(nullif(trim(jli.lot_no), ''), nullif(trim(jli.product_details->>'target_lot_number'), '')), ', ')
            FROM grnotes grn
            JOIN grnlineitems gli ON gli.grnotesid = grn.grnotesid
            JOIN joline_items jli ON gli.purchase_items_id = jli.id
            WHERE grn.grn_no = iry.ref_id
        ),
        (
            SELECT string_agg(DISTINCT coalesce(nullif(trim(pd.lot_number), ''), nullif(trim(min(pp.lot_number)), '')), ', ')
            FROM plan_details pd
            WHERE pd.production_plan_id = pp.production_plan_id
        )
    ) as lot_no,
    count(*) over() as total_records,
    jsonb_agg(
        jsonb_strip_nulls(
            to_jsonb(iry) - 'prod_plan_id' - 'ref_id' - 'compcode' - 'created_on'
        ) || 
        jsonb_build_object(
            'product_count', p.product_count,
            'product_name', p.product_name,
			'approved_by', concat(m.firstname, m.lastname),
			'reason', iry.reason,
			'store_id', iry.store_id,
			'store_name', sl.store_name,
			'sku_id', p.sku_id,
			'allocated_quantity',p.allocated_quantity,
			'product_code',p.product_code,
			'uom',uom.uom,
			'unit_cost', coalesce(p.cost, 0),
			'weighted_avg_rate', coalesce(nullif(p.moving_avg_cost, 0), p.cost, 0),
			'last_grn_rate', coalesce(nullif(p.moving_avg_cost, 0), p.cost, 0),
			'lot_no', coalesce(
			    nullif(trim(iry.lot_no), ''),
			    nullif(trim(pp.lot_number), ''),
			    (
			        SELECT string_agg(DISTINCT coalesce(nullif(trim(jli.lot_no), ''), nullif(trim(jli.product_details->>'target_lot_number'), '')), ', ')
			        FROM grnotes grn
			        JOIN grnlineitems gli ON gli.grnotesid = grn.grnotesid
			        JOIN joline_items jli ON gli.purchase_items_id = jli.id
			        WHERE grn.grn_no = iry.ref_id AND gli.product_id = iry.product_id
			    ),
			    (
			        SELECT string_agg(DISTINCT coalesce(nullif(trim(pd.lot_number), ''), nullif(trim(pp.lot_number), '')), ', ')
			        FROM plan_details pd
			        WHERE pd.production_plan_id = pp.production_plan_id
			    )
			)
        )
    ) AS data,
    CASE 
        WHEN bool_and(iry.status = 'Rejected') THEN 'Rejected'
        WHEN bool_and(iry.status = 'Approved') THEN 'Approved'
        WHEN bool_and (iry.status = 'Requested') THEN 'Requested'
        ELSE 'Partialy Approved'
    END AS status
FROM invregistry AS iry
left JOIN store_location AS sl ON iry.store_id = sl.store_id
left join packing_plan on iry.packing_process_id = packing_plan.packing_process_id
left join production_plan as pp on pp.production_plan_id = iry.prod_plan_id
LEFT JOIN products AS p ON p.product_id = iry.product_id
left join uom on uom.id =p.uom_id 
LEFT JOIN euser AS e ON iry.userid = e.userid
left join euser as m on iry.approval_id = m.userid
WHERE iry.deleted IS NOT TRUE 
  AND iry.compcode =:compcode {sql_con}
GROUP BY iry.prod_plan_id,iry.packing_process_id, iry.ref_id,iry.type,
pp.plan_unique , pp.production_plan_id,
packing_plan.package_unique,
concat(e.firstname, e.lastname)
ORDER BY min(iry.created_on) DESC
limit :limit offset :offset
        ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           is_from=request.args.get('is_from', None),
                                                           status=request.args.get('status', None),
                                                           ref_id=request.args.get('ref_id', None),
                                                           action=request.args.get('action', None),
                                                           is_returned=request.args.get('is_returned', None),
                                                           product_id=request.args.get('product_id', None),
                                                           releseid=request.args.get('releseid', None),
                                                           rawmaterials_id=request.args.get('ipss_asset_id', None),
                                                           compcode=compcode,
                                                           type=type,
                                                           asset_type=request.args.get('asset_type', None),
                                                           prod_plan_id=prod_plan_id,
                                                           packing_process_id = packing_process_id,
                                                           start_date=start_date,
                                                           end_date=end_date,
                                                           lot_no=request.args.get('lot_no', None),
                                                           limit=results_per_page,
                                                           offset=offset))
        return {
            'total_results': sql_query[0].get('total_records') if sql_query else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }

    @login_required()
    @invRegistry_api_route.expect(inventoryBulk_model)
    @invRegistry_api_route.marshal_with(create_inventoryRegistry_response)
    def post(self):
        """
        Create inventoryRegistry record and return inserted id
        :return:
        """
        data = request.json
        data = data.get('data') or []
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)

        # Guard: reject outward material requests against closed or rejected production plans
        outward_plan_ids = list({
            int(item.get('prod_plan_id'))
            for item in data
            if str(item.get('prod_plan_id') or '').isdigit() and str(item.get('action') or 'Outward').lower() == 'outward'
        })
        if outward_plan_ids:
            closed_plans = query_to_dict(db_client.engine.execute(
                text('''
                    SELECT production_plan_id, plan_unique, status, is_done
                    FROM production_plan
                    WHERE production_plan_id = ANY(:plan_ids)
                      AND compcode = :compcode
                      AND (is_done IS TRUE OR status IN ('Closed', 'Rejected') OR deleted IS TRUE)
                '''),
                plan_ids=outward_plan_ids,
                compcode=compcode
            ))
            if closed_plans:
                plan_names = ", ".join(p.get('plan_unique') or str(p.get('production_plan_id')) for p in closed_plans)
                return {
                    'success': False,
                    'message': f"Cannot raise material requests against closed or rejected production plans ({plan_names}).",
                    'error': "Plan is closed or rejected"
                }, 400
        # action = request.args.get('action', None)
        query = text('''
                select count(distinct invregistry.ref_id) from invregistry where compcode=:compcode and action='Outward' and ref_id like 'REQ-%'
                ''')
        result = query_to_dict(db_client.engine.execute(query, compcode=compcode))
        count = result[0].get('count', 0) if len(result) else 0
        print(count, "count")
        next_no = int(count) + 1
        formatnum = str(int(next_no)).zfill(6)
        sequenc_num = None
        sequenc_num = f"REQ-{formatnum}"
        print(sequenc_num)
        cc = {
            "compcode": compcode,
              'ref_id':sequenc_num,
              "created_on": datetime.datetime.now(),
              "userid": request.args.get('current_user', {}).get('userid')
        }
        data = [{**i, **cc} for i in data]
        pprint(data)
        error = ''
        s = db_client.session
        try:
            with s.begin():
                s.bulk_insert_mappings(mapper=InvRegistry, mappings=data)
                inv = inventory_ops()
                for i in data:
                    s.execute(inv, i)
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

    @invRegistry_api_route.expect(inventoryBulk_model)
    @invRegistry_api_route.marshal_with(update_inventoryRegistry_response)
    # @user_verify(permission='InventoryRegistry.edit', db_client=db_client)
    @login_required()
    # @login_required()
    def put(self):
        data = request.json
        data = data.get('data')
        update_query = text('''
        update invregistry set status=:status,
        approved_amount=:approved_amount,
        issued_date=:issued_date 
        where releseid=:releseid
        ''').bindparams(
            approved_amount=bindparam('approved_amount', type=NUMERIC),
            # bin_id=bindparam('bin_id', BigInteger),
            # grn_item_id=bindparam('grn_item_id',BigInteger),
            issued_date=bindparam('issued_date', type=DateTime),
            status=bindparam('status', type=String),
            releseid=bindparam('releseid', type=Integer)
        )
        inv = inventory_ops()
        try:
            with db_client.session.begin():
                for i in data:
                    db_client.session.execute(inv, i)
                    # db_client.session.execute(bins,data)
                    db_client.session.execute(update_query, i)
                    # db_client.session.commit()
            # db_client.engine.execute(update_query,data)
            # inventory_ops(data)
        except Exception as e:
            print(str(e))
            db_client.session.rollback()
            return abort(409, "There is Problem in relesing Stock")

        return {
            "success": True,
            "message": "Records Updated Successfully",
            "error": ""
        }
def product_allocation(releseid, data,s=db_client.session):
    try:
        query = text('''
                            select prod_plan_id from invregistry where releseid=:releseid
                            ''')
        result = s.execute(query, {"releseid": releseid}).fetchone()

        if not result:
            raise Exception(f"Invalid releseid: {releseid}")

        prod_plan_id = result.prod_plan_id
        product_id = data.get('product_id', None)
        store_id = data.get('store_id', None)
        compcode = request.args.get('current_user', {}).get('company_id')
        user = request.args.get('current_user', {}).get('username')

        # Query to see if the allocation record already exists (safely handling NULL store_id comparisons)
        exist_record = s.execute(text("""
            SELECT plan_allocation_id, deleted 
            FROM plan_allocation
            WHERE product_id = :product_id 
              AND prod_plan_id = :prod_plan_id
              AND (store_id = :store_id OR (store_id IS NULL AND :store_id IS NULL))
              AND compcode = :compcode
            LIMIT 1
        """), {
            "product_id": product_id,
            "prod_plan_id": prod_plan_id,
            "store_id": store_id,
            "compcode": compcode
        }).fetchone()

        if exist_record:
            # Update existing record
            query = text("""
                UPDATE plan_allocation
                SET allocated_amount = CASE WHEN deleted IS TRUE THEN :approved_amount ELSE allocated_amount + :approved_amount END,
                    modified_by = :modified_by,
                    modified_on = NOW(),
                    deleted = FALSE
                WHERE plan_allocation_id = :plan_allocation_id
            """)
            s.execute(query, {
                "approved_amount": data.get('approved_amount', 0),
                "modified_by": user,
                "plan_allocation_id": exist_record[0]
            })
        else:
            # Insert new record
            query = text("""
                INSERT INTO plan_allocation (
                    product_id,
                    prod_plan_id,
                    store_id,
                    allocated_amount,
                    compcode,
                    created_by,
                    created_on
                )
                VALUES (
                    :product_id,
                    :prod_plan_id,
                    :store_id,
                    :approved_amount,
                    :compcode,
                    :created_by,
                    NOW()
                )
            """)
            s.execute(query, {
                "product_id": product_id,
                "prod_plan_id": prod_plan_id,
                "store_id": store_id,
                "approved_amount": data.get('approved_amount', 0),
                "compcode": compcode,
                "created_by": user
            })
    except Exception:
        s.rollback()
        raise
@invRegistry_api_route.route('/<releseid>/')
class InventoryRegisteryUpdateApi(Resource):
    @staticmethod
    def update_record(data, releseid):

        s = db_client.session
        try:
            inv = None
            action = data.get('action', None)
            if action:
                if action == 'Outward':
                    inv = inventory_ops()
                else:
                    inv = inventory_inv()
                if data.get('status') == 'Approved':
                    data['approval_id'] = request.args.get('current_user').get('userid')
                    data['approval_date'] = datetime.datetime.now()
                    product_allocation(s=s,releseid=releseid, data=data)
                # print(data)
                s.execute(inv, data)
            result = update_local(
                model=InvRegistry,
                condition=InvRegistry.releseid == releseid,
                values=data
            )
            return result

        except Exception as e:
            # print(str(e))
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

    @invRegistry_api_route.marshal_with(get_inventoryRegistry_response)
    #@user_verify(permission='InventoryRegistry.view', db_client=db_client)
    @login_required()
    # @login_required()
    def get(self, releseid):
        """
        Read user record / single record
        :param id:
        :return:
        """

        user = InvRegistry.query.filter_by(releseid=int(releseid)).first()
        return user

    @invRegistry_api_route.expect(update_inventoryRegistry_model)
    @invRegistry_api_route.marshal_with(update_inventoryRegistry_response)
    # @user_verify(permission='InventoryRegistry.edit', db_client=db_client)
    @login_required()
    # @login_required()
    def put(self, releseid):
        """
        Update inventoryRegistry record
        :return:
        """
        data = request.json
        response = self.update_record(data, releseid)
        return response

    @invRegistry_api_route.expect(update_inventoryRegistry_model)
    @invRegistry_api_route.marshal_with(update_inventoryRegistry_response)
    # @user_verify(permission='InventoryRegistry.edit', db_client=db_client)
    @login_required()
    # @login_required()
    def patch(self, releseid):
        """
        Partial Update inventoryRegistry record
        :return:
        """
        data = request.json
        response = self.update_record(data, releseid)
        return response

    @invRegistry_api_route.marshal_with(update_inventoryRegistry_response)
    # @user_verify(permission='InventoryRegistry.delete', db_client=db_client)
    @login_required()
    # @login_required()
    def delete(self, releseid):
        """
        Soft delete inventoryRegistry record
        TODO: Make soft delete
        :return:
        """

        result = self.update_record(
            releseid = releseid,
            data={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result


@stockList_api_route.route('/')
class StockList(Resource):
    @login_required()
    @stockList_api_route.marshal_with(stock_list_response)
    @stockList_api_route.doc(params=stock_search)
    @stockList_api_route.doc(params=list_api_params)
    def get(self):
        product_id = request.args.get('product_id', None)
        product_group_id = request.args.get('product_group_id', None)
        store_id = request.args.get('store_id', None)
        lot_no = request.args.get('lot_no', None)
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        page = int(request.args.get('paged')) if request.args.get('paged') else 1
        result_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0
        sql_con = ''
        query_params = {
            'compcode': compcode,
            'limit': result_per_page,
            'offset': offset,
            'product_group_id': product_group_id,
            'store_id': store_id
        }
        if product_id:
            product_id = tuple(product_id.split(','))
            sql_con += ' and p.product_id in :product_id '
            query_params['product_id'] = product_id
        if product_group_id:
            sql_con += ' and p.product_group_id=:product_group_id '
        if store_id:
            sql_con += ' and sl.store_id=:store_id '
        if lot_no:
            lot_clean = lot_no.strip().upper()
            if lot_clean in ('__NONE__', 'NO_LOT', 'WITHOUT_LOT', 'NONE', 'NULL'):
                sql_con += ' and (sp.lot_no is null or trim(sp.lot_no) = \'\') '
            else:
                sql_con += ' and sp.lot_no=:lot_no '
                query_params['lot_no'] = lot_no.strip()
        query = text(f'''
            with cte as (
                select product_id, sum(allocated_amount) as allocated_amount
                from plan_allocation
                where compcode = :compcode and deleted is not true
                group by product_id
            )
            select p.product_id,p.product_code,p.product_name,sp.product_count,p.sku_id,
            coalesce(cte.allocated_amount, 0) as allocated_quantity,
            p.roql,u.uom,sl."store_name",sp.sub_location,sp.lot_no,
            coalesce(rj.rejected_qty, 0) as rejected_qty,
            coalesce(p.cost, 0) as unit_cost,
            coalesce(nullif(p.moving_avg_cost, 0), nullif(grn_rate.weighted_avg_rate, 0), p.cost, 0) as weighted_avg_rate,
            coalesce(nullif(p.moving_avg_cost, 0), nullif(grn_rate.weighted_avg_rate, 0), p.cost, 0) as last_grn_rate,
            coalesce(sp.product_count * coalesce(nullif(p.moving_avg_cost, 0), nullif(grn_rate.weighted_avg_rate, 0), nullif(p.cost, 0), 0), 0) as total_valuation,
            coalesce(pg.group_name, 'Unknown Category') as product_group, coalesce(pg.group_name, 'Unknown Category') as group_name, coalesce(pg.group_name, 'Unknown Category') as product_group_name,
            count(*) over () as total_value,
            JSON_OBJECT_AGG(COALESCE(va.variant_attribute_name, ' '), vv.variant_value) AS details
            from products as p 
            join store_product as sp on sp.product_id=p.product_id
            join store_location as sl on sl.store_id=sp.store_id
            left join product_group as pg on pg.product_group_id=p.product_group_id and pg.deleted is not true
            left join cte on cte.product_id = sp.product_id
            left join product_variant as pv on p.product_id = pv.product_id
            left join variant_value as vv on pv.variant_value_id = vv.variant_value_id
            left join variant_attribute as va on vv.variant_attribute_id = va.variant_attribute_id
            left join uom as u on u.id = p.uom_id
            left join (
                select product_id, store_id, sum(rejected_quantity) as rejected_qty
                from rejected_material
                where deleted is not true and status='Pending' and compcode=:compcode
                group by product_id, store_id
            ) as rj on rj.product_id = p.product_id and rj.store_id = sp.store_id
            left join (
                select 
                    gli.product_id,
                    case 
                        when sum(coalesce(gli.received_quantity, 0)) > 0 
                        then round(
                            sum(coalesce(gli.received_quantity, 0) * coalesce(nullif(regexp_replace(gli.rate_per_item, '[^0-9.]', '', 'g'), '')::numeric, 0)) / 
                            sum(coalesce(gli.received_quantity, 0)), 
                            4
                        )
                        else 0 
                    end as weighted_avg_rate
                from grnlineitems gli
                join grnotes gn on gn.grnotesid = gli.grnotesid
                where gn.compcode = :compcode 
                  and gn.deleted is not true 
                  and gli.deleted is not true
                  and gn.is_moved is true
                group by gli.product_id
            ) as grn_rate on grn_rate.product_id = p.product_id
            where p.compcode =:compcode {sql_con} and p.deleted is not true and sp.deleted is not true and (sp.compcode = :compcode or sp.compcode is null)
            group by p.product_id,u.uom,sl."store_name",sp.sub_location,sp.lot_no,sp.product_count,rj.rejected_qty,cte.allocated_amount,p.cost,p.moving_avg_cost,grn_rate.weighted_avg_rate,pg.group_name
            order by  p.product_id desc
            limit :limit offset :offset;
        ''')

        result = query_to_dict(db_client.engine.execute(query, **query_params))

        # count_query = text(f'''
        #     select count(*) from (select p.product_id from products as p
        #     left join product_variant as pv on p.product_id = pv.product_id
        #     left join variant_value as vv on pv.variant_value_id = vv.variant_value_id
        #     left join variant_attribute as va on vv.variant_attribute_id = va.variant_attribute_id
        #     where p.compcode =:compcode {sql_con} and p.deleted is not true
        #     group by p.product_id
        #     ) as pro
        # ''')
        # pprint(result)
        # sql_count = query_to_dict(db_client.engine.execute(count_query,compcode=compcode,
        #                                                    store_id=request.args.get('store_id'),
        #                                                    product_id=product_id, product_group_id=product_group_id))
        return {
            "total_results": result[0].get('total_value', 0) if len(result) else 0,
            "page": page,
            "results_per_page": result_per_page,
            "results": result
        }


@stockList_api_route.route('/distinct_lots/')
class DistinctStockLots(Resource):
    @login_required()
    def get(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        query = text('''
            SELECT DISTINCT sp.lot_no
            FROM store_product sp
            JOIN products p ON p.product_id = sp.product_id
            WHERE sp.deleted IS NOT TRUE 
              AND p.deleted IS NOT TRUE
              AND sp.lot_no IS NOT NULL 
              AND TRIM(sp.lot_no) != ''
              AND (sp.compcode = :compcode OR sp.compcode IS NULL)
            ORDER BY sp.lot_no ASC;
        ''')
        res = db_client.engine.execute(query, compcode=compcode).fetchall()
        lots = [r[0] for r in res if r[0]]
        return {
            'success': True,
            'results': lots
        }


@stockList_api_route.route('/store_product/')
class StoreProductList(Resource):

    @login_required()
    @stockList_api_route.marshal_with(store_product_list_model)
    @stockList_api_route.doc(params=stock_search)
    @stockList_api_route.doc(params=list_api_params)
    def get(self):
        """
        List of store products
        :return:
        """
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        page = int(request.args.get('paged')) if request.args.get('paged') else 1
        result_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0
        sql_con = ''
        product_id = request.args.get('product_id', None)
        product_group_id = request.args.get('product_group_id', None)
        store_id = request.args.get('store_id', None)
        if product_id:
            sql_con += ' and sp.product_id = :product_id '
        if product_group_id:
            sql_con += ' and p.product_group_id=:product_group_id '
        if store_id:
            sql_con += ' and sp.store_id=:store_id '

        query = text(f'''  
        with cte as(
        select product_id,
        coalesce(store_id, 0) as store_id,
        sum(allocated_amount) as allocated_amount
        from plan_allocation
        where compcode =:compcode and deleted is not true
        and (:product_id is null or product_id = :product_id)
        and (:store_id is null or store_id = :store_id or store_id is null)
        group by product_id, coalesce(store_id, 0)
        )
        select p.sku_id,sp.product_id ,p.product_name,p.product_code,p.product_count as overall_count, p.product_count,
        p.roql,
        json_agg(
        json_build_object(
        'store_name',  sl.store_name,
            'location', sl.location,
            'sub_location', sp.sub_location,
            'product_count', sp.product_count,
            'allocated_amount', coalesce(cte.allocated_amount, 0),
            'lot_no', sp.lot_no
        )
        ) as data,
        count(*) over () as total_results
        from store_product as sp
        left join cte on (cte.store_id = sp.store_id or cte.store_id = 0) and cte.product_id = sp.product_id
        join store_location as sl on sl.store_id = sp.store_id
        join products as p on p.product_id = sp.product_id
        where (sp.compcode=:compcode or sp.compcode is null) and sp.deleted is not true and p.deleted is not true {sql_con}
        group  by p.sku_id,sp.product_id,p.product_name,p.product_code,p.product_count,p.roql
        limit :limit offset :offset;
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                         compcode=compcode,
                                                         product_id = product_id,
                                                         product_group_id=product_group_id,
                                                         store_id=store_id,
                                                         limit=result_per_page,
                                                         offset=offset))

        return {
            "total_results": result[0].get('total_results', 0) if result else 0,
            "page": page,
            "results_per_page": result_per_page,
            "results": result
        }


@stockList_api_route.route('/store_product/sku/')
class StoreProductBySku(Resource):

    @login_required()
    @stockList_api_route.marshal_with(store_product_list_model)
    @stockList_api_route.doc(params={'sku_id': 'SKU ID of the product', **list_api_params})
    def get(self):
        """
        List of store products by SKU ID
        :return:
        """
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        page = int(request.args.get('paged')) if request.args.get('paged') else 1
        result_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0
        sql_con = ''
        sku_id = request.args.get('sku_id', None)
        product_group_id = request.args.get('product_group_id', None)
        store_id = request.args.get('store_id', None)
        if sku_id:
            sql_con += ' and p.sku_id = :sku_id '
        if product_group_id:
            sql_con += ' and p.product_group_id=:product_group_id '
        if store_id:
            sql_con += ' and sp.store_id=:store_id '

        query = text(f'''  
        with cte as(
        select product_id,
        coalesce(store_id, 0) as store_id,
        sum(allocated_amount) as allocated_amount
        from plan_allocation
        where compcode =:compcode and deleted is not true
        and (:sku_id is null or product_id in (select product_id from products where sku_id = :sku_id))
        and (:store_id is null or store_id = :store_id or store_id is null)
        group by product_id, coalesce(store_id, 0)
        )
        select p.sku_id,sp.product_id ,p.product_name,p.product_code,p.product_count as overall_count, p.product_count,
        p.roql,
        json_agg(
        json_build_object(
        'store_name',  sl.store_name,
            'location', sl.location,
            'sub_location', sp.sub_location,
            'product_count', sp.product_count,
            'allocated_amount', coalesce(cte.allocated_amount, 0),
            'lot_no', sp.lot_no
        )
        ) as data,
        count(*) over () as total_results
        from store_product as sp
        left join cte on (cte.store_id = sp.store_id or cte.store_id = 0) and cte.product_id = sp.product_id
        join store_location as sl on sl.store_id = sp.store_id
        join products as p on p.product_id = sp.product_id
        where (sp.compcode=:compcode or sp.compcode is null) and sp.deleted is not true and p.deleted is not true {sql_con}
        group  by p.sku_id,sp.product_id,p.product_name,p.product_code,p.product_count,p.roql
        limit :limit offset :offset;
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                         compcode=compcode,
                                                         sku_id=sku_id,
                                                         product_group_id=product_group_id,
                                                         store_id=store_id,
                                                         limit=result_per_page,
                                                         offset=offset))

        return {
            "total_results": result[0].get('total_results', 0) if result else 0,
            "page": page,
            "results_per_page": result_per_page,
            "results": result
        }


@invRegistry_api_route.route('/ref_id/<refid>/')
class InventoryRegisterUpdateApi(Resource):

    @staticmethod
    def update_record(data, ref_id):
        result = update_local(
            model=InvRegistry,
            condition=InvRegistry.ref_id == ref_id,
            values=data
        )
        return result

    @invRegistry_api_route.marshal_with(update_inventoryRegistry_response)
    # @user_verify(permission='InventoryRegistry.delete', db_client=db_client)
    @login_required()
    # @login_required()
    def delete(self, refid):
        """
        Soft delete by ref_id record
        TODO: Make soft delete
        :return:
        """

        result = self.update_record(
            ref_id=refid,
            data={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

@invRegistry_api_route.route('/manual_addition')
class ManualAddition(Resource):

    @login_required()
    @invRegistry_api_route.marshal_with(manual_list_response_model)
    @invRegistry_api_route.doc(params=list_api_params)
    def get(self):

        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        page = int(request.args.get('paged')) if request.args.get('paged') else 1
        result_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0

        query = text('''
        select inv.*,p.product_code,p.sku_id, uom.uom,p.uom_id,
        st.store_name, count(*) over () as total_results
         from invregistry as inv
        left join products as p on p.product_id = inv.product_id
        left join uom on uom.id =p.uom_id
        left join store_location as st on st.store_id = inv.store_id
        where inv.deleted is not true and inv.action = 'manual_addition' and inv.compcode=:compcode
        order by inv.releseid desc
        limit :limit offset :offset
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        limit=result_per_page,
                                                        offset=offset,
                                                        compcode=compcode))

        return {
            'total_results': result[0].get('total_results') if result else 0,
            'page': page,
            'results_per_page': result_per_page,
            'results': result
        }

    @login_required()
    @invRegistry_api_route.expect(manual_post_model)
    def post(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        created_by = current_user.get('username')

        cc = {
            'created_on': datetime.datetime.now(),
            'created_by': created_by,
            'compcode': compcode,
            'action': 'manual_addition'
        }

        data = request.json
        data = data.get('data')
        s = db_client.session
        try:
            for i in data:
                if not i.get('store_id'):
                    fallback_store_q = text('''
                        SELECT store_id FROM store_location 
                        WHERE compcode = :compcode AND deleted IS NOT TRUE 
                        ORDER BY store_id ASC 
                        LIMIT 1
                    ''')
                    resolved_store_id = s.execute(fallback_store_q, {'compcode': compcode}).scalar()
                    if not resolved_store_id:
                        return {'success': False, 'message': 'Store selection is missing and no default store found for manual adjustment'}, 400
                    i['store_id'] = resolved_store_id
                symbol = "+" if i['manual_count'].startswith("+") else "-"
                approved_amount = float(i['manual_count'].lstrip('+-'))

                if symbol == "-":
                    check_query = text('''
                        SELECT p.product_name, p.product_count as total_count, sp.product_count as store_count, 
                               COALESCE(pa.allocated_amount, 0) as allocated_amount
                        FROM products p 
                        LEFT JOIN store_product sp ON p.product_id = sp.product_id AND sp.store_id = :store_id AND COALESCE(sp.sub_location, '') = COALESCE(:sub_location, '') AND (sp.compcode = :compcode OR sp.compcode IS NULL)
                        LEFT JOIN (
                            SELECT store_id, product_id, SUM(allocated_amount) as allocated_amount
                            FROM plan_allocation
                            WHERE compcode = :compcode AND deleted IS NOT TRUE
                            GROUP BY store_id, product_id
                        ) pa ON pa.store_id = :store_id AND pa.product_id = :product_id
                        WHERE p.product_id = :product_id AND p.compcode = :compcode
                    ''')
                    stock_res = s.execute(check_query, {
                        'product_id': i.get('product_id'), 
                        'store_id': i.get('store_id'), 
                        'sub_location': i.get('sub_location', ''),
                        'compcode': compcode
                    }).fetchone()
                    
                    if not stock_res:
                        return {'success': False, 'message': 'Product not found'}, 400
                        
                    if (stock_res.total_count or 0) < approved_amount:
                        return {'success': False, 'message': f'Insufficient overall stock for product: {stock_res.product_name}'}, 400
                        
                    if (stock_res.store_count or 0) < approved_amount:
                        return {'success': False, 'message': f'Insufficient stock in store for product: {stock_res.product_name}'}, 400
                        
                    available_to_use = (stock_res.store_count or 0) - stock_res.allocated_amount
                    if available_to_use < approved_amount:
                        return {'success': False, 'message': f"Cannot reduce {approved_amount}. Available to use is only {available_to_use} (Allocated: {stock_res.allocated_amount})"}, 400

                query = text(f''' 
                        update products set product_count = coalesce(product_count,0) {symbol} :approved_amount
                        where product_id=:product_id
                        ''')

                s.execute(query, {'approved_amount': approved_amount,'symbol': symbol, 'product_id': i.get('product_id')})
                #################################
                query = text(f''' 
                                        INSERT INTO store_product (product_id, store_id, sub_location, product_count,compcode,created_by)
                        VALUES (:product_id, :store_id, :sub_location, :approved_amount,:compcode,:created_by)
                        ON CONFLICT (product_id, store_id, COALESCE(sub_location, ''))
                        DO UPDATE SET product_count = COALESCE(store_product.product_count, 0) {symbol} EXCLUDED.product_count,
                                      deleted = FALSE,
                                      deleted_at = NULL;

                                        ''')

                s.execute(query,
                          {'approved_amount': approved_amount, 'symbol': symbol, 'product_id': i.get('product_id'),
                           'store_id':i.get('store_id'), 'sub_location': i.get('sub_location'), **cc})
                ##################################

                # Update the store_id of any in-production serialized products matching this plan to the final target store
                if symbol == "+" and i.get('prod_plan_id') and i.get('store_id'):
                    s.execute(text("""
                        UPDATE public.store_serialized_products
                        SET store_id = :store_id,
                            updated_at = NOW()
                        WHERE production_plan_id = :prod_plan_id
                          AND product_id = :product_id
                          AND status = 'Available'
                          AND deleted IS NOT TRUE
                    """), {
                        'store_id': i.get('store_id'),
                        'prod_plan_id': i.get('prod_plan_id'),
                        'product_id': i.get('product_id')
                    })

                i.update(**cc)
            print(data)
            s.bulk_insert_mappings(mapper=InvRegistry, mappings=data)

            s.commit()
            print("fdsfdsfd")

        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)
        return {
            'success': True,
            'message': 'Update succesfully'
        }


@invRegistry_api_route.route('/manual_addition/<releseid>')
class ManualSubtraction(Resource):

    @login_required()
    def delete(self, releseid):

        s = db_client.session

        try:
            deleted_at = datetime.datetime.now()
            query1 = text('''
            select * from invregistry where releseid=:releseid
            ''')
            result = s.execute(query1, {'releseid': releseid})
            res = [dict(row) for row in result.mappings()]
            if res:
                product_id = res[0].get('product_id')
                symbol = "-" if res[0]['manual_count'].startswith("+") else "+"
                approved_amount = float(res[0]['manual_count'].lstrip('+-'))

                if symbol == "-":
                    check_query = text('''
                        SELECT p.product_name, p.product_count as total_count, sp.product_count as store_count, 
                               COALESCE(pa.allocated_amount, 0) as allocated_amount
                        FROM products p 
                        LEFT JOIN store_product sp ON p.product_id = sp.product_id AND sp.store_id = :store_id AND COALESCE(sp.sub_location, '') = COALESCE(:sub_location, '')
                        LEFT JOIN (
                            SELECT store_id, product_id, SUM(allocated_amount) as allocated_amount
                            FROM plan_allocation
                            GROUP BY store_id, product_id
                        ) pa ON pa.store_id = :store_id AND pa.product_id = :product_id
                        WHERE p.product_id = :product_id
                    ''')
                    stock_res = s.execute(check_query, {
                        'product_id': product_id, 
                        'store_id': res[0].get('store_id'), 
                        'sub_location': res[0].get('sub_location', '')
                    }).fetchone()

                    if not stock_res:
                        return {'success': False, 'message': 'Product not found'}, 400

                    if (stock_res.total_count or 0) < approved_amount:
                        return {'success': False, 'message': f'Insufficient overall stock for product: {stock_res.product_name}'}, 400

                    if (stock_res.store_count or 0) < approved_amount:
                        return {'success': False, 'message': f'Insufficient stock in store for product: {stock_res.product_name}'}, 400
                        
                    available_to_use = (stock_res.store_count or 0) - stock_res.allocated_amount
                    if available_to_use < approved_amount:
                        return {'success': False, 'message': f"Cannot reduce {approved_amount}. Available to use is only {available_to_use} (Allocated: {stock_res.allocated_amount})"}, 400

                query2 = text(f''' 
                                    update products set product_count = coalesce(product_count,0) {symbol} :approved_amount
                                    where product_id=:product_id
                                    ''')
                query3 = text(f'''
                            update invregistry set 
                            deleted = true,
                            deleted_at =:deleted_at
                            where releseid=:releseid
                ''')
                s.execute(query2, {'product_id': product_id, 'approved_amount': approved_amount})
                s.execute(query3, {'deleted_at': deleted_at, 'releseid': releseid})
                ##########################################################################
                i=res[0]
                # print(i,"i")
                # return ""
                query = text(f''' 
                                                        INSERT INTO store_product (product_id, store_id, sub_location, product_count,compcode,created_by)
                                        VALUES (:product_id, :store_id, :sub_location, :approved_amount,:compcode,:created_by)
                                        ON CONFLICT (product_id, store_id, COALESCE(sub_location, ''))
                                        DO UPDATE SET product_count = COALESCE(store_product.product_count, 0) {symbol} EXCLUDED.product_count,
                                                      deleted = FALSE,
                                                      deleted_at = NULL;

                                                        ''')

                s.execute(query,
                          {'symbol': symbol,'approved_amount': approved_amount, 'product_id': i.get('product_id'),
                           'store_id':i.get('store_id'), 'sub_location': i.get('sub_location'), 'compcode':i.get('compcode'),'created_by':i.get('created_by')})
                ##########################################################################
            s.commit()
        except Exception as e:
            s.rollback()
            if isinstance(e.orig, CheckViolation):
                constraint_name = e.orig.diag.constraint_name
                return {
                    'success': False,
                    'is_non_negative_violation': (constraint_name == 'check_column_positive'),
                    'message': 'Check constraint violated — likely a negative or invalid value for a restricted column',
                    'error': str(e.orig)
                }, 400
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': 'Stock Revert Successfully'
        }


@invRegistry_api_route.route('/store_transfer_log')
class StoreTransferLog(Resource):

    @login_required()
    @invRegistry_api_route.marshal_with(transfer_get_list_response)
    @invRegistry_api_route.doc(params={**list_api_params, **{'product_id': {
        'type': 'int',
        'description': "Filter by product ID"
    },
    'ref_id': {
        'type': 'str',
        'description': "Filter by reference ID"
    },
    'is_dispatch': {
        'type': 'bool',
        'description': "Filter by is_dispatch true/false"
    }
    }})
    def get(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        page = int(request.args.get('paged')) if request.args.get('paged') else 1
        result_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0

        ref_id = request.args.get('ref_id', None)
        is_dispatch = request.args.get('is_dispatch', None)
        sql_con = ''
        product_id = request.args.get('product_id', None)
        if ref_id:
            sql_con += ' and inv.ref_id=:ref_id '
        if product_id:
            sql_con += ' and inv.product_id=:product_id '
        if is_dispatch is not None:
            sql_con += ' and inv.is_dispatch=:is_dispatch '

        query = text(f'''
        select inv.ref_id,inv.product_id,inv.approved_amount,inv.is_dispatch,
        inv.created_on,inv.created_by,inv.store_id,
        p.product_code,p.sku_id, uom.uom,p.uom_id,stf.request_id as ref_name,
        st.store_name, count(*) over () as total_results
         from invregistry as inv
        left join products as p on p.product_id = inv.product_id and inv.action = 'store_transfer'
        left join uom on uom.id =p.uom_id
        left join store_location as st on st.store_id = inv.store_id
        left join store_transfer as stf on stf.store_transfer_id = inv.ref_id::bigint
        where inv.deleted is not true and inv.action = 'store_transfer' and inv.compcode=:compcode {sql_con}
        order by inv.releseid desc
        limit :limit offset :offset
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        ref_id=ref_id,
                                                        product_id=product_id,
                                                        is_dispatch=is_dispatch,
                                                        limit=result_per_page,
                                                        offset=offset,
                                                        compcode=compcode))

        return {
            'total_results': result[0].get('total_results') if result else 0,
            'page': page,
            'results_per_page': result_per_page,
            'results': result
        }

    @login_required()
    @invRegistry_api_route.expect(transfer_post_model)
    def post(self):

        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        created_by = current_user.get('username')

        cc = {
            'created_by': created_by,
            'compcode': compcode,
            'action': 'store_transfer',
            'created_on': datetime.datetime.now()
        }

        data = request.json
        data = data.get('data')
        s = db_client.session
        try:
            for i in data:
                symbol = "-" if i['is_dispatch'] is True else "+"

                query = text(f''' 
                        update products set product_count = coalesce(product_count,0) {symbol} :approved_amount
                        where product_id=:product_id
                        ''')

                query2 = text(f''' 
                        INSERT INTO store_product (product_id, store_id, sub_location, product_count,compcode,created_by)
                        VALUES (:product_id, :store_id, :sub_location, :approved_amount,:compcode,:created_by)
                        ON CONFLICT (product_id, store_id, COALESCE(sub_location, ''))
                        DO UPDATE SET product_count = COALESCE(store_product.product_count, 0) {symbol} EXCLUDED.product_count,
                                      deleted = FALSE,
                                      deleted_at = NULL;
                        ''')

                s.execute(query, {'approved_amount': i.get('approved_amount'),'symbol': symbol, 'product_id': i.get('product_id')})
                s.execute(query2,   {'approved_amount': i.get('approved_amount'),'symbol': symbol, 'product_id': i.get('product_id'),
                                     'store_id':i.get('store_id'), 'sub_location': i.get('sub_location'), **cc})
                ##################################
                i.update(**cc)

            s.bulk_insert_mappings(mapper=InvRegistry, mappings=data)

            s.commit()

        except Exception as e:
            print(e)
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)
        return {
            'success': True,
            'message': 'Store Transfer succesfully'
        }


@invRegistry_api_route.route('/action/<int:prod_plan_id>/')
class InventoryReport(Resource):

    @login_required()
    @invRegistry_api_route.marshal_with(inventory_report_response)
    def get(self, prod_plan_id):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        page = int(request.args.get('paged')) if request.args.get('paged') else 1
        result_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0

        product_id = request.args.get('product_id', None)

        sql_con1 = ''
        sql_con2 = ''
        if product_id:
            sql_con1 += ' and inv.product_id=:product_id '
            sql_con2 += ' and rm.product_id=:product_id '

        sql_query = text(f'''
        with dispatch_agg as (
            select d.releseid, sum(d.dispatch_amount) as dispatch_amount
            from dispatch d
            where d.deleted is not true
            group by d.releseid
        ),
        cte1 as(
        select inv.prod_plan_id,inv.product_id,sum(inv.requested_amount) as requested_amount,
        sum(inv.approved_amount) as approved_amount
        ,sum(d.dispatch_amount) as dispatch_amount from invregistry inv
        left join dispatch_agg d on d.releseid = inv.releseid 
        where inv.deleted is not true and inv.prod_plan_id is not null and inv.action = 'Outward' and  inv.status <> 'Rejected' and inv.compcode =:compcode and inv.prod_plan_id=:prod_plan_id {sql_con1}
        group by inv.prod_plan_id,inv.product_id
        ),
        cte2 as(
        select rm.prod_plan_id,rm.product_id,sum(rm.return_request_amount) as return_request_amount,
        sum(rm.return_amount) as return_amount from return_material rm
        where rm.deleted is not true and rm.compcode =:compcode and rm.prod_plan_id=:prod_plan_id {sql_con2}
        group by rm.prod_plan_id,rm.product_id
        ),
        cte3 as(
        select cte1.*,cte2.return_request_amount,cte2.return_amount from cte1
        left join cte2 on cte1.prod_plan_id = cte2.prod_plan_id and cte1.product_id = cte2.product_id
        )
        select cte3.prod_plan_id,
        json_agg(
        json_build_object(
        'product_id', cte3.product_id,
        'requested_amount', cte3.requested_amount,
        'approved_amount', cte3.approved_amount,
        'dispatch_amount', cte3.dispatch_amount,
        'return_request_amount', cte3.return_request_amount,
        'return_amount', cte3.return_amount
        )
        ) as data,
        count(*) over () as total_value
        from cte3
        group by cte3.prod_plan_id
            ''')
        result = query_to_dict(db_client.engine.execute(sql_query,
                                                        prod_plan_id=prod_plan_id,
                                                        product_id=product_id,
                                                        compcode=compcode))
        return {
            'total_results': result[0].get('total_value', 0) if result else 0,
            'page': page,
            'results_per_page': result_per_page,
            'results': result
        }


@stockList_api_route.route('/movement-report/')
class StockMovementReport(Resource):

    @login_required()
    @stockList_api_route.marshal_with(stock_movement_response)
    @stockList_api_route.doc(params={**stock_search, **list_api_params, **report_date_params})
    def get(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        
        page = int(request.args.get('paged')) if request.args.get('paged') else 1
        result_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (page - 1) * result_per_page

        product_id = request.args.get('product_id', None)
        product_group_id = request.args.get('product_group_id', None)
        store_id = request.args.get('store_id', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)

        if not start_date:
            start_date = datetime.date.today().strftime('%Y-%m-%d')
        if not end_date:
            end_date = start_date

        sql_con_inv = ''
        sql_con_fg = ''
        sql_con_dp = ''
        sql_con_dli = ''
        sql_con_rm = ''
        sql_con_main = ''

        if product_id:
            sql_con_inv += ' AND product_id = :product_id '
            sql_con_fg += ' AND pp.product_id = :product_id '
            sql_con_dp += ' AND ir.product_id = :product_id '
            sql_con_dli += ' AND cpi.product_id = :product_id '
            sql_con_rm += ' AND product_id = :product_id '
            sql_con_main += ' AND p.product_id = :product_id '

        if store_id:
            sql_con_inv += ' AND store_id = :store_id '
            sql_con_fg += ' AND fg.store_id = :store_id '
            sql_con_dp += ' AND dp.store_id = :store_id '
            sql_con_dli += ' AND COALESCE(fg.store_id, sp.store_id) = :store_id '
            sql_con_rm += ' AND store_id = :store_id '
            sql_con_main += ' AND sp.store_id = :store_id '

        if product_group_id:
            sql_con_main += ' AND p.product_group_id = :product_group_id '

        query = text(f'''
        WITH consolidated_transactions AS (
            -- 1. Manual Adjustments, Store Transfers, & Direct Deliveries/Returns
            SELECT 
                inv.product_id,
                COALESCE(inv.store_id, (SELECT sp_inner.store_id FROM store_product sp_inner WHERE sp_inner.product_id = inv.product_id AND (sp_inner.compcode = :compcode OR sp_inner.compcode IS NULL) AND sp_inner.deleted IS NOT TRUE LIMIT 1)) AS store_id,
                inv.sub_location,
                inv.created_on AS txn_date,
                CASE 
                    WHEN inv.action = 'manual_addition' AND inv.manual_count LIKE '+%' THEN CAST(SUBSTRING(inv.manual_count FROM 2) AS NUMERIC)
                    WHEN inv.action = 'store_transfer' AND inv.is_dispatch IS NOT TRUE THEN inv.approved_amount
                    WHEN inv.action IN ('Inward', 'GRN', 'GRN Inward') THEN inv.approved_amount
                    ELSE 0 
                END AS inward_qty,
                CASE 
                    WHEN inv.action = 'manual_addition' AND inv.manual_count LIKE '-%' THEN CAST(SUBSTRING(inv.manual_count FROM 2) AS NUMERIC)
                    WHEN inv.action = 'store_transfer' AND inv.is_dispatch IS TRUE THEN inv.approved_amount
                    WHEN inv.action = 'Outward' AND inv.type = 'Delivery' THEN inv.approved_amount
                    ELSE 0 
                END AS outward_qty
            FROM invregistry inv
            WHERE inv.deleted IS NOT TRUE AND inv.compcode = :compcode {sql_con_inv}

            UNION ALL

            -- 2. Finished Goods Additions
            SELECT 
                pp.product_id as product_id,
                fg.store_id,
                CAST(NULL AS VARCHAR(255)) AS sub_location,
                fg.created_on AS txn_date,
                fg.moved_quantity AS inward_qty,
                0 AS outward_qty
            FROM fg_to_store_log fg
            JOIN production_plan pp ON pp.production_plan_id = fg.production_plan_id
            WHERE fg.deleted IS NOT TRUE AND fg.compcode = :compcode {sql_con_fg}

            UNION ALL

            -- 3. Raw Material Dispatches
            SELECT 
                ir.product_id,
                COALESCE(dp.store_id, ir.store_id, (SELECT sp_inner.store_id FROM store_product sp_inner WHERE sp_inner.product_id = ir.product_id AND (sp_inner.compcode = :compcode OR sp_inner.compcode IS NULL) AND sp_inner.deleted IS NOT TRUE LIMIT 1)) AS store_id,
                ir.sub_location AS sub_location,
                dp.created_on AS txn_date,
                0 AS inward_qty,
                dp.dispatch_amount AS outward_qty
            FROM dispatch dp
            JOIN invregistry ir ON ir.releseid = dp.releseid
            WHERE dp.deleted IS NOT TRUE AND dp.compcode = :compcode {sql_con_dp}
        ),
        transaction_aggregates AS (
            SELECT 
                product_id,
                store_id,
                COALESCE(sub_location, '') AS sub_location,
                SUM(CASE WHEN txn_date::date BETWEEN CAST(:start_date AS DATE) AND CAST(:end_date AS DATE) THEN inward_qty ELSE 0 END) AS period_inward,
                SUM(CASE WHEN txn_date::date BETWEEN CAST(:start_date AS DATE) AND CAST(:end_date AS DATE) THEN outward_qty ELSE 0 END) AS period_outward,
                SUM(CASE WHEN txn_date::date > CAST(:end_date AS DATE) THEN inward_qty ELSE 0 END) AS post_end_inward,
                SUM(CASE WHEN txn_date::date > CAST(:end_date AS DATE) THEN outward_qty ELSE 0 END) AS post_end_outward,
                SUM(CASE WHEN txn_date::date >= CAST(:start_date AS DATE) THEN inward_qty ELSE 0 END) AS from_start_inward,
                SUM(CASE WHEN txn_date::date >= CAST(:start_date AS DATE) THEN outward_qty ELSE 0 END) AS from_start_outward
            FROM consolidated_transactions
            GROUP BY product_id, store_id, COALESCE(sub_location, '')
        )
        SELECT 
            p.product_id,
            p.product_code,
            p.product_name,
            sl.store_name,
            sp.sub_location,
            COALESCE(sp.product_count, 0) AS current_stock,
            (COALESCE(sp.product_count, 0) - COALESCE(ta.from_start_inward, 0) + COALESCE(ta.from_start_outward, 0)) AS open_stock,
            COALESCE(ta.period_inward, 0) AS inward_transactions,
            COALESCE(ta.period_outward, 0) AS outward_transactions,
            (COALESCE(sp.product_count, 0) - COALESCE(ta.post_end_inward, 0) + COALESCE(ta.post_end_outward, 0)) AS close_stock,
            COALESCE(nullif(p.moving_avg_cost, 0), nullif(grn_rate.weighted_avg_rate, 0), p.cost, 0) AS weighted_avg_rate,
            COALESCE(p.cost, 0) AS unit_cost,
            COALESCE(sp.product_count * COALESCE(nullif(p.moving_avg_cost, 0), nullif(grn_rate.weighted_avg_rate, 0), nullif(p.cost, 0), 0), 0) AS total_valuation,
            COALESCE((COALESCE(sp.product_count, 0) - COALESCE(ta.from_start_inward, 0) + COALESCE(ta.from_start_outward, 0)) * COALESCE(nullif(p.moving_avg_cost, 0), nullif(grn_rate.weighted_avg_rate, 0), nullif(p.cost, 0), 0), 0) AS open_valuation,
            COALESCE((COALESCE(sp.product_count, 0) - COALESCE(ta.post_end_inward, 0) + COALESCE(ta.post_end_outward, 0)) * COALESCE(nullif(p.moving_avg_cost, 0), nullif(grn_rate.weighted_avg_rate, 0), nullif(p.cost, 0), 0), 0) AS close_valuation,
            u.uom,
            p.sku_id,
            JSON_OBJECT_AGG(COALESCE(va.variant_attribute_name, ' '), vv.variant_value) AS details,
            count(*) over () as total_value
        FROM products p
        JOIN store_product sp ON sp.product_id = p.product_id
        JOIN store_location sl ON sl.store_id = sp.store_id
        LEFT JOIN product_variant pv ON p.product_id = pv.product_id
        LEFT JOIN variant_value vv ON pv.variant_value_id = vv.variant_value_id
        LEFT JOIN variant_attribute va ON vv.variant_attribute_id = va.variant_attribute_id
        LEFT JOIN uom u ON u.id = p.uom_id
        LEFT JOIN transaction_aggregates ta ON ta.product_id = p.product_id AND ta.store_id = sp.store_id AND ta.sub_location = COALESCE(sp.sub_location, '')
        LEFT JOIN (
            SELECT 
                gli.product_id,
                CASE 
                    WHEN sum(COALESCE(gli.received_quantity, 0)) > 0 
                    THEN round(
                        sum(COALESCE(gli.received_quantity, 0) * COALESCE(nullif(regexp_replace(gli.rate_per_item, '[^0-9.]', '', 'g'), '')::numeric, 0)) / 
                        sum(COALESCE(gli.received_quantity, 0)), 
                        4
                    )
                    ELSE 0 
                END AS weighted_avg_rate
            FROM grnlineitems gli
            JOIN grnotes gn ON gn.grnotesid = gli.grnotesid
            WHERE gn.compcode = :compcode 
              AND gn.deleted IS NOT TRUE 
              AND gli.deleted IS NOT TRUE
              AND gn.is_moved IS TRUE
            GROUP BY gli.product_id
        ) AS grn_rate ON grn_rate.product_id = p.product_id
        WHERE p.compcode = :compcode 
          AND p.deleted IS NOT TRUE 
          AND sp.deleted IS NOT TRUE
          AND (sp.compcode = :compcode OR sp.compcode IS NULL)
          {sql_con_main}
        GROUP BY p.product_id, p.product_code, p.product_name, p.sku_id, u.uom, sl.store_name, sp.sub_location, sp.product_count, p.cost, p.moving_avg_cost, grn_rate.weighted_avg_rate, ta.from_start_inward, ta.from_start_outward, ta.period_inward, ta.period_outward, ta.post_end_inward, ta.post_end_outward
        ORDER BY p.product_id DESC
        LIMIT :limit OFFSET :offset;
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        compcode=compcode,
                                                        product_id=product_id,
                                                        product_group_id=product_group_id,
                                                        store_id=store_id,
                                                        start_date=start_date,
                                                        end_date=end_date,
                                                        limit=result_per_page,
                                                        offset=offset))

        return {
            'total_results': result[0].get('total_value', 0) if len(result) else 0,
            'page': page,
            'results_per_page': result_per_page,
            'results': result
        }


@invRegistry_api_route.route('/reconciliation-alerts')
class ReconciliationAlerts(Resource):
    @login_required()
    @invRegistry_api_route.marshal_with(reconciliation_alerts_response)
    def get(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        
        # 1. Orphaned Allocations (deleted plans)
        orphaned_query = text('''
            SELECT COUNT(*) AS count, COALESCE(SUM(pa.allocated_amount), 0) AS total_amount
            FROM plan_allocation pa
            JOIN production_plan pp ON pa.prod_plan_id = pp.production_plan_id
            WHERE pa.deleted IS NOT TRUE
              AND pp.deleted IS TRUE
              AND pa.compcode = :compcode;
        ''')
        orphaned_res = query_to_dict(db_client.engine.execute(orphaned_query, compcode=compcode))
        
        # 2. Dispatched Leaks (already dispatched allocations)
        dispatched_query = text('''
            SELECT COUNT(*) AS count, COALESCE(SUM(pa.allocated_amount), 0) AS total_amount
            FROM plan_allocation pa
            JOIN invregistry inv ON pa.prod_plan_id = inv.prod_plan_id 
                                AND pa.product_id = inv.product_id
            WHERE pa.deleted IS NOT TRUE
              AND inv.action = 'Outward'
              AND inv.status = 'Approved'
              AND inv.is_dispatch IS TRUE
              AND inv.deleted IS NOT TRUE
              AND pa.compcode = :compcode;
        ''')
        dispatched_res = query_to_dict(db_client.engine.execute(dispatched_query, compcode=compcode))
        
        # 3. Rejected Leaks (rejected request allocations)
        rejected_query = text('''
            SELECT COUNT(*) AS count, COALESCE(SUM(pa.allocated_amount), 0) AS total_amount
            FROM plan_allocation pa
            JOIN invregistry inv ON pa.prod_plan_id = inv.prod_plan_id 
                                AND pa.product_id = inv.product_id
            WHERE pa.deleted IS NOT TRUE
              AND inv.status = 'Rejected'
              AND inv.action = 'Outward'
              AND inv.deleted IS NOT TRUE
              AND pa.compcode = :compcode;
        ''')
        rejected_res = query_to_dict(db_client.engine.execute(rejected_query, compcode=compcode))
        
        # 4. Approved & Unissued Requests
        unissued_query = text('''
            SELECT DISTINCT 
                inv.ref_id AS material_request_id, 
                inv.created_by AS requested_by, 
                inv.created_on AS requested_on, 
                inv.prod_plan_id
            FROM invregistry inv
            WHERE inv.action = 'Outward'
              AND inv.status = 'Approved'
              AND (inv.is_dispatch IS FALSE OR inv.is_dispatch IS NULL)
              AND inv.deleted IS NOT TRUE
              AND inv.compcode = :compcode
            ORDER BY inv.created_on DESC;
        ''')
        unissued_res = query_to_dict(db_client.engine.execute(unissued_query, compcode=compcode))
        
        # Format date objects to string to avoid JSON serialization issues
        for row in unissued_res:
            if row.get('requested_on'):
                row['requested_on'] = str(row['requested_on'])
        
        return {
            'orphaned_allocations': {
                'count': orphaned_res[0].get('count') if orphaned_res else 0,
                'total_amount': float(orphaned_res[0].get('total_amount')) if orphaned_res and orphaned_res[0].get('total_amount') is not None else 0.0
            },
            'dispatched_leaks': {
                'count': dispatched_res[0].get('count') if dispatched_res else 0,
                'total_amount': float(dispatched_res[0].get('total_amount')) if dispatched_res and dispatched_res[0].get('total_amount') is not None else 0.0
            },
            'rejected_leaks': {
                'count': rejected_res[0].get('count') if rejected_res else 0,
                'total_amount': float(rejected_res[0].get('total_amount')) if rejected_res and rejected_res[0].get('total_amount') is not None else 0.0
            },
            'approved_unissued_requests': unissued_res
        }


@invRegistry_api_route.route('/reconcile')
class ReconcileAction(Resource):
    @login_required()
    @invRegistry_api_route.expect(reconcile_post_model)
    @invRegistry_api_route.marshal_with(reconcile_response)
    def post(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        
        payload = request.json or {}
        action = payload.get('action')
        ref_id = payload.get('ref_id')
        
        updated_rows = 0
        
        if action == 'clear_orphaned':
            # Clear allocations for deleted plans
            query = text('''
                UPDATE plan_allocation pa
                SET deleted = TRUE,
                    modified_on = NOW(),
                    modified_by = 'api_reconciliation'
                FROM production_plan pp
                WHERE pa.prod_plan_id = pp.production_plan_id
                  AND pa.deleted IS NOT TRUE
                  AND pp.deleted IS TRUE
                  AND pa.compcode = :compcode;
            ''')
            res = db_client.engine.execute(query, compcode=compcode)
            updated_rows = res.rowcount
            
        elif action == 'clear_dispatched':
            # Clear allocations for already dispatched items
            query = text('''
                UPDATE plan_allocation pa
                SET deleted = TRUE,
                    modified_on = NOW(),
                    modified_by = 'api_reconciliation'
                FROM invregistry inv
                WHERE pa.prod_plan_id = inv.prod_plan_id 
                  AND pa.product_id = inv.product_id
                  AND pa.deleted IS NOT TRUE
                  AND inv.action = 'Outward'
                  AND inv.status = 'Approved'
                  AND inv.is_dispatch IS TRUE
                  AND inv.deleted IS NOT TRUE
                  AND pa.compcode = :compcode;
            ''')
            res = db_client.engine.execute(query, compcode=compcode)
            updated_rows = res.rowcount
            
        elif action == 'clear_rejected':
            # Clear allocations for rejected requests
            query = text('''
                UPDATE plan_allocation pa
                SET deleted = TRUE,
                    modified_on = NOW(),
                    modified_by = 'api_reconciliation'
                FROM invregistry inv
                WHERE pa.prod_plan_id = inv.prod_plan_id 
                  AND pa.product_id = inv.product_id
                  AND pa.deleted IS NOT TRUE
                  AND inv.status = 'Rejected'
                  AND inv.action = 'Outward'
                  AND inv.deleted IS NOT TRUE
                  AND pa.compcode = :compcode;
            ''')
            res = db_client.engine.execute(query, compcode=compcode)
            updated_rows = res.rowcount
            
        elif action == 'reverse_request':
            if not ref_id:
                return {'error': 'ref_id is required for reverse_request action'}, 400
            
            # Get plan IDs associated with this request to clear allocations
            plan_ids_query = text('''
                SELECT DISTINCT prod_plan_id 
                FROM invregistry 
                WHERE ref_id = :ref_id 
                  AND action = 'Outward' 
                  AND compcode = :compcode;
            ''')
            plan_ids = [r[0] for r in db_client.engine.execute(plan_ids_query, ref_id=ref_id, compcode=compcode).fetchall() if r[0] is not None]
            
            # Cancel the material request in the registry
            q1 = text('''
                UPDATE invregistry
                SET status = 'Rejected',
                    deleted = TRUE,
                    modified_on = NOW(),
                    modified_by = 'api_reconciliation'
                WHERE ref_id = :ref_id
                  AND action = 'Outward'
                  AND compcode = :compcode;
            ''')
            db_client.engine.execute(q1, ref_id=ref_id, compcode=compcode)
            
            if plan_ids:
                # Clear allocations for these plan IDs
                q2 = text('''
                    UPDATE plan_allocation
                    SET deleted = TRUE,
                        modified_on = NOW(),
                        modified_by = 'api_reconciliation'
                    WHERE prod_plan_id IN :plan_ids
                      AND deleted IS NOT TRUE
                      AND compcode = :compcode;
                ''')
                res = db_client.engine.execute(q2, plan_ids=tuple(plan_ids), compcode=compcode)
                updated_rows = res.rowcount
                
        else:
            return {'error': 'Invalid action specified'}, 400
            
        # Re-sync products table counts if any allocations were modified
        if updated_rows > 0 or action == 'reverse_request':
            # Sync product counts
            sync_query = text('''
                UPDATE products p
                SET allocated_quantity = COALESCE(pa_sum.total_allocated, 0)
                FROM (
                    SELECT product_id, SUM(allocated_amount) AS total_allocated
                    FROM plan_allocation
                    WHERE deleted IS NOT TRUE AND compcode = :compcode
                    GROUP BY product_id
                ) pa_sum
                WHERE p.product_id = pa_sum.product_id AND p.compcode = :compcode;
            ''')
            db_client.engine.execute(sync_query, compcode=compcode)
            
            # Reset 0 counts
            reset_query = text('''
                UPDATE products p
                SET allocated_quantity = 0
                WHERE p.compcode = :compcode
                  AND NOT EXISTS (
                    SELECT 1 
                    FROM plan_allocation pa 
                    WHERE pa.product_id = p.product_id 
                      AND pa.deleted IS NOT TRUE
                      AND pa.compcode = :compcode
                  );
            ''')
            db_client.engine.execute(reset_query, compcode=compcode)
            
        return {
            'success': True,
            'action': action,
            'updated_rows': updated_rows
        }



@invRegistry_api_route.route('/stock-audit')
class StockAuditList(Resource):
    @login_required()
    @invRegistry_api_route.marshal_with(stock_audit_response)
    def get(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        
        page = int(request.args.get('page', 1))
        results_per_page = int(request.args.get('limit', request.args.get('results_per_page', 50)))
        offset = (page - 1) * results_per_page
        
        discrepancy_type = request.args.get('type')
        search_term = request.args.get('search')
        store_id = request.args.get('store_id')
        store_filter_sql = ""
        if store_id:
            store_filter_sql = "AND sp.store_id = :store_id"
            
        base_cte = f"""
        WITH product_ledger AS (
            SELECT 
                inv.product_id,
                COALESCE(SUM(CASE 
                    WHEN inv.action = 'Inward' AND inv.status = 'Approved' THEN inv.approved_amount::numeric 
                    WHEN inv.action = 'manual_addition' AND inv.manual_count LIKE '+%' THEN COALESCE(NULLIF(REGEXP_REPLACE(SUBSTRING(inv.manual_count FROM 2), '[^0-9.]', '', 'g'), '')::NUMERIC, 0)
                    ELSE 0 
                END), 0) -
                COALESCE(SUM(CASE 
                    WHEN inv.action = 'Outward' AND inv.status = 'Approved' THEN inv.approved_amount::numeric 
                    WHEN inv.action = 'manual_addition' AND inv.manual_count LIKE '-%' THEN COALESCE(NULLIF(REGEXP_REPLACE(SUBSTRING(inv.manual_count FROM 2), '[^0-9.]', '', 'g'), '')::NUMERIC, 0)
                    ELSE 0 
                END), 0) AS calculated_ledger_stock,
                COUNT(CASE WHEN inv.action = 'Inward' AND inv.status = 'Approved' THEN 1 END) AS inward_count
            FROM invregistry inv
            WHERE (inv.status = 'Approved' OR inv.action = 'manual_addition')
              AND inv.deleted IS NOT TRUE
              AND inv.compcode = :compcode
            GROUP BY inv.product_id
        ),
        product_physical AS (
            SELECT 
                sp.product_id,
                MIN(sp.store_id) AS store_id,
                COALESCE(SUM(sp.product_count), 0) AS physical_stock
            FROM store_product sp
            WHERE sp.deleted IS NOT TRUE
              AND (sp.compcode = :compcode OR sp.compcode IS NULL)
              {store_filter_sql}
            GROUP BY sp.product_id
        ),
        product_allocated AS (
            SELECT 
                pa.product_id,
                COALESCE(SUM(pa.allocated_amount), 0) AS total_allocated
            FROM plan_allocation pa
            WHERE pa.deleted IS NOT TRUE
              AND pa.compcode = :compcode
            GROUP BY pa.product_id
        ),
        audit_base AS (
            SELECT 
                p.product_id,
                p.product_code,
                p.product_name,
                p.sku_id,
                u.uom,
                COALESCE(pp.store_id, (SELECT store_id FROM store_location WHERE compcode = :compcode AND deleted IS NOT TRUE ORDER BY store_id ASC LIMIT 1)) AS store_id,
                COALESCE(sl.store_name, 'Main Store') AS store_name,
                COALESCE(pp.physical_stock, 0)::float AS physical_stock,
                COALESCE(pl.calculated_ledger_stock, 0)::float AS ledger_stock,
                (COALESCE(pp.physical_stock, 0) - COALESCE(pl.calculated_ledger_stock, 0))::float AS variance,
                COALESCE(pa.total_allocated, p.allocated_quantity, 0)::float AS allocated_quantity,
                CASE 
                    WHEN COALESCE(pp.physical_stock, 0) = COALESCE(pl.calculated_ledger_stock, 0) THEN 'HEALTHY'
                    WHEN COALESCE(pp.physical_stock, 0) > 0 AND COALESCE(pl.calculated_ledger_stock, 0) = 0 AND COALESCE(pl.inward_count, 0) = 0 THEN 'UNRECORDED_OPENING_STOCK'
                    WHEN COALESCE(pl.calculated_ledger_stock, 0) < 0 THEN 'OVER_DISPATCHED'
                    WHEN COALESCE(pp.physical_stock, 0) > COALESCE(pl.calculated_ledger_stock, 0) THEN 'PHYSICAL_SURPLUS'
                    WHEN COALESCE(pp.physical_stock, 0) < COALESCE(pl.calculated_ledger_stock, 0) THEN 'LEDGER_SURPLUS'
                    ELSE 'DISCREPANCY'
                END AS diagnosed_reason,
                CASE 
                    WHEN (COALESCE(pp.physical_stock, 0) - COALESCE(pl.calculated_ledger_stock, 0)) > 0 THEN 'manual_addition'
                    WHEN (COALESCE(pp.physical_stock, 0) - COALESCE(pl.calculated_ledger_stock, 0)) < 0 THEN 'manual_deduction'
                    ELSE 'none'
                END AS suggested_action,
                ABS(COALESCE(pp.physical_stock, 0) - COALESCE(pl.calculated_ledger_stock, 0))::float AS suggested_qty
            FROM products p
            LEFT JOIN product_physical pp ON p.product_id = pp.product_id
            LEFT JOIN store_location sl ON pp.store_id = sl.store_id
            LEFT JOIN product_ledger pl ON p.product_id = pl.product_id
            LEFT JOIN product_allocated pa ON p.product_id = pa.product_id
            LEFT JOIN uom u ON p.uom_id = u.id
            WHERE p.compcode = :compcode 
              AND p.deleted IS NOT TRUE
        )
        """

        summary_query = text(base_cte + """
            SELECT 
                COUNT(*) AS total_products,
                COUNT(CASE WHEN diagnosed_reason = 'HEALTHY' THEN 1 END) AS healthy_count,
                COUNT(CASE WHEN diagnosed_reason != 'HEALTHY' THEN 1 END) AS discrepant_count,
                COALESCE(SUM(variance), 0) AS net_variance,
                COUNT(CASE WHEN diagnosed_reason = 'UNRECORDED_OPENING_STOCK' THEN 1 END) AS unrecorded_opening_count,
                COUNT(CASE WHEN diagnosed_reason = 'OVER_DISPATCHED' THEN 1 END) AS over_dispatched_count,
                COUNT(CASE WHEN diagnosed_reason NOT IN ('HEALTHY', 'UNRECORDED_OPENING_STOCK', 'OVER_DISPATCHED') THEN 1 END) AS other_discrepancy_count
            FROM audit_base;
        """)
        
        summary_res = query_to_dict(db_client.engine.execute(summary_query, compcode=compcode, **({'store_id': store_id} if store_id else {})))
        summary = summary_res[0] if summary_res else {
            'total_products': 0,
            'healthy_count': 0,
            'discrepant_count': 0,
            'net_variance': 0,
            'unrecorded_opening_count': 0,
            'over_dispatched_count': 0,
            'other_discrepancy_count': 0
        }

        where_clauses = ["1=1"]
        params = {'compcode': compcode, 'limit': results_per_page, 'offset': offset}
        if store_id:
            params['store_id'] = store_id
        
        if discrepancy_type == 'healthy':
            where_clauses.append("diagnosed_reason = 'HEALTHY'")
        elif discrepancy_type in ('discrepant', 'all_discrepancies'):
            where_clauses.append("diagnosed_reason != 'HEALTHY'")
        elif discrepancy_type == 'unrecorded_opening':
            where_clauses.append("diagnosed_reason = 'UNRECORDED_OPENING_STOCK'")
        elif discrepancy_type == 'over_dispatched':
            where_clauses.append("diagnosed_reason = 'OVER_DISPATCHED'")
        elif discrepancy_type == 'surplus':
            where_clauses.append("variance > 0")
        elif discrepancy_type == 'deficit':
            where_clauses.append("variance < 0")

        if search_term:
            where_clauses.append("(product_name ILIKE :search OR product_code ILIKE :search OR sku_id ILIKE :search)")
            params['search'] = f"%{search_term}%"

        where_sql = " AND ".join(where_clauses)

        items_query = text(base_cte + f"""
            SELECT *, COUNT(*) OVER() AS total_count
            FROM audit_base
            WHERE {where_sql}
            ORDER BY 
                CASE WHEN diagnosed_reason != 'HEALTHY' THEN 0 ELSE 1 END,
                ABS(variance) DESC, 
                product_id DESC
            LIMIT :limit OFFSET :offset;
        """)

        items = query_to_dict(db_client.engine.execute(items_query, **params))
        total_results = items[0].get('total_count', 0) if items else 0

        return {
            'summary': summary,
            'items': items,
            'total_results': total_results,
            'page': page,
            'results_per_page': results_per_page
        }


@invRegistry_api_route.route('/stock-audit/drilldown/<int:product_id>')
class StockAuditDrilldown(Resource):
    @login_required()
    @invRegistry_api_route.marshal_with(stock_audit_drilldown_response)
    def get(self, product_id):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')

        prod_query = text("""
            SELECT 
                p.product_id, p.product_code, p.product_name,
                COALESCE((SELECT SUM(product_count) FROM store_product WHERE product_id = p.product_id AND deleted IS NOT TRUE AND (compcode = :compcode OR compcode IS NULL)), 0)::float AS physical_stock,
                COALESCE((
                    SELECT 
                        COALESCE(SUM(CASE 
                            WHEN inv.action = 'Inward' AND inv.status = 'Approved' THEN inv.approved_amount::numeric 
                            WHEN inv.action = 'manual_addition' AND inv.manual_count LIKE '+%' THEN COALESCE(NULLIF(REGEXP_REPLACE(SUBSTRING(inv.manual_count FROM 2), '[^0-9.]', '', 'g'), '')::NUMERIC, 0)
                            ELSE 0 
                        END), 0) -
                        COALESCE(SUM(CASE 
                            WHEN inv.action = 'Outward' AND inv.status = 'Approved' THEN inv.approved_amount::numeric 
                            WHEN inv.action = 'manual_addition' AND inv.manual_count LIKE '-%' THEN COALESCE(NULLIF(REGEXP_REPLACE(SUBSTRING(inv.manual_count FROM 2), '[^0-9.]', '', 'g'), '')::NUMERIC, 0)
                            ELSE 0 
                        END), 0)
                    FROM invregistry inv
                    WHERE inv.product_id = p.product_id 
                      AND (inv.status = 'Approved' OR inv.action = 'manual_addition')
                      AND inv.deleted IS NOT TRUE 
                      AND inv.compcode = :compcode
                ), 0)::float AS ledger_stock,
                COALESCE((
                    SELECT SUM(approved_amount::numeric) FROM invregistry 
                    WHERE product_id = p.product_id AND action = 'Inward' AND status = 'Approved' AND deleted IS NOT TRUE AND compcode = :compcode
                ), 0)::float AS total_inward,
                COALESCE((
                    SELECT SUM(approved_amount::numeric) FROM invregistry 
                    WHERE product_id = p.product_id AND action = 'Outward' AND status = 'Approved' AND deleted IS NOT TRUE AND compcode = :compcode
                ), 0)::float AS total_outward,
                COALESCE((
                    SELECT SUM(COALESCE(NULLIF(REGEXP_REPLACE(SUBSTRING(manual_count FROM 2), '[^0-9.]', '', 'g'), '')::NUMERIC, 0)) FROM invregistry 
                    WHERE product_id = p.product_id AND action = 'manual_addition' AND manual_count LIKE '+%' AND deleted IS NOT TRUE AND compcode = :compcode
                ), 0)::float AS total_manual_addition,
                COALESCE((
                    SELECT SUM(COALESCE(NULLIF(REGEXP_REPLACE(SUBSTRING(manual_count FROM 2), '[^0-9.]', '', 'g'), '')::NUMERIC, 0)) FROM invregistry 
                    WHERE product_id = p.product_id AND action = 'manual_addition' AND manual_count LIKE '-%' AND deleted IS NOT TRUE AND compcode = :compcode
                ), 0)::float AS total_manual_deduction
            FROM products p
            WHERE p.product_id = :product_id AND p.compcode = :compcode;
        """)

        try:
            prod_res = query_to_dict(db_client.engine.execute(prod_query, product_id=product_id, compcode=compcode))
            if not prod_res:
                return {'message': 'Product not found'}, 404

            item = prod_res[0]
            item['variance'] = float(item.get('physical_stock') or 0) - float(item.get('ledger_stock') or 0)

            tx_query = text("""
                SELECT 
                    inv.releseid AS id,
                    inv.action,
                    inv.status,
                    inv.ref_id,
                    inv.approved_amount::float AS approved_amount,
                    inv.manual_count,
                    inv.created_on,
                    inv.created_by,
                    sl.store_name
                FROM invregistry inv
                LEFT JOIN store_location sl ON inv.store_id = sl.store_id
                WHERE inv.product_id = :product_id 
                  AND inv.deleted IS NOT TRUE
                  AND inv.compcode = :compcode
                ORDER BY inv.created_on DESC
                LIMIT 25;
            """)
            tx_rows = query_to_dict(db_client.engine.execute(tx_query, product_id=product_id, compcode=compcode))
            for row in tx_rows:
                if row.get('created_on'):
                    row['created_on'] = str(row['created_on'])
                if row.get('approved_amount') is not None:
                    row['approved_amount'] = float(row['approved_amount'])

            item['recent_transactions'] = tx_rows
            return item
        except Exception as e:
            return {'message': f'Error fetching drilldown details: {str(e)}'}, 500


@invRegistry_api_route.route('/stock-audit/reconcile')
class StockAuditReconcile(Resource):
    @login_required()
    @invRegistry_api_route.expect(stock_audit_reconcile_post_model)
    def post(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        created_by = current_user.get('username')

        payload = request.json or {}
        adjustments = payload.get('adjustments', [])

        if not adjustments:
            return {'success': False, 'message': 'No adjustments provided'}, 400

        s = db_client.session
        reconciled_count = 0

        try:
            for adj in adjustments:
                product_id = adj.get('product_id')
                store_id = adj.get('store_id')
                sub_location = adj.get('sub_location') or ''
                adjustment_qty = float(adj.get('adjustment_qty', 0))
                action = adj.get('action', 'manual_addition')
                reason = adj.get('reason') or 'Stock Audit Reconciliation'
                update_physical = adj.get('update_physical_stock', False)

                if adjustment_qty <= 0:
                    continue

                if not store_id:
                    fallback_store_q = text("SELECT store_id FROM store_location WHERE compcode = :compcode AND deleted IS NOT TRUE ORDER BY store_id ASC LIMIT 1")
                    store_id = s.execute(fallback_store_q, {'compcode': compcode}).scalar()

                symbol = '+' if action == 'manual_addition' else '-'
                manual_count_str = f"{symbol}{adjustment_qty}"

                # Insert invregistry audit entry
                inv_entry = {
                    'product_id': product_id,
                    'store_id': store_id,
                    'sub_location': sub_location,
                    'action': 'manual_addition',
                    'manual_count': manual_count_str,
                    'approved_amount': adjustment_qty,
                    'status': 'Approved',
                    'reason': reason,
                    'description': reason,
                    'created_on': datetime.datetime.now(),
                    'created_by': created_by,
                    'compcode': compcode,
                    'deleted': False
                }
                s.execute(text("""
                    INSERT INTO invregistry (
                        product_id, store_id, sub_location, action, manual_count, 
                        approved_amount, status, reason, description, created_on, created_by, compcode, deleted
                    ) VALUES (
                        :product_id, :store_id, :sub_location, :action, :manual_count,
                        :approved_amount, :status, :reason, :description, :created_on, :created_by, :compcode, :deleted
                    );
                """), inv_entry)

                # Update physical stock if requested
                if update_physical:
                    s.execute(text(f"""
                        UPDATE products 
                        SET product_count = COALESCE(product_count, 0) {symbol} :approved_amount
                        WHERE product_id = :product_id AND compcode = :compcode;
                    """), {'approved_amount': adjustment_qty, 'product_id': product_id, 'compcode': compcode})

                    s.execute(text(f"""
                        INSERT INTO store_product (product_id, store_id, sub_location, product_count, compcode, created_by)
                        VALUES (:product_id, :store_id, :sub_location, :approved_amount, :compcode, :created_by)
                        ON CONFLICT (product_id, store_id, COALESCE(sub_location, ''))
                        DO UPDATE SET product_count = COALESCE(store_product.product_count, 0) {symbol} EXCLUDED.product_count,
                                      deleted = FALSE,
                                      deleted_at = NULL;
                    """), {
                        'product_id': product_id,
                        'store_id': store_id,
                        'sub_location': sub_location,
                        'approved_amount': adjustment_qty,
                        'compcode': compcode,
                        'created_by': created_by
                    })

                reconciled_count += 1

            s.commit()
            return {
                'success': True,
                'reconciled_count': reconciled_count,
                'message': f'Successfully reconciled {reconciled_count} item(s).'
            }

        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)
