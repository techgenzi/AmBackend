import datetime
import json
from flask import request, jsonify
from flask_restx import Resource
from ipss_utils.decorators import login_required
from sqlalchemy import text
from .. import db_client
from ..routes.dashboard import dashboard_api_route
from ipss_utils.redis.ipss_redis import query_to_dict

@dashboard_api_route.route('/consolidated_dashboard')
class ConsolidatedDashboard(Resource):
    @login_required()
    def get(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', start_date)

        date_con_el = ""
        date_con_att = ""
        if start_date:
            date_con_el = " and el.opertaion_start_date >= cast(:start_date as timestamp) and el.opertaion_start_date < cast(:end_date as timestamp) + interval '1 day' "
            date_con_att = " and a.attendance_date >= cast(:start_date as timestamp) and a.attendance_date < cast(:end_date as timestamp) + interval '1 day' "
        else:
            today = datetime.datetime.today().strftime('%Y-%m-%d')
            date_con_el = f" and el.opertaion_start_date >= cast('{today}' as timestamp) and el.opertaion_start_date < cast('{today}' as timestamp) + interval '1 day' "
            date_con_att = f" and a.attendance_date >= cast('{today}' as timestamp) and a.attendance_date < cast('{today}' as timestamp) + interval '1 day' "
            start_date = today
            end_date = today

        # 1. Fetch Blocks (Floors)
        floors_query = text(f"""
            SELECT floor_id, floor_name, description as block_name 
            FROM floor 
            WHERE compcode = :compcode AND deleted is not true
        """)
        floors = query_to_dict(db_client.engine.execute(floors_query, compcode=compcode))

        # 2. Block-wise Costs & Quantities from Unified Daily Fact
        mv_logic = text("""
            SELECT 
                floor_id,
                COUNT(DISTINCT (emp_id::text || '_' || execution_date::text)) as used_man_days,
                COUNT(DISTINCT emp_id) as distinct_floor_operators,
                SUM(outward_qty) as wip_operations_qty,
                SUM(actual_labour_cost) as actual_direct_labour_cost,
                SUM(estimated_labour_cost) as total_estimated_cost,
                SUM(actual_material_cost) as total_material_cost,
                SUM(estimated_material_cost) as estimated_material_cost
            FROM mv_daily_manufacturing_fact
            WHERE compcode = :compcode
              AND execution_date >= cast(:start_date as date) 
              AND execution_date <= cast(:end_date as date)
            GROUP BY floor_id
        """)
        mv_data = query_to_dict(db_client.engine.execute(mv_logic, compcode=compcode, start_date=start_date, end_date=end_date))

        # Overall distinct shopfloor operators & total man-days across all floors
        mv_overall_logic = text("""
            SELECT 
                COUNT(DISTINCT emp_id) as total_distinct_operators,
                COUNT(DISTINCT (emp_id::text || '_' || execution_date::text)) as total_distinct_man_days
            FROM mv_daily_manufacturing_fact
            WHERE compcode = :compcode
              AND execution_date >= cast(:start_date as date) 
              AND execution_date <= cast(:end_date as date)
        """)
        try:
            mv_overall_res = db_client.engine.execute(mv_overall_logic, compcode=compcode, start_date=start_date, end_date=end_date).fetchone()
            total_distinct_operators = int(mv_overall_res['total_distinct_operators'] or 0) if mv_overall_res else 0
        except Exception:
            total_distinct_operators = 0

        # Original Produced Qty Logic (Final stage only)
        final_qty_logic = text(f"""
            SELECT 
                CASE 
                    WHEN lc.line_name = 'Medline Cutting Line 1' THEN 2
                    WHEN lc.line_name LIKE 'LV240%' OR lc.line_name LIKE '048%' OR lc.line_name LIKE '%Nada%' OR lc.line_name LIKE 'Patient Gown%' THEN 1
                    WHEN lc.line_name LIKE 'IG 27SMS2%' OR lc.line_name LIKE 'EP Line%' OR lc.line_name LIKE 'Labcoat%' OR lc.line_name LIKE 'Medline%' OR lc.line_name LIKE 'Pillow%' OR lc.line_name LIKE 'Shorts%' THEN 3
                    ELSE COALESCE(pp.floor_id, 0)
                END as floor_id, 
                SUM(el.outward_qty) as produced_qty
            FROM execution_log el
            JOIN plan_targets pt ON pt.plan_target_id = el.target_id AND pt.deleted IS NOT TRUE
            JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
            LEFT JOIN line_config lc ON lc.line_config_id = el.line_id
            JOIN production_stages ps ON ps.product_id = pt.product_id AND ps.stage_id = el.stage_id AND ps.deleted IS NOT TRUE
            JOIN activity_stage_map asm ON asm.production_stage_id = ps.id AND asm.is_final_process IS TRUE AND (el.process_id IS NULL OR asm.config_id = el.process_id) AND asm.deleted IS NOT TRUE
            WHERE el.compcode = :compcode AND el.deleted IS NOT TRUE AND coalesce(el.outward_qty, 0) > 0 {date_con_el}
              AND ps.rank_id = (SELECT MAX(rank_id) FROM production_stages WHERE product_id = pt.product_id AND deleted IS NOT TRUE)
            GROUP BY 1
        """)
        final_qty_data = query_to_dict(db_client.engine.execute(final_qty_logic, compcode=compcode, start_date=start_date, end_date=end_date))

        # Active manpower per floor (attributed to the operator's primary active floor/line based on production output)
        # Enforces outward_qty > 0 (filters 0-effort logs) and maps line configurations to actual blocks (e.g. Medline Cutting Line 1 -> B2)
        attendance_floor_logic = text(f"""
            WITH emp_floor_activity AS (
                SELECT 
                    el.emp_id, 
                    CASE 
                        WHEN lc.line_name = 'Medline Cutting Line 1' THEN 2
                        WHEN lc.line_name LIKE 'LV240%' OR lc.line_name LIKE '048%' OR lc.line_name LIKE '%Nada%' OR lc.line_name LIKE 'Patient Gown%' THEN 1
                        WHEN lc.line_name LIKE 'IG 27SMS2%' OR lc.line_name LIKE 'EP Line%' OR lc.line_name LIKE 'Labcoat%' OR lc.line_name LIKE 'Medline%' OR lc.line_name LIKE 'Pillow%' OR lc.line_name LIKE 'Shorts%' THEN 3
                        ELSE COALESCE(pp.floor_id, 0)
                    END as floor_id,
                    COUNT(DISTINCT el.hour_config_id) as floor_hrs,
                    SUM(COALESCE(el.outward_qty, 0)) as floor_qty,
                    ROW_NUMBER() OVER (
                        PARTITION BY el.emp_id 
                        ORDER BY COUNT(DISTINCT el.hour_config_id) DESC, SUM(COALESCE(el.outward_qty, 0)) DESC
                    ) as rn
                FROM execution_log el
                JOIN plan_targets pt ON pt.plan_target_id = el.target_id
                JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
                LEFT JOIN line_config lc ON lc.line_config_id = el.line_id
                WHERE el.compcode = :compcode AND el.deleted IS NOT TRUE AND COALESCE(el.outward_qty, 0) > 0 {date_con_el}
                GROUP BY el.emp_id, 2
            )
            SELECT 
                efa.floor_id,
                COUNT(DISTINCT efa.emp_id) as actual_manpower
            FROM emp_floor_activity efa
            WHERE efa.rn = 1
            GROUP BY efa.floor_id
        """)
        try:
            att_floor_data = query_to_dict(db_client.engine.execute(attendance_floor_logic, compcode=compcode, start_date=start_date, end_date=end_date))
        except Exception:
            att_floor_data = []


        # Block-wise Material Cost is now fetched from Unified Daily Fact (mv_data)

        # Merge direct data, estimated data, attendance data into floors
        floor_results = []
        for f in floors:
            f_id = int(float(f['floor_id'])) if f['floor_id'] is not None else None
            mv_row = next((item for item in mv_data if item['floor_id'] is not None and int(float(item['floor_id'])) == f_id), None)
            qty_row = next((item for item in final_qty_data if item['floor_id'] is not None and int(float(item['floor_id'])) == f_id), None)
            att_row = next((item for item in att_floor_data if item['floor_id'] is not None and int(float(item['floor_id'])) == f_id), None)
            
            f['produced_qty'] = float(qty_row['produced_qty']) if qty_row and qty_row['produced_qty'] else 0
            f['fg_produced_qty'] = f['produced_qty']
            f['wip_operations_qty'] = float(mv_row['wip_operations_qty']) if mv_row and mv_row['wip_operations_qty'] else 0
            f['stage_output_qty'] = f['wip_operations_qty']
            f['used_man_days'] = int(mv_row['used_man_days']) if mv_row and mv_row['used_man_days'] else 0
            f['actual_manpower'] = int(att_row['actual_manpower']) if att_row and att_row['actual_manpower'] else f['used_man_days']
            f['actual_direct_labour_cost'] = float(mv_row['actual_direct_labour_cost']) if mv_row and mv_row['actual_direct_labour_cost'] else 0
            f['estimated_cost'] = float(mv_row['total_estimated_cost']) if mv_row and mv_row['total_estimated_cost'] else 0
            f['difference_cost'] = f['estimated_cost'] - f['actual_direct_labour_cost']
            f['material_cost'] = float(mv_row['total_material_cost']) if mv_row and mv_row['total_material_cost'] else 0
            f['estimated_material_cost'] = float(mv_row['estimated_material_cost']) if mv_row and mv_row['estimated_material_cost'] else 0
            floor_results.append(f)

        # 3. Labour Cadre (Present vs Allocated vs Non-Allocated) & Department-wise Overhead
        # Accounts for unallocated employees (8h) and partial-shift direct workers (<8h unlogged idle floor hours)
        cadre_logic = text(f"""
            WITH att_present AS (
                SELECT DISTINCT a.hremploymastid as emp_id
                FROM att a
                WHERE a.raw_attdate >= cast(:start_date as timestamp) and a.raw_attdate < cast(:start_date as timestamp) + interval '1 day'
            ),
            allocated_emp AS (
                SELECT 
                    el.emp_id,
                    COUNT(DISTINCT el.hour_config_id) as worked_hours
                FROM execution_log el
                WHERE el.compcode = :compcode AND el.deleted IS NOT TRUE AND COALESCE(el.outward_qty, 0) > 0 {date_con_el}
                GROUP BY el.emp_id
            ),
            emp_details AS (
                SELECT 
                    h.hremploymastid as emp_id,
                    trim(concat(h.fname, ' ', coalesce(h.mname, ''), ' ', coalesce(h.lname, ''))) as employeename,
                    h.idcardno as emp_code,
                    CASE
                        WHEN h.daily_wages = TRUE THEN round((NULLIF(h.ctc_amount, '')::numeric / 8), 2)
                        ELSE round((NULLIF(h.ctc_amount, '')::numeric / (30 * 8)), 2)
                    END as hourly_rate,
                    COALESCE(dm.dept_name, 'Unassigned') as department,
                    COALESCE(desg.desg_name, 'Unassigned') as designation
                FROM hremploymast h
                LEFT JOIN department_mast dm ON dm.deptmastid = NULLIF(TRIM(h.deptname::text), '')::bigint
                LEFT JOIN designation_mast desg ON desg.desgmastid = NULLIF(TRIM(h.designation::text), '')::bigint
            )
            SELECT 
                ed.department,
                COUNT(DISTINCT ap.emp_id) as total_present,
                COUNT(DISTINCT CASE WHEN ae.emp_id IS NOT NULL THEN ap.emp_id END) as allocated_count,
                COUNT(DISTINCT CASE WHEN ae.emp_id IS NULL THEN ap.emp_id END) as non_allocated_count,
                SUM(
                    CASE 
                        WHEN ae.emp_id IS NULL THEN 8 * ed.hourly_rate 
                        WHEN ae.worked_hours < 8 THEN (8 - ae.worked_hours) * ed.hourly_rate
                        ELSE 0 
                    END
                ) as indirect_cost,
                SUM(
                    CASE 
                        WHEN ae.emp_id IS NOT NULL AND ae.worked_hours < 8 THEN (8 - ae.worked_hours) * ed.hourly_rate
                        ELSE 0 
                    END
                ) as partial_idle_cost,
                COUNT(DISTINCT CASE WHEN ae.emp_id IS NOT NULL AND ae.worked_hours < 8 THEN ap.emp_id END) as partial_workers_count,
                json_agg(
                    json_build_object(
                        'emp_id', ap.emp_id,
                        'emp_name', ed.employeename,
                        'emp_code', ed.emp_code,
                        'department', ed.department,
                        'designation', ed.designation,
                        'indirect_hours', CASE WHEN ae.emp_id IS NULL THEN 8 ELSE GREATEST(8 - ae.worked_hours, 0) END,
                        'indirect_cost', CASE WHEN ae.emp_id IS NULL THEN 8 * ed.hourly_rate ELSE GREATEST(8 - ae.worked_hours, 0) * ed.hourly_rate END,
                        'type', CASE WHEN ae.emp_id IS NULL THEN 'Unallocated Cadre' ELSE 'Floor Idle Time (<8h)' END
                    )
                ) FILTER (WHERE ae.emp_id IS NULL OR ae.worked_hours < 8) as employees
            FROM att_present ap
            JOIN emp_details ed ON ed.emp_id = ap.emp_id
            LEFT JOIN allocated_emp ae ON ae.emp_id = ap.emp_id
            GROUP BY ed.department
        """)

        try:
            cadre_data = query_to_dict(db_client.engine.execute(cadre_logic, compcode=compcode, start_date=start_date, end_date=end_date))
        except Exception:
            cadre_data = []

        # Fallback if att table has no records for the selected date
        if not cadre_data:
            indirect_logic = text(f"""
                WITH hourly_wage AS (
                    SELECT 
                        h.hremploymastid as emp_id,
                        trim(concat(h.fname, ' ', coalesce(h.mname, ''), ' ', coalesce(h.lname, ''))) as employeename,
                        h.idcardno as emp_code,
                        CASE
                            WHEN h.daily_wages = TRUE THEN round((NULLIF(h.ctc_amount, '')::numeric / 8), 2)
                            ELSE round((NULLIF(h.ctc_amount, '')::numeric / (30 * 8)), 2)
                        END as hourly_rate,
                        COALESCE(dm.dept_name, 'Unassigned') as department,
                        COALESCE(desg.desg_name, 'Unassigned') as designation
                    FROM hremploymast h
                    LEFT JOIN department_mast dm ON dm.deptmastid = NULLIF(TRIM(h.deptname::text), '')::bigint
                    LEFT JOIN designation_mast desg ON desg.desgmastid = NULLIF(TRIM(h.designation::text), '')::bigint
                ),
                log_with_apportion AS (
                    SELECT 
                        el.emp_id, date(el.opertaion_start_date) as work_date, count(DISTINCT hc.record_id) as worked_hours
                    FROM execution_log el
                    LEFT JOIN hour_config hc ON hc.record_id = el.hour_config_id
                    WHERE el.deleted is not true and el.compcode = :compcode {date_con_el}
                    GROUP BY el.emp_id, date(el.opertaion_start_date)
                )
                SELECT 
                    hw.department,
                    COUNT(DISTINCT lwa.emp_id) as total_present,
                    COUNT(DISTINCT lwa.emp_id) as allocated_count,
                    0 as non_allocated_count,
                    SUM(GREATEST(8 - lwa.worked_hours, 0) * hw.hourly_rate) as indirect_cost,
                    json_agg(
                        json_build_object(
                            'emp_id', lwa.emp_id,
                            'emp_name', hw.employeename,
                            'emp_code', hw.emp_code,
                            'department', hw.department,
                            'designation', hw.designation,
                            'indirect_hours', GREATEST(8 - lwa.worked_hours, 0),
                            'indirect_cost', GREATEST(8 - lwa.worked_hours, 0) * hw.hourly_rate
                        )
                    ) as employees
                FROM log_with_apportion lwa
                JOIN hourly_wage hw ON hw.emp_id = lwa.emp_id
                GROUP BY hw.department
            """)
            cadre_data = query_to_dict(db_client.engine.execute(indirect_logic, compcode=compcode, start_date=start_date, end_date=end_date))

        total_present = sum(int(row.get('total_present', 0) or 0) for row in cadre_data)
        total_allocated = sum(int(row.get('allocated_count', 0) or 0) for row in cadre_data)
        total_non_allocated = sum(int(row.get('non_allocated_count', 0) or 0) for row in cadre_data)

        for row in cadre_data:
            row['indirect_cost'] = float(row['indirect_cost']) if row.get('indirect_cost') else 0
            row['partial_idle_cost'] = float(row['partial_idle_cost']) if row.get('partial_idle_cost') else 0
            row['partial_workers_count'] = int(row.get('partial_workers_count', 0) or 0)
            row['headcount'] = int(row.get('non_allocated_count', 0) or 0)
            row['total_indirect_headcount'] = row['headcount'] + row['partial_workers_count']
            if isinstance(row.get('employees'), str):
                try:
                    row['employees'] = json.loads(row['employees'])
                except Exception:
                    row['employees'] = []
            elif row.get('employees') is None:
                row['employees'] = []

        total_produced_qty_query = text(f"""
            SELECT sum(el.outward_qty) as total
            FROM execution_log el
            JOIN plan_targets pt ON pt.plan_target_id = el.target_id
            JOIN production_stages ps ON ps.product_id = pt.product_id AND ps.stage_id = el.stage_id AND ps.deleted IS NOT TRUE
            JOIN activity_stage_map asm ON asm.production_stage_id = ps.id AND asm.is_final_process IS TRUE AND (el.process_id IS NULL OR asm.config_id = el.process_id) AND asm.deleted IS NOT TRUE
            WHERE el.compcode = :compcode AND el.opertaion_start_date >= cast(:start_date as timestamp) and el.opertaion_start_date < cast(:start_date as timestamp) + interval '1 day' AND el.deleted IS NOT TRUE AND coalesce(el.outward_qty, 0) > 0
              AND ps.rank_id = (SELECT MAX(rank_id) FROM production_stages WHERE product_id = pt.product_id AND deleted IS NOT TRUE)
        """)
        try:
            total_prod_res = db_client.engine.execute(total_produced_qty_query, compcode=compcode, start_date=start_date).fetchone()
            total_produced_qty = float(total_prod_res['total'] or 0) if total_prod_res else 0
        except Exception:
            total_produced_qty = sum(f['produced_qty'] for f in floor_results)

        total_estimated_cost = sum(f['estimated_cost'] for f in floor_results)
        total_actual_cost = sum(f['actual_direct_labour_cost'] for f in floor_results)
        
        total_material_cost = sum(f.get('material_cost', 0) for f in floor_results)
        total_difference_cost = total_estimated_cost - total_actual_cost

        # Sum of floor allocations (gross man-days)
        gross_floor_man_days = sum(f.get('used_man_days', 0) for f in floor_results)
        gross_floor_actual_manpower = sum(f.get('actual_manpower', 0) for f in floor_results)

        return {
            "success": True,
            "message": "Consolidated dashboard data fetched successfully",
            "data": {
                "kpis": {
                    "total_present": total_present if total_present > 0 else gross_floor_man_days,
                    "total_allocated": total_allocated if total_allocated > 0 else gross_floor_man_days,
                    "total_non_allocated": total_non_allocated,
                    "total_distinct_operators": total_distinct_operators if total_distinct_operators > 0 else total_allocated,
                    "total_used_man_days": gross_floor_man_days,
                    "total_used_manpower": gross_floor_man_days,
                    "total_actual_manpower": gross_floor_actual_manpower,
                    "total_produced_qty": total_produced_qty,
                    "total_fg_produced_qty": total_produced_qty,
                    "total_wip_operations_qty": sum(f.get('wip_operations_qty', 0) for f in floor_results),
                    "total_stage_output_qty": sum(f.get('wip_operations_qty', 0) for f in floor_results),
                    "total_estimated_cost": total_estimated_cost,
                    "total_actual_cost": total_actual_cost,
                    "total_material_cost": total_material_cost,
                    "total_difference_cost": total_difference_cost
                },
                "blocks": floor_results,
                "overhead_departments": cadre_data
            }
        }


@dashboard_api_route.route('/consolidated_dashboard/floor_details')
class FloorDetailsResource(Resource):
    @login_required()
    def get(self):
        try:
            current_user_raw = request.args.get('current_user', {})
            current_user = json.loads(current_user_raw) if isinstance(current_user_raw, str) else current_user_raw
            compcode = current_user.get('company_id', 1)
            start_date = request.args.get('start_date')
            floor_id = request.args.get('floor_id')

            if not start_date or not floor_id:
                return {"success": False, "message": "start_date and floor_id are required"}, 400

            details_query = text(f"""
                WITH active_logs AS (
                    SELECT 
                        el.emp_id,
                        el.target_id,
                        el.stage_id,
                        el.process_id,
                        el.outward_qty,
                        date(el.opertaion_start_date) as work_date,
                        hc.time_value as work_hour,
                        el.hour_config_id,
                        count(*) over(partition by el.emp_id, date(el.opertaion_start_date), hc.record_id) as logs_in_hour
                    FROM execution_log el
                    LEFT JOIN hour_config hc ON hc.record_id = el.hour_config_id
                    WHERE el.deleted is not true and el.compcode = :compcode AND coalesce(el.outward_qty, 0) > 0 
                      and el.opertaion_start_date >= cast(:start_date as timestamp) and el.opertaion_start_date < cast(:start_date as timestamp) + interval '1 day'
                ),
                hourly_wage AS MATERIALIZED (
                    SELECT 
                        h.hremploymastid as emp_id,
                        trim(concat(h.fname, ' ', coalesce(h.mname, ''), ' ', coalesce(h.lname, ''))) as employeename,
                        CASE
                            WHEN h.daily_wages = TRUE THEN round((NULLIF(h.ctc_amount, '')::numeric / 8), 2)
                            ELSE round((NULLIF(h.ctc_amount, '')::numeric / (30 * 8)), 2)
                        END as hourly_rate
                    FROM hremploymast h
                    WHERE h.hremploymastid IN (SELECT DISTINCT emp_id FROM active_logs)
                ),
                floor_mapping AS (
                    SELECT stage_id, max(floor_id) as floor_id FROM floor_stage_map WHERE deleted is not true GROUP BY stage_id
                ),
                apportioned_logs AS (
                    SELECT 
                        l.emp_id, l.target_id, l.stage_id, l.process_id, l.outward_qty, l.work_date, l.work_hour,
                        (hw.hourly_rate / l.logs_in_hour) as apportioned_cost,
                        hw.employeename,
                        COALESCE(pp.floor_id, fm.floor_id) as floor_id,
                        COALESCE(inc.incentive_amount, 0) as incentive_cost,
                        COALESCE(asm_check.is_final_process, false) as is_final_process
                    FROM active_logs l
                    JOIN hourly_wage hw ON hw.emp_id = l.emp_id
                    JOIN plan_targets pt ON pt.plan_target_id = l.target_id
                    JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
                    LEFT JOIN floor_mapping fm ON fm.stage_id = l.stage_id
                    LEFT JOIN LATERAL (
                        SELECT asm.is_final_process
                        FROM activity_stage_map asm
                        JOIN production_stages ps ON ps.id = asm.production_stage_id
                        WHERE ps.product_id = pt.product_id AND ps.stage_id = l.stage_id
                          AND (l.process_id IS NULL OR asm.config_id = l.process_id)
                          AND asm.deleted IS NOT TRUE
                        LIMIT 1
                    ) asm_check ON true
                    LEFT JOIN LATERAL (
                        SELECT pis.incentive_amount
                        FROM activity_stage_map asm
                        JOIN production_stages ps ON ps.id = asm.production_stage_id
                        JOIN process_incentive_slabs pis ON pis.activity_stage_map_id = asm.activity_stage_map_id AND pis.deleted IS NOT TRUE
                        WHERE ps.product_id = pt.product_id AND ps.stage_id = l.stage_id
                          AND (l.process_id IS NULL OR asm.config_id = l.process_id)
                          AND asm.deleted IS NOT TRUE
                          AND (l.outward_qty - asm.target_per_hour) >= pis.from_qty 
                          AND (pis.to_qty IS NULL OR (l.outward_qty - asm.target_per_hour) <= pis.to_qty)
                        ORDER BY pis.from_qty DESC LIMIT 1
                    ) inc ON true
                    WHERE COALESCE(pp.floor_id, fm.floor_id) = :floor_id
                ),
                plan_orders AS MATERIALIZED (
                    SELECT 
                        pd.production_plan_id,
                        string_agg(DISTINCT cp.order_unique, ', ') as order_no
                    FROM plan_details pd
                    JOIN order_items_extract oie ON oie.extract_id = pd.order_extract_id
                    JOIN customer_purchase_items cpi ON cpi.items_id = oie.order_items_id
                    JOIN customer_purchase cp ON cp.customer_purchase_id = cpi.customer_purchase_id
                    WHERE pd.deleted IS NOT TRUE
                      AND pd.production_plan_id IN (
                          SELECT DISTINCT pt.production_plan_id 
                          FROM apportioned_logs al
                          JOIN plan_targets pt ON pt.plan_target_id = al.target_id
                      )
                    GROUP BY pd.production_plan_id
                ),
                floor_plans AS (
                    SELECT DISTINCT pp.production_plan_id
                    FROM apportioned_logs al_sub
                    JOIN plan_targets pt_sub ON pt_sub.plan_target_id = al_sub.target_id
                    JOIN production_plan pp ON pp.production_plan_id = pt_sub.production_plan_id
                ),
                allocated AS (
                    SELECT prod_plan_id, product_id, sum(allocated_amount) as allocated_amount 
                    FROM plan_allocation 
                    WHERE deleted is not true AND prod_plan_id IN (SELECT production_plan_id FROM floor_plans)
                    GROUP BY prod_plan_id, product_id
                ),
                dispatched AS (
                    SELECT inv.prod_plan_id, inv.product_id, sum(d.dispatch_amount) as dispatch_amount 
                    FROM invregistry inv
                    JOIN dispatch d ON d.releseid = inv.releseid
                    WHERE inv.prod_plan_id IN (SELECT production_plan_id FROM floor_plans)
                    GROUP BY inv.prod_plan_id, inv.product_id
                ),
                returned AS (
                    SELECT rm.prod_plan_id, rm.product_id, sum(rm.return_amount) as return_amount 
                    FROM return_material rm
                    WHERE rm.status = 'Moved' AND rm.prod_plan_id IN (SELECT production_plan_id FROM floor_plans)
                    GROUP BY rm.prod_plan_id, rm.product_id
                ),
                consumed AS (
                    SELECT 
                        coalesce(a.prod_plan_id, d.prod_plan_id, r.prod_plan_id) as prod_plan_id,
                        coalesce(a.product_id, d.product_id, r.product_id) as product_id,
                        (coalesce(a.allocated_amount, 0) + coalesce(d.dispatch_amount, 0) - coalesce(r.return_amount, 0)) as consumed_qty
                    FROM allocated a
                    FULL OUTER JOIN dispatched d ON a.prod_plan_id = d.prod_plan_id AND a.product_id = d.product_id
                    FULL OUTER JOIN returned r ON coalesce(a.prod_plan_id, d.prod_plan_id) = r.prod_plan_id AND coalesce(a.product_id, d.product_id) = r.product_id
                ),
                plan_material AS (
                    SELECT c.prod_plan_id as production_plan_id, sum(c.consumed_qty * coalesce(mc.cost, 0)) as total_material_cost 
                    FROM consumed c
                    LEFT JOIN material_cost mc ON mc.product_id = c.product_id
                    GROUP BY c.prod_plan_id
                )
                SELECT
                    pp.production_plan_id as production_plan_id,
                    COALESCE(pp.plan_unique, 'Unknown Plan') as plan_no,
                    COALESCE(po.order_no, 'Unknown Order') as order_no,
                    COALESCE(
                        p.product_name, 
                        MAX(p_target.product_name),
                        (
                            SELECT string_agg(p2.product_name, ', ')
                            FROM production_plan_products ppp
                            JOIN products p2 ON p2.product_id = ppp.product_id
                            WHERE ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
                        ),
                        'Unknown Product'
                    ) as product_name,
                    MAX(COALESCE(pp.planed_quantity, 0)) as planned_qty,
                    COALESCE(
                        NULLIF(SUM(CASE WHEN al.is_final_process IS TRUE THEN al.outward_qty ELSE 0 END), 0),
                        SUM(al.outward_qty)
                    ) as produced_qty,
                    COUNT(DISTINCT al.emp_id) as no_of_labours,
                    SUM(al.apportioned_cost + al.incentive_cost) as actual_direct_labour_cost,
                    MAX(COALESCE(pmc.total_material_cost, 0)) as material_cost,
                    SUM(al.incentive_cost) as incentive_cost
                FROM apportioned_logs al
                LEFT JOIN plan_targets pt ON pt.plan_target_id = al.target_id
                LEFT JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
                LEFT JOIN products p ON p.product_id = pp.product_id
                LEFT JOIN products p_target ON p_target.product_id = pt.product_id
                LEFT JOIN plan_orders po ON po.production_plan_id = pp.production_plan_id
                LEFT JOIN plan_material pmc ON pmc.production_plan_id = pp.production_plan_id
                GROUP BY pp.production_plan_id, pp.plan_unique, po.order_no, p.product_name
            """)
            
            result = query_to_dict(db_client.engine.execute(details_query, compcode=compcode, start_date=start_date, floor_id=floor_id))
            
            for row in result:
                row['planned_qty'] = float(row['planned_qty']) if row['planned_qty'] else 0
                row['produced_qty'] = float(row['produced_qty']) if row['produced_qty'] else 0
                row['no_of_labours'] = int(row['no_of_labours']) if row['no_of_labours'] else 0
                row['material_cost'] = float(row['material_cost']) if row['material_cost'] else 0
                row['actual_direct_labour_cost'] = float(row['actual_direct_labour_cost']) if row['actual_direct_labour_cost'] else 0
                row['incentive_cost'] = float(row['incentive_cost']) if row['incentive_cost'] else 0
                
            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "message": str(e)}, 500


