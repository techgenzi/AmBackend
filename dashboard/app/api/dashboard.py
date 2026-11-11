import datetime
import calendar
import time
from decimal import Decimal
from pprint import pprint

from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.redis.ipss_redis import query_to_dict

from .errorhandling import map_sqlalchemy_error_to_http_status, update_local
# from joborder.app import ipss_db,db_client
from .. import db_client, ipss_db
from sqlalchemy.exc import SQLAlchemyError
from .helper import grn_qc_products, shedule_efficiency_product, plan_efficiency_product, wastage_products, cards, \
    summarize_order_data, customer_pending
from flask import request, jsonify
from flask_restx import Resource
from ipss_utils.decorators import login_required
from sqlalchemy import text, insert, update
from .. import db_client
from ..api_doc import search_filter, product_based_filter, order_filter, date_filter
from ..routes.dashboard import dashboard_api_route, plan_dashboard_report_model, update_dashboard_model, \
    order_list_response


# import pandas as pd
# import numpy as np
# from statsmodels.tsa.arima.model import ARIMA
# from sqlalchemy import create_engine
# from datetime import datetime, timedelta


# dashboard_get_all_model, \
#     create_dashboard_response, \
#     update_dashboard_model, update_dashboard_response, dashboard_model,
# from ..routes.dashboard import create_dashboard_model, get_dashboard_response,dashboard_get_all_model
# Primary key name
#
# def forecast_orders(months):
#     # Fetch all available historical data
#     query = """
#         SELECT order_date, order_count
#         FROM customer_orders
#         ORDER BY order_date;
#     """
#
#     # Load data into a DataFrame
#     df = pd.read_sql(query, db_client.engine)
#
#     if df.empty:
#         return jsonify({"error": "No data available"}), 400
#
#     # Convert 'order_date' to datetime and set as index
#     df['order_date'] = pd.to_datetime(df['order_date'])
#     df.set_index('order_date', inplace=True)
#
#     # Ensure data is sorted and fill missing dates
#     df = df.asfreq('D').fillna(0)  # Fill missing dates with 0 orders
#
#     # Train ARIMA Model on all historical data
#     model = ARIMA(df, order=(5, 1, 0))  # You can tune (p,d,q) values
#     model_fit = model.fit()
#
#     # Forecast for next months months (daily level)
#     forecast_days = months * 30  # Convert months to days
#     forecast = model_fit.forecast(steps=forecast_days)
#
#     # Create future date range
#     future_dates = pd.date_range(start=df.index[-1] + pd.Timedelta(days=1), periods=forecast_days, freq='D')
#
#     # Convert forecasted daily data to a DataFrame
#     forecast_df = pd.DataFrame({"date": future_dates, "forecasted_orders": forecast})
#
#     # Convert to month-wise total orders
#     forecast_df['month'] = forecast_df['date'].dt.strftime('%Y-%m')  # Extract year-month
#     month_wise_forecast = forecast_df.groupby('month')['forecasted_orders'].sum().reset_index()
#
#     # Convert to JSON format
#     forecast_json = [{"month": row["month"], "forecasted_orders": int(row["forecasted_orders"])} for _, row in
#                      month_wise_forecast.iterrows()]
#
#     return jsonify({"forecast": forecast_json})
@dashboard_api_route.route('/products')
class DashboardPlanProducts(Resource):
    @dashboard_api_route.doc(params={**list_api_params, **product_based_filter})
    @login_required()
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        page = int(request.args.get('paged')) if request.args.get('paged') else 1
        result_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0

        card_response = query_to_dict(db_client.engine.execute(cards(),
                                                               customer_id=request.args.get('customer_id'),
                                                               customer_purchase_id=request.args.get(
                                                                   'customer_purchase_id'),
                                                               product_id=request.args.get('product_id'),
                                                               compcode=ccode
                                                               ))

        shedule_efficiency = query_to_dict(db_client.engine.execute(shedule_efficiency_product(),
                                                                    limit=result_per_page,
                                                                    customer_id=request.args.get('customer_id'),
                                                                    customer_purchase_id=request.args.get(
                                                                        'customer_purchase_id'),
                                                                    product_id=request.args.get('product_id'),
                                                                    compcode=ccode,
                                                                    offset=offset))
        plan_efficiency = query_to_dict(db_client.engine.execute(plan_efficiency_product(),
                                                                 limit=result_per_page,
                                                                 customer_id=request.args.get('customer_id'),
                                                                 customer_purchase_id=request.args.get(
                                                                     'customer_purchase_id'),
                                                                 product_id=request.args.get('product_id'),
                                                                 compcode=ccode,
                                                                 offset=offset))
        wastage_product = query_to_dict(db_client.engine.execute(wastage_products(),
                                                                 limit=result_per_page,
                                                                 customer_id=request.args.get('customer_id'),
                                                                 customer_purchase_id=request.args.get(
                                                                     'customer_purchase_id'),
                                                                 product_id=request.args.get('product_id'),
                                                                 compcode=ccode,
                                                                 offset=offset))
        grn_qc_product = query_to_dict(db_client.engine.execute(grn_qc_products(),
                                                                limit=result_per_page,
                                                                customer_id=request.args.get('customer_id'),
                                                                customer_purchase_id=request.args.get(
                                                                    'customer_purchase_id'),
                                                                product_id=request.args.get('product_id'),
                                                                compcode=ccode,
                                                                offset=offset))

        return jsonify({
            "top_card": card_response,
            "shedule_efficiency": shedule_efficiency,
            "plan_efficiency": plan_efficiency,
            "wastage_product": wastage_product,
            "grn_qc_product": grn_qc_product
        })


@dashboard_api_route.route('/')
class DashboardPlan(Resource):

    @dashboard_api_route.marshal_with(plan_dashboard_report_model)
    @dashboard_api_route.doc(params=search_filter)
    # @login_required(permissions='dashboard.list')
    @login_required()
    def get(self):
        current_user = request.args.get('current_user')
        # print("QWER", current_user)
        compcode = current_user.get('company_id', None)
        # print("comp", compcode)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)

        end_date = end_date if end_date else start_date

        el_con = ''
        sql_con = ''
        closure_con = ''
        if start_date:
            el_con += ' and el.opertaion_start_date::date between :start_date and :end_date '
            closure_con += 'and pp.execution_end_date::date between :start_date and :end_date '
            sql_con += ' and cp.created_on::date between :start_date and :end_date '

        # plan_closure_query = text(f'''
        # select pp.plan_unique,pp.product_id,pp.planed_quantity::text,pp.end_date::date::text,pp.execution_end_date::date::text,
        # p.product_code,p.sku_id
        # from production_plan as pp
        # left join products as p on p.product_id = pp.product_id
        #
        # ''')

        plan_closure_query = text(f'''
        
					with cte11 as(
        select pp.plan_unique,pp.product_id,pp.production_plan_id,pp.planed_quantity,pp.end_date,pp.execution_end_date,
               el.stage_id, el.process_id, el.outward_qty
						from production_plan as pp
        join plan_targets as pt on pt.production_plan_id = pp.production_plan_id
        join execution_log as el on el.target_id = pt.plan_target_id
		where pp.is_done is true
						and pp.compcode=:compcode {closure_con}
					)
        ,cte12 as (
                    select distinct on (ps.product_id)
                    ps.product_id,ps.rank_id,ps.id,ps.stage_id,
                    asm.config_id,asm.is_final_process
                    from production_stages ps
                    left join activity_stage_map asm on asm.production_stage_id = ps.id
                    where ps.deleted is not true and asm.deleted is not true 
                    and ps.compcode=:compcode
                    order by ps.product_id,ps.rank_id desc
        )
        select cte11.plan_unique,cte11.end_date::date::text,cte11.execution_end_date::date::text, p.product_code,p.sku_id,cte11.planed_quantity::text,sum(cte11.outward_qty)::text as outward_qty from 
        cte11 
        join cte12 on cte11.product_id = cte12.product_id and cte11.stage_id = cte12.stage_id and (cte12.config_id is null or cte11.process_id = cte12.config_id)
		left join products as p on  cte11.product_id = p.product_id
		group by cte11.plan_unique,cte11.end_date,cte11.execution_end_date, p.product_code,p.sku_id,cte11.planed_quantity::text
        ''')

        plan_closure_result = query_to_dict(db_client.engine.execute(plan_closure_query,
                                                                             compcode=compcode,
                                                                             start_date=start_date,
                                                                             end_date=end_date))

        employee_query = text(f'''
        with cte as(
			SELECT DISTINCT ON (el.id)
                    el.id,el.emp_id, 
					el.outward_qty
					,asm.target_per_hour
                    FROM execution_log el
                    join plan_targets pt on pt.plan_target_id=el.target_id
                    join production_plan pp on el.target_id =pt.plan_target_id 
                    join production_stages ps on ps.stage_id =el.stage_id and ps.product_id =pp.product_id and ps.deleted is not true
                    join activity_stage_map asm on asm.production_stage_id =ps.id and asm.deleted is not true and
					(el.process_id IS NOT NULL AND asm.config_id = el.process_id 
                                 OR el.process_id IS NULL)
                    where 1=1 and el.emp_id IS NOT NULL and el.compcode=:compcode {el_con}),
					agg as(
					select cte.emp_id ,
					hrm.idcardno,
					sum(cte.outward_qty) as outward_qty,
					sum(cte.target_per_hour) as target,
						concat(hrm.fname,' ', hrm.mname, ' ', hrm.lname) as name ,
					(sum(cte.outward_qty)/sum(cte.target_per_hour)) * 100 as effciency
					FROM cte
                	left join hremploymast as hrm on hrm.hremploymastid = cte.emp_id
					group by cte.emp_id,hrm.idcardno,concat(hrm.fname,' ', hrm.mname, ' ', hrm.lname)
						) 
						select agg.emp_id as hrmemployemastid,agg.idcardno as emp_id,agg.name,
						agg.outward_qty::text,agg.target::text,
						round(agg.effciency,2)::text as effciency,
						rank() over( order by effciency desc) rank
						from agg
						order by rank
                ''')

        employee_efficiency_result = query_to_dict(db_client.engine.execute(employee_query,
                                                                             compcode=compcode,
                                                                             start_date=start_date,
                                                                             end_date=end_date))

        total_customer_order_query = text(f'''
            select 
            cp.order_unique,cp.order_date::date::text,
            v.companyname,cp.status,
            count(*) as no_of_products,
            count(*) over() total_results,
            sum(cpi.quantity_ordered)::text as quantity_ordered,
            sum(sum(cpi.quantity_ordered)) over()::text as total_quantity_ordered,
            sum(cpi.quantity_delivered)::text as quantity_delivered,
            sum(sum(cpi.quantity_delivered)) over()::text as total_quantity_delivered,
            json_agg(
            json_build_object(
            'product_code', p.product_code,
                'sku_id', p.sku_id,
                'quantity_ordered', cpi.quantity_ordered::text,
                'quantity_delivered', cpi.quantity_delivered::text
            )
            ) FILTER (WHERE p.product_code IS NOT NULL) as product_details
            from customer_purchase as cp
            left join customer_purchase_items as cpi on cpi.customer_purchase_id = cp.customer_purchase_id
            join products as p on p.product_id = cpi.product_id
            join vendor as v on v.vendorid = cp.customer_id
            where 
            cp.compcode=:compcode and cp.order_type='Customer'
            {sql_con}
            group by cp.order_unique,cp.order_type,cp.order_date::date::text,
            v.companyname,cp.status
            ''')

        customer_total_results = query_to_dict(db_client.engine.execute(total_customer_order_query,
                                                                        compcode=compcode,
                                                                        start_date=start_date,
                                                                        end_date=end_date))

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
            left join customer_purchase_items as cpi on cpi.customer_purchase_id = cp.customer_purchase_id
            left join order_items_extract oie ON cpi.items_id = oie.order_items_id
            join products as p on p.product_id = cpi.product_id
            join vendor as v on v.vendorid = cp.customer_id
            where cp.compcode=:compcode and cp.order_type='Customer' {sql_con}
            group by p.product_code,p.sku_id
            ''')

        customer_product_results = query_to_dict(db_client.engine.execute(details_customer_order,
                                                                          compcode=compcode,
                                                                          start_date=start_date,
                                                                          end_date=end_date))

        total_internal_order_query = text(f'''
            select 
            cp.order_unique,cp.order_date::date::text,cp.status,
            count(*) as no_of_products,
            count(*) over() total_results,
            sum(cpi.quantity_ordered)::text as quantity_ordered,
            sum(sum(cpi.quantity_ordered)) over()::text as total_quantity_ordered,
            sum(pp.moved_quantity)::text as moved_quantity,
            sum(sum(pp.moved_quantity)) over()::text as total_moved,
            json_agg(
            json_build_object(
            'product_code', p.product_code,
                'sku_id', p.sku_id,
                'quantity_ordered', oie.quantity_ordered::text
            )
            ) FILTER (WHERE p.product_code IS NOT NULL) as product_details
            from customer_purchase as cp
            left join customer_purchase_items as cpi on cpi.customer_purchase_id = cp.customer_purchase_id and cpi.deleted is not true
            left join order_items_extract oie ON cpi.items_id = oie.order_items_id and oie.deleted is not true
            left join plan_details as pd on pd.order_extract_id = oie.extract_id and pd.deleted is not true
            left join production_plan as pp on pp.production_plan_id = pd.production_plan_id and pp.deleted is not true
            left join products as p on p.product_id = oie.product_id
            where 
            cp.compcode=:compcode and cp.order_type='Internal'
            and cp.deleted is not true
            {sql_con}
            group by cp.order_unique,cp.order_type,cp.order_date::date::text,cp.status
            ''')

        internal_total_results = query_to_dict(db_client.engine.execute(total_internal_order_query,
                                                                        compcode=compcode,
                                                                        start_date=start_date,
                                                                        end_date=end_date))

        details_internal_order = text(f'''
                with cte as(
                select 
                p.product_code,p.sku_id,
                cp.order_unique,cp.order_date::date::text,oie.quantity_ordered,cp.status,
                sum(pp.moved_quantity) as moved_quantity
                from customer_purchase as cp
                left join customer_purchase_items as cpi on cpi.customer_purchase_id = cp.customer_purchase_id and cpi.deleted is not true
                left join order_items_extract oie ON cpi.items_id = oie.order_items_id and oie.deleted is not true
                left join plan_details as pd on pd.order_extract_id = oie.extract_id and pd.deleted is not true
                left join production_plan as pp on pp.production_plan_id = pd.production_plan_id and pp.deleted is not true
                left join products as p on p.product_id = oie.product_id
                where 
                cp.compcode=:compcode and cp.order_type='Internal'
                and cp.deleted is not true
                {sql_con}
                group by p.product_code,p.sku_id,cp.order_unique,cp.order_date::date::text,oie.quantity_ordered,cp.status
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
                    'quantity_ordered', cte.quantity_ordered,
                    'moved_quantity', cte.moved_quantity
                )
                ) as order_details
                from cte
                group by cte.product_code,cte.sku_id
                ''')

        internal_product_results = query_to_dict(db_client.engine.execute(details_internal_order,
                                                                          compcode=compcode,
                                                                          start_date=start_date,
                                                                          end_date=end_date))

        no_of_plan_close = 0
        no_of_plan_on_time_close = 0
        no_of_plan_on_time_close_arr = []
        no_of_plan_delayed_close = 0
        no_of_plan_delayed_close_arr = []
        no_of_plan_early_close = 0
        no_of_plan_early_close_arr = []
        fmt = "%Y-%m-%d"
        for plan in plan_closure_result:
            no_of_plan_close += 1

            execution_end_date = time.strptime(plan.get('execution_end_date'), fmt) if plan.get(
                'execution_end_date') else None
            end_date = time.strptime(plan.get('end_date'), fmt) if plan.get('end_date') else None
            if end_date is not None and execution_end_date is not None and end_date == execution_end_date:
                no_of_plan_on_time_close += 1
                no_of_plan_on_time_close_arr.append(plan)
            elif end_date is not None and execution_end_date is not None and end_date < execution_end_date:
                no_of_plan_delayed_close += 1
                no_of_plan_delayed_close_arr.append(plan)
            elif end_date is not None and execution_end_date is not None:
                no_of_plan_early_close += 1
                no_of_plan_early_close_arr.append(plan)

        result_dict = {
            'no_of_plan_close': no_of_plan_close,
            'closed_plan': plan_closure_result,
            'no_of_plan_on_time_close': no_of_plan_on_time_close,
            'no_of_plan_on_time_close_arr': no_of_plan_on_time_close_arr,
            'no_of_plan_delayed_close': no_of_plan_delayed_close,
            'no_of_plan_delayed_close_arr': no_of_plan_delayed_close_arr,
            'no_of_plan_early_close': no_of_plan_early_close,
            'no_of_plan_early_close_arr': no_of_plan_early_close_arr,
            'On_Schedule_Plan_Close': round((no_of_plan_on_time_close / no_of_plan_close) * 100, 2) if no_of_plan_close else 0,
            'Early_plan_Close': round((no_of_plan_early_close / no_of_plan_close) * 100, 2) if no_of_plan_close else 0,
            'Delayed_plan_Close': round((no_of_plan_delayed_close / no_of_plan_close) * 100, 2) if no_of_plan_close else 0
        }

        return {
            "results": {
                'customer_total': customer_total_results[0].get('total_results') if customer_total_results else 0,
                'customer_total_quantity_ordered': customer_total_results[0].get('total_quantity_ordered') if customer_total_results else 0,
                'total_quantity_delivered': customer_total_results[0].get('total_quantity_delivered') if customer_total_results else 0,
                'customer_summary': customer_total_results,
                'customer_total_products': customer_product_results[0].get('total_products') if customer_product_results else 0,
                'details_product': customer_product_results,
                'internal_total': internal_total_results[0].get('total_results') if internal_total_results else 0,
                'internal_total_quantity_ordered': internal_total_results[0].get('total_quantity_ordered') if internal_total_results else 0,
                'internal_total_quantity_moved': internal_total_results[0].get('total_moved') if internal_total_results else 0,
                'internal_total_results': internal_total_results,
                'internal_total_products': internal_product_results[0].get('total_products') if internal_product_results else 0,
                'internal_product_results': internal_product_results,
                "plan_closure": result_dict,
                'employee_efficiency': employee_efficiency_result
            }
        }


@dashboard_api_route.route('/pending')
class DashboardPending(Resource):
    @login_required()
    @dashboard_api_route.doc(params=search_filter)
    def get(self):

        current_user = request.args.get('current_user')
        compcode = current_user.get('company_id', None)

        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)

        end_date = end_date if end_date else start_date

        sql_con = ''
        if start_date:
            sql_con += ' and cp.created_on between :start_date and :end_date '

        summary_only = request.args.get('summary_only', 'false').lower() == 'true'

        filter_json = customer_pending(compcode=compcode, start_date=start_date, end_date=end_date, sql_con=sql_con, summary_only=summary_only)

        return {
            'results': filter_json
        }


@dashboard_api_route.route('/data')
class DashboardData(Resource):

    @login_required()
    @dashboard_api_route.marshal_with(update_dashboard_model)
    @dashboard_api_route.doc(params=search_filter)
    @dashboard_api_route.doc(params=date_filter)
    def get(self):

        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id', None)

        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date') if request.args.get('end_date') else start_date

        el_con = ''
        pp_con = ''
        cp_con = ''
        ef_con = ''
        month_start_date = None
        month_end_date = None

        if start_date:
            el_con += ' and el.opertaion_start_date::date between :start_date and :end_date '
            pp_con += ' and pp.created_on::date between :start_date and :end_date '
            cp_con += ' and cp.created_on::date between :start_date and :end_date '
            ef_con += ' and cte4.created_on::date between :start_date and :end_date '
            month_start_date = start_date
            month_end_date = end_date
        else:
            today = datetime.datetime.today()
            month_start_date = today.replace(day=1)  # First day of the current month
            next_month = today.replace(day=28) + datetime.timedelta(days=4)  # Move to next month
            month_end_date = next_month.replace(day=1) - datetime.timedelta(days=1)
        query = text(f'''
        select cp.order_type,cp.order_unique,
        cp.status,
        CASE 
        WHEN cp.status = 'Closed' THEN 'Closed'
        WHEN MAX(pd.plan_details_id) IS NULL THEN 'Pending'
        WHEN BOOL_AND(pp.is_done) THEN 'Completed'  -- If all is_done for the order are TRUE
        WHEN MAX(pd.plan_details_id) IS NOT NULL AND BOOL_AND(NOT pp.is_done) THEN 'In Progress'
        ELSE 'Pending'
        END AS calculated_status,
            json_agg(
                distinct jsonb_build_object(
                    'delivery_id', dli.id,
                        'status',
                        case 
                        when dli.id is not null then 
                            case 
                                when cp.expected_receiving_date::date <= dli.created_on::date then 'on time'
                                else 'delayed delivery'
                            end
                        end
                ) 
            ) as data
        from customer_purchase as cp
        left join customer_purchase_items as cpi on cpi.customer_purchase_id = cp.customer_purchase_id
        left join order_items_extract as oie on oie.order_items_id = cpi.items_id
        left join plan_details as pd on pd.order_extract_id = oie.extract_id
        left join production_plan as pp on pp.production_plan_id = pd.production_plan_id
        left join delivery_line_items as dli on dli."workOrderLineId" = cpi.items_id
        where cp.compcode=:compcode {cp_con}
        group by cp.order_type,cp.order_unique,cp.status
        ''')

        query2 = text('''
        WITH current_period AS (
    SELECT 
        order_type, 
        COUNT(*) AS current_period_count 
    FROM customer_purchase 
    WHERE created_on BETWEEN CAST(:start_date AS DATE) AND CAST(:end_date AS DATE)
    GROUP BY order_type
),
previous_period AS (
    SELECT 
        order_type, 
        COUNT(*) AS previous_period_count 
    FROM customer_purchase 
    WHERE created_on BETWEEN 
        (CAST(:start_date AS DATE) - INTERVAL '1 month') AND 
        (CAST(:end_date AS DATE) - INTERVAL '1 month')
    GROUP BY order_type
)
SELECT 
    COALESCE(c.order_type, p.order_type) AS order_type, 
    COALESCE(c.current_period_count, 0) AS current_period_count, 
    COALESCE(p.previous_period_count, 0) AS previous_period_count, 
    CASE 
        WHEN p.previous_period_count = 0 THEN NULL 
        ELSE ROUND(((c.current_period_count - p.previous_period_count) * 100.0 / p.previous_period_count), 2)::TEXT 
    END AS percentage_change 
FROM current_period c 
FULL OUTER JOIN previous_period p 
ON c.order_type = p.order_type 
ORDER BY order_type;
        ''')

#         query2 = text('''
#        WITH current_period AS (
#     SELECT
#         order_type,
#         COUNT(*) AS current_period_count
#     FROM customer_purchase
#     WHERE created_on BETWEEN :start_date::DATE AND :end_date::DATE
#     GROUP BY order_type
# ),
# previous_period AS (
#     SELECT
#         order_type,
#         COUNT(*) AS previous_period_count
#     FROM customer_purchase
#     WHERE created_on BETWEEN
#         ((:start_date)::DATE - (((:end_date)::DATE - (:start_date)::DATE)::INTEGER) * INTERVAL '1 day')
#         AND ((:start_date)::DATE - INTERVAL '1 day')
#     GROUP BY order_type
# )
# SELECT
#     COALESCE(c.order_type, p.order_type) AS order_type,
#     COALESCE(c.current_period_count, 0) AS current_period_count,
#     COALESCE(p.previous_period_count, 0) AS previous_period_count,
#     CASE
#         WHEN p.previous_period_count = 0 THEN NULL
#         ELSE ROUND(((c.current_period_count - p.previous_period_count) * 100.0 / p.previous_period_count), 2)::TEXT
#     END AS percentage_change
# FROM current_period c
# FULL OUTER JOIN previous_period p ON c.order_type = p.order_type
# ORDER BY order_type;
#         ''')
        employee_query = text(f'''
        WITH ranked_emp AS (
            SELECT 
            el.emp_id, 
            SUM(outward_qty) AS quantity,
            avg((outward_qty/asm.target_per_hour)*100) as effciency,
            RANK() OVER (ORDER BY avg((outward_qty/asm.target_per_hour)*100) DESC) AS final_rank
            FROM execution_log el
            join plan_targets pt on pt.plan_target_id=el.target_id
            join production_plan pp on el.target_id =pt.plan_target_id 
            join production_stages ps on ps.stage_id =el.stage_id and ps.product_id =pp.product_id and ps.deleted is not true
            left join activity_stage_map asm on asm.production_stage_id =ps.id and asm.deleted is not true and
            case when el.process_id is not null then 
            asm.config_id =el.process_id 
            else el.process_id is null end
            where 1=1 and el.emp_id IS NOT NULL and el.compcode=:compcode {el_con} 
            group by el.emp_id 
        )
        SELECT ranked_emp.emp_id,
        ranked_emp.quantity::text,round(effciency,2)::text as effciency,
        ranked_emp.final_rank,
        concat(hrm.fname,' ', hrm.mname, ' ', hrm.lname) as name FROM ranked_emp
        left join hremploymast as hrm on hrm.hremploymastid = ranked_emp.emp_id
        ORDER BY final_rank
        ''')
        query4 = text(f'''
            with cte1 as(
            select pp.production_plan_id,el.opertaion_start_date::date as created_on,pp.product_id,pp.planed_quantity,pp.wastage,el.stage_id,el.process_id,el.outward_qty,el.wastage as el_wastage from production_plan as pp
            left join plan_targets as pt on pp.production_plan_id = pt.production_plan_id
            left join execution_log as el on pt.plan_target_id = el.target_id
            where pp.compcode=:compcode {pp_con}
            ),
            cte2 as (
            select distinct on (ps.product_id)
            ps.product_id,ps.rank_id,ps.id,ps.stage_id,
            asm.config_id,asm.is_final_process
            from production_stages ps
            left join activity_stage_map asm on asm.production_stage_id = ps.id
            where ps.deleted is not true and asm.deleted is not true and ps.compcode=:compcode
            order by ps.product_id,ps.rank_id desc
            ),
            cte3 as(
            select cte1.production_plan_id,cte1.product_id,cte1.planed_quantity,cte1.wastage,cte1.stage_id,cte1.process_id,cte1.created_on::date,
            sum(cte1.outward_qty) as outward
            from cte1 
            join cte2 on cte1.product_id = cte2.product_id and cte1.stage_id = cte2.stage_id and (cte2.config_id is null or cte1.process_id = cte2.config_id)
            group by cte1.production_plan_id,cte1.product_id,cte1.planed_quantity,cte1.wastage,cte1.stage_id,cte1.process_id,
            cte1.created_on::date),
            cte4 as(
            select sum(cte3.planed_quantity) as planed_quantity,
            sum(cte3.outward) as outward,
            ( sum(cte3.outward)/sum(cte3.planed_quantity))*100 as effciency
            from cte3
            ),
            cte5 as (
            select 
                        sum(oie.quantity_ordered) as quantity_ordered
                        from customer_purchase as cp
                        left join customer_purchase_items as cpi on cpi.customer_purchase_id = cp.customer_purchase_id
                        left join order_items_extract as oie on cpi.items_id = oie.order_items_id
                where cp.compcode=:compcode and cp.deleted is not true {cp_con}
                )
                select cte5.quantity_ordered::text,cte4.outward::text,
                round(cte4.effciency,2)::text,
                cte4.planed_quantity::text
                from cte4, cte5
        ''')

        daily_efficiency_query = text(f'''
            with cte1 as(
            select pp.plan_unique,pp.product_id,pt.plan_target_id,pt.target_quantity,pp.wastage from production_plan as pp
            left join plan_targets as pt on pp.production_plan_id = pt.production_plan_id
            where pp.compcode=:compcode),
            cte2 as (
            select distinct on (ps.product_id)
            ps.product_id,ps.rank_id,ps.id,ps.stage_id,
            asm.config_id,asm.is_final_process
            from production_stages ps
            left join activity_stage_map asm on asm.production_stage_id = ps.id
            where ps.deleted is not true and asm.deleted is not true and ps.compcode=:compcode
            order by ps.product_id,ps.rank_id desc
            ),
            cte3 as(
            select * from cte1 
            join cte2 on cte1.product_id = cte2.product_id),
            cte4 as(
            select el.opertaion_start_date::date as created_on,sum(cte3.target_quantity) as target_quantity,sum(el.outward_qty) as outward_qty,
             sum(cte3.wastage) as planed_wastage, sum(el.wastage) as produced_wastage
             from cte3 
            join execution_log as el on el.target_id = cte3.plan_target_id and cte3.stage_id = el.stage_id and (cte3.config_id is null or el.process_id = cte3.config_id)
            group by el.opertaion_start_date::date)
            select cte4.created_on::text,round((cte4.outward_qty/cte4.target_quantity)*100,2)::text as efficiency,
                case 
                    when cte4.produced_wastage > 0 then 
                    round((cte4.planed_wastage/cte4.produced_wastage)*100,2)::text
                    else '0'
                end as wastage_efficiency
            from cte4
            where 1=1 {ef_con}
            order by cte4.created_on
        ''')

        wastage_eff = text(f'''
        select pp.plan_unique,pp.wastage_per,pp.wastage ,round(avg(el.wastage),2)::text as actual_wastage from production_plan pp 
        join plan_targets pt on pp.production_plan_id =pt.production_plan_id 
        left join execution_log el on el.target_id =pt.plan_target_id 
        join production_stages as ps on ps.product_id = pp.product_id
                                                    and ps.deleted is not true and ps.rank_id =(
                                                        select max(ips.rank_id) from production_stages as ips where 
                                                        ips.product_id = ps.product_id
                                                        and ips.deleted is not true
        --                                                and ps.compcode =:compcode
                                                   )
        left join activity_stage_map asm on asm.production_stage_id =ps.id and asm.deleted is not true and
                    case when el.process_id is not null then 
                    asm.config_id =el.process_id and asm.is_final_process is true
                    else el.process_id is null end
        where 1=1 and el.deleted is not true {el_con} and el.compcode =:compcode
        group by pp.plan_unique,pp.wastage_per,pp.wastage 
        ''')
        result = query_to_dict(db_client.engine.execute(query,
                                                        compcode=compcode,
                                                        start_date=start_date,
                                                        end_date=end_date))

        result2 = query_to_dict(db_client.engine.execute(query2, compcode=compcode,
                                                         start_date=month_start_date,
                                                         end_date=month_end_date))
        wastage_eff = query_to_dict(db_client.engine.execute(wastage_eff, compcode=compcode, start_date=start_date,
                                                             end_date=end_date))
        result3 = query_to_dict(db_client.engine.execute(employee_query, compcode=compcode, start_date=start_date,
                                                         end_date=end_date))

        daily_efficiency_result = query_to_dict(db_client.engine.execute(daily_efficiency_query,
                                                                         start_date=start_date,
                                                                         end_date=end_date,
                                                                         compcode=compcode))

        order_efficiency = query_to_dict(db_client.engine.execute(query4,
                                                                  start_date=start_date,
                                                                  end_date=end_date,
                                                                  compcode=compcode))

        total_order = 0
        customer_order = 0
        internal_order = 0
        customer_pending = 0
        customer_in_progress = 0
        customer_completed = 0
        customer_delivered = 0
        ####################
        internal_pending = 0
        internal_in_progress = 0
        internal_completed = 0
        internal_delivered = 0
        ######################
        on_time_delivery = 0
        delayed_delivery = 0
        performance = {}
        for i in result2:
            performance[i.get('order_type')] = i.get('percentage_change')
        for i in result:
            total_order += 1
            if i.get('order_type') == 'Customer':
                customer_order += 1
            elif i.get('order_type') == 'Internal':
                internal_order += 1
            if i.get('calculated_status') == 'Pending' and i.get('order_type') == 'Customer':
                customer_pending += 1
            elif i.get('calculated_status') == 'Closed' and i.get('order_type') == 'Customer':
                customer_delivered += 1
            elif i.get('calculated_status') == 'In Progress' and i.get('order_type') == 'Customer':
                customer_in_progress += 1
            elif i.get('calculated_status') == 'Completed' and i.get('order_type') == 'Customer':
                customer_completed += 1
                #########################
            if i.get('calculated_status') == 'Pending' and i.get('Internal') == 'Customer':
                customer_pending += 1
            elif i.get('calculated_status') == 'Closed' and i.get('Internal') == 'Customer':
                customer_delivered += 1
            elif i.get('calculated_status') == 'In Progress' and i.get('Internal') == 'Customer':
                customer_in_progress += 1
            elif i.get('calculated_status') == 'Completed' and i.get('Internal') == 'Customer':
                customer_completed += 1
                ################

            for j in i.get('data'):
                if j.get('status') == 'on time':
                    on_time_delivery += 1
                elif j.get('status') == 'delayed delivery':
                    delayed_delivery += 1

        order_status_overview = {
            'total_order': total_order,
            'customer_order': customer_order,
            'internal_order': internal_order,
            'customer_pending': customer_pending,
            'customer_in_progress': customer_in_progress,
            'customer_completed': customer_completed,
            'customer_delivered': internal_delivered,
            'internal_pending': internal_pending,
            'internal_in_progress': internal_in_progress,
            'internal_completed': internal_completed,
            'internal_delivered': internal_delivered
        }

        deliver_efficiency = {
            'on_time_delivery': on_time_delivery,
            'delayed_delivery': delayed_delivery
        }

        return {
            'order_status_overview': order_status_overview,
            'deliver_efficiency': deliver_efficiency,
            'performance': performance,
            'wastage_eff': wastage_eff,
            'employee_efficiency': result3,
            'order_efficiency': order_efficiency,
            'daily_efficiency': daily_efficiency_result
        }


