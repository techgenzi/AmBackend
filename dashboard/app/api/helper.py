import time
from pprint import pprint

from flask import request
from sqlalchemy import text
from ipss_utils.redis.ipss_redis import query_to_dict
from .. import db_client

def file_filters():
    int_con=''
    ord_con=''
    prod_con=''
    if request.args.get('customer_id'):

        int_con+=' and cp.customer_id=:customer_id '
    if request.args.get('customer_purchase_id'):
        int_con+=' and cp.customer_purchase_id=:customer_purchase_id '
    if request.args.get('product_id'):
        int_con+=' and oie.product_id=:product_id '
        prod_con+=' and p.product_id=:product_id '
    ord_con += f'''
                    and pp.production_plan_id in (select distinct(pd.production_plan_id) from plan_details pd
        join order_items_extract oie on oie.extract_id=pd.order_extract_id
        join customer_purchase_items cpi on cpi.items_id=oie.order_items_id
        join customer_purchase cp on cp.customer_purchase_id=cpi.customer_purchase_id 
        where 1=1  {int_con}
        )
                '''
    return ord_con,prod_con
def shedule_efficiency_product():
    ord_con,prod_con=file_filters()
    shed_query=text(f'''
                SELECT 
                SUM(target_quantity) AS target_quantity,
                SUM(outward_quantity) AS outward_quantity,
                product_id,product_code,product_name,sku_id,
                 count(*) over() as total_results
                FROM (
                    SELECT 
                        SUM(pt.target_quantity) AS target_quantity,p.product_id,p.product_code,p.product_name,p.sku_id,
                        COALESCE((
                            SELECT SUM(el.outward_qty) 
                            FROM execution_log el
                            WHERE el.target_id = pt.plan_target_id and el.deleted is not true
                        ), 0) AS outward_quantity
                    FROM plan_targets pt
                    join production_plan pp on pp.production_plan_id=pt.production_plan_id
                    join products p on p.product_id=pp.product_id
                    where 1=1  and pt.deleted is not true and pt.compcode=:compcode {ord_con} {prod_con}
                
                    GROUP BY pt.plan_target_id,p.sku_id,p.product_id,p.product_code,p.product_name
                ) AS subquery
                group by product_id,product_code,product_name,sku_id
                  limit :limit offset :offset
                
    ''')
    return shed_query
def plan_efficiency_product():
    ord_con, prod_con = file_filters()
    plan_eff_query=text(f'''
                        select sum(planed_quantity) as planed_quantity,sum(outward_qty) as outward_qty,
                        product_id,product_code,product_name,sku_id,
                        count(*) over() as total_results
                        from (
                        select pp.planed_quantity,
                        sum(el.outward_qty) as outward_qty,pp.production_plan_id ,
                        p.product_id,p.product_code,p.product_name,p.sku_id
                        from production_plan pp 
                        join products p on p.product_id=pp.product_id {prod_con}
                        left join plan_targets pt on pt.production_plan_id =pp.production_plan_id 
                        left join execution_log el on el.target_id =pt.plan_target_id 
                        left join stage s on s.stage_id =el.stage_id 
                        left join production_stages ps on ps.stage_id =s.stage_id and pp.product_id =ps.product_id and ps.rank_id =(select max(ips.rank_id) from production_stages as ips where 
                                                                        ips.product_id = ps.product_id
                                                                        and ips.deleted is not true)
                        left join activity_stage_map asm on asm.production_stage_id =ps.id and asm.is_final_process is true
                        where 1=1 and pp.deleted is not true and pp.compcode=:compcode {ord_con}
                        group by pp.production_plan_id,pp.planed_quantity,p.product_id,p.product_code,p.product_name,p.sku_id
                        order by production_plan_id desc) as cte
                        group by product_id,product_code,product_name,sku_id
                          limit :limit offset :offset
    ''')
    return plan_eff_query