@dashboard_api_route.route('/consolidated_dashboard_floor_labour')
class ConsolidatedDashboardFloorLabour(Resource):
    @login_required()
    def get(self):
        current_user_raw = request.args.get('current_user', {})
        if isinstance(current_user_raw, str):
            try:
                current_user = json.loads(current_user_raw)
            except Exception:
                current_user = {}
        elif isinstance(current_user_raw, dict):
            current_user = current_user_raw
        else:
            current_user = {}

        compcode = current_user.get('company_id', 1) or 1
        start_date = request.args.get('start_date', None)
        floor_id = request.args.get('floor_id', None)
        if not start_date or not floor_id:
            return {'success': False, 'message': 'Missing parameters'}, 400
        
        try:
            floor_id = int(floor_id)
            compcode = int(compcode)
            query = text("""
                WITH base_logs AS (
                    SELECT 
                        el.emp_id,
                        el.target_id,
                        el.stage_id,
                        el.process_id,
                        el.outward_qty,
                        date(el.opertaion_start_date) as work_date,
                        hc.time_value as work_hour,
                        el.hour_config_id,
                        pt.production_plan_id,
                        pt.product_id,
                        pt.target_quantity as default_target_qty,
                        count(*) over(partition by el.emp_id, el.opertaion_start_date::date, el.hour_config_id) as logs_in_hour
                    FROM execution_log el
                    LEFT JOIN hour_config hc ON hc.record_id = el.hour_config_id
                    JOIN plan_targets pt ON pt.plan_target_id = el.target_id
                    JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
                    LEFT JOIN LATERAL (
                        SELECT floor_id 
                        FROM floor_stage_map 
                        WHERE stage_id = el.stage_id AND deleted is not true 
                        ORDER BY (floor_id = :floor_id) DESC 
                        LIMIT 1
                    ) fsm ON true
                    WHERE el.compcode = :compcode AND el.deleted is not true 
                      AND COALESCE(pp.floor_id, fsm.floor_id) = :floor_id
                      AND el.opertaion_start_date >= cast(:start_date as timestamp) 
                      AND el.opertaion_start_date < cast(:start_date as timestamp) + interval '1 day'
                ),
                hourly_wage AS MATERIALIZED (
                    SELECT 
                        h.hremploymastid as emp_id,
                        h.idcardno as emp_code,
                        trim(concat(h.fname, ' ', coalesce(h.mname, ''), ' ', coalesce(h.lname, ''))) as emp_name,
                        CASE
                            WHEN h.daily_wages = TRUE THEN round((NULLIF(trim(h.ctc_amount), '')::numeric / 8), 2)
                            ELSE round((NULLIF(trim(h.ctc_amount), '')::numeric / (30 * 8)), 2)
                        END as hourly_rate,
                        CASE
                            WHEN h.daily_wages = TRUE THEN coalesce(NULLIF(trim(h.ctc_amount), ''), '0')::numeric
                            ELSE (coalesce(NULLIF(trim(h.ctc_amount), ''), '0')::numeric / 30)
                        END as day_ctc
                    FROM hremploymast h
                    WHERE h.hremploymastid IN (SELECT DISTINCT emp_id FROM base_logs)
                ),
                apportioned_logs AS (
                    SELECT 
                        bl.production_plan_id,
                        bl.product_id,
                        bl.emp_id,
                        bl.stage_id,
                        bl.process_id,
                        bl.outward_qty,
                        COALESCE(asm_info.target_per_hour, bl.default_target_qty, 0) as target_qty,
                        bl.work_hour,
                        bl.hour_config_id,
                        (hw.hourly_rate / bl.logs_in_hour) as apportioned_cost,
                        COALESCE(inc_info.incentive_amount, 0) as incentive_cost,
                        hw.emp_name,
                        hw.emp_code,
                        hw.day_ctc,
                        hw.hourly_rate
                    FROM base_logs bl
                    JOIN hourly_wage hw ON hw.emp_id = bl.emp_id
                    LEFT JOIN LATERAL (
                        SELECT asm.target_per_hour, asm.activity_stage_map_id
                        FROM activity_stage_map asm
                        JOIN production_stages ps ON ps.id = asm.production_stage_id
                        WHERE ps.product_id = bl.product_id AND ps.stage_id = bl.stage_id 
                          AND (bl.process_id IS NULL OR asm.config_id = bl.process_id)
                          AND asm.deleted IS NOT TRUE
                        LIMIT 1
                    ) asm_info ON true
                    LEFT JOIN LATERAL (
                        SELECT pis.incentive_amount
                        FROM process_incentive_slabs pis
                        WHERE pis.activity_stage_map_id = asm_info.activity_stage_map_id
                          AND pis.deleted IS NOT TRUE
                          AND (bl.outward_qty - asm_info.target_per_hour) >= pis.from_qty
                          AND (pis.to_qty IS NULL OR (bl.outward_qty - asm_info.target_per_hour) <= pis.to_qty)
                        ORDER BY pis.from_qty DESC
                        LIMIT 1
                    ) inc_info ON true
                ),
                emp_summary AS (
                    SELECT 
                        al.emp_id, al.emp_code, al.emp_name, al.day_ctc,
                        COUNT(DISTINCT al.hour_config_id) as worked_hrs,
                        SUM(COALESCE(al.apportioned_cost, 0) + COALESCE(al.incentive_cost, 0)) as labour_cost,
                        json_agg(
                            json_build_object(
                                'hour', al.work_hour,
                                'plan_id', al.production_plan_id,
                                'plan_unique', pp.plan_unique,
                                'product_name', COALESCE(p.product_name, p.product_code, '-'),
                                'product_code', p.product_code,
                                'sku_id', p.sku_id,
                                'stage_name', COALESCE(s.stage_name, '-'),
                                'process_name', COALESCE(pc.process_name, '-'),
                                'target_qty', COALESCE(al.target_qty, 0),
                                'produced_qty', COALESCE(al.outward_qty, 0),
                                'qty', COALESCE(al.outward_qty, 0),
                                'cost', round((COALESCE(al.apportioned_cost, 0) + COALESCE(al.incentive_cost, 0))::numeric, 2)
                            )
                        ) filter (where al.work_hour is not null or pp.plan_unique is not null) as hour_details
                    FROM apportioned_logs al
                    JOIN production_plan pp ON pp.production_plan_id = al.production_plan_id
                    LEFT JOIN products p ON p.product_id = COALESCE(al.product_id, pp.product_id)
                    LEFT JOIN stage s ON s.stage_id = al.stage_id
                    LEFT JOIN process_config pc ON pc.process_id = al.process_id
                    GROUP BY al.emp_id, al.emp_code, al.emp_name, al.day_ctc
                )
                SELECT * FROM emp_summary ORDER BY labour_cost DESC
            """)
            result = query_to_dict(db_client.engine.execute(query, compcode=compcode, start_date=start_date, floor_id=floor_id))
            for row in result:
                row['day_ctc'] = float(row['day_ctc']) if row['day_ctc'] else 0
                row['labour_cost'] = float(row['labour_cost']) if row['labour_cost'] else 0
                if isinstance(row.get('hour_details'), str):
                    try:
                        row['hour_details'] = json.loads(row['hour_details'])
                    except Exception:
                        row['hour_details'] = []
                elif row.get('hour_details') is None:
                    row['hour_details'] = []
            return {'success': True, 'data': result}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}, 500