@dashboard_api_route.route('/order_details')
class SupportService(Resource):

    @login_required()
    @dashboard_api_route.marshal_with(order_list_response)
    @dashboard_api_route.doc(params=order_filter)
    @dashboard_api_route.doc(params=date_filter)
    def get(self):

        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page if (paged - 1) * results_per_page else 0
        order_type = request.args.get('order_type', None)

        calculated_status = request.args.get('calculated_status', None)

        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date') if request.args.get('end_date') else start_date

        sql_con = ''

        if order_type:
            sql_con += ' and order_type=:order_type '

        if start_date:
            sql_con += ' and order_date::date between :start_date and :end_date '



        query = text(f'''
        with cte as(
        select cp.order_type,cp.order_unique,
        cp.order_date,cp.customer_id,
         v.companyname,v.emailid,v.mobileno,
        cp.status,
		count(distinct cpi.items_id) as no_of_products,
        CASE 
            WHEN cp.status = 'Closed' THEN 'Closed'
            WHEN MAX(pd.plan_details_id) IS NULL THEN 'Pending'
            WHEN BOOL_AND(pp.is_done) THEN 'Completed'  -- If all is_done for the order are TRUE
            WHEN MAX(pd.plan_details_id) IS NOT NULL AND BOOL_AND(NOT pp.is_done) THEN 'In Progress'
        ELSE 'Pending'
        END AS calculated_status
        from customer_purchase as cp
        left join customer_purchase_items as cpi on cpi.customer_purchase_id = cp.customer_purchase_id and cpi.deleted is not true
        left join order_items_extract as oie on oie.order_items_id = cpi.items_id
        left join plan_details as pd on pd.order_extract_id = oie.extract_id
        left join production_plan as pp on pp.production_plan_id = pd.production_plan_id
        left join delivery_line_items as dli on dli."workOrderLineId" = cpi.items_id
		left join vendor as v on v.vendorid = cp.customer_id 
        where cp.compcode=:compcode
        group by cp.order_type,cp.order_unique,cp.status,cp.order_date,cp.customer_id,
        v.companyname,v.emailid,v.mobileno
        )
        select *,
         count(*) over() as total_results from cte 
        where 1=1 {sql_con}
        {' and calculated_status=:calculated_status ' if calculated_status else ''}
        limit :limit offset :offset
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        calculated_status=calculated_status,
                                                        order_type=order_type,
                                                        start_date=start_date,
                                                        end_date=end_date,
                                                        compcode=compcode,
                                                        limit=results_per_page,
                                                        offset=offset))

        return {
            'total_results': result[0].get('total_results') if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }