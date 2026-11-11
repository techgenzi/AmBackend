from flask import request, jsonify
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text
from ..api_doc import report_filters
from ..routes.dispatch import dispatch_api_route,plan_response_model
from .. import db_client
@dispatch_api_route.route('/DispatchApiReport')
class DispatchApiReport(Resource):
    per_page = 20

    @dispatch_api_route.marshal_with(plan_response_model)
    @dispatch_api_route.doc(params=report_filters)
    # @dispatch_api_route.doc(params=search_filters)
    # @user_verify(permission='InventoryRegistry.list', db_client=db_client)
    @login_required(permissions='dispatch.list')
    # @login_required()
    def get(self):
        # paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        # results_per_page = int(request.args.get('results_per_page')) if request.args.get(
        #     'results_per_page') else 20
        # offset = (paged - 1) * results_per_page
        compcode = request.args.get('current_user', {}).get('company_id', None)
        # start_date = request.args.get('start_date', None)
        # end_date = request.args.get('end_date', start_date)
        sql_con = ''
        dispatch_end_date=request.args.get('dispatch_end_date') if request.args.get('dispatch_end_date') else request.args.get('dispatch_start_date')
        if request.args.get('dispatch_material_id'):
            sql_con+=' and i.product_id=:dispatch_material_id '
        if request.args.get('planned_productid'):
            sql_con += ' and (pp.product_id=:planned_productid OR EXISTS (SELECT 1 FROM production_plan_products sub_ppp WHERE sub_ppp.production_plan_id = pp.production_plan_id AND sub_ppp.product_id = :planned_productid)) '
        if request.args.get('ref_id'):
            sql_con += ' and i.ref_id=:ref_id '
        if request.args.get('production_plan_id'):
            sql_con += ' and pp.production_plan_id=:production_plan_id '
        if request.args.get('releseid'):
            sql_con += ' and i.releseid=:releseid '
        if request.args.get('dispatch_id'):
            sql_con += ' and d.dispatch_id=:dispatch_id '
        if request.args.get('dispatch_start_date'):
            sql_con+= ' and d.created_on::date >=:dispatch_start_date '
            sql_con+=' and d.created_on::date <=:dispatch_end_date '
            
        sql_query=text(f'''
        select  pp.plan_unique,
            cp.order_unique,
            count(*) over () as total_value,
            pp.wastage AS planned_wastage,
            pp.wastage_per AS planned_wastage_per,
            pp.status,
            pp.plan_date::date,
            pp.planed_quantity,
            fn.product_name AS planned_product,
            fn.sku_id AS planned_product_sku,
            i.ref_id as request_id,
            sum(d.dispatch_amount) as dispatch_amount,
            d.action,
            count(distinct p.sku_id) as product_count,d.created_on::date  as dispatch_date,
            p.product_name as product_name,
            p.sku_id as sku_id,
            p.product_code as product_code,
            fn.product_code as planned_product_code,
            i.approved_amount as approved_amount,
            i.requested_amount as requested_amount,
            i.status as request_status,
            i.approval_date as approval_date
    FROM invregistry i
        LEFT JOIN products p ON p.product_id = i.product_id
        LEFT JOIN dispatch d ON d.releseid = i.releseid AND d.deleted IS NOT TRUE
        LEFT JOIN production_plan pp ON pp.production_plan_id = i.prod_plan_id AND pp.deleted IS NOT TRUE
        LEFT JOIN (
            SELECT production_plan_id, MIN(product_id) as product_id
            FROM production_plan_products
            GROUP BY production_plan_id
        ) ppp ON ppp.production_plan_id = pp.production_plan_id
        LEFT JOIN products fn ON fn.product_id = COALESCE(ppp.product_id, pp.product_id)
        LEFT JOIN (
            select pd.production_plan_id, max(cp.order_unique) as order_unique
            from plan_details as pd
            join order_items_extract as oie on oie.extract_id = pd.order_extract_id
            join customer_purchase_items as cpi on cpi.items_id = oie.order_items_id
            join customer_purchase as cp on cp.customer_purchase_id = cpi.customer_purchase_id
            group by pd.production_plan_id
        ) as cp on cp.production_plan_id = pp.production_plan_id
        where i.deleted is not true and i.compcode=:ccode {sql_con}
        group by pp.plan_unique,cp.order_unique,pp.wastage,pp.wastage_per,pp.status,
            pp.plan_date,p.product_code,fn.product_code,
            pp.planed_quantity,fn.product_name,fn.sku_id,i.ref_id,d.action,
            d.created_on::date, p.product_name, p.sku_id,i.approved_amount,i.requested_amount,i.status, i.approval_date

                
       
                ''')
        from .helper import dataFormating

        sql_query=query_to_dict(db_client.engine.execute(sql_query,ccode=compcode,
                                                         dispatch_material_id=request.args.get('dispatch_material_id'),
                                                         planned_productid=request.args.get('planned_productid'),
                                                         ref_id=request.args.get('ref_id'),
                                                         production_plan_id=request.args.get('production_plan_id'),
                                                         releseid=request.args.get('releseid'),
                                                         dispatch_id=request.args.get('dispatch_id'),
                                                         dispatch_start_date=request.args.get('dispatch_start_date'),
                                                         dispatch_end_date=dispatch_end_date))
        if sql_query:
         sql_query = dataFormating(df=sql_query)
        return {"data":sql_query}
        # return jsonify({
        #     'total_results': sql_query[0].get('total_value') if sql_query else 0,
        #     'page': paged,
        #     'results_per_page': results_per_page,
        #     'data': sql_query
        # })


    # '''
    # SELECT
    #         pp.plan_unique,
    #         count(*) over () as total_value,
    #         pp.wastage AS planned_wastage,
    #         pp.wastage_per AS planned_wastage_per,
    #         pp.status,
    #         pp.plan_date,
    #         pp.planed_quantity,
    #         fn.product_name AS planned_product,
    #         fn.sku_id AS planned_product_sku,
    #
    #         -- Aggregate request data
    #         jsonb_agg(
    #             jsonb_build_object(
    #                 'request_id', i.ref_id,
    #                 'request_status', i.status,
    #                 'approval_date', i.approval_date,
    #                 'approved_amount', i.approved_amount,
    #                 'requested_amount', i.requested_amount,
    #                 'distpatch_data', (
    #                     SELECT jsonb_agg(
    #                         jsonb_build_object(
    #                             'dispatch_amount', d.dispatch_amount,
    #                             'action', d."action",
    #                             'dispatch_date', d.created_on,
    #                             'product_name', p.product_name,
    #                             'sku_id', p.sku_id
    #                         )
    #                     )
    #                     FROM dispatch d
    #                     LEFT JOIN products p ON p.product_id = i.product_id
    #                     WHERE d.releseid = i.releseid
    #                 )
    #             )
    #         ) AS request_data
    #
    #     FROM production_plan pp
    #     JOIN products fn ON fn.product_id = pp.product_id
    #     LEFT JOIN invregistry i ON i.prod_plan_id = pp.production_plan_id
    #     where 1=1 and pp.compcode=:ccode
    #     GROUP BY
    #         pp.plan_unique,
    #         pp.wastage,
    #         pp.wastage_per,
    #         pp.status,
    #         pp.plan_date,
    #         pp.planed_quantity,
    #         fn.product_name,
    #         fn.sku_id
    # '''

    ######################################
#     '''
#     SELECT
#     pp.plan_unique,
#     COUNT(*) OVER () AS total_value,
#     pp.wastage AS planned_wastage,
#     pp.wastage_per AS planned_wastage_per,
#     pp.status,
#     pp.plan_date,
#     pp.planed_quantity,
#     fn.product_name AS planned_product,
#     fn.sku_id AS planned_product_sku,
#
#     json_agg(det) AS request_data
#
# FROM production_plan pp
# JOIN products fn ON fn.product_id = pp.product_id
#
# -- Pre-aggregated subquery for request + dispatch
# LEFT JOIN (
#     SELECT
#         i.ref_id AS request_id,
#         i.prod_plan_id,
#
#         json_agg(
#             jsonb_build_object(
#                 'request_status', i.status,
#                 'approval_date', i.approval_date,
#                 'approved_amount', i.approved_amount,
#                 'requested_amount', i.requested_amount,
#                 'dispatch_amount', d.dispatch_amount,
#                 'action', d.action,
#                 'dispatch_date', d.created_on,
#                 'product_name', p.product_name,
#                 'sku_id', p.sku_id
#             ) order by d.created_on desc
#         ) AS distpatch_data
#
#     FROM invregistry i
#     LEFT JOIN dispatch d ON d.releseid = i.releseid
#     LEFT JOIN products p ON p.product_id = i.product_id
#
#     GROUP BY i.ref_id, i.prod_plan_id
# ) AS det ON det.prod_plan_id = pp.production_plan_id
# where pp.deleted is not true and pp.compcode=:ccode
#
# GROUP BY
#     pp.plan_unique,
#     pp.wastage,
#     pp.wastage_per,
#     pp.status,
#     pp.plan_date,
#     pp.planed_quantity,
#     fn.product_name,
#     fn.sku_id
#     '''