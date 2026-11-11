import datetime
from pprint import pprint

from flask import abort, jsonify

from .errorhandling import map_sqlalchemy_error_to_http_status, update_local
from .post_module import post_helper, update_model, update_quantity, revert_stock
from flask_restx import Resource
from ipss_utils.decorators import login_required
from flask import request
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, values, bindparam
from sqlalchemy.orm import mapper
from ..api_doc import delete_fields, plan_fields, report_filter, plan_to_outward_filter, drop_down_get_all_filter
from ipss_utils.ipss_api_doc import list_api_params
from ..models.planning import ProdPlans, PlanDetails, PlanTargets, Style, StyleProduct, ProductionMaterialCost
from .. import ipss_db
from .helper import add_cc, update_record, updated_extract_order, remove_duplicates, update_fg_log, get_labour_cost, \
    get_material_cost
from .. import db_client
from ..routes.planning import prod_plan_api_route, prod_plan_model, prod_plan_list_response, \
    post_response_model, prod_plan_bulk_model, report_response, moved_quantity_model, plan_stock_list_response, \
    plan_to_outward_list_response, plan_date_outward_list_response, style_plan_outward_list_response, \
    plan_datewise_list_response, prod_plan_get_all_list_response, fg_cost_report_list_response, \
    plan_wise_outward_resposne_model, production_plan_cost_model_list_response, plan_to_store_response_model
from ..redis_client.redis_client import redis_client

def get_clean_arg(key, default=None, is_int=False, is_bool=False):
    val = request.args.get(key)
    if val is None or str(val).strip() == '' or str(val).lower() in ('null', 'undefined'):
        return default
    if is_int:
        try:
            return int(val)
        except ValueError:
            return default
    if is_bool:
        if str(val).lower() == 'true':
            return True
        if str(val).lower() == 'false':
            return False
        return default
    return val

def get_clean_int_list(key):
    val = request.args.get(key)
    if val is None or str(val).strip() == '' or str(val).lower() in ('null', 'undefined'):
        return None
    try:
        return tuple(int(x.strip()) for x in val.split(',') if x.strip())
    except ValueError:
        return None