def wastage_products():
    ord_con, prod_con = file_filters()
    wastage_query=text(f'''
                        select sum(wastage) as wastage_allowed,sum(wastage_used) as wastage_used,
                        product_id,product_code,product_name,sku_id,
                        count(*) over() as total_results
                        from (select pp.wastage,
                        sum(el.wastage) as wastage_used,pp.production_plan_id,
                        p.product_id,p.product_code,p.product_name,p.sku_id
                        from production_plan pp 
                        join products p on p.product_id=pp.product_id
                        left join plan_targets pt on pt.production_plan_id =pp.production_plan_id 
                        left join execution_log el on el.target_id =pt.plan_target_id 
                        left join stage s on s.stage_id =el.stage_id 
                        left join production_stages ps on ps.stage_id =s.stage_id and pp.product_id =ps.product_id and ps.rank_id =(select max(ips.rank_id) from production_stages as ips where 
                                                                        ips.product_id = ps.product_id
                                                                        and ips.deleted is not true)
                        left join activity_stage_map asm on asm.production_stage_id =ps.id and asm.is_final_process is true
                        where 1=1 and pp.deleted is not true and pp.compcode=:compcode {ord_con}
                        group by pp.production_plan_id,pp.wastage,p.product_id,p.product_code,p.product_name,p.sku_id
                        order by production_plan_id desc) as cte
                        group by product_id,product_code,product_name,sku_id
                          limit :limit offset :offset

    ''')
    return wastage_query
def grn_qc_products():
    sql_con=''
    if request.args.get('product_id'):
        sql_con+='and p.product_id=:product_id'
    grn_qc_query=text(f'''
                        select sum(g.received_quantity) as received_quantity, p.product_id,p.product_code,p.product_name,p.sku_id,
                        sum(g.non_damaged_quantity::numeric) as non_damaged_quantity,count(*) over() as total_results
                        from grnlineitems g
                        join products p on p.product_id =g.product_id and g.deleted is not true and g.compcode=:compcode
                        where 1=1 {sql_con}
                        group by  p.product_id,p.product_code,p.product_name,p.sku_id
                          limit :limit offset :offset
    ''')
    return grn_qc_query

def cards():
    pp_con = ''
    if request.args.get('product_id'):
        pp_con += ' and pp.product_id=:product_id '

    if request.args.get('customer_purchase_id'):
        pp_con += ' and cp.customer_purchase_id=:customer_purchase_id '

    if request.args.get('customer_id'):
        pp_con += ' and cp.customer_id=:customer_id '

    query3 = text(f'''
                    with cte as (select 
                    cp.order_unique,
                    sum(cpi.quantity_ordered) as quantity_ordered,
                    sum(cpi.quantity_delivered) as quantity_delivered,
                    sum(case when pp.is_done = true then 1 else 0 end) as production_complete,
                    sum(case when pp.is_done != true then 1 else 0 end) as production_pending
                    from production_plan as pp
                    left join plan_details as pd on pp.production_plan_id = pd.production_plan_id
                    left join order_items_extract as oie on pd.order_extract_id = oie.extract_id
                    left join customer_purchase_items as cpi on cpi.items_id = oie.order_items_id
                    left join customer_purchase as cp on cpi.customer_purchase_id = cp.customer_purchase_id
                    where cp.order_type != 'Internal' and pp.compcode=:compcode {pp_con}
                    group by cp.order_unique)
                    select count(*) as total_orders,sum(quantity_delivered) as total_dispatch, sum(production_complete) as production_complete,
                    sum(cte.production_pending) as production_pending from cte
                    ''')

    return query3

#
# def order_convertion(filter_order_result):
#
#     customer_no_of_products = 0
#     internal_no_of_products = 0
#
#     customer_arr = []
#     customer = 0
#     internal_arr = []
#     internal = 0
#     customer_no_of_products_arr = []
#     customer_dict1 = {}
#     customer_delivered = 0
#     customer_delivery_arr = []
#     internal_dict1 = {}
#     internal_processing = 0
#     internal_processing_arr = []
#     internal_complete = 0
#     internal_complete_arr = []
#     customer_product_summary = {}
#     iternal_product_summary = {}
#     for item in filter_order_result:
#         if item.get("order_type") == 'Customer':
#             customer += 1
#             customer_arr.append(item)
#             product_details = item.get('product_details')
#             for i in product_details:
#                 product_code = i.get('product_code')
#                 if product_code in customer_dict1:
#                     customer_dict1[product_code].append(i)
#                 else:
#                     customer_dict1[product_code] = [i]
#                 customer_no_of_products += int(i.get('quantity_ordered')) if i.get('quantity_ordered') else 0
#                 customer_no_of_products_arr.append(i)
#                 if i.get('quantity_delivered'):
#                     customer_delivered += int(i.get('quantity_delivered', '0'))
#                     customer_delivery_arr.append(i)
#
#         else:
#             internal += 1
#             internal_arr.append(item)
#             internal_processing += 1 if item.get('plan_details_id') and item.get('is_done') is 'false' else 0
#             internal_processing_arr.append(item)
#             internal_complete += 1 if item.get('plan_details_id') and item.get('is_done') is 'true' else 0
#             product_details = item.get('product_details')
#             for i in product_details:
#                 internal_no_of_products += int(i.get('quantity_ordered')) if i.get('quantity_ordered') else 0
#                 product_code = i.get('product_code')
#                 if product_code in internal_dict1:
#                     internal_dict1[product_code].append(i)
#                 else:
#                     internal_dict1[product_code] = [i]
#                 internal_complete_arr.append(i)
#
#     filter_customer_items_order = len(customer_dict1)
#     filter_internal_items_order = len(internal_dict1)
#
#     filter_json = {
#         'customer': customer,
#         'customer_arr': customer_arr,
#         'internal': internal,
#         'internal_arr': internal_arr,
#         'filter_customer_items_order': filter_customer_items_order,
#         'customer_dict_details': customer_dict1,
#         'filter_internal_items_order': filter_internal_items_order,
#         'internal_dict_details': internal_dict1,
#         'customer_no_of_products': customer_no_of_products,
#         'internal_no_of_products': internal_no_of_products,
#         'delivered': customer_delivered,
#         'delivery_details': customer_delivery_arr,
#         'internal_processing': internal_processing,
#         'internal_processing_arr': internal_processing_arr,
#         'internal_complete': internal_complete,
#         'internal_complete_arr': internal_complete_arr
#     }
#
#     return filter_json


def summarize_order_data(filter_order_result):
    customer_no_of_products = 0
    internal_no_of_products = 0

    customer_arr = []
    internal_arr = []

    customer = 0
    internal = 0

    customer_no_of_products_arr = []
    customer_dict1 = {}
    customer_delivered = 0
    customer_delivery_arr = []

    internal_dict1 = {}

    customer_processing = 0
    customer_processing_arr = []
    customer_complete = 0
    customer_complete_arr = []

    internal_processing = 0
    internal_processing_arr = []
    internal_complete = 0
    internal_complete_arr = []

    for item in filter_order_result:
        order_type = item.get("order_type")
        product_details = item.get("product_details") or []
        plan_details = item.get("plan_details") or []

        if order_type == 'Customer':
            customer += 1
            customer_arr.append(item)

            for i in product_details:
                product_code = i.get('product_code')
                quantity_ordered = int(i.get('quantity_ordered') or 0)
                quantity_delivered = int(i.get('quantity_delivered') or 0)

                customer_no_of_products += quantity_ordered
                customer_no_of_products_arr.append(i)

                if quantity_delivered:
                    customer_delivered += quantity_delivered
                    customer_delivery_arr.append(i)

                customer_dict1.setdefault(product_code, []).append(i)

            for plan in plan_details:
                is_done = str(plan.get("is_done")).lower()
                plan_id = plan.get("plan_unique")

                if plan_id:
                    if is_done == 'false':
                        customer_processing += 1
                        customer_processing_arr.append(plan)
                    elif is_done == 'true':
                        customer_complete += 1
                        customer_complete_arr.append(plan)

        else:
            internal += 1
            internal_arr.append(item)

            for i in product_details:
                quantity_ordered = int(i.get('quantity_ordered') or 0)
                product_code = i.get('product_code')

                internal_no_of_products += quantity_ordered
                internal_dict1.setdefault(product_code, []).append(i)

            for plan in plan_details:
                is_done = str(plan.get("is_done")).lower()
                plan_id = plan.get("plan_unique")

                if plan_id:
                    if is_done == 'false':
                        internal_processing += 1
                        internal_processing_arr.append(plan)
                    elif is_done == 'true':
                        internal_complete += 1
                        internal_complete_arr.append(plan)

    filter_customer_items_order = len(customer_dict1)
    filter_internal_items_order = len(internal_dict1)

    filter_json = {
        'customer': customer,
        'customer_arr': customer_arr,
        'internal': internal,
        'internal_arr': internal_arr,

        'filter_customer_items_order': filter_customer_items_order,
        'customer_dict_details': customer_dict1,
        'filter_internal_items_order': filter_internal_items_order,
        'internal_dict_details': internal_dict1,

        'customer_no_of_products': customer_no_of_products,
        'customer_no_of_products_arr': customer_no_of_products_arr,
        'delivered': customer_delivered,
        'delivery_details': customer_delivery_arr,

        'customer_processing': customer_processing,
        'customer_processing_arr': customer_processing_arr,
        'customer_complete': customer_complete,
        'customer_complete_arr': customer_complete_arr,

        'internal_no_of_products': internal_no_of_products,
        'internal_processing': internal_processing,
        'internal_processing_arr': internal_processing_arr,
        'internal_complete': internal_complete,
        'internal_complete_arr': internal_complete_arr,
    }

    return filter_json


