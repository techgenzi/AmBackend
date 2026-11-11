import datetime
from pprint import pprint

from flask import request, session
from flask_restx import Resource, abort

from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, insert
from .. import ipss_db, db_client
from ..api_doc import product_filter, labour_cost_search
from ..models.labour import Labour, LabourLog
from ipss_utils.decorators import login_required
from ..routes.labour import create_record_response_model, labour_list_response, labour_api_route, labour_model, \
    labour_cost_list_response
from .errorhandling import map_sqlalchemy_error_to_http_status, update_local



@labour_api_route.route('/')
class LabourApi(Resource):

    @labour_api_route.marshal_with(labour_list_response)
    @labour_api_route.doc(params=list_api_params)
    @login_required(permissions='labour_cost.list')
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

        sql_con = ''

        if product_id:
            sql_con += 'and lc.product_id =:product_id '
        sql_query = text(f'''
                select lc.*, p.product_code, p.sku_id
                 from labour_cost as lc
                 left join products as p on p.product_id = lc.product_id
                 where lc.deleted is not true and lc.compcode=:compcode {sql_con}
                order by  lc.labour_cost_id DESC
                limit :limit offset :offset
        ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           product_id=product_id,
                                                           compcode=compcode,
                                                           limit=results_per_page,
                                                           offset=offset))
        sql_count = text(f'''
        select 
        count(*)
        from labour_cost as lc
        where lc.deleted is not true and lc.compcode=:compcode {sql_con}
        ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           compcode=compcode,
                                                           product_id=product_id))

        pprint(sql_query)

        return {
            'total_results': sql_count[0].get('count') if sql_count else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }

    @login_required(permissions='labour_cost.add')
    # @login_required(permissions='labour_cost')
    @labour_api_route.expect(labour_model)
    @labour_api_route.marshal_with(create_record_response_model)
    def post(self):
        data = request.json
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        username = cur.get('username', None)
        error = ''
        s = db_client.session
        try:
            with s.begin():
                data['compcode'] = compcode
                data['created_by'] = username
                data['created_on'] = datetime.datetime.now()
                stmt = insert(Labour).values(data).returning(Labour.labour_cost_id)
                result = s.execute(stmt)
                primary_key = result.scalar()
                data['labour_cost_id'] = primary_key
                stmt2 = insert(LabourLog).values(data)
                s.execute(stmt2)

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


@labour_api_route.route('/bulk_post')
class LabourBulkApi(Resource):

    @login_required(permissions='labour_cost.add')
    def post(self):
        data_list = request.json
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        username = cur.get('username', None)
        s = db_client.session
        try:
            with s.begin():
                for item in data_list:
                    product_id = item.get('product_id')
                    existing = s.query(Labour).filter(
                        Labour.product_id == product_id,
                        Labour.compcode == compcode,
                        Labour.deleted != True
                    ).first()

                    item['compcode'] = compcode
                    item['modified_by'] = username
                    item['modified_on'] = datetime.datetime.now()

                    if existing:
                        labour_id = existing.labour_cost_id
                        item['labour_cost_id'] = labour_id
                        s.query(Labour).filter(Labour.labour_cost_id == labour_id).update(item)
                    else:
                        item['created_by'] = username
                        item['created_on'] = datetime.datetime.now()
                        stmt = insert(Labour).values(item).returning(Labour.labour_cost_id)
                        res = s.execute(stmt)
                        item['labour_cost_id'] = res.scalar()

                    log_item = dict(item)
                    log_item['created_by'] = log_item.pop('modified_by', username) or username
                    log_item['created_on'] = log_item.pop('modified_on', datetime.datetime.now()) or datetime.datetime.now()
                    stmt_log = insert(LabourLog).values(log_item)
                    s.execute(stmt_log)

            return {'success': True, 'message': 'Bulk Labour Cost created/updated successfully'}, 200
        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)


@labour_api_route.route('/<int:labour_cost_id>')
class LabourUpdate(Resource):

    # @login_required()
    @login_required(permissions='labour_cost.edit')
    @labour_api_route.expect(labour_model)
    def put(self, labour_cost_id):
        data = request.json
        s = db_client.session
        error = ''
        try:
            result = update_local(model=Labour,
                                  condition=Labour.labour_cost_id == labour_cost_id,
                                  values=data,
                                  commit=False,
                                  s=s)
            if result['success']:
                data['labour_cost_id'] = labour_cost_id
                data['created_by'] = data.pop('modified_by', None)
                data['created_on'] = datetime.datetime.now()
                data.pop('modified_on', None)
                pprint(data)
                stmt2 = insert(LabourLog).values(data)
                s.execute(stmt2)
                s.commit()
            else:
                raise Exception('updation Failed')

        except Exception as e:
            s.rollback()
            s.flush()
            return map_sqlalchemy_error_to_http_status(e)

        return result

    # @login_required()
    @login_required(permissions='labour_cost.delete')
    def delete(self, labour_cost_id):

        result = update_local(model=Labour,
                              condition=Labour.labour_cost_id == labour_cost_id,
                              values={
                                  'deleted': True,
                                  'deleted_at': datetime.datetime.now()
                              })

        return result


