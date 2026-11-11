import datetime
from pprint import pprint

from flask import request
from flask_restx import Resource
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text
from ipss_utils.decorators import login_required

# from rank.app.api_doc import list_api_params
from ipss_utils.ipss_api_doc import list_api_params

# from order_reports.app.routes.rm_purchase import orderReportsAPIRoutes
# from ..routes.rm_purchase import orderServicesAPIRoutes
from .. import db_client
from ..api_doc import search_filters, all_plan_filters, material_filter, exec_prev_filtes
from ..routes.rm_purchase import orderServicesAPIRoutes, total_product_response, order_based_products_response, \
    overAllOrderModelResponse, orderBasedReportOrderModelResponse, porductBasedReportResponse, over_all_prod_model_list, \
    material_list_response, exe_nexted_prev_model, stage_wise_production_response


@orderServicesAPIRoutes.route('/execution_previous_stage_services')

class ExecutionMap(Resource):
    @login_required()
    @orderServicesAPIRoutes.marshal_with(exe_nexted_prev_model)
    @orderServicesAPIRoutes.doc(params={**exec_prev_filtes,**list_api_params})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con=''

        plan_target_id = request.args.get('plan_target_id')
        if plan_target_id == 'undefined' or plan_target_id == 'null' or not plan_target_id:
            plan_target_id = None
        else:
            try:
                plan_target_id = int(plan_target_id)
            except ValueError:
                plan_target_id = None

        stage_id = request.args.get('stage_id')
        if stage_id == 'undefined' or stage_id == 'null' or not stage_id:
            stage_id = None
        else:
            try:
                stage_id = int(stage_id)
            except ValueError:
                stage_id = None
        sql_query=text('''
        select ps.id AS production_stage_id, 
       ps.rank_id, 
       ps.product_id, 
       s.stage_id, 
       s.stage_name, 
       SUM(el.outward_qty) AS outward_qty, 
       el.process_id, 
       pc.process_name,
        count(*) over() as full_count
        from execution_log el 
        join stage s on s.stage_id =el.stage_id 
        left join process_config pc on pc.process_id =el.process_id 
        join plan_targets pt on pt.plan_target_id =el.target_id and pt.deleted is not true
        join production_plan pp on pp.production_plan_id =pt.production_plan_id and pp.deleted is not true
        JOIN plan_targets pt2 ON pp.production_plan_id = pt2.production_plan_id 
                                      AND pt2.plan_target_id = :plan_target_id and pt2.deleted is not true
                                      AND coalesce(el.product_id, pt.product_id, pp.product_id) = coalesce(pt2.product_id, pp.product_id)
        join production_stages ps on ps.stage_id =el.stage_id and ps.product_id = coalesce(el.product_id, pt.product_id, pp.product_id)
                                                                            and ps.deleted is not true
                                                                            and ps.rank_id =(SELECT ps1.rank_id - 1
                                                                            FROM production_stages ps1
                                                                            WHERE ps1.deleted IS NOT TRUE
                                                                              AND ps1.product_id = ps.product_id
                                                                              AND ps1.stage_id = :stage_id
                                                                            LIMIT 1 )
        left join activity_stage_map asm on asm.production_stage_id=ps.id and asm.config_id=el.process_id and asm.deleted is not true
        where el.deleted is not true and (asm.is_final_process is true or el.process_id is null)
        group by ps.id, ps.rank_id, 
               ps.product_id, 
               s.stage_id, 
               s.stage_name,el.process_id, 
               pc.process_name
        limit :limit offset :offset
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,limit=results_per_page,
                                                         plan_target_id=plan_target_id,
                                                         offset=offset,
                                                         stage_id=stage_id))
        # sql_count=text(f'''
        #         select count(distinct ps.id) from production_stages ps
        #         join stage s on s.stage_id =ps.stage_id
        #         join execution_log el on el.stage_id =s.stage_id
        #         join production_plan pp on pp.product_id =ps.product_id
        #         join plan_targets pt on pt.production_plan_id =pp.production_plan_id and pt.plan_target_id =el.target_id --and pt.plan_target_id =2478
        #         join activity_stage_map asm on asm.production_stage_id =ps.id and asm.is_final_process =true
        #         join process_config pc on pc.process_id =asm.config_id and asm.production_stage_id =ps.id
        #         where ps.rank_id =(SELECT rank_id - 1
        #             FROM production_stages
        #             WHERE stage_id = :stage_id AND product_id = ps.product_id and deleted is not true)
        #             {sql_con}
        # ''')
        # sql_count = query_to_dict(db_client.engine.execute(sql_count, limit=results_per_page,
        #                                                    plan_target_id=plan_target_id,
        #                                                    offset=offset,
        #                                                    stage_id=stage_id,
        #                                                    ccode=ccode))
        currenyt_stage=text('''
                                select sum(el.outward_qty) current_stage_outward from execution_log el 
                                join plan_targets pt on pt.plan_target_id =el.target_id 
                                join production_plan pp on pp.production_plan_id =pt.production_plan_id and pt.production_plan_id =(
                                select pt2.production_plan_id from plan_targets pt2 
                                where pt2.plan_target_id =:plan_target_id and pt2.deleted is not true
                                )
                                join production_stages ps on ps.stage_id =el.stage_id and ps.product_id =coalesce(el.product_id, pt.product_id, pp.product_id) and ps.deleted is not true and coalesce(el.product_id, pt.product_id, pp.product_id) = (select coalesce(pt3.product_id, pp.product_id) from plan_targets pt3 where pt3.plan_target_id = :plan_target_id and pt3.deleted is not true)
                                left join activity_stage_map asm on asm.production_stage_id =ps.id and asm.config_id =el.process_id and asm.deleted is not true 
                                where el.deleted is not true and pt.deleted is not true and pp.deleted is not true and (asm.is_final_process is true or el.process_id is null) and el.stage_id =:stage_id
                                -- group by pt.plan_target_id
        ''')
        currenyt_stage=query_to_dict(db_client.engine.execute(currenyt_stage,stage_id=stage_id,
                                     plan_target_id=plan_target_id))
        for i in sql_query:
            i['current_stage_outward']=currenyt_stage[0].get('current_stage_outward') if currenyt_stage else 0
        else:
            sql_query.append({"current_stage_outward":currenyt_stage[0].get('current_stage_outward') if currenyt_stage else 0})

        # pprint(sql_query)

        return {
            'total_results': sql_query[0].get('full_count') if sql_query else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'data': sql_query
        }


@orderServicesAPIRoutes.route('/product-combined')
class TotalProducts(Resource):
    @login_required()
    @orderServicesAPIRoutes.marshal_with(total_product_response)
    @orderServicesAPIRoutes.doc(params=search_filters)
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        sql_con = ''
        product_id = request.args.get('product_id')
        if product_id and product_id != 'null' and product_id != 'undefined':
            sql_con += ' and oie.product_id=:product_id '
        else:
            product_id = None
        customer_purchase_id = request.args.get('customer_purchase_id')
        if customer_purchase_id and customer_purchase_id != 'null' and customer_purchase_id != 'undefined':
            sql_con += ' and cp.customer_purchase_id=:customer_purchase_id '
        else:
            customer_purchase_id = None
        product_group_id = request.args.get('product_group_id')
        if product_group_id and product_group_id != 'null' and product_group_id != 'undefined':
            sql_con += ' and p2.product_group_id=:product_group_id '
        else:
            product_group_id = None
        sql_query=text(f'''
        select oie.product_id as rawmaterialsid,sum(oie.quantity_ordered) quantity_ordered,sum(oie.quantity_planned) as quantity_planned,
        p.product_code as productcode,p.product_name as product_name
        from order_items_extract oie 
        join products p on p.product_id =oie.product_id 
        join customer_purchase_items cpi on cpi.items_id =oie.order_items_id 
        join products p2 on p2.product_id =cpi.product_id
        join customer_purchase cp on cp.customer_purchase_id =cpi.customer_purchase_id 
        where oie.quantity_ordered >coalesce (oie.quantity_planned,0) and 
        cp.deleted is not true and oie.deleted is not true and cpi.deleted is not true and 
        cpi.quantity_ordered > coalesce(cpi.quantity_delivered,0)  
        and cp.status<>'Delivered' and oie.compcode=:ccode {sql_con}
        group by oie.product_id,p.product_code,p.product_name
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,ccode=ccode,
                                                         product_group_id=product_group_id,
                                                         product_id=product_id,
                                                         customer_purchase_id=customer_purchase_id
                                                         ))

        return {"data":sql_query}

@orderServicesAPIRoutes.route('/product-individual-extract')
class OrderBasedProducts(Resource):
    @login_required()
    @orderServicesAPIRoutes.marshal_with(order_based_products_response)
    @orderServicesAPIRoutes.doc(params=search_filters)
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        sql_con=''
        product_id = request.args.get('product_id')
        if product_id and product_id != 'null' and product_id != 'undefined':
            sql_con+=' and oie.product_id=:product_id '
        else:
            product_id = None
        customer_purchase_id = request.args.get('customer_purchase_id')
        if customer_purchase_id and customer_purchase_id != 'null' and customer_purchase_id != 'undefined':
            sql_con += ' and cp.customer_purchase_id=:customer_purchase_id '
        else:
            customer_purchase_id = None
        sql_query=text(f'''
        select oie.extract_id,oie.product_id as rawmaterialsid,oie.quantity_ordered,oie.quantity_planned,
        cp.order_unique,cpi.items_id,
        p.product_code as productcode,p.product_name as product_name
        from order_items_extract oie 
        join products p on p.product_id =oie.product_id 
        join customer_purchase_items cpi on cpi.items_id =oie.order_items_id 
        join customer_purchase cp on cp.customer_purchase_id =cpi.customer_purchase_id 
        where oie.quantity_ordered >coalesce (oie.quantity_planned,0) and 
        cp.deleted is not true and oie.deleted is not true and cpi.deleted is not true and 
        cpi.quantity_ordered > coalesce(cpi.quantity_delivered,0)  
        and cp.status<>'Delivered' and oie.compcode=:ccode {sql_con}
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,ccode=ccode,
                                                         product_id=product_id,
                                                         customer_purchase_id=customer_purchase_id
                                                         ))

        return {"data":sql_query}