@dashboard_api_route.route('/consolidated_dashboard_floor_material')
class ConsolidatedDashboardFloorMaterial(Resource):
    @login_required()
    def get(self):
        current_user_raw = request.args.get('current_user', {})
        if isinstance(current_user_raw, str):
            try:
                current_user = json.loads(current_user_raw)
            except Exception:
                current_user = {}
        elif isinstance(current_user_raw, dict):
            current_user = current_user_raw
        else:
            current_user = {}

        compcode = current_user.get('company_id', 1) or 1
        start_date = request.args.get('start_date', None)
        floor_id = request.args.get('floor_id', None)
        if not start_date or not floor_id:
            return {'success': False, 'message': 'Missing parameters'}, 400
        
        try:
            floor_id = int(floor_id)
            compcode = int(compcode)
            query = text("""
                WITH plan_materials AS (
                    SELECT 
                        pp.production_plan_id,
                        bc.product_id as material_id,
                        SUM(COALESCE(el.outward_qty * CAST(NULLIF(bc.quantity, '')::numeric AS numeric), 0)) as consumed_qty,
                        SUM(COALESCE(el.outward_qty * CAST(NULLIF(bc.quantity, '')::numeric AS numeric) * mc.cost, 0)) as total_cost
                    FROM execution_log el
                    JOIN plan_targets pt ON pt.plan_target_id = el.target_id
                    JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
                    JOIN bom b ON b.product_id = COALESCE(el.product_id, pt.product_id, pp.product_id) AND b.deleted IS NOT TRUE
                    LEFT JOIN (
                        SELECT DISTINCT ON (product_id) product_id, stage_id as first_stage_id
                        FROM production_stages WHERE deleted IS NOT TRUE ORDER BY product_id, rank_id ASC, stage_id ASC
                    ) first_stage ON first_stage.product_id = COALESCE(el.product_id, pt.product_id, pp.product_id)
                    JOIN bom_component bc ON bc.bom_id = b.bom_id AND bc.deleted IS NOT TRUE 
                        AND ( (bc.stage_id IS NOT NULL AND bc.stage_id = el.stage_id) OR (bc.stage_id IS NULL AND el.stage_id = first_stage.first_stage_id) )
                    LEFT JOIN material_cost mc ON mc.product_id = bc.product_id
                    LEFT JOIN (
                        SELECT DISTINCT ON (ps.product_id, ps.stage_id)
                               ps.product_id, ps.stage_id, asm.config_id AS last_process_id
                        FROM production_stages ps
                        JOIN activity_stage_map asm ON asm.production_stage_id = ps.id AND asm.deleted IS NOT TRUE
                        WHERE ps.deleted IS NOT TRUE
                        ORDER BY ps.product_id, ps.stage_id, asm.is_final_process DESC, asm.config_id DESC
                    ) slp ON slp.product_id = COALESCE(el.product_id, pt.product_id, pp.product_id) AND slp.stage_id = el.stage_id
                    WHERE el.compcode = :compcode AND el.deleted IS NOT TRUE AND el.opertaion_start_date >= cast(:start_date as timestamp) and el.opertaion_start_date < cast(:start_date as timestamp) + interval '1 day'
                      AND pp.floor_id = :floor_id
                      AND (slp.last_process_id IS NULL OR el.process_id IS NULL OR el.process_id = slp.last_process_id)
                    GROUP BY pp.production_plan_id, bc.product_id
                )
                SELECT 
                    pm.production_plan_id,
                    pp.plan_unique,
                    json_agg(
                        json_build_object(
                            'product_name', p.product_name,
                            'product_code', p.product_code,
                            'sku_id', p.sku_id,
                            'uom', u.uom,
                            'consumed', pm.consumed_qty,
                            'total_cost', pm.total_cost
                        )
                    ) filter (where p.product_code is not null) as materials
                FROM plan_materials pm
                JOIN production_plan pp ON pp.production_plan_id = pm.production_plan_id
                JOIN products p ON p.product_id = pm.material_id
                LEFT JOIN uom u ON u.id = p.uom_id
                WHERE pm.consumed_qty > 0
                GROUP BY pm.production_plan_id, pp.plan_unique
            """)
            result = query_to_dict(db_client.engine.execute(query, compcode=compcode, start_date=start_date, floor_id=floor_id))
            for row in result:
                if isinstance(row.get('materials'), str):
                    try:
                        row['materials'] = json.loads(row['materials'])
                    except Exception:
                        row['materials'] = []
                elif row.get('materials') is None:
                    row['materials'] = []
            return {'success': True, 'data': result}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}, 500