def customer_pending(compcode, start_date, end_date, sql_con, summary_only=False):

    total_customer_order_query = text(f'''
		select 
        cp.order_unique,cp.order_date::date::text,
        v.companyname,cp.status,
        count(*) as no_of_products,
        count(*) over() total_results,
		sum(cpi.quantity_ordered)::text as quantity_ordered,
		sum(sum(cpi.quantity_ordered)) over()::text as total_quantity_ordered,
		sum(cpi.quantity_delivered)::text as quantity_delivered,
		sum(sum(cpi.quantity_delivered)) over()::text as total_quantity_delivered
        {"" if summary_only else """,
        json_agg(
        json_build_object(
        'product_code', p.product_code,
            'sku_id', p.sku_id,
            'quantity_ordered', cpi.quantity_ordered::text,
            'quantity_delivered', cpi.quantity_delivered::text
        )
        ) FILTER (WHERE p.product_code IS NOT NULL) as product_details
        """}
        from customer_purchase as cp
        left join customer_purchase_items as cpi on cpi.customer_purchase_id = cp.customer_purchase_id and cpi.deleted is not true
        join products as p on p.product_id = cpi.product_id
        join vendor as v on v.vendorid = cp.customer_id
        where 
		cp.compcode=:compcode 
		and cp.deleted is not true
		and COALESCE(LOWER(TRIM(cp.status)), 'pending') not in ('closed', 'completed', 'cancelled') and cp.order_type='Customer'
		{sql_con}
        group by cp.order_unique,cp.order_type,cp.order_date::date::text,
        v.companyname,cp.status
    ''')

    customer_total_results = query_to_dict(db_client.engine.execute(total_customer_order_query,
                                                                    compcode=compcode,
                                                                    start_date=start_date,
                                                                    end_date=end_date))

    if summary_only:
        customer_product_results = []
    else:
        details_customer_order = text(f'''
        select 
            p.product_code,p.sku_id,
            SUM(cpi.quantity_ordered)::text AS quantity_ordered,
            SUM(cpi.quantity_delivered)::text AS quantity_delivered,
            sum(sum(cpi.quantity_ordered)) over()::text as total_quantity_ordered,
            sum(sum(cpi.quantity_delivered)) over()::text as total_quantity_delivered,
            count(*) over() as total_products,
            json_agg(
            json_build_object(
                'order_unique',cp.order_unique,
                'order_date', cp.order_date::date::text,
                'status', cp.status,
                'customer_name', v.companyname,
                'quantity_ordered', cpi.quantity_ordered::text,
                'quantity_delivered', cpi.quantity_delivered::text
            )
            ) as order_details
            from customer_purchase as cp
            left join customer_purchase_items as cpi on cpi.customer_purchase_id = cp.customer_purchase_id and cpi.deleted is not true
            join products as p on p.product_id = cpi.product_id
            join vendor as v on v.vendorid = cp.customer_id
            where cp.compcode=:compcode and cp.deleted is not true and COALESCE(LOWER(TRIM(cp.status)), 'pending') not in ('closed', 'completed', 'cancelled') and cp.order_type='Customer' {sql_con}
            group by p.product_code,p.sku_id
        ''')

        customer_product_results = query_to_dict(db_client.engine.execute(details_customer_order,
                                                                          compcode=compcode,
                                                                          start_date=start_date,
                                                                          end_date=end_date))


    total_internal_order_query = text(f'''
        with moved_summary as (
            SELECT 
                cpi.items_id,
                COALESCE(SUM(pp.moved_quantity), 0) AS moved_quantity
            FROM customer_purchase_items cpi
            LEFT JOIN order_items_extract oie ON oie.order_items_id = cpi.items_id AND oie.deleted IS NOT TRUE
            LEFT JOIN plan_details pd ON pd.order_extract_id = oie.extract_id AND pd.deleted IS NOT TRUE
            LEFT JOIN production_plan pp ON pp.production_plan_id = pd.production_plan_id AND pp.deleted IS NOT TRUE
            WHERE cpi.deleted IS NOT TRUE
            GROUP BY cpi.items_id
        )
        select 
        cp.order_unique,cp.order_date::date::text,cp.status,
        count(*) as no_of_products,
        count(*) over() total_results,
		sum(cpi.quantity_ordered)::text as quantity_ordered,
		sum(sum(cpi.quantity_ordered)) over()::text as total_quantity_ordered,
		sum(COALESCE(ms.moved_quantity, 0))::text as moved_quantity,
		sum(sum(COALESCE(ms.moved_quantity, 0))) over()::text as total_moved
        {"" if summary_only else """,
        json_agg(
        json_build_object(
        'product_code', p.product_code,
            'sku_id', p.sku_id,
            'quantity_ordered', cpi.quantity_ordered::text
        )
        ) FILTER (WHERE p.product_code IS NOT NULL) as product_details
        """}
        from customer_purchase as cp
        left join customer_purchase_items as cpi on cpi.customer_purchase_id = cp.customer_purchase_id and cpi.deleted is not true
        left join moved_summary as ms on ms.items_id = cpi.items_id
        join products as p on p.product_id = cpi.product_id
        where 
		cp.compcode=:compcode 
		and cp.deleted is not true
		and COALESCE(LOWER(TRIM(cp.status)), 'pending') not in ('closed', 'completed', 'cancelled') and cp.order_type='Internal'
		{sql_con}
        group by cp.order_unique,cp.order_type,cp.order_date::date::text,cp.status
        ''')

    internal_total_results = query_to_dict(db_client.engine.execute(total_internal_order_query,
                                                                    compcode=compcode,
                                                                    start_date=start_date,
                                                                    end_date=end_date))

    if summary_only:
        internal_product_results = []
    else:
        details_internal_order = text(f'''
            with item_moved as (
                SELECT 
                    cpi.items_id,
                    COALESCE(SUM(pp.moved_quantity), 0) AS moved_quantity
                FROM customer_purchase_items cpi
                LEFT JOIN order_items_extract oie ON oie.order_items_id = cpi.items_id AND oie.deleted IS NOT TRUE
                LEFT JOIN plan_details pd ON pd.order_extract_id = oie.extract_id AND pd.deleted IS NOT TRUE
                LEFT JOIN production_plan pp ON pp.production_plan_id = pd.production_plan_id AND pp.deleted IS NOT TRUE
                WHERE cpi.deleted IS NOT TRUE
                GROUP BY cpi.items_id
            ),
            cte as (
                select 
                    p.product_code,p.sku_id,
                    cp.order_unique,cp.order_date::date::text as order_date,cp.status,
                    cpi.quantity_ordered,
                    COALESCE(im.moved_quantity, 0) as moved_quantity
                from customer_purchase as cp
                join customer_purchase_items as cpi on cpi.customer_purchase_id = cp.customer_purchase_id and cpi.deleted is not true
                left join item_moved as im on im.items_id = cpi.items_id
                join products as p on p.product_id = cpi.product_id
                where 
                    cp.compcode=:compcode and cp.deleted is not true and
                    COALESCE(LOWER(TRIM(cp.status)), 'pending') not in ('closed', 'completed', 'cancelled') and cp.order_type='Internal'
                    {sql_con}
            )
            select cte.product_code,cte.sku_id,
            sum(cte.quantity_ordered)::text as quantity_ordered,
            sum(sum(cte.quantity_ordered)) over()::text as total_quantity_ordered,
            sum(cte.moved_quantity)::text as moved_quantity,
            sum(sum(cte.moved_quantity)) over()::text as total_moved_quantity,
            count(*) over() as total_products,
            json_agg(
            json_build_object(
            'order_unique', cte.order_unique,
                'order_date', cte.order_date,
                'status', cte.status,
                'quantity_ordered', cte.quantity_ordered::text,
                'moved_quantity', cte.moved_quantity::text
            )
            ) as order_details
            from cte
            group by cte.product_code,cte.sku_id
            ''')

        internal_product_results = query_to_dict(db_client.engine.execute(details_internal_order,
                                                                          compcode=compcode,
                                                                          start_date=start_date,
                                                                          end_date=end_date))

    production_plan = text(f'''
    select pp.plan_unique,pp.product_id,pp.planed_quantity::text,pp.plan_date::date::text,pp.execution_start_date::date::text
    {"" if summary_only else ", p.product_code, p.sku_id"}
    from production_plan as pp
    {"" if summary_only else "left join products as p on p.product_id = pp.product_id"}
    where pp.is_done is not true and pp.compcode=:compcode
    ''')

    production_plan_result = query_to_dict(db_client.engine.execute(production_plan,
                                                                    compcode=compcode))

    no_of_plan = 0
    no_of_plan_not_started = 0
    no_of_plan_not_started_arr = []
    no_of_plan_on_time_start = 0
    no_of_plan_on_time_start_arr = []
    no_of_plan_delayed_start = 0
    no_of_plan_delayed_start_arr = []
    no_of_plan_early_start = 0
    no_of_plan_early_start_arr = []
    fmt = "%Y-%m-%d"
    for plan in production_plan_result:
        no_of_plan += 1

        execution_start_date = time.strptime(plan.get('execution_start_date'), fmt) if plan.get(
            'execution_start_date') else None
        plan_date = time.strptime(plan.get('plan_date'), fmt) if plan.get('plan_date') else None
        if execution_start_date is None:
            no_of_plan_not_started += 1
            if not summary_only:
                no_of_plan_not_started_arr.append(plan)
        elif plan_date is not None and execution_start_date is not None and plan_date == execution_start_date:
            no_of_plan_on_time_start += 1
            if not summary_only:
                no_of_plan_on_time_start_arr.append(plan)
        elif plan_date is not None and execution_start_date is not None and plan_date < execution_start_date:
            no_of_plan_delayed_start += 1
            if not summary_only:
                no_of_plan_delayed_start_arr.append(plan)
        elif plan_date is not None and execution_start_date is not None:
            no_of_plan_early_start += 1
            if not summary_only:
                no_of_plan_early_start_arr.append(plan)

    return {
        'customer_total': customer_total_results[0].get('total_results') if customer_total_results else 0,
        'customer_total_quantity_ordered': customer_total_results[0].get('total_quantity_ordered') if customer_total_results else 0,
        'total_quantity_delivered': customer_total_results[0].get('total_quantity_delivered') if customer_total_results else 0,
        'customer_summary': [] if summary_only else customer_total_results,
        'customer_total_products': customer_product_results[0].get('total_products') if customer_product_results else 0,
        'details_product': customer_product_results,
        'internal_total': internal_total_results[0].get('total_results') if internal_total_results else 0,
        'internal_total_quantity_ordered': internal_total_results[0].get('total_quantity_ordered') if internal_total_results else 0,
        'internal_total_quantity_moved': internal_total_results[0].get('total_moved') if internal_total_results else 0,
        'internal_total_results': [] if summary_only else internal_total_results,
        'internal_total_products': internal_product_results[0].get('total_products') if internal_product_results else 0,
        'internal_product_results': internal_product_results,
        'no_of_plan': no_of_plan,
        'plan_details': [] if summary_only else production_plan_result,
        'no_of_plan_not_started': no_of_plan_not_started,
        'no_of_plan_not_started_arr': no_of_plan_not_started_arr,
        'no_of_plan_on_time_start': no_of_plan_on_time_start,
        'no_of_plan_on_time_start_arr': no_of_plan_on_time_start_arr,
        'no_of_plan_delayed_start': no_of_plan_delayed_start,
        'no_of_plan_delayed_start_arr': no_of_plan_delayed_start_arr,
        'no_of_plan_early_start': no_of_plan_early_start,
        'no_of_plan_early_start_arr': no_of_plan_early_start_arr,
        'On_Schedule_Plan_Starts': round((no_of_plan_on_time_start/no_of_plan)*100, 2) if no_of_plan else 0,
        'Early_plan_starts': round((no_of_plan_early_start / no_of_plan)*100, 2) if no_of_plan else 0,
        'Delayed_plan_starts': round((no_of_plan_delayed_start / no_of_plan)*100, 2) if no_of_plan else 0,
        'Uninitiated_Plans': round((no_of_plan_not_started / no_of_plan)*100, 2) if no_of_plan else 0
    }