@orderServicesAPIRoutes.route('/OverallOrders')
class OverAllOrders(Resource):
    @login_required()
    @orderServicesAPIRoutes.marshal_with(overAllOrderModelResponse)
    @orderServicesAPIRoutes.doc(params=search_filters)
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        sql_con = ''
        product_id = request.args.get('product_id')
        if product_id and product_id != 'null' and product_id != 'undefined':
            sql_con += ' and oie.product_id=:product_id '
        else:
            product_id = None
        customer_purchase_id = request.args.get('customer_purchase_id')
        if customer_purchase_id and customer_purchase_id != 'null' and customer_purchase_id != 'undefined':
            sql_con += ' and cp.customer_purchase_id=:customer_purchase_id '
        else:
            customer_purchase_id = None
        product_group_id = request.args.get('product_group_id')
        if product_group_id and product_group_id != 'null' and product_group_id != 'undefined':
            sql_con += ' and p2.product_group_id=:product_group_id '
        else:
            product_group_id = None
        sql_query=text(f'''
        select distinct on (cp.customer_purchase_id) cp.customer_purchase_id ,cp.order_unique,
        v.companyname, v.contactname
        from order_items_extract oie 
        join products p on p.product_id =oie.product_id 
        join customer_purchase_items cpi on cpi.items_id =oie.order_items_id 
        join customer_purchase cp on cp.customer_purchase_id =cpi.customer_purchase_id 
        left join vendor v on v.vendorid =cp.customer_id
        join products p2 on p2.product_id =cpi.product_id 
        where oie.quantity_ordered >coalesce (oie.quantity_planned,0) and 
        cp.deleted is not true and oie.deleted is not true and cpi.deleted is not true and 
        cpi.quantity_ordered > coalesce(cpi.quantity_delivered,0)  
        and cp.status<>'Delivered' and oie.compcode=:ccode {sql_con}
        order by cp.customer_purchase_id desc
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,ccode=ccode,
                                                         product_group_id=product_group_id,
                                                         product_id=product_id,
                                                         customer_purchase_id=customer_purchase_id
                                                         ))

        return {"data":sql_query}
@orderServicesAPIRoutes.route('/')
class OrderBasedReport(Resource):
    @login_required()
    @orderServicesAPIRoutes.marshal_with(orderBasedReportOrderModelResponse)
    @orderServicesAPIRoutes.doc(params={**search_filters,**list_api_params})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        # ccode = 1539147649705
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con = ''
        sql_con_1=''
        sql_con=''' and oie.quantity_ordered>COALESCE(oie.quantity_planned,0)
        '''
        sql_con_1=''' and cpi.quantity_ordered>COALESCE(cpi.quantity_delivered,0) and 
        cp.status<>'Delivered' '''
        if request.args.get('product_id'):
            sql_con+=' and oie.product_id=:product_id '
        if request.args.get('customer_purchase_id'):
            sql_con_1+=' and cp.customer_purchase_id=:customer_purchase_id '
        if request.args.get('product_group_id'):
            sql_con+=' and p2.product_group_id=:product_group_id '
        sql_query=text(f'''
        with cte1 as (with cte as (select p.product_id,sum(oie.quantity_ordered) as quantity_ordered,sum(oie.quantity_planned) quantity_planned,
        p.product_code,p.product_name,p.product_count,p.sku_id,b.bom_id,
        exists(select 1 from production_stages ps where ps.product_id=p.product_id and ps.deleted is not true) as production_stages,
        case when b.product_id is null then false else true end bom_config
        from order_items_extract as oie
        join customer_purchase_items cpi on cpi.items_id =oie.order_items_id 
        join products p2 on p2.product_id =cpi.product_id
        join products p on p.product_id =oie.product_id 
        -- left join production_stages ps on ps.product_id=p.product_id and ps.deleted is not true
        left join "bom" as b on b.product_id=p.product_id and b.deleted is not true
        where oie.deleted is not true and oie.compcode=:ccode {sql_con}
        group by p.product_id,p.product_code,p.product_count,b.product_id,p.product_name,p.sku_id,b.bom_id
        limit :limit offset :offset
        )
        
        select cte.*,
        jsonb_agg(json_build_object(
        'customer_purchase_id',cp.customer_purchase_id,
        'extract_id',oie.extract_id,
        'quantity_ordered',oie.quantity_ordered,
        'quantity_planned',oie.quantity_planned,
        'order_unique',cp.order_unique,
        'description',cpi.description
        )) as orders
        from cte
        join order_items_extract oie on oie.product_id =cte.product_id
                
        join customer_purchase_items cpi on cpi.items_id =oie.order_items_id 
        join products p2 on p2.product_id =cpi.product_id 
        join customer_purchase cp on cp.customer_purchase_id =cpi.customer_purchase_id 
        where oie.deleted is not true and oie.compcode=:ccode {sql_con_1} {sql_con}
        and cp.deleted is not true
        group by cte.product_id,cte.quantity_ordered,cte.sku_id,cte.bom_id,
        cte.quantity_planned,cte.product_code,cte.product_name,cte.product_count,cte.production_stages,cte.bom_config)
        select cte1.*,
        
        json_agg(json_build_object(
                'product_id',bc.product_id,
                'quantity',bc.quantity::numeric,
                'product_code',p.product_code,
                'product_name',p.product_name,
                'sku_id',p.sku_id,
                'product_count',p.product_count,
                'allocated_quantity',p.allocated_quantity
                )) as bom_sets 
         
        from cte1
        left join (select bc.bom_id, bc.product_id, sum(bc.quantity::numeric) as quantity from bom_component bc where bc.deleted is not true group by bc.bom_id, bc.product_id) bc on bc.bom_id=cte1.bom_id
        left join products p on p.product_id=bc.product_id 
        group by cte1.product_id,cte1.quantity_ordered,cte1.quantity_planned,
        cte1.product_code,cte1.product_name,cte1.product_count,
        cte1.production_stages,cte1.orders,cte1.sku_id,cte1.bom_id,
        cte1.bom_config
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,ccode=ccode,
                                                         customer_purchase_id=request.args.get('customer_purchase_id'),
                                                         product_id=request.args.get('product_id'),
                                                         limit=results_per_page,
                                                         product_group_id=request.args.get('product_group_id'),
                                                         offset=offset))
        sql_count=text(f'''
        select count(distinct cpi.product_id) from 
        order_items_extract oie
        join customer_purchase_items cpi on cpi.items_id =oie.order_items_id 
        join products p2 on p2.product_id =cpi.product_id 
        join customer_purchase cp on cp.customer_purchase_id =cpi.customer_purchase_id 
        where oie.deleted is not true and oie.compcode=:ccode {sql_con_1} {sql_con}
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,
                                                         ccode=ccode,
                                                         customer_purchase_id=request.args.get('customer_purchase_id'),
                                                         product_id=request.args.get('product_id'),
                                                         product_group_id=request.args.get('product_group_id'),
                                                         ))
        return {

            'total_results': sql_count[0].get('count') if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'data': sql_query
        }
@orderServicesAPIRoutes.route('/product_services')
class ProductServices(Resource):
    @login_required()
    @orderServicesAPIRoutes.marshal_with(porductBasedReportResponse)
    @orderServicesAPIRoutes.doc(params={**list_api_params,**search_filters})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con = ''
        sql_con_1 = ''
        sql_con = ''' and oie.quantity_ordered>COALESCE(oie.quantity_planned,0)
                '''
        sql_con_1 = ''' and cpi.quantity_ordered>COALESCE(cpi.quantity_delivered,0) and 
                cp.status<>'Delivered' '''
        if request.args.get('product_id'):
            sql_con += ' and oie.product_id=:product_id '
        if request.args.get('customer_purchase_id'):
            sql_con_1 += ' and cp.customer_purchase_id=:customer_purchase_id '
        if request.args.get('product_group_id'):
            sql_con_1 += ' and p2.product_group_id=:product_group_id '
        sql_query = text(f'''
                with cte as (
                select distinct on (oie.extract_id) oie.extract_id,oie.order_items_id,oie.product_id,oie.quantity_ordered,oie.quantity_planned,
                p.product_count,p.sku_id,b.bom_id,
                p.product_name ,p.product_code,u.uom,cp.order_date,cp.expected_receiving_date,cp.order_unique,cp.order_type,
                cpi.description,
                exists(select 1 from production_stages ps where ps.product_id=p.product_id and ps.deleted is not true) as production_stages,
                case when b.product_id is null then false else true end bom_config
                from order_items_extract oie
                join customer_purchase_items cpi on cpi.items_id =oie.order_items_id 
                join products p2 on p2.product_id =cpi.product_id
                join products p on p.product_id =oie.product_id 
                -- left join production_stages ps on ps.product_id=p.product_id and ps.deleted is not true
                left join "bom" as b on b.product_id=p.product_id and b.deleted is not true
                left join uom as u on u.id = p.uom_id
                left join (
                    select cil.cpo_item_id, json_agg(json_build_object('id', cil.id, 'lot_number', cil.lot_number, 'lot_qty', cil.lot_qty)) as lot_breakdown
                    from cpo_item_lots cil
                    where cil.deleted is not true and (cast(cil.compcode as varchar) = cast(:ccode as varchar) or cil.compcode is null)
                    group by cil.cpo_item_id
                ) lots on lots.cpo_item_id = cpi.items_id
                where oie.deleted is not true and oie.compcode=:ccode and
                cpi.deleted is not true and cp.deleted is not true
                {sql_con}{sql_con_1})
                select cte.*,
                lots_agg.lot_breakdown,
                json_agg(json_build_object(
                'product_id',bc.product_id,
                'quantity',bc.quantity::numeric,-- * cte.quantity_ordered,
                'product_code',p.product_code,
                'product_name',p.product_name,
                'sku_id',p.sku_id,
                'product_count',p.product_count,
                'uom', u.uom,
                'allocated_quantity',p.allocated_quantity
                )) as bom_sets
                from cte
                left join (
                    select cil.cpo_item_id, json_agg(json_build_object('id', cil.id, 'lot_number', cil.lot_number, 'lot_qty', cil.lot_qty)) as lot_breakdown
                    from cpo_item_lots cil
                    where cil.deleted is not true and (cast(cil.compcode as varchar) = cast(:ccode as varchar) or cil.compcode is null)
                    group by cil.cpo_item_id
                ) lots_agg on lots_agg.cpo_item_id = cte.order_items_id
                left join "bom" b on b.product_id=cte.product_id and b.deleted is not true 
                left join bom_component bc on bc.bom_id=b.bom_id and bc.deleted is not true
                left join products p on p.product_id=bc.product_id 
                left join uom as u on u.id = p.uom_id
                group by cte.extract_id,cte.order_items_id,cte.product_id,cte.quantity_ordered,cte.quantity_planned,
                cte.sku_id,cte.bom_id,
                cte.product_name ,cte.product_code,cte.order_date,cte.expected_receiving_date,cte.order_unique,
                cte.order_type,
                cte.production_stages,
                cte.bom_config,cte.product_count,cte.uom,cte.description,lots_agg.lot_breakdown
                ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query, ccode=ccode,
                                                           product_id=request.args.get('product_id'),
                                                           customer_purchase_id=request.args.get(
                                                               'customer_purchase_id'),
                                                           product_group_id=request.args.get('product_group_id'),
                                                           limit=results_per_page,
                                                           offset=offset))
        sql_count = text(f'''
                select count(distinct cp.customer_purchase_id) from order_items_extract oie
                join customer_purchase_items cpi on cpi.items_id =oie.order_items_id 
        join products p2 on p2.product_id =cpi.product_id
                join products p on p.product_id =oie.product_id 
                -- left join production_stages ps on ps.product_id=p.product_id and ps.deleted is not true
                left join "bom" as b on b.product_id=p.product_id and b.deleted is not true
                --join customer_purchase_items cpi on cpi.items_id =oie.order_items_id 
                join customer_purchase cp on cp.customer_purchase_id =cpi.customer_purchase_id
                where oie.deleted is not true and oie.compcode=:ccode
                {sql_con}{sql_con_1}
                ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           ccode=ccode,
                                                           product_group_id=request.args.get('product_group_id'),

                                                           customer_purchase_id=request.args.get(
                                                               'customer_purchase_id'),
                                                           product_id=request.args.get('product_id'),
                                                           ))
        return {

            'total_results': sql_count[0].get('count') if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'data': sql_query
        }

@orderServicesAPIRoutes.route('/OverallPlan')
class OverAllPlan(Resource):
    @login_required()
    @orderServicesAPIRoutes.marshal_with(stage_wise_production_response)
    @orderServicesAPIRoutes.doc(params={**all_plan_filters,**list_api_params})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con=''
        val=''
        sql_con1=''
        if request.args.get('production_plan_id'):
            sql_con+=' and pp.production_plan_id=:production_plan_id '
        if request.args.get('product_id'):
            sql_con1+=' and COALESCE(pt.product_id, pp.product_id)=:product_id '
        # if request.args.get('plan_date'):
        #     sql_con+=' and pp.plan_date::date =cast(:plan_date as date) '
        if request.args.get('is_hourly'):
            val='and pt.is_hourly_target = :is_hourly '
        # if request.args.get('is_hourly')=='false':
        #     val='and pt.stage_id is null'
        # if request.args.get('production_plan_id'):
        #     sql_con+=' and pp.production_plan_id=:production_plan_id '
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date and not end_date:
            end_date = start_date

        if start_date:
                sql_con1+=' and el_date.target_date >=cast(:start_date as date) '
        if end_date:
                sql_con1+=' and el_date.target_date <=cast(:end_date as date) '

        # start_time = datetime.datetime.now()
        sql_query=text(f'''
        with pp as (select pp.production_plan_id,pp.product_id,pp.planed_quantity,pp.plan_unique,
        pp.wastage,pp.wastage_per
        from production_plan pp 
         where pp.deleted is not true and pp.compcode=:ccode and LOWER(pp.status) = 'approved'
         {sql_con}),
        el_date as (
         select pp.production_plan_id, pp.planed_quantity, pp.plan_unique, pp.wastage, pp.wastage_per,
         s.stage_id,s.stage_name,pt.target_quantity,pt.day_target,pt.plan_target_id,
         COALESCE(el.opertaion_start_date::date, pt.start_date::date) as target_date,
         el.outward_qty,pcc.process_name,
         ps.rank_id, COALESCE(pt.product_id, pp.product_id) as product_id, p.sku_id, p.product_code, p.product_name, p.product_count
         from pp
         join plan_targets pt on pt.production_plan_id =pp.production_plan_id {val}
         left join products p on p.product_id = COALESCE(pt.product_id, pp.product_id)
         left join stage as s on s.stage_id=coalesce (pt.stage_id,(SELECT stage_id 
         FROM production_stages
         WHERE product_id = COALESCE(pt.product_id, pp.product_id) and deleted is not true
         ORDER BY rank_id DESC
         LIMIT 1))  and s.deleted is not true
         left join production_stages ps on ps.product_id=COALESCE(pt.product_id, pp.product_id) and ps.deleted is not true and ps.stage_id=s.stage_id
         left join execution_log el on el.target_id =pt.plan_target_id 
         left join process_config pcc on pcc.process_id=COALESCE(pt.process_id,el.process_id)
         where pt.deleted is not true
        ),
        el as(
         select production_plan_id, planed_quantity, plan_unique, wastage, wastage_per,
         stage_id,stage_name,target_quantity,day_target,plan_target_id,target_date as start_date,
         avg(outward_qty) as achieved_quantity_per_hour,process_name,
         rank_id, product_id, sku_id, product_code, product_name, product_count,
         sum(outward_qty) as achieved_quantity_day 
         from el_date
         where 1=1 {sql_con1}
         group by production_plan_id,product_id,planed_quantity,
         wastage,wastage_per,sku_id,product_code,product_name,process_name,
         product_count,stage_name,stage_id,plan_target_id,
         target_quantity,target_date,day_target,plan_unique,rank_id
        ),
		plan_det as (
		select 
		el.production_plan_id,el.product_id,el.product_code,el.product_name,
		el.sku_id,el.plan_unique,el.planed_quantity,
		el.wastage,el.wastage_per,el.stage_id,el.stage_name,el.process_name,el.rank_id,
		sum(el.achieved_quantity_day) as produced,
		json_agg(
		json_build_object(
		'target_id', el.plan_target_id,
		'date', el.start_date,
		'day_target',el.day_target,
		'target_quantity', el.target_quantity,
		'achieved_quantity_day', el.achieved_quantity_day,
		'achieved_quantity_per_hour', el.achieved_quantity_per_hour
		) order by el.rank_id asc
		) as data
		from el
		where COALESCE(el.achieved_quantity_day, 0) > 0
		group by 
		el.production_plan_id,el.product_id,el.product_code,el.product_name,
		el.sku_id,el.plan_unique,el.planed_quantity,
		el.wastage,el.wastage_per,el.stage_id,el.stage_name,el.process_name,el.rank_id
		),
		product_det as (
		select product_id,product_code,product_name,
		sku_id,production_plan_id,plan_unique,planed_quantity,wastage,wastage_per,stage_id,stage_name,rank_id,
		json_agg(
		json_build_object(
		'process', process_name,
		'produced', produced,
		'data', data
		)
		) as data
		from plan_det
		group by product_id,product_code,product_name,
		sku_id,production_plan_id,plan_unique,planed_quantity,wastage,wastage_per,stage_id,stage_name,rank_id
		),
		plan_det2 as (
		select product_id,product_code,product_name,sku_id,production_plan_id,plan_unique,planed_quantity,wastage,wastage_per,
		json_agg(
		json_build_object(
		'stage_id', stage_id,
		'stage_name', stage_name,
		'rank_id', rank_id,
		'data', data
		) order by rank_id  asc
		) as data
		from product_det 
		group by product_id,product_code,product_name,sku_id,production_plan_id,plan_unique,planed_quantity,wastage,wastage_per
		)
		select product_id,product_code,product_name,sku_id,
		json_agg(
		json_build_object(
		'production_plan_id', production_plan_id,
		'plan_unique', plan_unique,
		'planed_quantity', planed_quantity,
		'wastage', wastage,
		'wastage_per', wastage_per,
		'data', data
		) order by production_plan_id asc
		) as data,
		count(*) over() as count
		from plan_det2 
		group by product_id,product_code,product_name,sku_id
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,ccode=ccode,
                                                         # is_hourly=request.args.get('is_hourly'),
                                                         end_date=end_date,
                                                         is_hourly=request.args.get('is_hourly'),
                                                         start_date=start_date,
                                                         product_id=request.args.get('product_id'),
                                                         production_plan_id=request.args.get('production_plan_id')
                                                         ))

        # print("Time taken for execution the query", (datetime.datetime.now() - start_time).total_seconds())
        return {
            'total_results': sql_query[0].get('count') if sql_query else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }

@orderServicesAPIRoutes.route('/packing/SetItems')
class TotalProducts(Resource):
    @login_required()
    @orderServicesAPIRoutes.marshal_with(total_product_response)
    @orderServicesAPIRoutes.doc(params=search_filters)
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        sql_con = ''
        if request.args.get('product_id'):
            sql_con += ' and cpi.product_id=:product_id '
        if request.args.get('customer_purchase_id'):
            sql_con += ' and cp.customer_purchase_id=:customer_purchase_id '
        if request.args.get('product_group_id'):
            sql_con += ' and p.product_group_id=:product_group_id '
        sql_query=text(f'''
        -- Main query to fetch customer purchase item details with packing plan quantity
SELECT 
    cpi.product_id AS rawmaterialsid,
    SUM(cpi.quantity_ordered) AS quantity_ordered,
    p.product_code AS productcode,
    p.product_name AS product_name,
    p.product_count,
    p.sku_id,
    COALESCE(temps.quantity_planned, 0) AS quantity_planned 
FROM  
    customer_purchase_items cpi
JOIN 
    products p ON p.product_id = cpi.product_id 
JOIN 
    customer_purchase cp ON cp.customer_purchase_id = cpi.customer_purchase_id  
LEFT JOIN LATERAL (
    -- Subquery to calculate planned quantity from packing plan for each product
    SELECT 
        SUM(pp2.quantity) AS quantity_planned,
        cpi2.product_id
    FROM 
        packing_plan pp2
    JOIN 
        customer_purchase_items cpi2 ON pp2.order_items_id = cpi2.items_id
    WHERE
        cpi2.product_id = cpi.product_id  -- Correlate with the outer query's product_id
    GROUP BY 
        cpi2.product_id
) temps ON TRUE  -- Return planned quantity for each product, or NULL if not found
WHERE 
    cp.deleted IS NOT TRUE  -- Ensure the customer purchase is not deleted
    AND cpi.deleted IS NOT TRUE  -- Ensure the purchase item is not deleted
    AND cpi.quantity_ordered > COALESCE(cpi.quantity_delivered, 0)  
    AND cp.status <> 'Delivered' {sql_con}
GROUP BY 
    cpi.product_id, p.product_code, p.product_name, temps.quantity_planned, p.product_count,p.sku_id;  

        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,ccode=ccode,
                                                         product_group_id=request.args.get('product_group_id'),
                                                         product_id=request.args.get('product_id'),
                                                         customer_purchase_id=request.args.get('customer_purchase_id')
                                                         ))

        return {"data":sql_query}
# @orderServicesAPIRoutes.route('/product_services')
# class ProductServices(Resource):
#     @login_required()
#     @orderServicesAPIRoutes.marshal_with(porductBasedReportResponse)
#     @orderServicesAPIRoutes.doc(params={**list_api_params,**search_filters})
#     def get(self):
#         current_user = request.args.get('current_user', {})
#         ccode = current_user.get('company_id')
#         paged = int(request.args.get('paged')) if request.args.get('paged') else 1
#         results_per_page = int(request.args.get('results_per_page')) if request.args.get(
#             'results_per_page') else 20
#         offset = (paged - 1) * results_per_page
#         sql_con = ''
#         sql_con_1 = ''
#         sql_con = ''' and oie.quantity_ordered>COALESCE(oie.quantity_planned,0)
#                 '''
#         sql_con_1 = ''' and cpi.quantity_ordered>COALESCE(cpi.quantity_delivered,0) and
#                 cp.status<>'Delivered' '''
#         if request.args.get('product_id'):
#             sql_con += ' and oie.product_id=:product_id '
#         if request.args.get('customer_purchase_id'):
#             sql_con_1 += ' and cp.customer_purchase_id=:customer_purchase_id '
#         if request.args.get('product_group_id'):
#             sql_con_1 += ' and p2.product_group_id=:product_group_id '
#         sql_query = text(f'''
#                 with cte as (select distinct on (oie.extract_id) oie.extract_id,oie.order_items_id,oie.product_id,oie.quantity_ordered,oie.quantity_planned,
#                 p.product_count,p.sku_id,
#                 p.product_name ,p.product_code,cp.order_date,cp.expected_receiving_date,cp.order_unique,cp.order_type,
#                 exists(select 1 from production_stages ps where ps.product_id=p.product_id and ps.deleted is not true) as production_stages,
#                 case when b.product_id is null then false else true end bom_config
#                 from order_items_extract oie
#                 join customer_purchase_items cpi on cpi.items_id =oie.order_items_id
#                 join products p2 on p2.product_id =cpi.product_id
#                 join products p on p.product_id =oie.product_id
#                 -- left join production_stages ps on ps.product_id=p.product_id and ps.deleted is not true
#                 left join "bom" as b on b.product_id=p.product_id and b.deleted is not true
#                 --join customer_purchase_items cpi on cpi.items_id =oie.order_items_id
#                 join customer_purchase cp on cp.customer_purchase_id =cpi.customer_purchase_id
#                 where oie.deleted is not true and oie.compcode=:ccode and
#                 cpi.deleted is not true and cp.deleted is not true
#                 {sql_con}{sql_con_1})
#                 select cte.*,
#                 json_agg(json_build_object(
#                 'product_id',bc.product_id,
#                 'quantity',bc.quantity::numeric * cte.quantity_ordered,
#                 'product_code',p.product_code,
#                 'product_name',p.product_name,
#                 'sku_id',p.sku_id,
#                 'product_count',p.product_count,
#                 'allocated_quantity',p.allocated_quantity
#                 )) as bom_sets
#                 from cte
#                 left join "bom" b on b.product_id=cte.product_id and b.deleted is not true
#                 left join (select bc.bom_id, bc.product_id, sum(bc.quantity::numeric) as quantity from bom_component bc where bc.deleted is not true group by bc.bom_id, bc.product_id) bc on bc.bom_id=b.bom_id
#                 left join products p on p.product_id=bc.product_id
#                 group by cte.extract_id,cte.order_items_id,cte.product_id,cte.quantity_ordered,cte.quantity_planned,
#                 cte.sku_id,
#                 cte.product_name ,cte.product_code,cte.order_date,cte.expected_receiving_date,cte.order_unique,
#                 cte.order_type,
#                 cte.production_stages,
#                 cte.bom_config,cte.product_count
#                 ''')
#         sql_query = query_to_dict(db_client.engine.execute(sql_query, ccode=ccode,
#                                                            product_id=request.args.get('product_id'),
#                                                            customer_purchase_id=request.args.get(
#                                                                'customer_purchase_id'),
#                                                            product_group_id=request.args.get('product_group_id'),
#                                                            limit=results_per_page,
#                                                            offset=offset))
#         sql_count = text(f'''
#                 select count(distinct cp.customer_purchase_id) from order_items_extract oie
#                 join customer_purchase_items cpi on cpi.items_id =oie.order_items_id
#         join products p2 on p2.product_id =cpi.product_id
#                 join products p on p.product_id =oie.product_id
#                 -- left join production_stages ps on ps.product_id=p.product_id and ps.deleted is not true
#                 left join "bom" as b on b.product_id=p.product_id and b.deleted is not true
#                 --join customer_purchase_items cpi on cpi.items_id =oie.order_items_id
#                 join customer_purchase cp on cp.customer_purchase_id =cpi.customer_purchase_id
#                 where oie.deleted is not true and oie.compcode=:ccode
#                 {sql_con}{sql_con_1}
#                 ''')
#         sql_count = query_to_dict(db_client.engine.execute(sql_count,
#                                                            ccode=ccode,
#                                                            product_group_id=request.args.get('product_group_id'),
#
#                                                            customer_purchase_id=request.args.get(
#                                                                'customer_purchase_id'),
#                                                            product_id=request.args.get('product_id'),
#                                                            ))
#         return {
#
#             'total_results': sql_count[0].get('count') if len(sql_count) else 0,
#             'page': paged,
#             'results_per_page': results_per_page,
#             'data': sql_query
#         }
@orderServicesAPIRoutes.route('/pack/product_services')
class ProductService(Resource):
    @login_required()
    @orderServicesAPIRoutes.marshal_with(porductBasedReportResponse)
    @orderServicesAPIRoutes.doc(params={**list_api_params,**search_filters})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con = ''
        sql_con_1 = ''
        # sql_con = ''' and oie.quantity_ordered>COALESCE(oie.quantity_planned,0)
        #         '''
        sql_con_1 = ''' and cpi.quantity_ordered>COALESCE(cpi.quantity_delivered,0) and 
                cp.status<>'Delivered' '''
        if request.args.get('product_id'):
            sql_con += ' and cpi.product_id=:product_id '
        if request.args.get('customer_purchase_id'):
            sql_con_1 += ' and cp.customer_purchase_id=:customer_purchase_id '
        if request.args.get('product_group_id'):
            sql_con_1 += ' and p.product_group_id=:product_group_id '
        sql_query = text(f'''
                select cpi.items_id order_items_id,cpi.product_id,cpi.quantity_ordered quantity_ordered,sum(pp.quantity) quantity_planned,
                p.product_count,p.sku_id,
                p.product_name ,p.product_code,cp.order_date,cp.expected_receiving_date,cp.order_unique,cp.order_type,cpi.description
                from customer_purchase_items cpi
                join products p on p.product_id =cpi.product_id
                join customer_purchase cp on cp.customer_purchase_id =cpi.customer_purchase_id
                left join packing_plan pp on pp.order_items_id=cpi.items_id
                where cpi.deleted is not true and cpi.compcode=:ccode 
                and
                cpi.deleted is not true and cp.deleted is not true
                {sql_con}{sql_con_1}
                group by cpi.items_id,cpi.product_id,cpi.quantity_ordered,
                p.product_count,p.sku_id,
                p.product_name ,p.product_code,cp.order_date,cp.expected_receiving_date,cp.order_unique,cp.order_type,cpi.description
               
                ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query, ccode=ccode,
                                                           product_id=request.args.get('product_id'),
                                                           customer_purchase_id=request.args.get(
                                                               'customer_purchase_id'),
                                                           product_group_id=request.args.get('product_group_id'),
                                                           limit=results_per_page,
                                                           offset=offset))
        sql_count = text(f'''
                select count(distinct cpi.items_id)
                from customer_purchase_items cpi
                join products p on p.product_id =cpi.product_id
                join customer_purchase cp on cp.customer_purchase_id =cpi.customer_purchase_id
                left join packing_plan pp on pp.order_items_id=cpi.items_id
                where cpi.deleted is not true --and cpi.compcode=:ccode 
                and
                cpi.deleted is not true and cp.deleted is not true
                {sql_con}{sql_con_1}
                ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           ccode=ccode,
                                                           product_group_id=request.args.get('product_group_id'),

                                                           customer_purchase_id=request.args.get(
                                                               'customer_purchase_id'),
                                                           product_id=request.args.get('product_id'),
                                                           ))
        return {

            'total_results': sql_count[0].get('count') if len(sql_count) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'data': sql_query
        }


@orderServicesAPIRoutes.route('/approved_rawmaterial')
class ApprovedMaterial(Resource):

    @login_required()
    @orderServicesAPIRoutes.doc(params=material_filter)
    @orderServicesAPIRoutes.marshal_with(material_list_response)
    def get(self):

        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id')
        status = request.args.get('status', None)
        prod_plan_id = request.args.get('prod_plan_id', None)
        sql_con = ''
        if status:
            sql_con += ' and inv.status=:status '

        if prod_plan_id:
            sql_con += ' and inv.prod_plan_id=:prod_plan_id '
        query = text(f'''
                select 
                distinct
                pp.production_plan_id,
                pp.plan_unique,
                inv.product_id,
                inv.requested_amount,
                inv.approved_amount,
                p.product_code,
                p.product_name,
                u.uom,p.sku_id
                from invregistry as inv
                left join production_plan as pp on inv.prod_plan_id = pp.production_plan_id
                left join products as p on p.product_id = inv.product_id
                left join uom as u on u.id = p.uom_id
                where inv.deleted is not true
                and inv.compcode=:compcode
                {sql_con}
    ''')
        result = query_to_dict(db_client.engine.execute(query,
                                          compcode=compcode,
                                          prod_plan_id=prod_plan_id,
                                          status=status))

        return {
            'results': result
        }