@dashboard_api_route.route('/consolidated_dashboard_produced_details')
class ConsolidatedDashboardProducedDetails(Resource):
    @login_required()
    def get(self):
        current_user_raw = request.args.get('current_user', {})
        if isinstance(current_user_raw, str):
            try:
                current_user = json.loads(current_user_raw)
            except Exception:
                current_user = {}
        elif isinstance(current_user_raw, dict):
            current_user = current_user_raw
        else:
            current_user = {}

        compcode = current_user.get('company_id', 1) or 1
        start_date = request.args.get('start_date', None)
        if not start_date:
            return {'success': False, 'message': 'Missing parameters'}, 400

        try:
            compcode = int(compcode)
            query = text("""
                SELECT 
                    pp.plan_unique as plan_no,
                    cp.order_unique,
                    p.product_name,
                    p.product_code,
                    p.sku_id,
                    s.stage_name,
                    pc.process_name,
                    pt.target_quantity as target_qty,
                    sum(el.outward_qty) as produced_qty
                FROM execution_log el
                JOIN plan_targets pt ON pt.plan_target_id = el.target_id
                JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
                LEFT JOIN LATERAL (
                    SELECT DISTINCT cp.order_unique
                    FROM plan_details pd
                    JOIN order_items_extract oie ON oie.extract_id = pd.order_extract_id AND oie.deleted IS NOT TRUE
                    JOIN customer_purchase_items cpi ON cpi.items_id = oie.order_items_id AND cpi.deleted IS NOT TRUE
                    JOIN customer_purchase cp ON cp.customer_purchase_id = cpi.customer_purchase_id AND cp.deleted IS NOT TRUE
                    WHERE pd.production_plan_id = pp.production_plan_id AND pd.deleted IS NOT TRUE
                    LIMIT 1
                ) cp ON true
                JOIN products p ON p.product_id = pt.product_id
                JOIN production_stages ps ON ps.product_id = pt.product_id AND ps.stage_id = el.stage_id AND ps.deleted IS NOT TRUE
                JOIN activity_stage_map asm ON asm.production_stage_id = ps.id AND asm.is_final_process IS TRUE AND (el.process_id IS NULL OR asm.config_id = el.process_id) AND asm.deleted IS NOT TRUE
                LEFT JOIN stage s ON s.stage_id = el.stage_id
                LEFT JOIN process_config pc ON pc.process_id = el.process_id
                WHERE el.compcode = :compcode 
                  AND el.opertaion_start_date >= cast(:start_date as timestamp) and el.opertaion_start_date < cast(:start_date as timestamp) + interval '1 day' 
                  AND el.deleted IS NOT TRUE
                  AND coalesce(el.outward_qty, 0) > 0
                  AND ps.rank_id = (SELECT MAX(rank_id) FROM production_stages WHERE product_id = pt.product_id AND deleted IS NOT TRUE)
                GROUP BY pp.plan_unique, cp.order_unique, p.product_name, p.product_code, p.sku_id, s.stage_name, pc.process_name, pt.target_quantity
                ORDER BY pp.plan_unique, s.stage_name, pc.process_name
            """)
            result = query_to_dict(db_client.engine.execute(query, compcode=compcode, start_date=start_date))
            for row in result:
                row['produced_qty'] = float(row['produced_qty']) if row['produced_qty'] is not None else 0
                row['fg_produced_qty'] = row['produced_qty']
                row['target_qty'] = float(row['target_qty']) if row['target_qty'] is not None else 0
            return {'success': True, 'data': result}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}, 500
