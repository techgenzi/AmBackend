from flask import request
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text


# from rank.app.api_doc import list_api_params
from .. import db_client
from ipss_utils.ipss_api_doc import list_api_params
from ..routes.rm_purchase import orderReportsAPIRoutes, orderPlanReportModelResponse, del_model_response, \
    delivery_model_list_response, planBasedNestedModelResponse, report_order_list_response, \
    report_order_plan_list_response
from ..api_doc import search_filters, deleivery_filters, paln_filterss, requestPlanFilter, report_filter, materialProductionFilter

@orderReportsAPIRoutes.route('/production-vs-issued')
class AuditReportAPI(Resource):
    @login_required()
    @orderReportsAPIRoutes.doc(params={**list_api_params, **materialProductionFilter, 'order_id': {'type': int, 'description': 'Search by order_id'}})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get('results_per_page') else 20
        offset = (paged - 1) * results_per_page
        
        sql_con = ''
        if request.args.get('product_id'):
            sql_con += ' AND p.product_id = :product_id '
        if request.args.get('production_plan_id'):
            sql_con += ' AND pp.production_plan_id = :production_plan_id '
        if request.args.get('order_id'):
            sql_con += ' AND cp.customer_purchase_id = :order_id '
        if request.args.get('start_date'):
            sql_con += ' AND pp.production_plan_id IN (SELECT DISTINCT pt2.production_plan_id FROM plan_targets pt2 JOIN execution_log el2 ON el2.target_id = pt2.plan_target_id WHERE el2.opertaion_start_date::date >= cast(:start_date as date) AND el2.deleted IS NOT TRUE AND pt2.deleted IS NOT TRUE) '
        if request.args.get('end_date'):
            sql_con += ' AND pp.production_plan_id IN (SELECT DISTINCT pt2.production_plan_id FROM plan_targets pt2 JOIN execution_log el2 ON el2.target_id = pt2.plan_target_id WHERE el2.opertaion_start_date::date <= cast(:end_date as date) AND el2.deleted IS NOT TRUE AND pt2.deleted IS NOT TRUE) '
            
        sql_query = text(f'''
            WITH latest_bom AS (
                SELECT bom_id, product_id
                FROM (
                    SELECT b.bom_id, b.product_id, ROW_NUMBER() OVER(PARTITION BY b.product_id ORDER BY b.bom_id DESC) as rn
                    FROM bom b
                    WHERE b.deleted IS NOT TRUE AND b.compcode = :ccode
                ) sub
                WHERE rn = 1
            )
            SELECT 
                cp.order_unique AS order_id,
                pp.plan_unique AS plan_id,
                CONCAT('(', p.sku_id, ') ', p.product_code) AS product,
                b.bom_id,
                s.stage_name,
                CONCAT('(', mp.sku_id, ') ', mp.product_code) AS material_name,
                mp.sku_id AS material_sku_id,
                u.uom AS uom_name,
                bc.quantity::numeric * COALESCE(pd.plan_quantity, ppp.planned_quantity, pp.planed_quantity) AS bom_required_qty,
                COALESCE(
                    (SELECT SUM(d.dispatch_amount::numeric)
                     FROM dispatch d
                     JOIN invregistry i ON i.releseid = d.releseid
                     WHERE i.prod_plan_id = pp.production_plan_id
                       AND i.product_id = bc.product_id
                       AND d.deleted IS NOT TRUE
                       AND i.deleted IS NOT TRUE), 0
                ) AS issued_qty,
                COALESCE(
                    (SELECT SUM(el.outward_qty) / COALESCE(NULLIF(MAX(ps.required_quantity_per_unit), 0), 1)
                     FROM execution_log el 
                     JOIN plan_targets pt ON el.target_id = pt.plan_target_id 
                     JOIN production_stages ps ON ps.product_id = p.product_id AND ps.deleted IS NOT TRUE
                     LEFT JOIN activity_stage_map asm ON asm.production_stage_id = ps.id AND asm.config_id = el.process_id AND asm.deleted IS NOT TRUE
                     WHERE pt.production_plan_id = pp.production_plan_id 
                       AND pt.product_id = p.product_id
                       AND pt.deleted IS NOT TRUE
                       AND el.deleted IS NOT TRUE
                       AND ps.stage_id = COALESCE(bc.stage_id, (
                           SELECT ps_final.stage_id 
                           FROM production_stages ps_final 
                           WHERE ps_final.product_id = p.product_id AND ps_final.deleted IS NOT TRUE 
                           ORDER BY ps_final.rank_id DESC LIMIT 1
                       ))
                       AND el.stage_id = ps.stage_id
                       AND (asm.is_final_process IS TRUE OR asm.activity_stage_map_id IS NULL)
                    ), 0
                ) * bc.quantity::numeric AS execution_qty
            FROM production_plan pp
            LEFT JOIN plan_details pd ON pd.production_plan_id = pp.production_plan_id AND pd.deleted IS NOT TRUE
            LEFT JOIN order_items_extract oie ON oie.extract_id = pd.order_extract_id AND oie.deleted IS NOT TRUE
            LEFT JOIN customer_purchase_items cpi ON cpi.items_id = oie.order_items_id AND cpi.deleted IS NOT TRUE
            LEFT JOIN customer_purchase cp ON cp.customer_purchase_id = cpi.customer_purchase_id AND cp.deleted IS NOT TRUE
            LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id AND pd.plan_details_id IS NULL AND ppp.deleted IS NOT TRUE
            JOIN products p ON p.product_id = COALESCE(oie.product_id, ppp.product_id, pp.product_id) AND p.deleted IS NOT TRUE
            JOIN latest_bom b ON b.product_id = p.product_id
            JOIN bom_component bc ON bc.bom_id = b.bom_id AND bc.deleted IS NOT TRUE
            LEFT JOIN stage s ON s.stage_id = bc.stage_id AND s.deleted IS NOT TRUE
            JOIN products mp ON mp.product_id = bc.product_id AND mp.deleted IS NOT TRUE
            LEFT JOIN uom u ON u.id = mp.uom_id AND u.deleted IS NOT TRUE
            WHERE pp.compcode = :ccode AND pp.deleted IS NOT TRUE {sql_con}
            ORDER BY cp.order_unique, pp.plan_unique, s.stage_name, mp.product_name
            LIMIT :limit OFFSET :offset
        ''')
        
        sql_query_count = text(f'''
            WITH latest_bom AS (
                SELECT bom_id, product_id
                FROM (
                    SELECT b.bom_id, b.product_id, ROW_NUMBER() OVER(PARTITION BY b.product_id ORDER BY b.bom_id DESC) as rn
                    FROM bom b
                    WHERE b.deleted IS NOT TRUE AND b.compcode = :ccode
                ) sub
                WHERE rn = 1
            )
            SELECT COUNT(1)
            FROM production_plan pp
            LEFT JOIN plan_details pd ON pd.production_plan_id = pp.production_plan_id AND pd.deleted IS NOT TRUE
            LEFT JOIN order_items_extract oie ON oie.extract_id = pd.order_extract_id AND oie.deleted IS NOT TRUE
            LEFT JOIN customer_purchase_items cpi ON cpi.items_id = oie.order_items_id AND cpi.deleted IS NOT TRUE
            LEFT JOIN customer_purchase cp ON cp.customer_purchase_id = cpi.customer_purchase_id AND cp.deleted IS NOT TRUE
            LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id AND pd.plan_details_id IS NULL AND ppp.deleted IS NOT TRUE
            JOIN products p ON p.product_id = COALESCE(oie.product_id, ppp.product_id, pp.product_id) AND p.deleted IS NOT TRUE
            JOIN latest_bom b ON b.product_id = p.product_id
            JOIN bom_component bc ON bc.bom_id = b.bom_id AND bc.deleted IS NOT TRUE
            LEFT JOIN stage s ON s.stage_id = bc.stage_id AND s.deleted IS NOT TRUE
            JOIN products mp ON mp.product_id = bc.product_id AND mp.deleted IS NOT TRUE
            WHERE pp.compcode = :ccode AND pp.deleted IS NOT TRUE {sql_con}
        ''')
        
        params = {
            'ccode': ccode,
            'limit': results_per_page,
            'offset': offset,
            'product_id': request.args.get('product_id'),
            'production_plan_id': request.args.get('production_plan_id'),
            'order_id': request.args.get('order_id'),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
        }
        
        results = query_to_dict(db_client.engine.execute(sql_query, **params))
        count_res = query_to_dict(db_client.engine.execute(sql_query_count, **params))
        
        for row in results:
            row['bom_required_qty'] = float(row.get('bom_required_qty') or 0)
            row['issued_qty'] = float(row.get('issued_qty') or 0)
            row['execution_qty'] = float(row.get('execution_qty') or 0)
            row['variance'] = row['execution_qty'] - row['issued_qty']
            
        return {
            'total_results': count_res[0].get('count', 0) if len(count_res) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': results
        }


@orderReportsAPIRoutes.route('/request-product-report')
class RequestReport(Resource):
    @login_required()
    @orderReportsAPIRoutes.marshal_with(planBasedNestedModelResponse)
    @orderReportsAPIRoutes.doc(params={**list_api_params,**requestPlanFilter})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con=''
        if request.args.get('product_id'):
            sql_con+=' and p.product_id=:product_id '
        if request.args.get('production_plan_id'):
            sql_con+=' and pp.production_plan_id=:production_plan_id '
        end_date=request.args.get('end_date') if request.args.get('end_date') else request.args.get('start_date')
        if request.args.get('start_date'):
            sql_con+=' and i.approval_date::date >=cast(:start_date as date) '
            sql_con += ' and i.approval_date::date <=cast(:end_date as date) '
        sql_query=text(f'''
            with latest_bom as (
                select distinct on (b.product_id) b.bom_id, b.product_id
                from bom b
                where b.deleted is not true
                order by b.product_id, b.bom_id desc
            ),
            bom_comp_agg as (
                select bc.bom_id, bc.product_id, sum(bc.quantity::numeric) as quantity
                from bom_component bc
                where bc.deleted is not true
                group by bc.bom_id, bc.product_id
            ),
            plan_req_qty as (
                select pp.production_plan_id, bc.product_id as rm_product_id,
                       sum(coalesce(bc.quantity, 0) * coalesce(ppp.planned_quantity, pp.planed_quantity)::numeric) as required_quantity
                from production_plan pp
                left join production_plan_products ppp on ppp.production_plan_id = pp.production_plan_id and ppp.deleted is not true
                left join latest_bom b on b.product_id = coalesce(ppp.product_id, pp.product_id)
                left join bom_comp_agg bc on bc.bom_id = b.bom_id
                where pp.deleted is not true and pp.compcode = :ccode
                group by pp.production_plan_id, bc.product_id
            )
            select p.product_id,p.product_name,p.product_code,p.sku_id,u.uom,
            jsonb_agg(json_build_object(
            'production_plan_id',pp.production_plan_id ,
            'releseid',i.releseid,
            'plan_unique',pp.plan_unique ,
            'order_unique',cp.order_unique,
            'planed_quantity',pp.planed_quantity ,
            'required_quantity', coalesce(prq.required_quantity, 0),
            'approved_amount',i.approved_amount ,
            'doc_id',i.doc_id 
            )) as plan_details
            from products p 
            left join uom as u on u.id = p.uom_id
            join invregistry i on i.product_id =p.product_id and i.status ='Approved' and i.deleted is not true
            join production_plan pp on pp.production_plan_id =i.prod_plan_id and pp.deleted is not true
            left join (
                select pd.production_plan_id, max(cp.order_unique) as order_unique
                from plan_details as pd
                join order_items_extract as oie on oie.extract_id = pd.order_extract_id
                join customer_purchase_items as cpi on cpi.items_id = oie.order_items_id
                join customer_purchase as cp on cp.customer_purchase_id = cpi.customer_purchase_id
                where pd.deleted is not true
                group by pd.production_plan_id
            ) as cp on cp.production_plan_id = pp.production_plan_id
            left join plan_req_qty prq on prq.production_plan_id = pp.production_plan_id and prq.rm_product_id = p.product_id
            where p.compcode=:ccode {sql_con}
            group by p.product_id,p.product_name,p.product_code,p.sku_id,u.uom
            limit :limit offset :offset
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,ccode=ccode,
                                                         production_plan_id=request.args.get('production_plan_id'),
                                                         product_id=request.args.get('product_id'),
                                                         end_date=end_date,
                                                         start_date=request.args.get('start_date'),
                                                         limit=results_per_page,
                                                         offset=offset))
        sql_count=text(f'''
        select count(distinct p.product_id)
        from products p 
        join invregistry i on i.product_id =p.product_id and i.status ='Approved'
        join production_plan pp on pp.production_plan_id =i.prod_plan_id 
        where p.compcode=:ccode {sql_con}
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,ccode=ccode,
                                                         production_plan_id=request.args.get('production_plan_id'),
                                                         product_id=request.args.get('product_id'),
                                                         end_date=end_date,
                                                         start_date=request.args.get('start_date'),
                                                         ))
        return {
            'total_results': sql_count[0].get('count', 0) if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }

@orderReportsAPIRoutes.route('/requestBasedPlan-product')
class RequestReport(Resource):
    @login_required()
    @orderReportsAPIRoutes.marshal_with(planBasedNestedModelResponse)
    @orderReportsAPIRoutes.doc(params={**list_api_params,**requestPlanFilter})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con=''
        if request.args.get('product_id'):
            sql_con+=' and p.product_id=:product_id '
        if request.args.get('production_plan_id'):
            sql_con+=' and pp.production_plan_id=:production_plan_id '
        end_date=request.args.get('end_date') if request.args.get('end_date') else request.args.get('start_date')
        if request.args.get('start_date'):
            sql_con+=' and i.approval_date::date >=cast(:start_date as date) '
            sql_con += ' and i.approval_date::date <=cast(:end_date as date) '
        sql_query=text(f'''
            with latest_bom as (
                select distinct on (b.product_id) b.bom_id, b.product_id
                from bom b
                where b.deleted is not true
                order by b.product_id, b.bom_id desc
            ),
            bom_comp_agg as (
                select bc.bom_id, bc.product_id, sum(bc.quantity::numeric) as quantity
                from bom_component bc
                where bc.deleted is not true
                group by bc.bom_id, bc.product_id
            ),
            plan_req_qty as (
                select pp.production_plan_id, bc.product_id as rm_product_id,
                       sum(coalesce(bc.quantity, 0) * coalesce(ppp.planned_quantity, pp.planed_quantity)::numeric) as required_quantity
                from production_plan pp
                left join production_plan_products ppp on ppp.production_plan_id = pp.production_plan_id and ppp.deleted is not true
                left join latest_bom b on b.product_id = coalesce(ppp.product_id, pp.product_id)
                left join bom_comp_agg bc on bc.bom_id = b.bom_id
                where pp.deleted is not true and pp.compcode = :ccode
                group by pp.production_plan_id, bc.product_id
            )
            select p.product_id,p.product_name,p.product_code,p.sku_id,
            jsonb_agg(json_build_object(
            'production_plan_id',pp.production_plan_id ,
            'plan_unique',pp.plan_unique ,
            'planed_quantity',pp.planed_quantity ,
            'required_quantity', coalesce(prq.required_quantity, 0),
            'approved_amount',i.approved_amount ,
            'doc_id',i.doc_id 
            )) as plan_details
            from products p 
            join invregistry i on i.product_id =p.product_id and i.status ='Approved' and i.deleted is not true
            join production_plan pp on pp.production_plan_id =i.prod_plan_id and pp.deleted is not true
            left join plan_req_qty prq on prq.production_plan_id = pp.production_plan_id and prq.rm_product_id = p.product_id
            where p.compcode=:ccode {sql_con}
            group by p.product_id,p.product_name,p.product_code,p.sku_id
            limit :limit offset :offset
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,ccode=ccode,
                                                         production_plan_id=request.args.get('production_plan_id'),
                                                         product_id=request.args.get('product_id'),
                                                         end_date=end_date,
                                                         start_date=request.args.get('start_date'),
                                                         limit=results_per_page,
                                                         offset=offset))
        sql_count=text(f'''
        select count(distinct p.product_id)
        from products p 
        join invregistry i on i.product_id =p.product_id and i.status ='Approved'
        join production_plan pp on pp.production_plan_id =i.prod_plan_id 
        where p.compcode=:ccode {sql_con}
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,ccode=ccode,
                                                         production_plan_id=request.args.get('production_plan_id'),
                                                         product_id=request.args.get('product_id'),
                                                         end_date=end_date,
                                                         start_date=request.args.get('start_date'),
                                                         ))
        return {
            'total_results': sql_count[0].get('count', 0) if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }
@orderReportsAPIRoutes.route('/OrderPlans')
class OrderPlanReports(Resource):
    @login_required()
    @orderReportsAPIRoutes.marshal_with(orderPlanReportModelResponse)
    @orderReportsAPIRoutes.doc(params={**list_api_params,**search_filters})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        end_date=request.args.get('start_date') if not request.args.get('end_date') else request.args.get('end_date')
        sql_con=''
        if request.args.get('customer_purchase_id'):
            sql_con+=' and cp.customer_purchase_id=:customer_purchase_id '
        if request.args.get('status'):
            sql_con+=' and cp.status=:status '
        if request.args.get('start_date'):
            sql_con+=' and cp.order_date::date>=cast(:start_date as date) '
        if end_date:
            sql_con+=' and cp.order_date::date<=cast(:end_date as date) '
        if request.args.get('production_plan_id'):
            sql_con+=' and pd.production_plan_id=:production_plan_id '
        if request.args.get('product_id'):
            sql_con+=' and cpi.product_id=:product_id '
        sql_query=text(f'''
        with cte as (select cp.customer_purchase_id,cp.order_date,cp.expected_receiving_date,cp.order_unique,
        oie.product_id,oie.quantity_ordered as quantity_ordered,p.product_code ,p.product_name ,coalesce(p.product_count,0)product_count,p.sku_id ,
        coalesce(sum(pd.plan_quantity),0) as planed_qty
        from customer_purchase cp 
        join customer_purchase_items cpi on cpi.customer_purchase_id =cp.customer_purchase_id 
        join order_items_extract oie on oie.order_items_id =cpi.items_id 
        join products p on p.product_id =oie.product_id 
        left join plan_details pd on pd.order_extract_id =oie.extract_id and pd.deleted is not true
        left join production_plan as pp on pp.production_plan_id=pd.production_plan_id and pp.status<>'Rejected'
        where cp.deleted is not true and cpi.deleted is not true and oie.deleted is not true
        and cp.compcode=:ccode{sql_con}
        group by  cp.customer_purchase_id,cp.order_date,cp.expected_receiving_date,cp.order_unique,
        oie.product_id,oie.quantity_ordered,oie.quantity_planned,p.product_code ,p.product_name ,p.product_count,p.sku_id)
        select cte.customer_purchase_id,cte.order_date,cte.expected_receiving_date,cte.order_unique,
        jsonb_agg(json_build_object(
        'product_id',cte.product_id,
        'quantity_ordered',cte.quantity_ordered,
        'product_code',cte.product_code,
        'product_name',cte.product_name,
        'product_count',cte.product_count,
        'sku_id',cte.sku_id,
        'planed_qty',cte.planed_qty
        )) as plan_details
        from cte
        group by cte.customer_purchase_id,cte.order_date,cte.expected_receiving_date,cte.order_unique
        limit :limit offset :offset
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,ccode=ccode,
                                                         production_plan_id=request.args.get('production_plan_id'),
                                                         end_date=end_date,
                                                         limit=results_per_page,
                                                         offset=offset,
                                                         customer_purchase_id=request.args.get('customer_purchase_id'),
                                                         start_date=request.args.get('start_date'),
                                                         status=request.args.get('status'),
                                                         product_id=request.args.get('product_id'),
                                                         ))
        sql_count=text(f'''
        select count(distinct cp.customer_purchase_id)
        from customer_purchase cp 
        join customer_purchase_items cpi on cpi.customer_purchase_id =cp.customer_purchase_id 
        join order_items_extract oie on oie.order_items_id =cpi.items_id 
        join products p on p.product_id =oie.product_id 
        left join plan_details pd on pd.order_extract_id =oie.extract_id 
        where cp.deleted is not true and cpi.deleted is not true and oie.deleted is not true
        and cp.compcode=:ccode {sql_con}
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,ccode=ccode,
                                                         production_plan_id=request.args.get('production_plan_id'),
                                                         end_date=end_date,
                                                         limit=results_per_page,
                                                         offset=offset,
                                                         product_id=request.args.get('product_id'),
                                                         customer_purchase_id=request.args.get('customer_purchase_id'),
                                                         start_date=request.args.get('start_date'),
                                                         status=request.args.get('status'),
                                                         ))
        return {
            'total_results': sql_count[0].get('count',0) if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }
@orderReportsAPIRoutes.route('/Production-report')
class ProductionReport(Resource):
    @login_required()
    @orderReportsAPIRoutes.marshal_with(del_model_response)
    @orderReportsAPIRoutes.doc(params={**list_api_params,**paln_filterss})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        end_date=request.args.get('start_date') if not request.args.get('end_date') else request.args.get('end_date')
        sql_con=''
        if request.args.get('product_id'):
           sql_con+=' and p.product_id=:product_id '
        if request.args.get('production_plan_id'):
           sql_con+=' and pp.production_plan_id=:production_plan_id '
        if request.args.get('status'):
           sql_con+=' and pp.status=:status '
        end_date = request.args.get('start_date') if not request.args.get('end_date') else request.args.get('end_date')
        if request.args.get('start_date'):
            sql_con+=' and pp.plan_date::date >=cast(:start_date as date) '
        if end_date:
            sql_con+=' and pp.plan_date::date <=cast(:end_date as date) '
        sql_query=text(f'''
        SELECT pp.plan_unique,
       p.product_id,
       pp.wastage AS allowed_wastage,
       p.product_code,
       p.product_name,
       oie.quantity_ordered,
       COALESCE(pd.plan_quantity, ppp.planned_quantity, pp.planed_quantity) as planed_quantity,
       pp.production_plan_id, 
       u.id as uom_id,
	   u.uom,
       round(sum(case when asm.is_final_process is true or asm.activity_stage_map_id is null then el.outward_qty 
       else 0 end),2) as outward_qty,
       round(avg(el.wastage),2) as actual_wastage,
       s.stage_name,
       cp.order_unique,
       p.sku_id
FROM production_plan pp
LEFT JOIN plan_details as pd on pp.production_plan_id = pd.production_plan_id
LEFT JOIN order_items_extract as oie on oie.extract_id = pd.order_extract_id
LEFT JOIN customer_purchase_items as cpi on cpi.items_id = oie.order_items_id
LEFT JOIN customer_purchase as cp on cpi.customer_purchase_id =cp.customer_purchase_id
LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id AND pd.plan_details_id IS NULL AND ppp.deleted IS NOT TRUE
JOIN products p ON p.product_id = COALESCE(oie.product_id, ppp.product_id, pp.product_id) 
left join uom as u on p.uom_id = u.id
LEFT JOIN (
    SELECT product_id, MAX(rank_id) AS max_rank_id
    FROM production_stages
    where deleted is not true
    GROUP BY product_id
) ps_max ON ps_max.product_id = p.product_id
LEFT JOIN production_stages ps ON ps.product_id = p.product_id AND ps.rank_id = ps_max.max_rank_id and ps.deleted is not true
left join stage s on s.stage_id =ps.stage_id 
LEFT JOIN plan_targets pt ON pt.production_plan_id = pp.production_plan_id AND pt.product_id = p.product_id
LEFT JOIN execution_log el ON el.target_id = pt.plan_target_id and el.stage_id=s.stage_id
left join activity_stage_map asm on asm.production_stage_id =ps.id and asm.config_id=el.process_id
where pp.deleted is not true and pp.compcode=:ccode {sql_con}
group by pp.plan_unique,p.product_id,pp.wastage,p.product_code,p.product_name,oie.quantity_ordered,s.stage_name,p.sku_id,pd.plan_quantity,ppp.planned_quantity,pp.planed_quantity,pp.production_plan_id,
u.id,
u.uom,
cp.order_unique
        limit :limit offset :offset
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,ccode=ccode,
                                                         product_id=request.args.get('product_id'),
                                                         end_date=end_date,
                                                         limit=results_per_page,
                                                         offset=offset,
                                                         production_plan_id=request.args.get('production_plan_id'),
                                                         start_date=request.args.get('start_date'),
                                                         status=request.args.get('status'),
                                                         ))
        sql_count=text(f'''
        select count(1) from (
            SELECT pp.production_plan_id
            FROM production_plan pp
            LEFT JOIN plan_details as pd on pp.production_plan_id = pd.production_plan_id
            LEFT JOIN order_items_extract as oie on oie.extract_id = pd.order_extract_id
            LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id AND pd.plan_details_id IS NULL AND ppp.deleted IS NOT TRUE
            JOIN products p ON p.product_id = COALESCE(oie.product_id, ppp.product_id, pp.product_id) 
            where pp.deleted is not true and pp.compcode=:ccode {sql_con}
            GROUP BY pp.production_plan_id, p.product_id
        ) sub
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,ccode=ccode,
                                                         end_date=end_date,
                                                         limit=results_per_page,
                                                         production_plan_id=request.args.get('production_plan_id'),
                                                         offset=offset,
                                                         product_id=request.args.get('product_id'),
                                                         start_date=request.args.get('start_date'),
                                                         status=request.args.get('status'),

                                                         ))
        return {
            'total_results': sql_count[0].get('count',0) if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }
@orderReportsAPIRoutes.route('/Delivery-report')
class DelievryReport(Resource):
    @login_required()
    @orderReportsAPIRoutes.marshal_with(delivery_model_list_response)
    @orderReportsAPIRoutes.doc(params={**list_api_params,**search_filters,**deleivery_filters})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        end_date = request.args.get('start_date') if not request.args.get('end_date') else request.args.get('end_date')
        sql_con = ''
        if request.args.get('customer_purchase_id'):
            sql_con += ' and cp.customer_purchase_id=:customer_purchase_id '
        if request.args.get('status'):
            sql_con += ' and cp.status=:status '
        if request.args.get('start_date'):
            sql_con += ' and d.delivery_date::date>=cast(:start_date as date) '
        if end_date:
            sql_con += ' and d.delivery_date::date<=cast(:end_date as date) '
        if request.args.get('deliveryid'):
            sql_con+=' and d.deliveryid=:deliveryid '
        if request.args.get('customer_id'):
            sql_con+=' and v.vendorid=:customer_id '
        if request.args.get('product_id'):
            sql_con+=' and p.product_id=:product_id '
        sql_query = text(f'''
                	select d.deliveryno,d.delivery_date,d.driver_name,d.driver_number,d.vehicle_number,
                	cp.order_unique,cp.customer_purchase_id,count(cpi.*) as number_of_products,
                    v.companyname as customer_name,
                    to_char(d.created_on, 'YYYY-MM-DD HH24:MI:SS') as created_on,
                    jsonb_agg(json_build_object(
                    'product_code',p.product_code,
                    'product_name',p.product_name,
                    'sku_id',p.sku_id,
                    'delivered_qty',dli.quantity,
                    'quantity_ordered', cpi.quantity_ordered,
                    'serial_numbers', (select coalesce(json_agg(serial_number), '[]'::json) from delivery_serialized_items where delivery_line_item_id = dli.id and deleted is not true),
                    'rejected_qty', dli.rejected_quantity,
                    'is_rejected', dli.is_rejected,
                    'rejection_action', dli.rejection_action,
                    'rejection_store_id', dli.rejection_store_id,
                    'rejection_store_name', (select store_name from store_location where store_id = dli.rejection_store_id)
                    )) as products
                    from delivery as d
                    
                    join delivery_line_items dli on dli.deliveryid =d.deliveryid 
                    join customer_purchase_items cpi on cpi.items_id =dli."workOrderLineId" 
                    join customer_purchase cp on cp.customer_purchase_id =cpi.customer_purchase_id 
                    left join vendor v on v.vendorid = COALESCE(cp.customer_id, d.customerid) 
                    join products p on p.product_id =cpi.product_id 
                    where d.deleted is not true and d.compcode=:ccode {sql_con}
                    group by  d.deliveryno,d.delivery_date,d.driver_name,d.driver_number,d.vehicle_number,
                    v.companyname,cp.order_unique,cp.customer_purchase_id,d.created_on
                    order by d.deliveryno desc
                limit :limit offset :offset
                ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           ccode=ccode,
                                                           customer_id=request.args.get('customer_id'),
                                                           end_date=end_date,
                                                           limit=results_per_page,
                                                           product_id=request.args.get('product_id'),
                                                           offset=offset,
                                                           deliveryid=request.args.get('deliveryid'),
                                                           customer_purchase_id=request.args.get(
                                                               'customer_purchase_id'),
                                                           start_date=request.args.get('start_date'),
                                                           status=request.args.get('status'),
                                                           ))
        sql_count = text(f'''
                select count(distinct d.deliveryid)
                     from delivery as d
                    join delivery_line_items dli on dli.deliveryid =d.deliveryid 
                    join customer_purchase_items cpi on cpi.items_id =dli."workOrderLineId" 
                    join customer_purchase cp on cp.customer_purchase_id =cpi.customer_purchase_id 
                    left join vendor v on v.vendorid = COALESCE(cp.customer_id, d.customerid) 
                    join products p on p.product_id =cpi.product_id 
                    where d.deleted is not true and d.compcode=:ccode {sql_con}
                ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count, ccode=ccode,
                                                           customer_id=request.args.get('customer_id'),
                                                           end_date=end_date,
                                                           deliveryid=request.args.get('deliveryid'),
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           product_id=request.args.get('product_id'),
                                                           customer_purchase_id=request.args.get(
                                                               'customer_purchase_id'),
                                                           start_date=request.args.get('start_date'),
                                                           status=request.args.get('status'),
                                                           ))
        return {
            'total_results': sql_count[0].get('count', 0) if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }


@orderReportsAPIRoutes.route('/order_production_report')
class OrderPlanRepoert(Resource):

    @orderReportsAPIRoutes.marshal_with(report_order_list_response)
    @orderReportsAPIRoutes.doc(params=report_filter)
    @login_required()
    def get(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page

        customer_id = request.args.get('customer_id', None)
        customer_purchase_id = request.args.get('customer_purchase_id', None)
        product_id = request.args.get('product_id', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        sql_con = ''
        if customer_id:
            sql_con += ' and cp.customer_id=:customer_id '
        if customer_purchase_id:
            sql_con += ' and cp.customer_purchase_id=:customer_purchase_id '
        if start_date:
            sql_con += ' and cp.created_on::date between :start_date '
            if end_date:
                sql_con += ' and :end_date '
            else:
                sql_con += ' and :start_date '
        if product_id:
            sql_con += ' and fj.product_id=:product_id '

        query = text(f'''
			with  final_json as(
			with cte as(
                    with cte1 as( 
                    select distinct on(ps.product_id) ps.product_id,ps.rank_id,ps.stage_id,asm.config_id from production_stages as ps
                    left join activity_stage_map as asm on ps.id = asm.production_stage_id and asm.is_final_process is true and asm.deleted is not true
                    where ps.deleted is not true
                    order by ps.product_id, ps.rank_id desc
                    ) 
                    select pp.production_plan_id,COALESCE(ppp.product_id, pp.product_id) as product_id,pp.plan_unique,COALESCE(ppp.planned_quantity, pp.planed_quantity) as planed_quantity,COALESCE(ppp.wastage, pp.wastage) as allowed_was,sum(el.wastage) as act_wastage,sum(el.outward_qty) as out_qua
                    from production_plan as pp
                    LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
                    left join cte1 on cte1.product_id = COALESCE(ppp.product_id, pp.product_id)
                    left join plan_targets as pt on pt.production_plan_id = pp.production_plan_id and pt.deleted is not true AND coalesce(pt.product_id, pp.product_id) = COALESCE(ppp.product_id, pp.product_id)
                    left join execution_log as el on el.target_id = pt.plan_target_id and el.deleted is not true and el.stage_id = cte1.stage_id and (cte1.config_id is null or el.process_id is null or el.process_id = cte1.config_id)
                    where pp.deleted is not true and pp.compcode = :compcode and COALESCE(pp.status, '') <> 'Rejected'
                    group by pp.production_plan_id,pp.plan_unique,COALESCE(ppp.product_id, pp.product_id),COALESCE(ppp.wastage, pp.wastage),COALESCE(ppp.planned_quantity, pp.planed_quantity)
                    )
                    select 
                    cp.customer_purchase_id,oie.product_id,p2.product_code,p2.sku_id,oie.quantity_ordered,
					sum(pd.plan_quantity) as planed_quantity,
					sum(cte.out_qua) as out_ward,
                    json_agg(
                    json_build_object(
                    'product_id', cte.product_id,
                    'product_name', p.product_code,
                    'production_plan_id', cte.production_plan_id,
                    'plan_unique', cte.plan_unique,
                    'plan_quantity', coalesce(pd.plan_quantity, cte.planed_quantity),
                    'allowed_wastage', cte.allowed_was,
                    'actual_wastage', cte.act_wastage,
                    'outward_quantity', cte.out_qua
                    )
                    ) as data
                    from customer_purchase as cp 
                    left join customer_purchase_items as cpi on cpi.customer_purchase_id = cp.customer_purchase_id and cpi.deleted is not true
                    left join order_items_extract as oie on cpi.items_id = oie.order_items_id and oie.deleted is not true
                    left join plan_details as pd on pd.order_extract_id = oie.extract_id and pd.deleted is not true
                    left join cte on cte.production_plan_id = pd.production_plan_id and cte.product_id = oie.product_id
                    left join products as p on cte.product_id = p.product_id
                    left join products as p2 on p2.product_id = oie.product_id
                    where cp.compcode = :compcode and cp.deleted is not true
                    group by cp.customer_purchase_id,oie.product_id,p2.product_code,p2.sku_id,oie.quantity_ordered
				)
				select cp.customer_purchase_id,
				cp.order_unique,
				cp.customer_id,
				v.companyname,
				cp.order_date,
				cp.expected_receiving_date,
				json_agg(
				json_build_object(
				'product_id', fj.product_id,
					'product_code', fj.product_code,
					'sku_id', fj.sku_id,
					'quantity_ordered', fj.quantity_ordered,
					'planed_quantity', fj.planed_quantity,
					'outward_quantity', fj.out_ward,
					'plan_details', fj.data
				)
				) as product_details,
				count(*) over() as total_results
				from final_json as fj
				left join customer_purchase as cp on fj.customer_purchase_id = cp.customer_purchase_id
				left join vendor as v on v.vendorid = cp.customer_id
                where cp.compcode =:compcode and cp.deleted is not true {sql_con}
				group by cp.customer_purchase_id,
				cp.order_unique, cp.customer_id, v.companyname, cp.order_date, cp.expected_receiving_date
                order by cp.customer_purchase_id desc
                limit :limit offset :offset
        ''')

        result = query_to_dict(
            db_client.engine.execute(query,
                                     compcode=compcode,
                                     limit=results_per_page,
                                     offset=offset,
                                     start_date=start_date,
                                     end_date=end_date,
                                     customer_id=customer_id,
                                     customer_purchase_id=customer_purchase_id,
                                     product_id=product_id)
        )

        return {
            'total_results': result[0].get('total_results', 0) if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }


@orderReportsAPIRoutes.route('/order_plan_produced_report')
class OrderPlanProducedReport(Resource):

    @login_required()
    @orderReportsAPIRoutes.marshal_with(report_order_plan_list_response)
    @orderReportsAPIRoutes.doc(params=report_filter)
    def get(self):

        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        product_id = request.args.get('product_id', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', start_date)
        customer_purchase_id = request.args.get('customer_purchase_id', None)

        sql_con = ''

        if product_id:
            sql_con += ' and p.product_id=:product_id '

        if customer_purchase_id:
            sql_con += ' and cp.customer_purchase_id=:customer_purchase_id '

        if start_date:
            sql_con += ' and cp.order_date::date between :start_date and :end_date '

        query = text(f'''
        with final_process as (
            select distinct on(ps.product_id) ps.product_id, ps.rank_id, ps.stage_id, asm.config_id
            from production_stages as ps
            left join activity_stage_map as asm on ps.id = asm.production_stage_id and asm.is_final_process is true and asm.deleted is not true
            where ps.deleted is not true
            order by ps.product_id, ps.rank_id desc
        ),
        plan_produced as (
            select pt.production_plan_id,
                   coalesce(pt.product_id, pp.product_id) as product_id,
                   sum(el.outward_qty) as produced
            from plan_targets pt
            join production_plan pp on pp.production_plan_id = pt.production_plan_id and pp.deleted is not true and pp.compcode = :ccode
            join final_process fp on fp.product_id = coalesce(pt.product_id, pp.product_id)
            join execution_log el on el.target_id = pt.plan_target_id
                and el.deleted is not true
                and el.stage_id = fp.stage_id
                and (fp.config_id is null or el.process_id is null or el.process_id = fp.config_id)
            where pt.deleted is not true
            group by pt.production_plan_id, coalesce(pt.product_id, pp.product_id)
        ),
        cte1 as(
        select p.product_id,p.sku_id,p.product_code,p.product_name,cp.customer_purchase_id,cp.order_date,cp.order_unique,
        oie.quantity_ordered,coalesce(sum(pd.plan_quantity), 0) as planed,coalesce(sum(pprod.produced), 0) as produced 
        from customer_purchase as cp
        left join customer_purchase_items as cpi on cpi.customer_purchase_id =cp.customer_purchase_id and cpi.deleted is not true
        left join order_items_extract as oie on cpi.items_id = oie.order_items_id and oie.deleted is not true
        left join products as p on p.product_id = oie.product_id
        left join plan_details as pd on oie.extract_id = pd.order_extract_id and pd.deleted is not true
        left join production_plan pp on pp.production_plan_id = pd.production_plan_id and pp.deleted is not true and coalesce(pp.status, '') <> 'Rejected'
        left join plan_produced pprod on pprod.production_plan_id = pp.production_plan_id and pprod.product_id = oie.product_id
        where cp.deleted is not true and cp.compcode=:ccode {sql_con}
        group by p.product_id,p.sku_id,p.product_code,p.product_name,cp.customer_purchase_id,
        cp.order_date,cp.order_unique,oie.quantity_ordered
        )
        select cte1.product_id,cte1.sku_id,cte1.product_code,cte1.product_name,
        json_agg(
        json_build_object(
        'customer_purchase_id', cte1.customer_purchase_id,
            'order_date', cte1.order_date,
            'order_unique', cte1.order_unique,
            'ordered_quantity', cte1.quantity_ordered,
            'planed', cte1.planed,
            'produced', cte1.produced
        )
        ) as data,
        count(*) over() as total_results
        from cte1
        group by 
        cte1.product_id,cte1.sku_id,cte1.product_code,cte1.product_name
        limit :limit offset :offset
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                         ccode=compcode,
                                                         limit=results_per_page,
                                                         offset=offset,
                                                        product_id=product_id,
                                                        customer_purchase_id=customer_purchase_id,
                                                        start_date=start_date,
                                                        end_date=end_date)
        )

        return {
            'total_results': result[0].get('total_results', 0) if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }

@orderReportsAPIRoutes.route('/material-production-report')
class MaterialProductionReportAPI(Resource):
    @login_required()
    @orderReportsAPIRoutes.doc(params={**list_api_params, **materialProductionFilter})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get('results_per_page') else 20
        offset = (paged - 1) * results_per_page
        
        sql_con = ''
        if request.args.get('product_id'):
            sql_con += ' and COALESCE(ppp.product_id, pp.product_id)=:product_id '
        if request.args.get('production_plan_id'):
            sql_con += ' and pp.production_plan_id=:production_plan_id '
        end_date = request.args.get('end_date') if request.args.get('end_date') else request.args.get('start_date')
        if request.args.get('start_date'):
            sql_con += ' and pp.plan_date::date >=cast(:start_date as date) '
            if end_date:
                sql_con += ' and pp.plan_date::date <=cast(:end_date as date) '
                
        sql_query = text(f'''
        with latest_bom as (
            select distinct on (b.product_id) b.bom_id, b.product_id
            from bom b
            where b.deleted is not true
            order by b.product_id, b.bom_id desc
        ),
        bom_comp_agg as (
            select bc.bom_id, bc.product_id, sum(bc.quantity::numeric) as quantity
            from bom_component bc
            where bc.deleted is not true
            group by bc.bom_id, bc.product_id
        ),
        inv_agg as (
            select
                i.prod_plan_id,
                i.product_id,
                sum(i.approved_amount) as approved_amount,
                sum(coalesce(d_sub.dispatched_qty, 0)) as dispatched_qty,
                string_agg(distinct i.ref_id, ', ') as request_id,
                to_char(max(i.created_on), 'DD-MM-YYYY') as dispatched_date,
                to_char(max(i.created_on), 'HH12:MI:SS AM') as dispatched_time,
                string_agg(distinct i.created_by, ', ') as dispatched_by
            from invregistry i
            left join (
                select releseid, sum(dispatch_amount) as dispatched_qty
                from dispatch
                where deleted is not true
                group by releseid
            ) d_sub on d_sub.releseid = i.releseid
            where i.deleted is not true and i.status = 'Approved' and i.action = 'Outward'
            group by i.prod_plan_id, i.product_id
        ),
        raw_materials as (
            SELECT
                pp.production_plan_id,
                pp.plan_unique,
                COALESCE(ppp.product_id, pp.product_id) as final_product_id,
                COALESCE(ppp.planned_quantity, pp.planed_quantity)::numeric as planned_quantity,
                b.bom_id,
                bc.product_id as raw_material_id,
                p_rm.product_code as rm_code,
                p_rm.product_name as rm_name,
                p_rm.sku_id as rm_sku,
                u_rm.uom as rm_uom,
                bc.quantity::numeric as bom_quantity,
                i.approved_amount,
                i.dispatched_qty,
                i.request_id,
                i.dispatched_date,
                i.dispatched_time,
                i.dispatched_by
            FROM production_plan pp
            LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
            JOIN latest_bom b ON b.product_id = COALESCE(ppp.product_id, pp.product_id)
            JOIN bom_comp_agg bc ON bc.bom_id = b.bom_id
            JOIN products p_rm ON p_rm.product_id = bc.product_id
            LEFT JOIN uom u_rm ON u_rm.id = p_rm.uom_id
            LEFT JOIN inv_agg i ON i.prod_plan_id = pp.production_plan_id AND i.product_id = bc.product_id
            WHERE pp.deleted is not true and pp.status = 'Approved' and pp.compcode=:ccode {sql_con}
        ),
        final_process as (
            select distinct on(ps.product_id) ps.product_id, ps.rank_id, ps.stage_id, asm.config_id 
            from production_stages as ps
            left join activity_stage_map as asm on ps.id = asm.production_stage_id and asm.is_final_process is true and asm.deleted is not true
            where ps.deleted is not true
            order by ps.product_id, ps.rank_id desc
        ),
        order_details as (
            select pd.production_plan_id, string_agg(distinct cp.order_unique, ', ') as order_number
            from plan_details pd
            join order_items_extract oie on oie.extract_id = pd.order_extract_id
            join customer_purchase_items cpi on cpi.items_id = oie.order_items_id
            join customer_purchase cp on cp.customer_purchase_id = cpi.customer_purchase_id
            where pd.deleted is not true
            group by pd.production_plan_id
        ),
        actual_production as (
            SELECT 
                pt.production_plan_id, 
                coalesce(pt.product_id, pp.product_id) as product_id, 
                sum(el.outward_qty) as actual_produced,
                to_char(max(el.opertaion_start_date), 'DD-MM-YYYY HH12:MI:SS AM') as last_execution_date
            FROM plan_targets pt
            JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id AND pp.deleted IS NOT TRUE AND pp.compcode = :ccode
            JOIN execution_log el ON el.target_id = pt.plan_target_id AND el.deleted IS NOT TRUE
            JOIN final_process fp ON fp.product_id = coalesce(pt.product_id, pp.product_id)
            WHERE pt.deleted IS NOT TRUE AND el.stage_id = fp.stage_id and (fp.config_id is null or el.process_id is null or el.process_id = fp.config_id)
            GROUP BY pt.production_plan_id, coalesce(pt.product_id, pp.product_id)
        ),
        grouped_materials as (
            SELECT 
                rm.production_plan_id,
                rm.plan_unique,
                rm.final_product_id,
                rm.planned_quantity,
                json_agg(json_build_object(
                    'raw_material_id', rm.raw_material_id,
                    'rm_code', rm.rm_code,
                    'rm_name', rm.rm_name,
                    'rm_sku', rm.rm_sku,
                    'rm_uom', rm.rm_uom,
                    'bom_quantity', rm.bom_quantity,
                    'required_qty', (rm.bom_quantity * rm.planned_quantity),
                    'approved_amount', rm.approved_amount,
                    'dispatched_qty', coalesce(rm.dispatched_qty, 0),
                    'request_id', rm.request_id,
                    'dispatched_date', rm.dispatched_date,
                    'dispatched_time', rm.dispatched_time,
                    'dispatched_by', rm.dispatched_by,
                    'theoretical_production', case when rm.bom_quantity > 0 then coalesce(rm.dispatched_qty, 0) / rm.bom_quantity else 0 end
                )) as materials_list,
                string_agg(distinct rm.dispatched_by, ', ') as dispatched_by
            FROM raw_materials rm
            GROUP BY rm.production_plan_id, rm.plan_unique, rm.final_product_id, rm.planned_quantity
        )
        SELECT 
            gm.production_plan_id,
            gm.plan_unique,
            od.order_number,
            fp.product_id as fp_id,
            fp.product_code as fp_code,
            fp.product_name as fp_name,
            fp.sku_id as fp_sku,
            gm.planned_quantity::float,
            coalesce(ap.actual_produced, 0)::float as actual_produced,
            gm.dispatched_by,
            ap.last_execution_date,
            gm.materials_list as data,
            count(*) over() as total_results
        FROM grouped_materials gm
        JOIN products fp ON fp.product_id = gm.final_product_id
        LEFT JOIN actual_production ap ON ap.production_plan_id = gm.production_plan_id AND ap.product_id = gm.final_product_id
        LEFT JOIN order_details od ON od.production_plan_id = gm.production_plan_id
        ORDER BY gm.production_plan_id DESC, gm.final_product_id
        LIMIT :limit OFFSET :offset
        ''')
        
        result = query_to_dict(
            db_client.engine.execute(sql_query,
                                     ccode=ccode,
                                     limit=results_per_page,
                                     offset=offset,
                                     product_id=request.args.get('product_id'),
                                     production_plan_id=request.args.get('production_plan_id'),
                                     start_date=request.args.get('start_date'),
                                     end_date=end_date)
        )
        
        return {
            'total_results': result[0].get('total_results', 0) if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }

from .lifecycle_report import OrderLifecycleReport