@prod_plan_api_route.route('/')
class PlanPost(Resource):
    @login_required()
    # @prod_plan_api_route.marshal_with(post_response_model)
    @prod_plan_api_route.expect(prod_plan_bulk_model)
    def patch(self):
        data = request.json
        print(data, "data")
        return update_model(values=data.get('data'))
    @login_required()
    # @prod_plan_api_route.marshal_with(post_response_model)
    @prod_plan_api_route.expect(prod_plan_bulk_model)
    def post(self):
        data=request.json
        data=post_helper(values=data.get('data'))
        if data.get('success'):
            print("company id",request.args.get('current_user', {}).get('company_id', ''))
            try:
                redis_client.xadd(
                    "notification",
                    {
                        "production_plan_id": data.get('production_plan_id', ''),
                        "plan_unique": data.get('plan_unique', ''),
                        "company_id": request.args.get('current_user', {}).get('company_id', ''),
                        "action": "production_plan_creation",
                        "username": request.args.get('current_user', {}).get('username', '')
                    }
                )
            except Exception as e:
                print("Failed to add notification to redis:", str(e))
        return jsonify(data)
    @login_required()
    @prod_plan_api_route.marshal_with(prod_plan_list_response)
    @prod_plan_api_route.doc(params={**list_api_params,**plan_fields})
    def get(self):
        paged = get_clean_arg('paged', default=1, is_int=True)
        results_per_page = get_clean_arg('results_per_page', default=20, is_int=True)
        offset = (paged - 1) * results_per_page
        ccode = request.args.get('current_user', {}).get('company_id', None)
        sql_con = ''
        is_rawmaterials_received = False
        tar_con = ''

        production_plan_id = get_clean_arg('production_plan_id', is_int=True)
        product_id = get_clean_arg('product_id', is_int=True)
        is_emergency_plan = get_clean_arg('is_emergency_plan', is_bool=True)
        is_done = get_clean_arg('is_done', is_bool=True)
        is_closed = get_clean_arg('is_closed', is_bool=True)
        status = get_clean_arg('status')
        plan_date = get_clean_arg('plan_date')
        target_date = get_clean_arg('target_date')

        if production_plan_id is not None:
            sql_con+=' and pp.production_plan_id=:production_plan_id '
        if product_id is not None:
            sql_con+=' and pp.product_id=:product_id '
        if plan_date is not None:
            sql_con+=' and pp.plan_date=:plan_date '
        if is_emergency_plan is not None:
            sql_con+=' and pp.is_emergency_plan=:is_emergency_plan '
        if is_done is not None:
            sql_con+=' and pp.is_done=:is_done '
        if is_closed is True:
            sql_con+=" and (pp.is_done is true or pp.status in ('Closed', 'Rejected')) "
        elif is_closed is False:
            sql_con+=" and (pp.is_done is not true and pp.status not in ('Closed', 'Rejected')) "
        if status is not None:
            sql_con+=' and pp.status=:status '
        if request.args.get('is_rawmaterials_received')=='true':
            is_rawmaterials_received=True
            sql_con+=' and d.dispatch_id is not null '
        if request.args.get('is_rawmaterials_received')=='false':
            sql_con+=' and d.dispatch_id is null '
        if target_date is not None:
            tar_con+=''' and
            pt.start_date >= cast(:target_date as date)
  AND cast(:target_date as date) <= COALESCE(pt.end_date, pt.start_date)
            '''

        sql_query=text(f'''
        with pp as (select pp.production_plan_id,pp.end_date,
        COALESCE(p.product_name, (
            SELECT string_agg(p2.product_name, ', ') 
            FROM production_plan_products ppp 
            JOIN products p2 ON p2.product_id = ppp.product_id 
            WHERE ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
        )) as product_name,
        COALESCE(p.product_code, 'MULTI') as product_code,
        f.floor_id,f.floor_name,
        COALESCE(p.sku_id, 'MULTI') as sku_id,
        COALESCE(p.is_serializable, FALSE) as is_serializable,
        p.serialization_params,
        {is_rawmaterials_received} as is_rawmaterials_received,
        uom.uom,
        COALESCE(pp.product_id, CAST(:product_id AS BIGINT)) as product_id,
        pp.planed_quantity,pp.moved_quantity,pp.wastage,pp.wastage_per,pp.plan_unique,pp.plan_date ,
        pp.execution_start_date,pp.execution_end_date,pp.is_emergency_plan,
        pp.is_done,pp.status,pp.additional::jsonb,
        pp.is_multi_product,
        (
          SELECT jsonb_agg(jsonb_build_object(
            'product_id', ppp.product_id,
            'product_name', p2.product_name,
            'product_code', p2.product_code,
            'sku_id', p2.sku_id,
            'planned_quantity', ppp.planned_quantity,
            'moved_quantity', ppp.moved_quantity,
            'wastage', ppp.wastage,
            'wastage_per', ppp.wastage_per,
            'floor_id', ppp.floor_id
          ))
          FROM production_plan_products ppp 
          JOIN products p2 ON p2.product_id = ppp.product_id 
          WHERE ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
        ) AS products,
        json_agg(distinct jsonb_build_object('stage_id',s.stage_id,
        'target_per_hour', asm.target_per_hour,
        'rank_id',ps.rank_id,
        'config_id',asm.config_id,
        'config_name',cm.process_name,
        'is_final_process',asm.is_final_process,
        'stage_name',s.stage_name,
        'product_id', pm.product_id,
        'product_name', pm.product_name,
        'product_code', pm.product_code)  )::text::jsonb all_stages
        from production_plan as pp
        LEFT JOIN invregistry i ON i.prod_plan_id = pp.production_plan_id and i.deleted is not true
        LEFT JOIN dispatch d ON d.releseid = i.releseid and d.deleted is not true
        left join floor f on f.floor_id =pp.floor_id
        left join products as p on p.product_id=pp.product_id 
        left join uom on uom.id =p.uom_id 
        left join products as pm on (pm.product_id = pp.product_id) OR (pp.is_multi_product is true AND pm.product_id IN (
            SELECT ppp.product_id FROM production_plan_products ppp 
            WHERE ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
        ))
        left join production_stages ps on ps.product_id = pm.product_id and ps.deleted is not true
        left join stage s on s.stage_id =ps.stage_id and s.deleted is not true
        left join activity_stage_map as asm on asm.production_stage_id=ps.id and asm.deleted is not true
        left join process_config cm on cm.process_id=asm.config_id and cm.deleted is not true
        where pp.deleted is not true and pp.compcode=:ccode {sql_con}
        group by pp.production_plan_id,uom.uom,
        p.product_name,p.product_code,f.floor_id,f.floor_name,
        p.sku_id, p.is_serializable, p.serialization_params,
        pp.product_id,pp.planed_quantity,pp.wastage,pp.plan_unique,pp.plan_date ,
        pp.execution_start_date,pp.execution_end_date,pp.is_emergency_plan,pp.end_date,
        pp.is_done,pp.status,pp.additional::jsonb, pp.is_multi_product
        order by production_plan_id 
        limit :limit offset :offset
        ),
        pd as (
        select pp.*,cp.order_unique,cp.order_type,cp.status as order_status ,
        jsonb_agg(json_build_object(
          'plan_details_id', pd.plan_details_id,
          'production_plan_id', pd.production_plan_id,
          'plan_quantity', pd.plan_quantity,
          'wastage', pd.wastage,
          'wastage_per', pd.wastage_per,
          'order_extract_id',pd.order_extract_id ,
          'is_done', pd.is_done,
          'order_unique', cp.order_unique,
          'ordered_quantity', cpi.quantity_ordered,
          'order_type', cp.order_type,
          'status', cp.status,
          'product_name', p_det.product_name,
          'product_code', p_det.product_code,
          'sku_id', p_det.sku_id,
          'product_id', oie.product_id,
          'cumulative_planned_quantity', oie.quantity_planned
        )) details
        --,jsonb_agg(pd.*) as details
        from pp 
        left join plan_details as pd on pp.production_plan_id=pd.production_plan_id
        left join order_items_extract as oie on oie.extract_id=pd.order_extract_id
        left join customer_purchase_items cpi on cpi.items_id=oie.order_items_id
        left join customer_purchase cp on cp.customer_purchase_id=cpi.customer_purchase_id
        left join products as p_det on p_det.product_id = oie.product_id
        where pd.deleted is not true or pd.plan_details_id is null
        group by pp."production_plan_id",pp.product_id,pp.planed_quantity,pp.moved_quantity,pp.wastage,pp.wastage_per,pp.plan_unique,pp.plan_date ,
        pp.execution_start_date,pp.execution_end_date,pp.is_emergency_plan,pp.product_name,pp.product_code,pp.sku_id,pp.is_rawmaterials_received,
        pp.is_serializable, pp.serialization_params,
        cp.order_unique,cp.order_type,cp.status,pp.floor_id,pp.floor_name,pp.all_stages,pp.end_date,pp.uom,
        pp.is_done,pp.status,pp.additional::jsonb, pp.is_multi_product, pp.products
        )
        
        select pd.*,
        
        case when bool_or(pt.is_hourly_target = true) then true 
             when bool_or(pt.is_hourly_target = false) then false else null end as is_hourly,

        json_agg(CASE
               WHEN pt.is_hourly_target is false THEN json_build_object(
                   'plan_target_id', pt.plan_target_id,
                   'production_plan_id', pt.production_plan_id,
                   'stage_id',pt.stage_id,
          'stage_name',s.stage_name,
          'rank_id',ps.rank_id,
          'is_outsource',pt.is_outsource,
          -- 'config_id',asm.config_id,
        --'config_name',cm.config_name,
                   'target_quantity', pt.target_quantity,
                   'start_date', pt.start_date,
                   'end_date', pt.end_date,
                   'product_id', pt.product_id,
                   'product_name', p_tar.product_name,
                   'product_code', p_tar.product_code
               )
               ELSE null
           END ORDER BY pt.start_date
       ) AS targets,
          
          json_agg(CASE
               WHEN pt.is_hourly_target is true THEN json_build_object('plan_target_id',pt.plan_target_id,
          'production_plan_id',pt.production_plan_id,
          'target_quantity',pt.target_quantity,
          'stage_id',pt.stage_id,
          'stage_name', s.stage_name,
          'rank_id',ps.rank_id,
          'is_outsource', COALESCE(pt.is_outsource, FALSE),
          'start_date',pt.start_date,
          'end_date',pt.end_date,
          'alter_hours',pt.alter_hours,
          'day_target',pt.day_target,
          'process_id',pt.process_id,
        'config_name',cm.process_name,
        'product_id', pt.product_id,
        'product_name', p_tar.product_name,
        'product_code', p_tar.product_code
          --'end_date',pt2.end_date
          )
          ELSE null
           END
        order by ps.rank_id) as hourly_target
          
           from pd
        left join plan_targets pt on pt.production_plan_id =pd.production_plan_id
--        left join plan_targets pt2 on pt2.production_plan_id =pd.production_plan_id and pt2.stage_id is not null
        --left join production_stages ps on ps.id=pt.stage_id and ps.deleted is not true
        
        left join stage as s on s.stage_id=pt.stage_id and s.deleted is not true
        left join production_stages ps on ps.stage_id=s.stage_id and ps.deleted is not true and pd.product_id=ps.product_id
        --left join activity_stage_map as asm on asm.production_stage_id=ps.id and asm.deleted is not true
        left join process_config cm on cm.process_id=pt.process_id and cm.deleted is not true and cm.process_id=pt.process_id
        left join products p_tar on p_tar.product_id = pt.product_id
        where pt.deleted is not true or pt.plan_target_id is null {tar_con}
 
        group by pd."production_plan_id",pd.uom,pd.product_id,pd.planed_quantity,pd.moved_quantity,pd.wastage,pd.wastage_per,pd.plan_unique,pd.plan_date ,
--        pt2.production_plan_id,
        pt.production_plan_id,
        pd.execution_start_date,pd.execution_end_date,pd.is_emergency_plan,pd.product_name,pd.product_code,pd.details,
        pd.sku_id,pd.floor_id,pd.floor_name,pd.end_date,pd.is_rawmaterials_received,
        pd.order_unique,pd.order_type,pd.order_status,pd.all_stages,
        pd.is_serializable, pd.serialization_params,
        pd.is_done,pd.status,pd.additional::jsonb, pd.is_multi_product, pd.products
        order by production_plan_id desc
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,ccode=ccode,
                                                         status=status,
                                                         is_done=is_done,
                                                         target_date=target_date,
                                                         is_emergency_plan=is_emergency_plan,
                                                         plan_date=plan_date,
                                                         product_id=product_id,
                                                         production_plan_id=production_plan_id,
                                                         limit=results_per_page,offset=offset))
        sql_count=text(f'''
        select count (distinct pp.production_plan_id) from production_plan as pp
         LEFT JOIN invregistry i ON i.prod_plan_id = pp.production_plan_id and i.deleted is not true
        LEFT JOIN dispatch d ON d.releseid = i.releseid and d.deleted is not true
        left join plan_details as pd on pd.production_plan_id=pp.production_plan_id
        left join plan_targets as pt on pt.production_plan_id=pp.production_plan_id
        where pp.deleted is not true and pp.compcode=:ccode and pd.deleted is not true and
        pt.deleted is not true {sql_con}
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,ccode=ccode,
                                                         status=status,
                                                         target_date=target_date,
                                                         is_done=is_done,
                                                         is_emergency_plan=is_emergency_plan,
                                                         plan_date=plan_date,
                                                         product_id=product_id,
                                                         production_plan_id=production_plan_id,
                                                         ))
        for i in sql_query:
            i['hourly_target'] = list(filter(None, i.get('hourly_target', [])))
            i['targets'] = list(filter(None, i.get('targets', [])))
            stages = i.get('all_stages') or []
            if not isinstance(stages, list):
                stages = []
            i['all_stages'] = sorted(
                [x for x in stages if x and isinstance(x, dict) and x.get('rank_id') is not None],
                key=lambda x: x["rank_id"]
            )
            # if i.get('hourly_target') and not i.get('hourly_target')[0].get('plan_target_id'):
            #     i['hourly_target']=[]
            # else:
            #     i['hourly_target']=remove_duplicates(i.get('hourly_target'))
            # if i.get('targets') and not i.get('targets')[0].get('plan_target_id'):
            #     i['targets']=[]
            # else:
            #     i['targets']=remove_duplicates(i.get('targets'))
        # pprint(sql_query)
        return {
            'total_results': sql_count[0].get('count') if sql_count else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }

    @login_required()
    @prod_plan_api_route.doc(params=delete_fields)
    def delete(self):
        model=''
        pkey=''
        ids=0
        if request.args.get('production_plan_id'):
            model=ProdPlans
            pkey=ProdPlans.production_plan_id
            ids=request.args.get('production_plan_id')
            # Release allocations when plan is deleted
            s = db_client.session
            s.execute(text('''
                UPDATE products p
                SET allocated_quantity = GREATEST(0, COALESCE(p.allocated_quantity::numeric, 0) - sub.leftover)
                FROM (
                    SELECT product_id, SUM(allocated_amount) as leftover
                    FROM plan_allocation
                    WHERE prod_plan_id = :production_plan_id
                    GROUP BY product_id
                ) sub
                WHERE p.product_id = sub.product_id;
            '''), {'production_plan_id': ids})
            s.execute(text('DELETE FROM plan_allocation WHERE prod_plan_id = :production_plan_id'),
                      {'production_plan_id': ids})
            s.commit()
        elif request.args.get('plan_details_id'):
            plan_det_id = request.args.get('plan_details_id')
            s = db_client.session
            # Validation 1: Fetch plan_details and parent production_plan
            det_row = s.execute(text('''
                SELECT pd.plan_details_id, pd.production_plan_id, pd.order_extract_id, 
                       pp.status, pp.is_done, pp.is_multi_product, pp.moved_quantity
                FROM plan_details pd
                JOIN production_plan pp ON pp.production_plan_id = pd.production_plan_id
                WHERE pd.plan_details_id = :det_id AND pd.deleted IS NOT TRUE
            '''), {'det_id': plan_det_id}).fetchone()

            if not det_row:
                return {'success': False, 'message': 'Plan detail item not found or already deleted'}, 404

            _, plan_id, extract_id, plan_status, is_done, is_multi_prod, moved_qty = det_row

            # Validation 2: Plan status check (must be Pending)
            if plan_status != 'Pending':
                return {'success': False, 'message': f'Cannot delete item. Plan status is {plan_status} (only Pending plans can be edited)'}, 400

            if is_done:
                return {'success': False, 'message': 'Cannot delete item. This production plan is closed'}, 400

            # Validation 3: Check execution / moved quantity
            if moved_qty and float(moved_qty) > 0:
                return {'success': False, 'message': 'Cannot delete item. Production execution has already commenced for this plan'}, 400

            # Validation 4: Must not be the last active detail item
            active_count = s.execute(text('''
                SELECT COUNT(*) FROM plan_details 
                WHERE production_plan_id = :plan_id AND deleted IS NOT TRUE
            '''), {'plan_id': plan_id}).scalar()

            if active_count <= 1:
                return {'success': False, 'message': 'Cannot delete the only item in the plan. Delete the entire plan from the list view instead'}, 400

            model = PlanDetails
            pkey = PlanDetails.plan_details_id
            ids = plan_det_id
        elif request.args.get('plan_target_id'):
            model=PlanTargets
            pkey=PlanTargets.plan_target_id
            ids = request.args.get('plan_target_id')
        if not model:
            return abort(409,"There is nothing to delete")
        result = ipss_db.update_record(
            model=model,
            condition=pkey == ids,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        # When deleting a production plan, also soft-delete its plan_details
        # and recalculate oie.quantity_planned so "Yet to Plan" is restored correctly
        # When deleting an individual plan_detail, recalculate oie.quantity_planned and update parent plan/products
        if request.args.get('plan_details_id') and result.get('success'):
            s = db_client.session
            try:
                # Recalculate quantity_planned on order_items_extract using extract_id
                s.execute(text('''
                    UPDATE order_items_extract oie
                    SET quantity_planned = COALESCE((
                        SELECT SUM(pd.plan_quantity)
                        FROM plan_details pd
                        WHERE pd.order_extract_id = :extract_id
                          AND pd.deleted IS NOT TRUE
                    ), 0)
                    WHERE oie.extract_id = :extract_id
                '''), {'extract_id': extract_id})

                # Update production_plan planned_quantity as sum of remaining non-deleted details
                s.execute(text('''
                    UPDATE production_plan
                    SET planed_quantity = COALESCE((
                        SELECT SUM(pd.plan_quantity)
                        FROM plan_details pd
                        WHERE pd.production_plan_id = :plan_id
                          AND pd.deleted IS NOT TRUE
                    ), 0)
                    WHERE production_plan_id = :plan_id
                '''), {'plan_id': plan_id})

                # If multi-product plan, synchronize production_plan_products planned_quantity
                if is_multi_prod:
                    s.execute(text('''
                        UPDATE production_plan_products ppp
                        SET planned_quantity = COALESCE((
                            SELECT SUM(pd.plan_quantity)
                            FROM plan_details pd
                            JOIN order_items_extract oie ON oie.extract_id = pd.order_extract_id
                            WHERE pd.production_plan_id = :plan_id
                              AND oie.product_id = ppp.product_id
                              AND pd.deleted IS NOT TRUE
                        ), 0)
                        WHERE ppp.production_plan_id = :plan_id
                          AND ppp.deleted IS NOT TRUE
                    '''), {'plan_id': plan_id})

                s.commit()
            except Exception as e:
                s.rollback()
                print(e, '<<< Error reconciling plan after detail delete')

        if request.args.get('production_plan_id') and result.get('success'):
            s = db_client.session
            try:
                # Soft-delete all plan_details for this plan
                s.execute(
                    text('UPDATE plan_details SET deleted=true, deleted_at=NOW() WHERE production_plan_id=:plan_id AND deleted IS NOT TRUE'),
                    {'plan_id': ids}
                )
                # Soft-delete all plan_targets for this plan
                s.execute(
                    text('UPDATE plan_targets SET deleted=true, deleted_at=NOW() WHERE production_plan_id=:plan_id AND deleted IS NOT TRUE'),
                    {'plan_id': ids}
                )
                # Soft-delete all production_plan_products for this plan
                s.execute(
                    text('UPDATE production_plan_products SET deleted=true, deleted_at=NOW() WHERE production_plan_id=:plan_id AND deleted IS NOT TRUE'),
                    {'plan_id': ids}
                )
                # Recalculate quantity_planned on order_items_extract
                # from the SUM of non-deleted plan_details only
                s.execute(text('''
                    UPDATE order_items_extract oie
                    SET quantity_planned = COALESCE((
                        SELECT SUM(pd.plan_quantity)
                        FROM plan_details pd
                        WHERE pd.order_extract_id = oie.extract_id
                          AND pd.deleted IS NOT TRUE
                    ), 0)
                    WHERE oie.extract_id IN (
                        SELECT DISTINCT pd2.order_extract_id
                        FROM plan_details pd2
                        WHERE pd2.production_plan_id = :plan_id
                    )
                '''), {'plan_id': ids})
                s.commit()
            except Exception as e:
                s.rollback()
                print(e, '<<< Error resetting quantity_planned on delete')
        return result



@prod_plan_api_route.route('/get_production_plan')
class ProductionPlanSingleGet(Resource):

    @login_required()
    @prod_plan_api_route.marshal_with(prod_plan_get_all_list_response)
    @prod_plan_api_route.doc(params={**drop_down_get_all_filter,**list_api_params})
    def get(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id', None)
        paged = get_clean_arg('paged', default=1, is_int=True)
        results_per_page = get_clean_arg('results_per_page', default=20, is_int=True)
        offset = (paged - 1) * results_per_page

        is_done = get_clean_arg('is_done', is_bool=True)
        is_closed = get_clean_arg('is_closed', is_bool=True)
        status = get_clean_arg('status')
        sql_con = ''

        if status:
            sql_con += ' and bp.status=:status '
        if is_done is not None:
            sql_con += ' and bp.is_done=:is_done '
        if is_closed is True:
            sql_con += " and (bp.is_done is true or bp.status in ('Closed', 'Rejected')) "
        elif is_closed is False:
            sql_con += " and (bp.is_done is not true and bp.status not in ('Closed', 'Rejected')) "
        if request.args.get('is_rawmaterials_received') == 'true':
            sql_con += ' and df.is_rawmaterials_received is true '
        if request.args.get('is_rawmaterials_received') == 'false':
            sql_con += ' and df.is_rawmaterials_received is not true '

        # start_time = datetime.datetime.now()
        query = text(f'''
                        WITH base_plan AS (
                  SELECT
                    pp.production_plan_id,
                    pp.end_date,
                    uom.uom,
                    pp.product_id,
                    pp.planed_quantity,
                    pp.moved_quantity,
                    pp.wastage,
                    pp.wastage_per,
                    pp.plan_unique,
                    pp.plan_date,
                    pp.execution_start_date,
                    pp.execution_end_date,
                    pp.is_emergency_plan,
                    pp.is_done,
                    pp.status,
                    pp.additional::jsonb,
                    COALESCE(p.product_name, (
                      SELECT string_agg(p2.product_name, ', ') 
                      FROM production_plan_products ppp 
                      JOIN products p2 ON p2.product_id = ppp.product_id 
                      WHERE ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
                    )) AS product_name,
                    COALESCE(p.product_code, 'MULTI') AS product_code,
                    COALESCE(p.sku_id, 'MULTI') AS sku_id,
                    pp.is_multi_product,
                    (
                      SELECT json_agg(json_build_object(
                        'product_id', ppp.product_id,
                        'product_name', p2.product_name,
                        'product_code', p2.product_code,
                        'sku_id', p2.sku_id,
                        'planned_quantity', ppp.planned_quantity,
                        'moved_quantity', ppp.moved_quantity,
                        'wastage', ppp.wastage,
                        'wastage_per', ppp.wastage_per,
                        'floor_id', ppp.floor_id
                      ))
                      FROM production_plan_products ppp 
                      JOIN products p2 ON p2.product_id = ppp.product_id 
                      WHERE ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
                    ) AS products
                  FROM production_plan pp
                  LEFT JOIN products p 
                    ON p.product_id = pp.product_id AND p.deleted IS NOT TRUE
                  LEFT JOIN uom 
                    ON uom.id = p.uom_id AND uom.deleted IS NOT TRUE
                  WHERE pp.deleted IS NOT TRUE and pp.compcode=:compcode
                ),
                order_details AS (
                  SELECT
                    pd.production_plan_id,
                    json_agg(
                      DISTINCT jsonb_build_object(
                        'order_extract_id', pd.order_extract_id,
                        'order_unique', cp.order_unique
                      )
                    ) AS details
                  FROM production_plan pp
                  join plan_details pd on pp.production_plan_id = pd.production_plan_id
                  JOIN order_items_extract oie ON oie.extract_id = pd.order_extract_id
                  JOIN customer_purchase_items cpi ON cpi.items_id = oie.order_items_id
                  JOIN customer_purchase cp ON cp.customer_purchase_id = cpi.customer_purchase_id
                  where pp.compcode=:compcode
                  GROUP BY pd.production_plan_id
                ),
                dispatch_flag AS (
                  SELECT
                    i.prod_plan_id AS production_plan_id,
                    TRUE AS is_rawmaterials_received
                  FROM invregistry i
                  JOIN dispatch d 
                    ON d.releseid = i.releseid
                   AND d.deleted IS NOT TRUE
                  WHERE i.deleted IS NOT TRUE and d.compcode=:compcode
                  GROUP BY i.prod_plan_id
                )
                SELECT
                  bp.*,
                  COALESCE(df.is_rawmaterials_received, FALSE) AS is_rawmaterials_received,
                  od.details,
                  COUNT(*) OVER() AS total_results
                FROM base_plan bp
                LEFT JOIN order_details od 
                  ON od.production_plan_id = bp.production_plan_id
                LEFT JOIN dispatch_flag df 
                  ON df.production_plan_id = bp.production_plan_id
                  where 1=1 {sql_con}
                ORDER BY bp.production_plan_id DESC
                limit :limit offset :offset
                ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        status=status,
                                                        is_done=is_done,
                                                        compcode=compcode,
                                                        limit=results_per_page,
                                                        offset=offset))

        # print("Time taken to execute the query", (datetime.datetime.now()-start_time).total_seconds())

        return {
            "total_results": result[0].get('total_results', 0) if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            "results": result
        }
@prod_plan_api_route.route('/planreport')
class PlanReport(Resource):

    @login_required()
    @prod_plan_api_route.marshal_with(report_response)
    @prod_plan_api_route.doc(params={**report_filter, **list_api_params})
    def get(self):

        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id')
        page = get_clean_arg('paged', default=1, is_int=True)
        result_per_page = get_clean_arg('results_per_page', default=20, is_int=True)
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0

        production_plan_id = get_clean_arg('production_plan_id', is_int=True)
        customer_purchase_id = get_clean_arg('customer_purchase_id', is_int=True)
        sql_con = ''
        end_date = request.args.get('end_date') if request.args.get('end_date') else request.args.get('start_date')
        if production_plan_id is not None:
            sql_con += ' and pp.production_plan_id=:production_plan_id '
        if end_date:
            sql_con += ''' and (
                (el.opertaion_start_date >= cast(:start_date as timestamp) and el.opertaion_start_date < cast(:end_date as timestamp) + interval '1 day')
                or (el.opertaion_end_date >= cast(:start_date as timestamp) and el.opertaion_end_date < cast(:end_date as timestamp) + interval '1 day')
            ) '''
        if customer_purchase_id:
            sql_con += ' and cp.customer_purchase_id=:customer_purchase_id '


        query = text(f'''
                    SELECT 
                    cp.customer_purchase_id,
                    cp.order_unique,
                    pp.production_plan_id,
                    COALESCE(pt.product_id, pp.product_id) as product_id,
                    pp.planed_quantity,
                    pp.plan_date,
                    pp.plan_unique,
                    p.product_code,
                    p.product_name,
                p.sku_id,
                jsonb_agg(distinct
                    jsonb_build_object(
                        'target_quantity', pt.target_quantity,
                        'line_name', lc.line_name,
                        'stage_name', s.stage_name,
                        'opertaion_start_date',el.opertaion_start_date::date,
                        'opertaion_end_date',el.opertaion_end_date::date,
                        'process_name', pc.process_name,
                        'outward_qty', el.outward_qty,
                        'id',el.id,
                        'employee_name', CONCAT(h.fname, ' ', h.lname),
                        'time_value', hc.time_value
                    )
                ) AS target_details,
                count(*) over() as total_count
            FROM 
                production_plan pp
            JOIN 
                plan_targets pt ON pt.production_plan_id = pp.production_plan_id
            JOIN 
                execution_log el ON el.target_id = pt.plan_target_id
            JOIN 
                stage s ON s.stage_id = el.stage_id
            left join line_config as lc on lc.line_config_id = el.line_id
            JOIN 
                production_stages ps ON ps.product_id = COALESCE(pt.product_id, pp.product_id) AND ps.stage_id = s.stage_id 
            --JOIN 
              --  activity_stage_map asm ON asm.production_stage_id = ps.id
            left JOIN 
                process_config pc ON pc.process_id = el.process_id
            JOIN 
                hremploymast h ON h.hremploymastid = el.emp_id
            JOIN 
                hour_config hc ON hc.record_id = el.hour_config_id
            JOIN 
                products p ON p.product_id = COALESCE(pt.product_id, pp.product_id)
            left join
                plan_details as pd on pp.production_plan_id = pd.production_plan_id 
                AND EXISTS (
                    SELECT 1 FROM order_items_extract oie_sub 
                    WHERE oie_sub.extract_id = pd.order_extract_id 
                    AND oie_sub.product_id = COALESCE(pt.product_id, pp.product_id)
                )
            left join 
                order_items_extract as oie on oie.extract_id = pd.order_extract_id
            left join 
                customer_purchase_items as cpi on oie.order_items_id = cpi.items_id
            left join
                customer_purchase as cp on cpi.customer_purchase_id = cp.customer_purchase_id
            where pp.compcode =:compcode and pp.deleted is not true {sql_con}
            GROUP BY 
                cp.customer_purchase_id, cp.order_unique,pp.production_plan_id, COALESCE(pt.product_id, pp.product_id), pp.planed_quantity, pp.plan_date, pp.plan_unique,
                p.product_code, p.product_name, p.sku_id
        ''')

        result = query_to_dict(db_client.engine.execute(query, compcode=compcode,
                                                        production_plan_id=production_plan_id,
                                                        customer_purchase_id=customer_purchase_id,
                                                        end_date=end_date,
                                                        start_date=request.args.get('start_date'),
                                                        limit=result_per_page,
                                                        offset=offset
                                                        ))

        return {
            "total_results": result[0].get('total_count', 0) if result else 0,
            "page": page,
            "results_per_page": result_per_page,
            "results": result
        }

@prod_plan_api_route.route('/<int:production_plan_id>')
class PlanCloser(Resource):

    @login_required()
    @prod_plan_api_route.expect(moved_quantity_model)
    def patch(self, production_plan_id):
        current_user = request.args.get('current_user', {})
        username = current_user.get('username')
        data = request.json
        s = db_client.session
        #For quantity Log
        if data.get('moved_quantity'):
            print("Updating moved quantity log")
            value = update_fg_log(s=s, commit=False, data=data, production_plan_id=production_plan_id)
            if isinstance(value, tuple):
                s.rollback()
                return value
            if isinstance(value, dict) and value.get('success') is False:
                s.rollback()
                return value

        result = update_quantity(values=data, production_plan_id=production_plan_id, s=s, commit=False)
        if isinstance(result, tuple):
            s.rollback()
            return result
        if isinstance(result, dict) and result.get('success') is False:
            s.rollback()
            return result

        if data.get('is_done') is not None and data.get('is_done') is True:
            # Release leftover allocations when plan is completed
            s.execute(text('''
                UPDATE products p
                SET allocated_quantity = GREATEST(0, COALESCE(p.allocated_quantity::numeric, 0) - sub.leftover)
                FROM (
                    SELECT product_id, SUM(allocated_amount) as leftover
                    FROM plan_allocation
                    WHERE prod_plan_id = :production_plan_id
                    GROUP BY product_id
                ) sub
                WHERE p.product_id = sub.product_id;
            '''), {'production_plan_id': production_plan_id})
            s.execute(text('DELETE FROM plan_allocation WHERE prod_plan_id = :production_plan_id'),
                      {'production_plan_id': production_plan_id})

            cost_data = get_labour_cost(s=s, production_plan_id=production_plan_id)
            material_cost = get_material_cost(production_plan_id=production_plan_id)
            cost = 0
            for i in material_cost:
                cost += i.get('total_cost')
                i.update({'compcode': current_user.get('company_id'),
                          'created_by': username,
                          'created_on': datetime.datetime.now(datetime.timezone.utc)})
            if material_cost:
                s.execute(text('update production_material_cost '
                               ' set deleted=true, deleted_at=:now '
                               ' where production_plan_id=:production_plan_id'),
                          {'production_plan_id': production_plan_id, 'now': datetime.datetime.now(datetime.timezone.utc)})
                s.bulk_insert_mappings(ProductionMaterialCost, material_cost)
            update_local(model=ProdPlans,
                          condition=ProdPlans.production_plan_id == production_plan_id,
                          values={
                                'total_material_cost': cost,
                              'total_labour_cost': cost_data.get('total_labour_cost', 0),
                              'labour_cost_per_product': cost_data.get('labour_cost_per_product', 0)},
                          s=s, commit=False)

        s.commit()
        return result


@prod_plan_api_route.route('/revert_stock/<int:production_plan_id>')
class RevertStock(Resource):

    @login_required()
    def post(self, production_plan_id):
        data = request.json or {}
        s = db_client.session
        return revert_stock(values=data, production_plan_id=production_plan_id, s=s)


@prod_plan_api_route.route('/plan_to_stock')
class PlanToStock(Resource):

    @login_required()
    @prod_plan_api_route.marshal_with(plan_stock_list_response)
    @prod_plan_api_route.doc(params=report_filter)
    def get(self):
        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id')
        page = get_clean_arg('paged', default=1, is_int=True)
        result_per_page = get_clean_arg('results_per_page', default=20, is_int=True)
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0

        production_plan_id = get_clean_arg('production_plan_id', is_int=True)
        s = db_client.session
        sql_con = ''
        if production_plan_id is not None:
            sql_con += ' and pp.production_plan_id=:production_plan_id '

        query = text(f'''
        WITH plan_products AS (
            SELECT 
                ppp.production_plan_id,
                ppp.product_id,
                COALESCE(ppp.planned_quantity, pp.planed_quantity) AS planned_quantity,
                COALESCE(ppp.moved_quantity, 0) AS moved_quantity
            FROM production_plan_products ppp
            JOIN production_plan pp ON pp.production_plan_id = ppp.production_plan_id
            WHERE pp.compcode = :compcode AND pp.deleted IS NOT TRUE AND ppp.deleted IS NOT TRUE

            UNION ALL

            SELECT 
                pp.production_plan_id,
                pp.product_id,
                pp.planed_quantity AS planned_quantity,
                COALESCE(pp.moved_quantity, 0) AS moved_quantity
            FROM production_plan pp
            WHERE pp.compcode = :compcode AND pp.deleted IS NOT TRUE AND pp.product_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM production_plan_products ppp 
                  WHERE ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
              )
        ),
        final_stage_def AS (
            SELECT DISTINCT ON (ps.product_id)
                ps.product_id,
                ps.stage_id AS final_stage_id,
                ps.rank_id AS final_rank_id,
                asm.config_id AS final_process_id
            FROM production_stages ps
            JOIN activity_stage_map asm ON asm.production_stage_id = ps.id AND asm.deleted IS NOT TRUE
            WHERE ps.deleted IS NOT TRUE AND ps.compcode = :compcode AND asm.is_final_process IS TRUE
            ORDER BY ps.product_id, ps.rank_id DESC NULLS LAST
        ),
        outward_summary AS (
            SELECT 
                pt.production_plan_id,
                COALESCE(el.product_id, pt.product_id, pp.product_id) AS product_id,
                COALESCE(SUM(el.outward_qty), 0) AS outward_qty
            FROM execution_log el
            JOIN plan_targets pt ON pt.plan_target_id = el.target_id AND pt.deleted IS NOT TRUE
            JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
            JOIN final_stage_def fsd ON fsd.product_id = COALESCE(el.product_id, pt.product_id, pp.product_id)
                AND el.stage_id = fsd.final_stage_id
                AND el.process_id = fsd.final_process_id
            WHERE el.deleted IS NOT TRUE AND pp.deleted IS NOT TRUE AND pp.compcode = :compcode
            GROUP BY pt.production_plan_id, COALESCE(el.product_id, pt.product_id, pp.product_id)
        ),
        lot_summary AS (
            SELECT DISTINCT ON (pt.production_plan_id, COALESCE(el.product_id, pt.product_id, pp.product_id))
                pt.production_plan_id,
                COALESCE(el.product_id, pt.product_id, pp.product_id) AS product_id,
                el.production_lot_no
            FROM execution_log el
            JOIN plan_targets pt ON pt.plan_target_id = el.target_id AND pt.deleted IS NOT TRUE
            JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
            LEFT JOIN final_stage_def fsd ON fsd.product_id = COALESCE(el.product_id, pt.product_id, pp.product_id)
            WHERE el.deleted IS NOT TRUE AND pp.deleted IS NOT TRUE AND pp.compcode = :compcode
              AND el.production_lot_no IS NOT NULL AND TRIM(el.production_lot_no) != ''
            ORDER BY 
                pt.production_plan_id, 
                COALESCE(el.product_id, pt.product_id, pp.product_id),
                (CASE WHEN el.stage_id = fsd.final_stage_id AND el.process_id = fsd.final_process_id THEN 1 ELSE 2 END),
                el.id DESC
        ),
        lot_list_summary AS (
            SELECT 
                pt.production_plan_id,
                COALESCE(el.product_id, pt.product_id, pp.product_id) AS product_id,
                json_agg(DISTINCT el.production_lot_no) AS available_lot_numbers
            FROM execution_log el
            JOIN plan_targets pt ON pt.plan_target_id = el.target_id AND pt.deleted IS NOT TRUE
            JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
            WHERE el.deleted IS NOT TRUE AND pp.deleted IS NOT TRUE AND pp.compcode = :compcode
              AND el.production_lot_no IS NOT NULL AND TRIM(el.production_lot_no) != ''
            GROUP BY pt.production_plan_id, COALESCE(el.product_id, pt.product_id, pp.product_id)
        )
        SELECT 
            pp.production_plan_id,
            pp.plan_unique,
            p.product_id,
            p.product_code,
            p.product_name,
            p.sku_id,
            COALESCE(prod.planned_quantity, pp.planed_quantity) AS planed_quantity,
            COALESCE(prod.moved_quantity, 0) AS moved_quantity,
            COALESCE(ow.outward_qty, 0) AS outward_qty,
            ls.production_lot_no,
            lls.available_lot_numbers,
            COUNT(*) OVER() AS total_results
        FROM production_plan pp
        JOIN plan_products prod ON prod.production_plan_id = pp.production_plan_id
        JOIN products p ON p.product_id = prod.product_id AND p.deleted IS NOT TRUE
        LEFT JOIN outward_summary ow ON ow.production_plan_id = pp.production_plan_id AND ow.product_id = prod.product_id
        LEFT JOIN lot_summary ls ON ls.production_plan_id = pp.production_plan_id AND ls.product_id = prod.product_id
        LEFT JOIN lot_list_summary lls ON lls.production_plan_id = pp.production_plan_id AND lls.product_id = prod.product_id
        WHERE pp.deleted IS NOT TRUE AND pp.compcode = :compcode {sql_con}
        ORDER BY pp.production_plan_id DESC
        ''')
        result = query_to_dict(db_client.engine.execute(query, compcode=compcode,
                                  production_plan_id=production_plan_id))


        return  {
            "total_results": result[0].get('total_results', 0) if result else 0,
            "page": page,
            "results_per_page": result_per_page,
            "results": result
        }


@prod_plan_api_route.route('/plan_to_outward')
class PlanOutward(Resource):

    @login_required()
    @prod_plan_api_route.marshal_with(plan_to_outward_list_response)
    @prod_plan_api_route.doc(params={**plan_to_outward_filter, **list_api_params})
    def get(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id', None)
        sql_con = ''
        production_plan_id = get_clean_arg('production_plan_id', is_int=True)
        product_id = get_clean_arg('product_id', is_int=True)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', start_date)
        status = request.args.get('status', None)
        time_con = ''

        if production_plan_id is not None:
            sql_con += ' and pp.production_plan_id=:production_plan_id '
        if product_id is not None:
            sql_con += ' and COALESCE(ppp.product_id, pp.product_id)=:product_id '
        if status:
            sql_con += ' and pp.status=:status '
        if start_date:
            time_con += ' and created_on between cast(:start_date as timestamp) and cast(:end_date as timestamp)'

        query = text(f'''
        with cte as(
        select product_id,max(rank_id) as max_rank from production_stages as ps
        where deleted is not true and compcode =:compcode
        group by product_id)
        ,
        cte2 as(
        select ps1.product_id,ps1.stage_id,asm.config_id from production_stages as ps1
        join cte on cte.product_id = ps1.product_id and cte.max_rank = ps1.rank_id and ps1.deleted is not true
        left join activity_stage_map asm on asm.production_stage_id = ps1.id and asm.is_final_process is true and asm.deleted is not true
        ),
        el_agg as(
        select el.target_id,el.stage_id,el.process_id,sum(el.outward_qty) as quantity from execution_log el
        where el.deleted is not true and el.compcode =:compcode {time_con}
            group by el.target_id,el.stage_id,el.process_id
        )
        select pp.production_plan_id,pp.plan_unique,COALESCE(ppp.product_id, pp.product_id) as product_id,p.product_name,p.product_code,p.sku_id,pp.status,sum(el_agg.quantity),
        count(*) over() as total_results
         from production_plan as pp
        LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
        left join cte2 on COALESCE(ppp.product_id, pp.product_id) = cte2.product_id
        left join plan_targets pt on pt.production_plan_id = pp.production_plan_id and pt.deleted is not true and pp.deleted is not true and pp.compcode =:compcode and coalesce(pt.product_id, pp.product_id) = cte2.product_id
        left join el_agg on el_agg.target_id = pt.plan_target_id and el_agg.stage_id = cte2.stage_id and (cte2.config_id is null or el_agg.process_id is null or el_agg.process_id = cte2.config_id)
        join products as p on p.deleted is not true and COALESCE(ppp.product_id, pp.product_id) = p.product_id
        where pp.compcode =:compcode and pp.deleted is not true {sql_con}
        group by pp.production_plan_id,pp.plan_unique,COALESCE(ppp.product_id, pp.product_id),p.product_name,p.product_code,p.sku_id,pp.status
        order by pp.production_plan_id desc
        ''')

        results = query_to_dict(db_client.engine.execute(query, compcode=compcode,
                                                         production_plan_id=production_plan_id,
                                                        product_id=product_id,
                                                        start_date=start_date,
                                                        end_date=end_date,
                                                         status=status
                                                        ))

        return {
            "total_results": results[0].get('total_results', 0) if results else 0,
            "results": results
        }


@prod_plan_api_route.route('/product_date_outward')
class ProductDateOutward(Resource):

    @login_required()
    @prod_plan_api_route.marshal_with(plan_date_outward_list_response)
    def get(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id', None)
        product_id = get_clean_arg('product_id', is_int=True)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', start_date)
        page = get_clean_arg('paged', default=1, is_int=True)
        result_per_page = get_clean_arg('results_per_page', default=20, is_int=True)
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0
        sql_con = ''

        if start_date:
            sql_con += ' and el.opertaion_start_date >= cast(:start_date as timestamp) and el.opertaion_start_date < cast(:end_date as timestamp) + interval \'1 day\' '
        if product_id is not None:
            sql_con += ' and COALESCE(ppp.product_id, pp.product_id)=:product_id '

        query = text(f'''
        with cte1 as(
        select COALESCE(ppp.product_id, pp.product_id) as product_id,cp.order_unique,pp.plan_unique,
        el.opertaion_start_date::date as created_on,s.stage_id,s.stage_name,sum(el.outward_qty) as total from execution_log el 
        join plan_targets pt on pt.plan_target_id = el.target_id and el.compcode =:compcode
        join production_plan pp on pp.production_plan_id = pt.production_plan_id
        LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id
        join plan_details pd on pd.production_plan_id = pp.production_plan_id
        join order_items_extract as oie on oie.extract_id = pd.order_extract_id
        join customer_purchase_items as cpi on oie.order_items_id = cpi.items_id
        join customer_purchase as cp on cpi.customer_purchase_id = cp.customer_purchase_id
        join stage s on el.stage_id = s.stage_id and el.compcode =:compcode
        where 1=1 {sql_con}
        group by COALESCE(ppp.product_id, pp.product_id),cp.order_unique,pp.plan_unique,el.opertaion_start_date::date,s.stage_id,s.stage_name
            )
            ,
            cte2 as(
            select product_id,created_on,order_unique,plan_unique,
            json_agg(
            json_build_object(
                'stage_id', stage_id,
                'stage_name', stage_name,
                'produced', total
            )
            ) as details
            from cte1
            group by product_id,created_on,order_unique,plan_unique
                ),
                plan_details as(
                select product_id,created_on,
                json_agg(
                json_build_object(
                'order_unique', order_unique, 
                'plan_unique', plan_unique,
                    'details', details
                )
                ) as plan_details
                from cte2
                group by product_id,created_on
                ),
                cte3 as (
                select product_id,created_on,stage_id,stage_name,sum(total) as produced from cte1
                group by product_id,created_on,stage_id,stage_name
                ),
                product_details as (
                select product_id,created_on,
                    json_agg(
                    json_build_object(
                    'stage_id', stage_id,
                        'stage_name', stage_name,
                        'produced', produced
                    )
                    ) as prod_details
                    from cte3
                    group by product_id,created_on
                )
                select pd.product_id,
                p.product_name,
                p.product_code,
                p.sku_id,
                u.uom,
                json_agg(
                json_build_object(
                'product_details', pd.prod_details,
                    'created_on', pd.created_on,
                    'plan_details', pld.plan_details
                )
                ) as details,
                count(*) over() as total_results
                from product_details pd
                join plan_details pld on pld.product_id = pd.product_id and pld.created_on = pd.created_on
                join products as p on p.product_id = pd.product_id
                join uom as u on u.id = p.uom_id
                where pd.product_id is not null and pd.product_id = pld.product_id
                group by pd.product_id,p.product_name,p.product_code,p.sku_id,u.uom
                limit :limit offset :offset
        ''')

        results = query_to_dict(db_client.engine.execute(query,
                                                         compcode=compcode,
                                                         limit=result_per_page,
                                                         offset=offset,
                                                         product_id=product_id,
                                                         start_date=start_date,
                                                         end_date=end_date
                                                         ))

        return {
            'total_results': results[0].get('total_results') if results else 0,
            'page': page,
            'results_per_page': result_per_page,
            'results': results
        }




@prod_plan_api_route.route('/style_product_date_outward')
class StyleProductDateOutward(Resource):

    @login_required()
    @prod_plan_api_route.marshal_with(style_plan_outward_list_response)
    @prod_plan_api_route.doc(params={**plan_to_outward_filter, **list_api_params, **{
        'vendorid': "int",
        'description': "Filter apply on Vendor_id"
    }})
    def get(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id', None)
        product_id = get_clean_arg('product_id', is_int=True)
        customer_purchase_id = request.args.get('customer_purchase_id', None)
        customer_id = request.args.get('vendorid', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', start_date)
        page = get_clean_arg('paged', default=1, is_int=True)
        result_per_page = get_clean_arg('results_per_page', default=20, is_int=True)
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0
        sql_con = ''
        date_filter = ''
        customer_purchase_ids = None
        customer_ids = None
        if start_date:
            date_filter += ' and el.created_on >= cast(:start_date as timestamp) and el.created_on < cast(:end_date as timestamp) + interval \'1 day\' '
        if product_id is not None:
            sql_con += ' and COALESCE(ppp.product_id, pp.product_id)=:product_id '
        
        customer_purchase_ids = get_clean_int_list('customer_purchase_id')
        if customer_purchase_ids:
            sql_con += ' and cp.customer_purchase_id in :customer_purchase_ids '

        customer_ids = get_clean_int_list('vendorid')
        if customer_ids:
            sql_con += ' and cp.customer_id in :customer_ids '

        # start_time = datetime.datetime.now()
        query = text(f'''
	WITH ordered_cte AS (
    SELECT
    distinct 
        oie.extract_id,
        COALESCE(ppp.product_id, pp.product_id) as product_id,
        ps.stage_id,
        cpi.quantity_ordered AS ordered
    FROM customer_purchase cp
    JOIN customer_purchase_items cpi ON cpi.customer_purchase_id = cp.customer_purchase_id
    JOIN order_items_extract oie ON oie.order_items_id = cpi.items_id
    JOIN plan_details pd ON oie.extract_id = pd.order_extract_id
    JOIN production_plan pp ON pd.production_plan_id = pp.production_plan_id
    LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id
    join production_stages ps on ps.product_id = COALESCE(ppp.product_id, pp.product_id) and ps.deleted is not true
    WHERE cp.compcode =:compcode {sql_con}
),cte as (
SELECT 
        pt.production_plan_id,
		COALESCE(ppp.product_id, pp.product_id) as product_id,
        el.stage_id,
		el.process_id,
        SUM(el.outward_qty) AS total
    FROM plan_targets pt
    JOIN execution_log el ON pt.plan_target_id = el.target_id
	join production_plan pp on pt.production_plan_id = pp.production_plan_id
    LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id
    WHERE pt.compcode =:compcode {date_filter}
    GROUP BY pt.production_plan_id,COALESCE(ppp.product_id, pp.product_id), el.stage_id,el.process_id
	order by pt.production_plan_id desc
),
cte2 as(
select ps.product_id,ps.rank_id,ps.stage_id,asm.config_id,asm.is_final_process from production_stages ps
join activity_stage_map asm on asm.production_stage_id = ps.id and asm.deleted is not true
where ps.deleted is not true and asm.is_final_process is not false and ps.compcode =:compcode
),
execution_cte as(
select cte.production_plan_id,cte.product_id,cte.stage_id,cte.process_id,cte.total,cte2.is_final_process  from cte
join cte2 on cte2.product_id = cte.product_id and cte.stage_id = cte2.stage_id and cte.process_id = cte2.config_id
),
summed as(
SELECT 
    c.category_id,
    c.category_name,
    sp.style_product_id,
    COALESCE(ppp.product_id, pp.product_id) as product_id,
    p.product_name,
    s.stage_id,
    s.stage_name,
    ps.rank_id,
    COALESCE(ps.required_quantity_per_unit, 1) as required_quantity_per_unit,
    vv.variant_value,
    oc.ordered as ordered,
    ec.total as total
FROM customer_purchase cp
LEFT JOIN customer_purchase_items cpi ON cpi.customer_purchase_id = cp.customer_purchase_id
LEFT JOIN order_items_extract oie ON oie.order_items_id = cpi.items_id
LEFT JOIN plan_details pd ON oie.extract_id = pd.order_extract_id
LEFT JOIN production_plan pp ON pd.production_plan_id = pp.production_plan_id
LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id
LEFT JOIN production_stages ps ON ps.product_id = COALESCE(ppp.product_id, pp.product_id) AND ps.deleted IS NOT TRUE AND ps.compcode =:compcode
LEFT JOIN stage s ON s.stage_id = ps.stage_id
LEFT JOIN execution_cte ec ON ec.production_plan_id = pp.production_plan_id AND ec.product_id = COALESCE(ppp.product_id, pp.product_id) AND ec.stage_id = ps.stage_id
LEFT JOIN ordered_cte oc ON oc.extract_id = oie.extract_id AND oc.product_id = COALESCE(ppp.product_id, pp.product_id) AND oc.stage_id = ps.stage_id
LEFT JOIN style_product sp ON sp.product_id = COALESCE(ppp.product_id, pp.product_id) and sp.deleted is not true
JOIN style st ON st.style_id = sp.style_id and st.deleted is not true
JOIN products p ON p.product_id = sp.product_id
JOIN product_variant pv ON pv.product_id = p.product_id
JOIN variant_value vv ON vv.variant_value_id = pv.variant_value_id AND st.attribute_id = vv.variant_attribute_id
JOIN style_category sc ON sc.style_id = st.style_id and sc.deleted is not true
JOIN category c ON c.category_id = sc.category_id and c.deleted is not true
WHERE cp.compcode =:compcode {sql_con}
GROUP BY 
    c.category_id, c.category_name, sp.style_product_id, COALESCE(ppp.product_id, pp.product_id), p.product_name,
    s.stage_id, s.stage_name, ps.rank_id, COALESCE(ps.required_quantity_per_unit, 1), vv.variant_value, oc.ordered, ec.total
ORDER BY 
    c.category_id, c.category_name, sp.style_product_id, COALESCE(ppp.product_id, pp.product_id), p.product_name, ps.rank_id
)
SELECT
    category_id,
    category_name,
    json_agg(
        json_build_object(
            'product_name', product_name,
            'products', style_products
        )
    ) AS products,
    COUNT(*) OVER() AS total_results
FROM (
    SELECT 
        category_id,
        category_name,
        product_name,
        json_agg(
            json_build_object(
                'style_product_id', style_product_id,
                'stages', stages
            )
            ORDER BY style_product_id desc
        ) AS style_products
    FROM (
        SELECT 
            category_id,
            category_name,
            product_name,
            style_product_id,
            json_agg(
                json_build_object(
                    'stage_id', stage_id,
                    'stage_name', stage_name,
                    'rank_id', rank_id,
                    'variants', variants
                )
                ORDER BY rank_id
            ) AS stages
        FROM (
            SELECT
                category_id,
                category_name,
                product_name,
                style_product_id,
                stage_id,
                stage_name,
                rank_id,
                json_agg(
                    json_build_object(
                        'variant_value', variant_value,
                        'ordered', ordered,
                        'total', total,
                        'required_quantity_per_unit', required_quantity_per_unit
                    )
                    ORDER BY variant_value
                ) AS variants
            FROM summed
            GROUP BY category_id, category_name, product_name, style_product_id, stage_id, stage_name, rank_id
        ) AS stage_level
        GROUP BY category_id, category_name, product_name, style_product_id
    ) AS style_level
    GROUP BY category_id, category_name, product_name
) AS product_level
GROUP BY category_id, category_name
LIMIT :limit OFFSET :offset;
''')
        results = query_to_dict(db_client.engine.execute(query,
                                                         compcode=compcode,
                                                         limit=result_per_page,
                                                         offset=offset,
                                                         product_id=product_id,
                                                         customer_purchase_ids=customer_purchase_ids,
                                                         customer_ids=customer_ids,
                                                         start_date=start_date,
                                                         end_date=end_date
                                                         ))

        # end_time = datetime.datetime.now()

        # print("Query Execution Time:", (end_time - start_time).total_seconds(), "seconds")

        return {
            'total_results': results[0].get('total_results') if results else 0,
            'page': page,
            'results_per_page': result_per_page,
            'results': results
        }


@prod_plan_api_route.route('/plan_datewise_outward')
class PlanDateOutward(Resource):

    @login_required()
    @prod_plan_api_route.marshal_with(plan_datewise_list_response)
    @prod_plan_api_route.doc(params={
        'production_plan_id': {
            'type': int,
            'description': "here you filter by production Plan Id"
        }
    })
    def get(self):

        production_plan_id = get_clean_arg('production_plan_id', is_int=True)
        sql_con = ''
        if production_plan_id is not None:
            sql_con += ' and pp.production_plan_id=:production_plan_id '

        # start_time = datetime.datetime.now()
        query = text(f"""
                with cte1 as(
                    select product_id,max(rank_id) from production_stages
                    where deleted is not true and compcode =:compcode
                    group by product_id
                ),
                cte2 as (
                    select ps.product_id,ps.stage_id from production_stages ps
                    join cte1 on cte1.product_id = ps.product_id and ps.rank_id = cte1.max
                ),
                cte3 as(
                select pp.production_plan_id,pp.plan_unique,
                el.opertaion_start_date::date,sum(el.outward_qty),
                CASE
					WHEN pt.is_hourly_target IS true THEN NULL
					ELSE SUM(pt.target_quantity)
        		END AS target_qty
                from production_plan pp
                LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id
                left join plan_targets pt on pp.production_plan_id = pt.production_plan_id and pp.compcode =:compcode and pt.deleted is not true AND pt.product_id = COALESCE(ppp.product_id, pp.product_id)
                left join execution_log el on pt.plan_target_id = el.target_id 
                left join cte2 on el.stage_id = cte2.stage_id and COALESCE(ppp.product_id, pp.product_id) = cte2.product_id
                where 1=1 {sql_con}
                group by pp.production_plan_id,pp.plan_unique,
                el.opertaion_start_date::date,pt.is_hourly_target)
                select 
                    production_plan_id,
                    plan_unique,
                    json_agg(
                    json_build_object(
                        'opertaion_start_date',opertaion_start_date,
                        'target_qty', target_qty,
                        'outward_qty',sum
                    ) order by opertaion_start_date
                    ) as data,
                    count(*) over() as total_results
                from cte3
                group by production_plan_id,plan_unique
        """)
        results = query_to_dict(db_client.engine.execute(query,
                                                         compcode=request.args.get('current_user', {}).get('company_id'),
                                                         production_plan_id=production_plan_id
                                                         ))

        # print("Query execution time", (datetime.datetime.now() - start_time).total_seconds())

        return {
            'total_results': results[0].get('total_results') if results else 0,
            'results': results
        }


@prod_plan_api_route.route('/fg_cost_report')
class FGCostReport(Resource):

    @login_required()
    @prod_plan_api_route.marshal_with(fg_cost_report_list_response)
    def get(self):

        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id') or 1
        try:
            compcode = int(compcode)
        except (ValueError, TypeError):
            compcode = 1

        sql_con = ''
        page = get_clean_arg('paged', default=1, is_int=True)
        result_per_page = get_clean_arg('results_per_page', default=20, is_int=True)
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0

        production_plan_id = get_clean_arg('production_plan_id', is_int=True)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', start_date)
        customer_purchase_id = get_clean_arg('customer_purchase_id', is_int=True)
        product_id = get_clean_arg('product_id', is_int=True)
        is_done = get_clean_arg('is_done', is_bool=True)

        if production_plan_id is not None:
            sql_con += ' and pp.production_plan_id=:production_plan_id '
        if start_date:
            sql_con += ''' and (
                EXISTS (
                    select 1 from execution_log el 
                    join plan_targets pt on pt.plan_target_id = el.target_id 
                    where pt.production_plan_id = pp.production_plan_id 
                      and el.opertaion_start_date >= cast(:start_date as timestamp) 
                      and el.opertaion_start_date < cast(:end_date as timestamp) + interval '1 day' 
                      and el.deleted is not true and pt.deleted is not true
                )
                OR (fsl.created_on >= cast(:start_date as timestamp) and fsl.created_on < cast(:end_date as timestamp) + interval '1 day')
            ) '''
        if customer_purchase_id is not None:
            sql_con += ' and cp.customer_purchase_id=:customer_purchase_id '
        if product_id is not None:
            sql_con += ' and pp.product_id=:product_id '
        if is_done is not None:
            sql_con += ' and pp.is_done=:is_done '

        fsl_date_join = ""
        if start_date:
            fsl_date_join = " and fsl.created_on >= cast(:start_date as timestamp) and fsl.created_on < cast(:end_date as timestamp) + interval '1 day' "

        query = text(f'''
        with active_plans as (
                select cp.customer_purchase_id, cp.order_unique, pp.production_plan_id, pp.plan_unique,
                       pp.product_id,
                       coalesce(p.product_code, string_agg(distinct p2.product_code, ', ')) as product_code
                from production_plan pp
                join plan_details as pd on pp.production_plan_id = pd.production_plan_id and pd.deleted is not true
                left join products p on p.product_id = pp.product_id
                left join production_plan_products ppp on ppp.production_plan_id = pp.production_plan_id and ppp.deleted is not true
                left join products p2 on p2.product_id = ppp.product_id
                left join order_items_extract as oie on oie.extract_id = pd.order_extract_id and oie.deleted is not true
                left join customer_purchase_items as cpi on cpi.items_id = oie.order_items_id and cpi.deleted is not true
                left join customer_purchase as cp on cpi.customer_purchase_id = cp.customer_purchase_id and cp.deleted is not true
                left join fg_to_store_log fsl on fsl.production_plan_id = pp.production_plan_id and fsl.compcode = :compcode {fsl_date_join}
                where pp.compcode = :compcode and pp.deleted is not true {sql_con}
                group by cp.customer_purchase_id, cp.order_unique, pp.production_plan_id, pp.plan_unique, pp.product_id, p.product_code
        ),
        plan_fsl as (
                select fsl.production_plan_id,
                       fsl.created_on::date as created_on,
                       fsl.created_by,
                       to_char(fsl.created_on, 'HH24:MI') AS created_time,
                       sum(fsl.moved_quantity) as moved_quantity,
                       sum(fsl.cost_of_rawmaterial) as cost_of_rawmaterial
                from fg_to_store_log fsl
                where fsl.compcode = :compcode {fsl_date_join}
                group by fsl.production_plan_id, fsl.created_on, fsl.created_by
        ),
        cte1 as (
                select ap.customer_purchase_id, ap.order_unique, ap.production_plan_id, ap.plan_unique,
                       ap.product_id, ap.product_code,
                       coalesce(pf.created_on, coalesce(cast(:start_date as date), current_date)) as created_on,
                       coalesce(pf.created_by, 'production') as created_by,
                       coalesce(pf.created_time, '00:00') as created_time,
                       coalesce(pf.moved_quantity, 0) as moved_quantity,
                       coalesce(pf.cost_of_rawmaterial, 0) as cost_of_rawmaterial
                from active_plans ap
                left join plan_fsl pf on pf.production_plan_id = ap.production_plan_id
        ),
        cte2 as(
                select cte1.customer_purchase_id,cte1.order_unique,cte1.production_plan_id,cte1.plan_unique,
                cte1.product_id,cte1.product_code,
                cte1.created_on,
                sum(cte1.cost_of_rawmaterial) as cost_of_rawmaterial,
                sum(cte1.moved_quantity) as moved_quantity,
                json_agg(
                json_build_object(
                'created_time', cte1.created_time,
                'created_by', cte1.created_by,
                'moved_quantity', cte1.moved_quantity,
                'cost_of_rawmaterial', cte1.cost_of_rawmaterial
                )
                ) as data
                from cte1
                group by
                cte1.customer_purchase_id,cte1.order_unique,cte1.production_plan_id,cte1.plan_unique,
                cte1.product_id,cte1.product_code,cte1.created_on
        ),
        cte3 as(
                select cte2.customer_purchase_id,cte2.order_unique,
                cte2.production_plan_id,cte2.plan_unique,cte2.product_code,
                sum(cte2.cost_of_rawmaterial) as cost_of_rawmaterial,
                sum(cte2.moved_quantity) as moved_quantity,
                json_agg(
                json_build_object(
                'raw_material_cost', cte2.cost_of_rawmaterial,
                'moved_quantity', cte2.moved_quantity,
                'date', cte2.created_on,
                'data', cte2.data
                )
                ) as data
                from cte2
                group by cte2.customer_purchase_id,cte2.order_unique,
                cte2.production_plan_id,cte2.plan_unique,cte2.product_code
        ) 
        select cte3.customer_purchase_id,cte3.order_unique,
        json_agg(
        json_build_object(
        'production_plan_id', cte3.production_plan_id,
        'plan_unique', cte3.plan_unique,
        'product_code', cte3.product_code,
        'raw_material_cost', cte3.cost_of_rawmaterial,
        'moved_quantity', cte3.moved_quantity,
        'data', cte3.data
        )
        ) as data,
        count(*) over() as total_results
        from cte3
        group by cte3.customer_purchase_id,cte3.order_unique
        order by cte3.customer_purchase_id desc
        limit :limit offset :offset
        ''')

        results = query_to_dict(db_client.engine.execute(query,
                                                            compcode=compcode,
                                                            production_plan_id=production_plan_id,
                                                            start_date=start_date,
                                                            end_date=end_date,
                                                            customer_purchase_id=customer_purchase_id,
                                                            product_id=product_id,
                                                            limit=result_per_page,
                                                            offset=offset,
                                                            is_done=is_done
                                                         ))

        all_plan_ids = []
        for row in results:
            for plan in row.get('data', []):
                all_plan_ids.append(plan.get('production_plan_id'))

        actual_material_bulk = {}
        if all_plan_ids:
            date_con = ""
            if start_date and end_date:
                date_con = " AND execution_date >= cast(:start_date as date) AND execution_date <= cast(:end_date as date) "

            act_query = text(f"""
                SELECT production_plan_id, sum(actual_material_cost) as total_cost 
                FROM mv_daily_manufacturing_fact
                WHERE production_plan_id IN :production_plan_ids {date_con}
                GROUP BY production_plan_id
            """).bindparams(bindparam('production_plan_ids', expanding=True))
            act_res = db_client.engine.execute(act_query, {"production_plan_ids": list(set(all_plan_ids)), "start_date": start_date, "end_date": end_date}).fetchall()
            actual_material_bulk = {row[0]: float(row[1] or 0) for row in act_res}

        # Fetch planned / total quantities to calculate proportional unit actual material cost
        plan_qty_map = {}
        if all_plan_ids:
            pq_query = text("""
                select pp.production_plan_id, 
                       coalesce(
                           nullif(pp.planed_quantity, 0),
                           nullif((select sum(ppp.planned_quantity) from production_plan_products ppp where ppp.production_plan_id = pp.production_plan_id and ppp.deleted is not true), 0),
                           nullif((select sum(pd.plan_quantity) from plan_details pd where pd.production_plan_id = pp.production_plan_id and pd.deleted is not true), 0),
                           nullif(max(pt.target_quantity), 0),
                           1
                       ) as total_qty
                from production_plan pp
                left join plan_targets pt on pt.production_plan_id = pp.production_plan_id and pt.deleted is not true
                where pp.production_plan_id IN :production_plan_ids
                group by pp.production_plan_id, pp.planed_quantity
            """).bindparams(bindparam('production_plan_ids', expanding=True))
            pq_res = db_client.engine.execute(pq_query, {'production_plan_ids': list(set(all_plan_ids))}).fetchall()
            plan_qty_map = {row[0]: float(row[1] or 1) for row in pq_res}

        # Query accurate BOM unit material cost directly from BOM master to prevent any historical batch multiplication
        bom_unit_cost_map = {}
        if all_plan_ids:
            bom_cost_query = text("""
                with plan_base as (
                    select pp.production_plan_id,
                           coalesce(ppp.product_id, pp.product_id) as product_id,
                           coalesce(ppp.planned_quantity, pp.planed_quantity) as planned_quantity
                    from production_plan pp
                    left join production_plan_products ppp on ppp.production_plan_id = pp.production_plan_id and ppp.deleted is not true
                    where pp.production_plan_id IN :production_plan_ids and pp.deleted is not true
                )
                select pb.production_plan_id,
                       coalesce(sum(coalesce(nullif(bc.quantity, '')::numeric, 0) * coalesce(mc.cost, 0)), 0) / nullif(coalesce(nullif(sum(pb.planned_quantity), 0), 1), 0) as unit_bom_cost
                from plan_base pb
                left join bom b on b.product_id = pb.product_id and b.deleted is not true
                left join bom_component bc on bc.bom_id = b.bom_id and bc.deleted is not true
                left join material_cost mc on mc.product_id = bc.product_id
                group by pb.production_plan_id
            """).bindparams(bindparam('production_plan_ids', expanding=True))
            b_res = db_client.engine.execute(bom_cost_query, {'production_plan_ids': list(set(all_plan_ids))}).fetchall()
            bom_unit_cost_map = {r[0]: float(r[1] or 0.0) for r in b_res}

        for row in results:
            for plan in row.get('data', []):
                plan_id = plan.get('production_plan_id')
                tot_material_cost = actual_material_bulk.get(plan_id, 0.0)
                tot_plan_qty = plan_qty_map.get(plan_id, 1.0)
                period_moved_qty = float(plan.get('moved_quantity') or 0.0)
                
                # Compute authentic estimated raw_material_cost from BOM unit cost * period_moved_qty
                unit_bom = bom_unit_cost_map.get(plan_id, 0.0)
                if unit_bom > 0 and period_moved_qty > 0:
                    plan['raw_material_cost'] = round(unit_bom * period_moved_qty, 2)

                if tot_plan_qty > 0 and period_moved_qty < tot_plan_qty:
                    # Apportion plan actual material consumption cost proportionally to units moved in this period
                    plan['actual_material_cost'] = round((tot_material_cost / tot_plan_qty) * period_moved_qty, 2)
                else:
                    plan['actual_material_cost'] = tot_material_cost

        return {
            'total_results': results[0].get('total_results') if results else 0,
            'page': page,
            'results_per_page': result_per_page,
            'results': results
        }



@prod_plan_api_route.route('/plan_wise_execution_log/<int:production_plan_id>')
class PlanWiseExecutionLog(Resource):

    @login_required()
    @prod_plan_api_route.marshal_with(plan_wise_outward_resposne_model)
    def get(self, production_plan_id):
        sql_con = ''
        stage_id = request.args.get('stage_id', None)
        if stage_id:
            sql_con += ' and el.stage_id=:stage_id '
        query = text(f'''
with cte as (
SELECT 
        pt.production_plan_id,
		pp.planed_quantity,
		COALESCE(el.product_id, pt.product_id, pp.product_id) as product_id,
        el.stage_id,
		el.process_id,
        SUM(el.outward_qty) AS total
    FROM plan_targets pt
    JOIN execution_log el ON pt.plan_target_id = el.target_id
	join production_plan pp on pt.production_plan_id = pp.production_plan_id
    WHERE pt.compcode =:compcode and pp.production_plan_id =:production_plan_id {sql_con}
    GROUP BY pt.production_plan_id,pp.planed_quantity,COALESCE(el.product_id, pt.product_id, pp.product_id), el.stage_id,el.process_id
	order by pt.production_plan_id desc
),
cte2 as(
select ps.product_id,ps.rank_id,ps.required_quantity_per_unit,ps.stage_id,asm.config_id,asm.is_final_process from production_stages ps
join activity_stage_map asm on asm.production_stage_id = ps.id and asm.deleted is not true
where ps.deleted is not true and asm.is_final_process is not false and ps.compcode =:compcode
)
select cte.production_plan_id,cte.product_id,cte.planed_quantity,cte2.required_quantity_per_unit,cte.stage_id,cte.process_id,cte.total,cte2.is_final_process  from cte
join cte2 on cte2.product_id = cte.product_id and cte.stage_id = cte2.stage_id and cte.process_id = cte2.config_id
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                         compcode=request.args.get('current_user', {}).get('company_id'),
                                                        stage_id=stage_id,
                                                         production_plan_id=production_plan_id
                                                         ))

        pprint(result)

        return {"results": result}


@prod_plan_api_route.route('/calculate_cost/<int:production_plan_id>')
class CalculateCost(Resource):

    @login_required()
    @prod_plan_api_route.marshal_with(production_plan_cost_model_list_response)
    def get(self, production_plan_id):

        query = text('''
            with allocated as (
                select prod_plan_id, product_id, sum(allocated_amount) as allocated_amount 
                from plan_allocation 
                where prod_plan_id =:production_plan_id and deleted is not true
                group by prod_plan_id, product_id
            ),
            dispatched as(
                select inv.prod_plan_id,inv.product_id,sum(d.dispatch_amount) as dispatch_amount from invregistry inv
                join dispatch d on d.releseid = inv.releseid
                where inv.prod_plan_id =:production_plan_id
                group  by inv.product_id,inv.prod_plan_id
            ),
            returned as (
                select rm.prod_plan_id, rm.product_id,sum(rm.return_amount) as return_amount from return_material rm
                where rm.prod_plan_id =:production_plan_id and rm.status = 'Moved'
                group  by rm.prod_plan_id, rm.product_id
            ),
            consumed as(
                select 
                    coalesce(a.prod_plan_id, d.prod_plan_id, r.prod_plan_id) as prod_plan_id,
                    coalesce(a.product_id, d.product_id, r.product_id) as product_id,
                    (coalesce(a.allocated_amount, 0) + coalesce(d.dispatch_amount, 0) - coalesce(r.return_amount, 0)) as consumed 
                from allocated a
                full outer join dispatched d on a.prod_plan_id = d.prod_plan_id and a.product_id = d.product_id
                full outer join returned r on coalesce(a.prod_plan_id, d.prod_plan_id) = r.prod_plan_id and coalesce(a.product_id, d.product_id) = r.product_id
            ),
            dynamic_pmc as (
                select c.prod_plan_id as production_plan_id, c.product_id, c.consumed, (c.consumed*coalesce(mc.cost,0)) as total_cost 
                from consumed c
                left join material_cost mc on mc.product_id = c.product_id
            ),
            needed as (
                select pp.production_plan_id, bc.product_id, sum(COALESCE(ppp.planned_quantity, pp.planed_quantity) * bc.quantity::numeric) as need_quantity
                from production_plan pp
                left join production_plan_products ppp on ppp.production_plan_id = pp.production_plan_id and ppp.deleted is not true
                left join bom b on b.product_id = COALESCE(pp.product_id, ppp.product_id) and b.deleted is not true
                left join bom_component bc on bc.bom_id = b.bom_id and bc.deleted is not true
                where pp.production_plan_id = :production_plan_id
                group by pp.production_plan_id, bc.product_id
            )
            select coalesce(n.production_plan_id, pmc.production_plan_id) as production_plan_id,
            json_agg(
            json_build_object(
                'product_id', coalesce(n.product_id, pmc.product_id),
                'product_name', p.product_name,
                'product_code', p.product_code,
                'sku_id', p.sku_id,
                'uom', uom.uom,
                'need_quantity', coalesce(n.need_quantity, 0),
                'consumed', COALESCE(pmc.consumed, 0),
                'total_cost', COALESCE(pmc.total_cost, 0)
            )
            ) as data
            from needed n
            full outer join dynamic_pmc pmc on pmc.production_plan_id = n.production_plan_id and n.product_id = pmc.product_id
            left join products p on p.product_id = coalesce(n.product_id, pmc.product_id)
            left join uom on p.uom_id = uom.id 
            where coalesce(n.product_id, pmc.product_id) IS NOT NULL
            group by coalesce(n.production_plan_id, pmc.production_plan_id)
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                            compcode=request.args.get('current_user', {}).get('company_id'),
                                                            production_plan_id=production_plan_id
                                                         ))

        return {"results": result}


@prod_plan_api_route.route('/fg_to_store/produced_qty')
class ProducedQty(Resource):

    @login_required()
    @prod_plan_api_route.marshal_with(plan_to_store_response_model)
    def get(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')

        sql_con = ''
        is_done = get_clean_arg('is_done', is_bool=True)
        is_rawmaterials_received = get_clean_arg('is_rawmaterials_received', is_bool=True)
        status = request.args.get('status')
        page = get_clean_arg('paged', default=1, is_int=True)
        result_per_page = get_clean_arg('results_per_page', default=20, is_int=True)
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0
        plan_date = request.args.get('plan_date', None)
        production_plan_id = get_clean_arg('production_plan_id', is_int=True)
        
        if production_plan_id is not None:
            sql_con += ' and bp.production_plan_id = :production_plan_id '

        if is_done is not None:
            sql_con += ' and bp.is_done =:is_done '

        if is_rawmaterials_received is not None:
            sql_con += ' and COALESCE(df.is_rawmaterials_received, FALSE) =:is_rawmaterials_received '

        if status:
            sql_con += ' and bp.status =:status '

        if plan_date:
            sql_con += 'and bp.plan_date >= cast(:plan_date as timestamp) and bp.plan_date < cast(:plan_date as timestamp) + interval \'1 day\''
        try:

            # start_time = datetime.datetime.now()

            query = text(f'''
            with order_details AS (
                  SELECT
                    pd.production_plan_id,
                    json_agg(
                      DISTINCT jsonb_build_object(
                        'order_extract_id', pd.order_extract_id,
                        'order_unique', cp.order_unique
                      )
                    ) AS details
                  FROM production_plan pp
                  join plan_details pd on pp.production_plan_id = pd.production_plan_id
                  JOIN order_items_extract oie ON oie.extract_id = pd.order_extract_id
                  JOIN customer_purchase_items cpi ON cpi.items_id = oie.order_items_id
                  JOIN customer_purchase cp ON cp.customer_purchase_id = cpi.customer_purchase_id
                  where pp.compcode=:compcode
                  GROUP BY pd.production_plan_id
            ),
            final_stage_def AS (
                SELECT DISTINCT ON (ps.product_id)
                    ps.product_id,
                    ps.stage_id AS final_stage_id,
                    ps.rank_id AS final_rank_id,
                    asm.config_id AS final_process_id
                FROM production_stages ps
                JOIN activity_stage_map asm ON asm.production_stage_id = ps.id AND asm.deleted IS NOT TRUE
                WHERE ps.deleted IS NOT TRUE AND ps.compcode = :compcode AND asm.is_final_process IS TRUE
                ORDER BY ps.product_id, ps.rank_id DESC NULLS LAST
            ),
            outward_summary AS (
                SELECT 
                    pt.production_plan_id,
                    COALESCE(el.product_id, pt.product_id, pp.product_id) AS product_id,
                    COALESCE(SUM(el.outward_qty), 0) AS outward_qty
                FROM execution_log el
                JOIN plan_targets pt ON pt.plan_target_id = el.target_id AND pt.deleted IS NOT TRUE
                JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
                JOIN final_stage_def fsd ON fsd.product_id = COALESCE(el.product_id, pt.product_id, pp.product_id)
                    AND el.stage_id = fsd.final_stage_id
                    AND el.process_id = fsd.final_process_id
                WHERE el.deleted IS NOT TRUE AND pp.deleted IS NOT TRUE AND pp.compcode = :compcode
                GROUP BY pt.production_plan_id, COALESCE(el.product_id, pt.product_id, pp.product_id)
            ),
            produced_qty AS (
                SELECT production_plan_id, SUM(outward_qty) AS outward_qty
                FROM outward_summary
                GROUP BY production_plan_id
            ),
            base_plan AS (
                  SELECT
                    pp.production_plan_id,
                    pp.plan_unique,
                    COALESCE(
                      (SELECT SUM(ppp.planned_quantity) FROM production_plan_products ppp WHERE ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE),
                      pp.planed_quantity,
                      0
                    ) AS planed_quantity,
                    pp.end_date,
                    uom.uom,
                    pp.product_id,
                        COALESCE(
                          CASE WHEN pp.is_multi_product IS TRUE THEN (
                            SELECT SUM(ppp.moved_quantity) 
                            FROM production_plan_products ppp 
                            WHERE ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
                          )
                          ELSE pp.moved_quantity
                          END,
                          (
                            SELECT SUM(ppp.moved_quantity) 
                            FROM production_plan_products ppp 
                            WHERE ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
                          ),
                          pp.moved_quantity,
                          0
                        ) AS moved_quantity,
                        COALESCE(
                          pp.moved_date,
                          (
                            SELECT MAX(ppp.moved_date)
                            FROM production_plan_products ppp
                            WHERE ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
                          )
                        ) AS moved_date,
                        pp.plan_date,
                        pp.execution_start_date,
                        pp.execution_end_date,
                        pp.is_emergency_plan,
                        pp.is_done,
                        pp.status,
                        pp.additional::jsonb,
                        p.product_name,
                        p.product_code,
                        p.sku_id
                      FROM production_plan pp
                      LEFT JOIN products p 
                        ON p.product_id = pp.product_id AND p.deleted IS NOT TRUE
                      LEFT JOIN uom 
                        ON uom.id = p.uom_id AND uom.deleted IS NOT TRUE
                      WHERE pp.deleted IS NOT TRUE and pp.compcode=:compcode
                    ),
                    dispatch_flag AS (
                      SELECT
                        i.prod_plan_id AS production_plan_id,
                        TRUE AS is_rawmaterials_received
                      FROM invregistry i
                      JOIN dispatch d 
                        ON d.releseid = i.releseid
                       AND d.deleted IS NOT TRUE
                      WHERE i.deleted IS NOT TRUE and d.compcode=:compcode
                      GROUP BY i.prod_plan_id
                    )
                    SELECT
                      bp.*,
                      od.details,
                      pq.outward_qty as produced_qty,
                      COALESCE(df.is_rawmaterials_received, FALSE) AS is_rawmaterials_received,
                      COUNT(*) OVER() AS total_results
                    FROM base_plan bp
                    LEFT JOIN order_details od ON od.production_plan_id = bp.production_plan_id
                    LEFT JOIN dispatch_flag df 
                      ON df.production_plan_id = bp.production_plan_id
                    left join produced_qty pq on pq.production_plan_id = bp.production_plan_id
                      where 1=1 {sql_con}
                    ORDER BY bp.production_plan_id DESC
                    limit :limit offset :offset
            ''')

            result = query_to_dict(db_client.engine.execute(query,
                                                            limit=result_per_page,
                                                            offset=offset,
                                                            compcode=compcode,
                                                            is_done = is_done,
                                                            plan_date=plan_date,
                                                            production_plan_id=production_plan_id,
                                                            status=status,
                                                            is_rawmaterials_received=is_rawmaterials_received
                                                            ))

            # print("Query execution time", (datetime.datetime.now() - start_time).total_seconds(), "seconds")

            return {
                'total_results': result[0].get('total_results') if result else 0,
                'results_per_page': result_per_page,
                'page': page,
                'results': result
            }

        except Exception as e:
            print("Error", e)
            return map_sqlalchemy_error_to_http_status(e)