@labour_api_route.route('/labour_cost')
class LabourCost(Resource):

    @login_required()
    @labour_api_route.doc(params={**list_api_params, **labour_cost_search})
    @labour_api_route.marshal_with(labour_cost_list_response)
    def get(self):

        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id', None)
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page

        sql_con = ''
        product_id = request.args.get('product_id', None)
        production_plan_id = request.args.get('production_plan_id', None)
        customer_purchase_id = request.args.get('customer_purchase_id', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', start_date)
        is_done = request.args.get('is_done', None)
        if production_plan_id:
            sql_con += 'and pp.production_plan_id =:production_plan_id '
        if product_id:
            sql_con += 'and pp.product_id =:product_id '
        if customer_purchase_id:
            sql_con += 'and EXISTS (select 1 from plan_details pd join order_items_extract oie on oie.extract_id = pd.order_extract_id join customer_purchase_items cpi on cpi.items_id = oie.order_items_id where pd.production_plan_id = pp.production_plan_id and cpi.customer_purchase_id = :customer_purchase_id) '
        el_date_con = ''
        mv_date_con = ''
        if start_date:
            sql_con += " and exists (select 1 from mv_daily_manufacturing_fact mv_check where mv_check.production_plan_id = pp.production_plan_id and mv_check.execution_date >= cast(:start_date as date) and mv_check.execution_date <= cast(:end_date as date)) "
            el_date_con += " and el.opertaion_start_date >= cast(:start_date as timestamp) and el.opertaion_start_date < cast(:end_date as timestamp) + interval '1 day' "
            mv_date_con += " and mv.execution_date >= cast(:start_date as date) and mv.execution_date <= cast(:end_date as date) "

        if is_done is not None:
            sql_con += 'and pp.is_done =:is_done '

        query = text(f'''
WITH filtered_plans AS (
    SELECT pp.production_plan_id,
           pp.plan_unique,
           pp.is_done,
           pp.product_id,
           COALESCE(p.product_name, (
               SELECT string_agg(p2.product_name, ', ')
               FROM production_plan_products ppp
               JOIN products p2 ON p2.product_id = ppp.product_id
               WHERE ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
           )) AS product_name,
           COALESCE(p.product_code, 'MULTI') AS product_code,
           COALESCE(p.sku_id, 'MULTI') AS sku_id,
           uom.uom,
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
           COUNT(*) OVER() as total_count
    FROM production_plan pp
    LEFT JOIN products p ON p.product_id = pp.product_id
    LEFT JOIN uom ON uom.id = p.uom_id
    WHERE pp.compcode = :compcode AND pp.deleted IS NOT TRUE {sql_con}
    ORDER BY pp.production_plan_id DESC
    LIMIT :limit OFFSET :offset
),
target_emps AS (
    SELECT DISTINCT e.emp_id
    FROM mv_daily_manufacturing_fact e
    WHERE e.production_plan_id IN (SELECT production_plan_id FROM filtered_plans)
      AND e.emp_id > 0 {mv_date_con.replace("mv.", "e.")}
),
emp_wages AS MATERIALIZED (
    SELECT 
        h.hremploymastid as emp_id,
        h.idcardno,
        trim(concat(h.fname, ' ', coalesce(h.mname, ''), ' ', coalesce(h.lname, ''))) as emp_name,
        CASE WHEN h.daily_wages = TRUE THEN coalesce(NULLIF(trim(h.ctc_amount), ''), '0')::numeric ELSE (coalesce(NULLIF(trim(h.ctc_amount), ''), '0')::numeric / 30) END as day_ctc
    FROM target_emps te
    JOIN hremploymast h ON h.hremploymastid = te.emp_id
),
stage_employees AS (
    SELECT 
        emp_cost.production_plan_id,
        emp_cost.stage_id,
        json_agg(
            json_build_object(
                'emp_id', emp_cost.emp_id,
                'emp_code', ew.idcardno,
                'emp_name', ew.emp_name,
                'labour_cost', round(emp_cost.actual_cost::numeric, 2),
                'day_ctc', round(ew.day_ctc::numeric, 2),
                'hours_worked', 8
            )
        ) as employees
    FROM (
        SELECT 
            e.production_plan_id,
            e.stage_id,
            e.emp_id,
            SUM(e.actual_labour_cost) as actual_cost
        FROM mv_daily_manufacturing_fact e
        WHERE e.production_plan_id IN (SELECT production_plan_id FROM filtered_plans)
          AND e.emp_id > 0 {mv_date_con.replace("mv.", "e.")}
        GROUP BY e.production_plan_id, e.stage_id, e.emp_id
    ) emp_cost
    JOIN emp_wages ew ON ew.emp_id = emp_cost.emp_id
    GROUP BY emp_cost.production_plan_id, emp_cost.stage_id
),
distinct_stages AS (
    SELECT 
        mv.production_plan_id, 
        mv.stage_id,
        SUM(mv.actual_labour_cost) as total_labour_cost,
        SUM(mv.estimated_labour_cost) as total_estimated_cost,
        SUM(mv.outward_qty) as total_produced_qty,
        COALESCE(MAX(se.employees::text)::json, '[]'::json) as employees
    FROM mv_daily_manufacturing_fact mv
    LEFT JOIN stage_employees se ON se.production_plan_id = mv.production_plan_id AND se.stage_id = mv.stage_id
    WHERE mv.production_plan_id IN (SELECT production_plan_id FROM filtered_plans) {mv_date_con}
    GROUP BY mv.production_plan_id, mv.stage_id
),
grouped_stage_cost as (
    select fp.production_plan_id,fp.plan_unique,fp.is_done,
    fp.product_id, fp.product_name, fp.product_code, fp.sku_id, fp.uom, fp.moved_quantity,
    coalesce(sum(cte.total_labour_cost), 0) as labour_cost,
    coalesce(sum(cte.total_estimated_cost), 0) as estimated_cost, 
    coalesce(json_agg(
        json_build_object(
            'stage_id', s.stage_id,
            'stage_name', s.stage_name,
            'labour_cost', coalesce(cte.total_labour_cost, 0),
            'estimated_cost', coalesce(cte.total_estimated_cost, 0),
            'produced_qty', coalesce(cte.total_produced_qty, 0),
            'employees', coalesce(cte.employees, '[]'::json)
        )
    ) filter (where s.stage_id is not null), '[]'::json) as data,
    fp.total_count
    from filtered_plans fp
    left join distinct_stages cte on cte.production_plan_id = fp.production_plan_id
    left join stage s on s.stage_id = cte.stage_id
    group by fp.production_plan_id,fp.plan_unique,fp.is_done,fp.product_id,fp.product_name,fp.product_code,fp.sku_id,fp.uom,fp.moved_quantity,fp.total_count
),
order_details AS (
  SELECT pd.production_plan_id,
  json_agg(DISTINCT jsonb_build_object('customer_purchase_id', cp.customer_purchase_id, 'order_unique', cp.order_unique)) AS details
  FROM filtered_plans fp
  JOIN plan_details pd on fp.production_plan_id = pd.production_plan_id
  JOIN order_items_extract oie ON oie.extract_id = pd.order_extract_id
  JOIN customer_purchase_items cpi ON cpi.items_id = oie.order_items_id
  JOIN customer_purchase cp ON cp.customer_purchase_id = cpi.customer_purchase_id
  where pd.deleted is not true
  GROUP BY pd.production_plan_id
)
select g.*, od.details as order_details
from grouped_stage_cost g
left join order_details od on od.production_plan_id = g.production_plan_id
order by g.production_plan_id desc
        ''')
        result = query_to_dict(db_client.engine.execute(query,
                                                       compcode=compcode,
                                                        limit=results_per_page,
                                                        production_plan_id=production_plan_id,
                                                        customer_purchase_id=customer_purchase_id,
                                                        product_id=product_id,
                                                        start_date=start_date,
                                                        end_date=end_date,
                                                        is_done=is_done,
                                                        offset=offset))

        return {
            'total_results': result[0].get('total_count') if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }


@labour_api_route.route('/labour_cost_employee_wise')
class EmployeeWiseLabourCost(Resource):

    @login_required()
    @labour_api_route.doc(params=list_api_params)
    def get(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id', None)
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get('results_per_page') else 20
        offset = (paged - 1) * results_per_page

        sql_con = ''
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', start_date)
        emp_id = request.args.get('emp_id', None)

        if start_date:
            sql_con += ' and el.opertaion_start_date >= cast(:start_date as timestamp) and el.opertaion_start_date < cast(:end_date as timestamp) + interval \'1 day\' '
        if emp_id:
            sql_con += ' and el.emp_id = :emp_id '

        query = text(f'''
WITH active_logs AS (
    SELECT 
        el.emp_id,
        el.target_id,
        el.stage_id,
        el.process_id,
        el.outward_qty,
        date(el.opertaion_start_date) as work_date,
        hc.time_value as work_hour,
        count(*) over(partition by el.emp_id, date(el.opertaion_start_date), hc.record_id) as logs_in_hour
    FROM execution_log el
    LEFT JOIN hour_config hc ON hc.record_id = el.hour_config_id
    WHERE el.deleted is not true and el.compcode = :compcode AND coalesce(el.outward_qty, 0) > 0 {sql_con}
),
hourly_wage AS MATERIALIZED (
    SELECT 
        hremploymastid as emp_id,
        COALESCE(
            CASE
                WHEN daily_wages = TRUE THEN round((NULLIF(trim(ctc_amount), '')::numeric / 8), 2)
                ELSE round((NULLIF(trim(ctc_amount), '')::numeric / (30 * 8)), 2)
            END,
            0
        ) as hourly_rate,
        fname, lname, idcardno
    FROM hremploymast
    WHERE hremploymastid IN (SELECT DISTINCT emp_id FROM active_logs)
),
apportioned_logs AS (
    SELECT 
        l.emp_id,
        l.target_id,
        l.stage_id,
        l.process_id,
        l.outward_qty,
        l.work_date,
        l.work_hour,
        (hw.hourly_rate / l.logs_in_hour) as apportioned_cost,
        COALESCE(inc.incentive_amount, 0) as incentive_cost
    FROM active_logs l
    JOIN hourly_wage hw ON hw.emp_id = l.emp_id
    LEFT JOIN plan_targets pt ON pt.plan_target_id = l.target_id AND pt.deleted IS NOT TRUE
    LEFT JOIN LATERAL (
        SELECT pis.incentive_amount 
        FROM activity_stage_map asm
        JOIN production_stages ps ON ps.id = asm.production_stage_id AND ps.deleted IS NOT TRUE
        JOIN process_incentive_slabs pis ON pis.activity_stage_map_id = asm.activity_stage_map_id AND pis.deleted IS NOT TRUE
        WHERE ps.product_id = pt.product_id AND ps.stage_id = l.stage_id 
          AND (l.process_id IS NULL OR asm.config_id = l.process_id)
          AND asm.deleted IS NOT TRUE
          AND (l.outward_qty - asm.target_per_hour) >= pis.from_qty 
          AND (pis.to_qty IS NULL OR (l.outward_qty - asm.target_per_hour) <= pis.to_qty)
          AND pis.compcode = :compcode
        ORDER BY pis.from_qty DESC 
        LIMIT 1
    ) inc ON true
),
employee_cost AS (
    SELECT 
        al.emp_id,
        CONCAT(hw.fname, ' ', hw.lname) as employee_name,
        hw.idcardno,
        SUM(al.apportioned_cost + al.incentive_cost)::float as total_labour_cost,
        COUNT(DISTINCT (al.work_date::text || '-' || al.work_hour::text)) as total_hours_worked
    FROM apportioned_logs al
    JOIN hourly_wage hw ON hw.emp_id = al.emp_id
    GROUP BY al.emp_id, hw.fname, hw.lname, hw.idcardno
),
paginated_employees AS (
    SELECT 
        ec.emp_id,
        ec.employee_name,
        ec.idcardno,
        ROUND(ec.total_labour_cost::numeric, 2)::float as total_labour_cost,
        ec.total_hours_worked,
        count(*) over() as total_count
    FROM employee_cost ec
    ORDER BY ec.total_labour_cost DESC
    LIMIT :limit OFFSET :offset
),
plan_orders AS MATERIALIZED (
    SELECT 
        pd.production_plan_id,
        string_agg(DISTINCT cp.order_unique, ', ') as order_unique
    FROM plan_details pd
    JOIN order_items_extract oie ON oie.extract_id = pd.order_extract_id
    JOIN customer_purchase_items cpi ON cpi.items_id = oie.order_items_id
    JOIN customer_purchase cp ON cp.customer_purchase_id = cpi.customer_purchase_id
    WHERE pd.deleted IS NOT TRUE
      AND pd.production_plan_id IN (
          SELECT DISTINCT pt.production_plan_id 
          FROM apportioned_logs al
          JOIN paginated_employees pe ON pe.emp_id = al.emp_id
          JOIN plan_targets pt ON pt.plan_target_id = al.target_id
      )
    GROUP BY pd.production_plan_id
),
est_cost AS MATERIALIZED (
    SELECT 
        lc.product_id,
        (elem->>'stage_id')::int AS stage_id,
        sum((elem->>'rate')::numeric) AS rate
    FROM labour_cost lc
    JOIN (
        SELECT DISTINCT COALESCE(pt.product_id, pp.product_id) as product_id
        FROM apportioned_logs al
        JOIN paginated_employees pe ON pe.emp_id = al.emp_id
        JOIN plan_targets pt ON pt.plan_target_id = al.target_id
        JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
        WHERE COALESCE(pt.product_id, pp.product_id) IS NOT NULL
    ) ep ON ep.product_id = lc.product_id
    CROSS JOIN LATERAL json_array_elements(COALESCE(lc.add_attribute::json, '[]'::json)) AS elem
    WHERE lc.compcode = :compcode and lc.deleted is not true
    GROUP BY lc.product_id, stage_id
),
employee_hours AS (
    SELECT
        sub.emp_id,
        json_agg(
            jsonb_build_object(
                'work_date', sub.work_date,
                'work_hour', sub.work_hour,
                'hourly_salary', sub.hourly_salary,
                'plans', sub.plans_worked
            )
        ) as hours_worked
    FROM (
        SELECT 
            sub2.emp_id,
            sub2.work_date,
            sub2.work_hour,
            hw.hourly_rate as hourly_salary,
            json_agg(
                jsonb_build_object(
                    'production_plan_id', sub2.production_plan_id,
                    'order_unique', sub2.order_unique,
                    'plan_unique', sub2.plan_unique,
                    'product_name', sub2.product_name,
                    'product_code', sub2.product_code,
                    'stage_name', sub2.stage_name,
                    'process_name', sub2.process_name,
                    'produced_qty', coalesce(sub2.produced_qty, 0),
                    'actual_cost', coalesce(sub2.actual_cost, 0),
                    'estimated_cost', (coalesce(sub2.produced_qty, 0) * coalesce(sub2.rate, 0))::float
                )
            ) as plans_worked
        FROM (
            SELECT 
                al.emp_id, 
                al.work_date,
                al.work_hour,
                pp.production_plan_id, 
                pp.plan_unique, 
                COALESCE(po.order_unique, '-') as order_unique,
                COALESCE(p.product_name, p.product_code) as product_name,
                p.product_code,
                s.stage_name,
                pc.process_name,
                SUM(al.outward_qty)::float as produced_qty,
                SUM(al.apportioned_cost + al.incentive_cost)::float as actual_cost,
                ec.rate
            FROM apportioned_logs al
            JOIN paginated_employees pe ON pe.emp_id = al.emp_id
            JOIN plan_targets pt ON pt.plan_target_id = al.target_id
            JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
            LEFT JOIN products p ON p.product_id = COALESCE(pt.product_id, pp.product_id) and p.deleted is not true
            LEFT JOIN est_cost ec ON ec.product_id = p.product_id AND ec.stage_id = al.stage_id
            LEFT JOIN plan_orders po ON po.production_plan_id = pp.production_plan_id
            LEFT JOIN process_config pc ON pc.process_id = al.process_id and pc.deleted is not true
            LEFT JOIN stage s ON s.stage_id = al.stage_id and s.deleted is not true
            GROUP BY al.emp_id, al.work_date, al.work_hour, pp.production_plan_id, pp.plan_unique, po.order_unique, p.product_name, p.product_code, s.stage_name, pc.process_name, ec.rate
        ) sub2
        JOIN hourly_wage hw ON hw.emp_id = sub2.emp_id
        GROUP BY sub2.emp_id, sub2.work_date, sub2.work_hour, hw.hourly_rate
    ) sub
    GROUP BY sub.emp_id
)
SELECT 
    pe.emp_id,
    pe.employee_name,
    pe.idcardno,
    pe.total_labour_cost,
    pe.total_hours_worked,
    COALESCE(eh.hours_worked, '[]'::json) as hours_worked,
    pe.total_count
FROM paginated_employees pe
LEFT JOIN employee_hours eh ON eh.emp_id = pe.emp_id
ORDER BY pe.total_labour_cost DESC
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        compcode=compcode,
                                                        limit=results_per_page,
                                                        start_date=start_date,
                                                        end_date=end_date,
                                                        emp_id=emp_id,
                                                        offset=offset))

        return {
            'total_results': result[0].get('total_count') if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }

