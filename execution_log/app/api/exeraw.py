import datetime
import time

from flask import request
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.ipss_db import query_to_dict
from select import error
from sqlalchemy import update, text, bindparam

from .errorhandling import map_sqlalchemy_error_to_http_status
from .helper import get_labour_cost
from ..api_doc import execution_report_filters
from ..routes.exeraw import execution_log_api_route, execution_model_rawmaterials, create_execution_log_response, \
    list_exec_report_response, execution_model_rawmaterials_bulk
from .. import db_client, ipss_db
from ..models.logs import ExecutionRawmaterials, ExecutionLog

import redis
import os
import json
REDIS_URL = os.getenv("REDIS_DB_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)



def add_cc(data=[], pkey='', p_value=''):
    compcode = request.args.get('current_user', {})
    cc = {"compcode": compcode.get('company_id'),
          "created_on": datetime.datetime.now()
          }
    data = [{**cc, **i, **{pkey: p_value}} for i in data]
    return data


@execution_log_api_route.route('/bulkpost-execution_rawmaterials')
class BulkPostRaw(Resource):
    @login_required()
    @execution_log_api_route.expect(execution_model_rawmaterials_bulk)
    @execution_log_api_route.marshal_with(create_execution_log_response)
    def post(self):
        """
        Create execution_log record and return inserted id
        :return:
        """
        data = request.json
        datas = data.get('data', [])
        error = ''
        for data in datas:
            rawmaterials = data.pop('captured_parameters', [])
            serialized_units = data.get('serialized_units', [])
            compcode = request.args.get('current_user', {})
            cc = {"compcode": compcode.get('company_id'),
                  "created_on": datetime.datetime.now()
                  }
            postData = [
                {**rawmaterials.pop(i), **cc} for i in range(len(rawmaterials) - 1, -1, -1)
                if not rawmaterials[i].get('record_id')
            ]

            try:
                # with db_client.session.begin():
                labour_cost = get_labour_cost(emp_id=data.get('emp_id'),
                                              plan_target_id=data.get('target_id'),
                                              outward_qty=data.get('outward_qty'),
                                              s=db_client.session
                                              )
                if not data.get('product_id') and data.get('target_id'):
                    res = db_client.session.execute(
                        text("SELECT product_id FROM plan_targets WHERE plan_target_id = :target_id"),
                        {"target_id": data.get('target_id')}
                    ).fetchone()
                    if res and res[0]:
                        data['product_id'] = res[0]

                if not data.get('id'):
                    # Check for duplicate execution log in the last 10 seconds to prevent double click submissions
                    dup_q = text('''
                        SELECT id FROM execution_log
                        WHERE target_id IS NOT DISTINCT FROM :target_id 
                          AND stage_id IS NOT DISTINCT FROM :stage_id
                          AND process_id IS NOT DISTINCT FROM :process_id
                          AND emp_id IS NOT DISTINCT FROM :emp_id
                          AND line_id IS NOT DISTINCT FROM :line_id
                          AND outward_qty IS NOT DISTINCT FROM :outward_qty
                          AND hour_config_id IS NOT DISTINCT FROM :hour_config_id
                          AND cast(opertaion_start_date as date) IS NOT DISTINCT FROM cast(:opertaion_start_date as date)
                          AND compcode IS NOT DISTINCT FROM :compcode
                          AND deleted IS NOT TRUE
                          AND created_on >= NOW() - INTERVAL '10 seconds'
                        LIMIT 1
                    ''')
                    dup_check = db_client.session.execute(dup_q, {
                        "target_id": data.get('target_id'),
                        "stage_id": data.get('stage_id'),
                        "process_id": data.get('process_id'),
                        "emp_id": data.get('emp_id'),
                        "line_id": data.get('line_id'),
                        "outward_qty": data.get('outward_qty'),
                        "hour_config_id": data.get('hour_config_id'),
                        "opertaion_start_date": data.get('opertaion_start_date'),
                        "compcode": cc.get('compcode')
                    }).fetchone()
                    if dup_check:
                        print(f"Skipping duplicate execution log insert for target {data.get('target_id')}")
                        continue

                    data.update({'labour_cost': labour_cost})
                    result = ipss_db.insert_record(model=ExecutionLog, values=data, commit=False)
                    pkey = result.get('primary_key_id')[0] if result.get('success') else None

                else:
                    data.update({'labour_cost': labour_cost})
                    stmt = (
                        update(ExecutionLog)
                        .where(ExecutionLog.id == data.get('id'))
                        .values(**data)
                    )
                    result = db_client.session.execute(stmt)
                    pkey = data.get('id')
                if not pkey:
                    db_client.session.rollback()
                    db_client.session.flush()
                    return result
                postData = add_cc(postData, pkey='execution_id', p_value=pkey)
                # details = add_cc(details, pkey='production_plan_id', p_value=pkey)
                if postData:
                    db_client.session.bulk_insert_mappings(mapper=ExecutionRawmaterials, mappings=postData)

                if rawmaterials:
                    db_client.session.bulk_update_mappings(mappings=rawmaterials, mapper=ExecutionRawmaterials)
                
                if serialized_units:
                    # Lookup production_plan_id and product_id from target_id
                    lookup_query = text('''
                        SELECT pt.production_plan_id, COALESCE(pt.product_id, pp.product_id) as product_id
                        FROM plan_targets pt
                        JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
                        WHERE pt.plan_target_id = :target_id
                    ''')
                    lookup_result = db_client.session.execute(lookup_query, {"target_id": data.get('target_id')}).fetchone()
                    
                    pp_id = lookup_result.production_plan_id if lookup_result else None
                    p_id = lookup_result.product_id if lookup_result else None

                    # Resolve store_id
                    store_id = None
                    company_id = compcode.get('company_id')
                    if pp_id and p_id:
                        plan_alloc_q = text('''
                            SELECT store_id FROM plan_allocation
                            WHERE prod_plan_id = :prod_plan_id AND product_id = :product_id AND compcode = :compcode AND deleted IS NOT TRUE
                            LIMIT 1
                        ''')
                        store_id = db_client.session.execute(plan_alloc_q, {
                            'prod_plan_id': pp_id, 
                            'product_id': p_id, 
                            'compcode': company_id
                        }).scalar()

                    if not store_id and p_id:
                        store_prod_q = text('''
                            SELECT store_id FROM store_product
                            WHERE product_id = :product_id AND compcode = :compcode AND deleted IS NOT TRUE
                            LIMIT 1
                        ''')
                        store_id = db_client.session.execute(store_prod_q, {
                            'product_id': p_id, 
                            'compcode': company_id
                        }).scalar()

                    if not store_id:
                        fallback_store_q = text('''
                            SELECT store_id FROM store_location 
                            WHERE compcode = :compcode AND deleted IS NOT TRUE 
                            ORDER BY store_id ASC 
                            LIMIT 1
                        ''')
                        store_id = db_client.session.execute(fallback_store_q, {
                            'compcode': company_id
                        }).scalar()

                    import json
                    for unit in serialized_units:
                        serial_number = None
                        serial_variations = ["serial_number", "serial no", "serial number", "serial_no"]
                        for k, v in unit.items():
                            if k.lower() in serial_variations:
                                serial_number = str(v).strip()
                                break
                        
                        if not serial_number:
                            continue

                        insert_stmt = text('''
                            INSERT INTO public.store_serialized_products 
                                (product_id, store_id, serial_number, status, compcode, created_at, updated_at, deleted, execution_log_id, production_plan_id, unit_data)
                            VALUES 
                                (:product_id, :store_id, :serial_number, 'Available', :compcode, NOW(), NOW(), false, :execution_log_id, :production_plan_id, :unit_data)
                            ON CONFLICT (compcode, product_id, serial_number) 
                            DO UPDATE SET 
                                store_id = EXCLUDED.store_id, 
                                status = 'Available', 
                                updated_at = NOW(), 
                                deleted = false, 
                                execution_log_id = EXCLUDED.execution_log_id, 
                                production_plan_id = EXCLUDED.production_plan_id, 
                                unit_data = EXCLUDED.unit_data;
                        ''')
                        db_client.session.execute(insert_stmt, {
                            'product_id': p_id,
                            'store_id': store_id,
                            'serial_number': serial_number,
                            'compcode': company_id,
                            'execution_log_id': pkey,
                            'production_plan_id': pp_id,
                            'unit_data': json.dumps(unit)
                        })

                # Check for execution quantity exceeded
                target_id = data.get('target_id')
                if target_id:
                    # Flush to ensure latest insertions are considered in aggregate functions
                    db_client.session.flush()

                    target_query = text('''
                        SELECT pt.production_plan_id, COALESCE(pt.product_id, pp.product_id) as product_id, pt.target_quantity, pp.plan_unique
                        FROM plan_targets pt
                        JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
                        WHERE pt.plan_target_id = :target_id
                    ''')
                    t_result = db_client.session.execute(target_query, {"target_id": target_id}).fetchone()
                    
                    if t_result and t_result.target_quantity:
                        target_qty = float(t_result.target_quantity)
                        
                        total_query = text('''
                            SELECT SUM(outward_qty) as total_qty FROM execution_log
                            WHERE target_id = :target_id AND deleted is not true
                        ''')
                        total_res = db_client.session.execute(total_query, {"target_id": target_id}).fetchone()
                        total_qty = float(total_res.total_qty) if total_res and total_res.total_qty else 0.0
                        
                        if total_qty > target_qty:
                            current_user_data = request.args.get('current_user', {})
                            try:
                                redis_client.xadd("notification", {
                                    "action": "execution_qty_exceeded",
                                    "target_id": str(target_id),
                                    "production_plan_id": str(t_result.production_plan_id),
                                    "plan_unique": str(t_result.plan_unique),
                                    "company_id": str(compcode.get('company_id')),
                                    "username": str(current_user_data.get('username')),
                                    "total_qty": str(total_qty),
                                    "target_qty": str(target_qty)
                                })
                            except Exception as re:
                                print("Failed to add notification to redis:", str(re))


            except Exception as e:
                error = str(e)
                db_client.session.rollback()
                db_client.session.flush()
                return map_sqlalchemy_error_to_http_status(e)
        db_client.session.commit()
        return {
            'success': True if not error else False,
            'message': "Records Created Successfully" if not error else"There is an Error",
            'error': error,
        }, 200

    @login_required()
    @execution_log_api_route.marshal_with(list_exec_report_response)
    @execution_log_api_route.doc(params={**list_api_params, **execution_report_filters})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get('results_per_page') else 20
        offset = (paged - 1) * results_per_page
        # sql_con = ' where el.deleted is not true and el.compcode=:ccode '
        sql_con = ''
        if request.args.get('id'):
            sql_con += ' and el.id=:id '
        if request.args.get('record_id'):
            sql_con += ' and er.record_id=:record_id '
        if request.args.get('production_plan_id'):
            sql_con += ' and pp.production_plan_id=:production_plan_id '
        if request.args.get('stage_id'):
            sql_con += ' and el.stage_id=:stage_id '
        if request.args.get('process_id'):
            sql_con += ' and el.process_id=:process_id '
        if request.args.get('hour_config_id'):
            sql_con += ' and el.hour_config_id=:hour_config_id '
        if request.args.get('line_id'):
            sql_con += ' and el.line_id=:line_id '
        if request.args.get('machine_id'):
            sql_con += ' and el.machine_id=:machine_id '
        if request.args.get('activity_id'):
            sql_con += ' and el.activity_id=:activity_id '
        if request.args.get('operation_date'):
            sql_con += " and el.opertaion_start_date >= cast(:operation_date as date) and el.opertaion_start_date < (cast(:operation_date as date) + interval '1 day') "

        start_time = time.time()
        sql_query = text(f'''
                SELECT 
                el.id, el.target_id, pp.plan_unique, el.stage_id, s.stage_name, 
                el.inward_qty, el.outward_qty, el.opertaion_start_date, 
                 hc.time_value,el.hour_config_id,
                el.opertaion_end_date, el.is_outsource, el.process_id, cm.process_name as config_name, 
                el.emp_id,
                CONCAT(h.fname, ' ', h.lname) AS emp_name, 
                el.line_id, lc.line_name,el.wastage, el.serialized_units,
                el.supplier_lot_no, el.production_lot_no,
                el.job_order_id, el.vendor_id, jo.joborderno as job_order_no, v.companyname as vendor_name,
                cm1.config_id as machine_id,cm1.config_name as machine_name,cm2.config_id as activity_id,cm2.config_name as activity_name,
                COALESCE(
                    jsonb_agg(
                        jsonb_build_object(
                        'parameter_id', cp.parameter_id,
                            'parameter_name', COALESCE(cp.parameter_name, 'No Name'),
                            'stage_param_value', er.stage_param_value,
                            'is_eval', er.is_eval,
                            'record_id', er.record_id,
                            'rawmaterials_id', er.rawmaterials_id,
                            'product_name', p.product_name,
                            'product_code', p.product_code,
                            'sku_id', p.sku_id,
                            'supplier_lot_no', er.supplier_lot_no,
                            'production_lot_no', er.production_lot_no
                        )
                    ) FILTER (WHERE er.record_id IS NOT NULL), 
                    '[]'::JSONB
                ) AS captured_parameters,
                count(*) over() as total_results
            FROM execution_log el
             join hour_config as hc on hc.record_id=el.hour_config_id and el.compcode=:ccode and el.deleted is not true
            JOIN plan_targets pt ON pt.plan_target_id = el.target_id
            JOIN stage s ON s.stage_id = el.stage_id
            JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
            JOIN hremploymast h ON h.hremploymastid = el.emp_id and h.deleted is not true
            JOIN process_config cm ON cm.process_id = el.process_id
            LEFT JOIN line_config lc ON lc.line_config_id = el.line_id
            LEFT JOIN execution_rawmaterials er ON er.execution_id = el.id and er.deleted is not true
            left join stage_params sp on sp.stage_param_id=er.parameter_id and sp.deleted is not true
            LEFT JOIN config_params cp ON cp.parameter_id = er.parameter_id and cp.deleted is not true
            LEFT JOIN products p ON p.product_id = er.rawmaterials_id
            left join config_master cm1 on cm1.config_id =el.machine_id
            left join config_master cm2 on cm2.config_id =el.activity_id
            left join joborder jo on jo.joborderid = el.job_order_id and jo.deleted is not true
            left join vendor v on v.vendorid = el.vendor_id and v.deleted is not true
            where 1=1 {sql_con}
            GROUP BY 
                el.id, el.target_id, pp.plan_unique, el.stage_id, s.stage_name, 
                el.inward_qty, el.outward_qty, el.opertaion_start_date,el.hour_config_id,
                el.opertaion_end_date, el.is_outsource, el.process_id, cm.process_name, 
                el.emp_id, 
                emp_name, 
                el.line_id, lc.line_name, el.wastage, hc.time_value, el.serialized_units,
                el.supplier_lot_no, el.production_lot_no,
                el.job_order_id, el.vendor_id, jo.joborderno, v.companyname
                ,cm1.config_id,cm1.config_name,cm2.config_id,cm2.config_name
            limit :limit offset :offset
        ''')

        sql_query = query_to_dict(db_client.engine.execute(sql_query, ccode=ccode,
                                                           machine_id=request.args.get('machine_id'),
                                                           activity_id=request.args.get('activity_id'),
                                                           record_id=request.args.get('record_id'),
                                                           hour_config_id=request.args.get('hour_config_id'),
                                                           id=request.args.get('record_id'),
                                                           operation_date=request.args.get('operation_date'),
                                                           stage_id=request.args.get('stage_id'),
                                                           process_id = request.args.get('process_id'),
                                                           line_id=request.args.get('line_id'),
                                                           production_plan_id= request.args.get('production_plan_id'),
                                                           offset=offset,
                                                           limit=results_per_page))

        end_time = time.time()

        # print(f"Query Time Taken: {end_time - start_time} seconds")
        return {
            "total_results": sql_query[0].get('total_results') if sql_query else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "data": sql_query
        }


@execution_log_api_route.route('/<record_id>/')
class EmployeeUpdateApi(Resource):
    from ..routes.logs import update_execution_log_response
    @execution_log_api_route.marshal_with(update_execution_log_response)
    @login_required()
    def delete(self, record_id):
        """
        Soft delete ExecutionLog record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=ExecutionRawmaterials,
            condition=ExecutionRawmaterials.record_id == record_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result


@execution_log_api_route.route('/plan_serials')
class PlanSerials(Resource):
    @login_required()
    def get(self):
        plan_id = request.args.get('production_plan_id')
        if not plan_id:
            return {"success": False, "message": "production_plan_id is required"}, 400
        
        query = text('''
            SELECT serial_number 
            FROM store_serialized_products 
            WHERE production_plan_id = :plan_id AND deleted IS NOT TRUE
        ''')
        results = db_client.engine.execute(query, plan_id=plan_id).fetchall()
        serials = [row[0] for row in results if row[0]]
        
        return {
            "success": True,
            "serials": serials
        }, 200


@execution_log_api_route.route('/plan_audit')
class PlanAudit(Resource):
    @login_required()
    def get(self):
        plan_id = request.args.get('production_plan_id')
        if not plan_id:
            return {"success": False, "message": "production_plan_id is required"}, 400
        
        query = text('''
            WITH serials_agg AS (
                SELECT 
                    execution_log_id, 
                    COUNT(*) AS serial_count,
                    COUNT(DISTINCT serial_number) AS unique_serial_count
                FROM public.store_serialized_products
                WHERE production_plan_id = :plan_id AND deleted IS NOT TRUE
                GROUP BY execution_log_id
            ),
            serialization_logs AS (
                SELECT 
                    el.opertaion_start_date::date AS log_date,
                    SUM(el.outward_qty) AS ser_qty,
                    SUM(COALESCE(s.serial_count, 0)) AS registered_serials,
                    SUM(COALESCE(s.unique_serial_count, 0)) AS unique_serials
                FROM public.execution_log el
                LEFT JOIN serials_agg s ON s.execution_log_id = el.id
                JOIN public.plan_targets pt ON el.target_id = pt.plan_target_id
                WHERE pt.production_plan_id = :plan_id 
                  AND el.stage_id = 10 
                  AND el.process_id = 21
                  AND el.deleted IS NOT TRUE
                GROUP BY el.opertaion_start_date::date
            ),
            packing_logs AS (
                SELECT 
                    el.opertaion_start_date::date AS log_date,
                    SUM(el.outward_qty) AS pack_qty
                FROM public.execution_log el
                JOIN public.plan_targets pt ON el.target_id = pt.plan_target_id
                WHERE pt.production_plan_id = :plan_id 
                  AND el.stage_id = 7 
                  AND el.process_id = 20
                  AND el.deleted IS NOT TRUE
                GROUP BY el.opertaion_start_date::date
            )
            SELECT 
                COALESCE(s.log_date, p.log_date)::text AS log_date,
                COALESCE(s.ser_qty, 0) AS serialization_qty,
                COALESCE(s.registered_serials, 0) AS registered_serials,
                COALESCE(s.unique_serials, 0) AS unique_serials,
                COALESCE(p.pack_qty, 0) AS packing_qty
            FROM serialization_logs s
            FULL OUTER JOIN packing_logs p ON s.log_date = p.log_date
            ORDER BY log_date ASC;
        ''')
        
        results = db_client.engine.execute(query, plan_id=plan_id).fetchall()
        audit_data = []
        for row in results:
            audit_data.append({
                "date": row.log_date,
                "serialization_qty": int(row.serialization_qty),
                "registered_serials": int(row.registered_serials),
                "unique_serials": int(row.unique_serials),
                "packing_qty": int(row.packing_qty)
            })
            
        return {
            "success": True,
            "results": audit_data
        }, 200


@execution_log_api_route.route('/resolve_duplicate_serial')
class ResolveDuplicateSerial(Resource):
    @login_required()
    def post(self):
        data = request.json or {}
        plan_id = data.get('production_plan_id')
        serial_number = data.get('serial_number')
        execution_log_id = data.get('execution_log_id')
        
        if not plan_id or not serial_number:
            return {"success": False, "message": "production_plan_id and serial_number are required"}, 400
            
        try:
            with db_client.session.begin():
                # --- Safeguard Check: Dispatched ---
                if execution_log_id:
                    status_check_q = text("""
                        SELECT status, store_id, product_id, compcode 
                        FROM public.store_serialized_products
                        WHERE production_plan_id = :plan_id
                          AND serial_number = :serial_number
                          AND execution_log_id = :execution_log_id
                        ORDER BY (status = 'Dispatched') DESC, (store_id IS NOT NULL) DESC
                        LIMIT 1
                    """)
                    check_params = {
                        "plan_id": plan_id,
                        "serial_number": serial_number,
                        "execution_log_id": execution_log_id
                    }
                else:
                    status_check_q = text("""
                        SELECT status, store_id, product_id, compcode 
                        FROM public.store_serialized_products
                        WHERE production_plan_id = :plan_id
                          AND serial_number = :serial_number
                        ORDER BY (status = 'Dispatched') DESC, (store_id IS NOT NULL) DESC
                        LIMIT 1
                    """)
                    check_params = {
                        "plan_id": plan_id,
                        "serial_number": serial_number
                    }

                status_row = db_client.session.execute(status_check_q, check_params).fetchone()

                curr_store_id = None
                p_id = None
                c_code = None
                if status_row:
                    curr_status, curr_store_id, p_id, c_code = status_row[0], status_row[1], status_row[2], status_row[3]
                    if curr_status == 'Dispatched':
                        return {
                            "success": False,
                            "message": f"Serial number '{serial_number}' has already been DISPATCHED on a Delivery Challan and cannot be deleted."
                        }, 400

                # --- Proceed with safe deletion ---
                deleted = False
                target_log_id = execution_log_id

                if execution_log_id:
                    del_q = text("""
                        DELETE FROM public.store_serialized_products 
                        WHERE id = (
                            SELECT id FROM public.store_serialized_products
                            WHERE production_plan_id = :plan_id
                              AND serial_number = :serial_number
                              AND execution_log_id = :execution_log_id
                            LIMIT 1
                        )
                        RETURNING id, store_id, product_id, compcode
                    """)
                    res = db_client.session.execute(del_q, {
                        "plan_id": plan_id,
                        "serial_number": serial_number,
                        "execution_log_id": execution_log_id
                    }).fetchone()
                    if res:
                        deleted = True
                        if res[1] is not None:
                            curr_store_id = res[1]
                        if res[2] is not None:
                            p_id = res[2]
                        if res[3] is not None:
                            c_code = res[3]
                else:
                    del_q = text("""
                        DELETE FROM public.store_serialized_products
                        WHERE id = (
                            SELECT id FROM public.store_serialized_products
                            WHERE production_plan_id = :plan_id AND serial_number = :serial_number
                            ORDER BY id DESC
                            LIMIT 1
                        )
                        RETURNING execution_log_id, store_id, product_id, compcode
                    """)
                    res = db_client.session.execute(del_q, {
                        "plan_id": plan_id,
                        "serial_number": serial_number
                    }).fetchone()
                    if res:
                        deleted = True
                        target_log_id = res[0]
                        if res[1] is not None:
                            curr_store_id = res[1]
                        if res[2] is not None:
                            p_id = res[2]
                        if res[3] is not None:
                            c_code = res[3]

                if not deleted:
                    return {
                        "success": False,
                        "message": f"Serial number '{serial_number}' not found for plan {plan_id} or already removed."
                    }, 404

                # Update the JSON serialized_units field in execution_log & decrement outward_qty
                if target_log_id:
                    log_row = db_client.session.execute(
                        text("SELECT serialized_units FROM public.execution_log WHERE id = :log_id"),
                        {"log_id": target_log_id}
                    ).fetchone()
                    if log_row and log_row[0]:
                        try:
                            units = json.loads(log_row[0]) if isinstance(log_row[0], str) else log_row[0]
                            if isinstance(units, list):
                                new_units = []
                                removed = False
                                for u in units:
                                    serial_val = None
                                    for k in ['serial_number', 'Serial No', 'Serial Number', 'serial_no']:
                                        if k in u:
                                            serial_val = u[k]
                                            break
                                    if not serial_val and u:
                                        serial_val = list(u.values())[0]
                                        
                                    if serial_val == serial_number and not removed:
                                        removed = True
                                        continue
                                    new_units.append(u)
                                
                                if removed:
                                    db_client.session.execute(
                                        text("UPDATE public.execution_log SET serialized_units = :new_units, outward_qty = GREATEST(0, outward_qty - 1) WHERE id = :log_id"),
                                        {"new_units": json.dumps(new_units), "log_id": target_log_id}
                                    )
                        except Exception as json_err:
                            pass

                # If this serial was already moved to store, reconcile store inventory and plan moved_quantity
                if curr_store_id is not None and p_id is not None:
                    # Check if production plan actually has moved_quantity > 0
                    pp_check_q = text("""
                        SELECT COALESCE(moved_quantity, 0) 
                        FROM public.production_plan 
                        WHERE production_plan_id = :plan_id
                    """)
                    pp_moved = db_client.session.execute(pp_check_q, {"plan_id": plan_id}).scalar() or 0
                    
                    if pp_moved > 0:
                        db_client.session.execute(
                            text("UPDATE public.production_plan SET moved_quantity = GREATEST(0, moved_quantity - 1) WHERE production_plan_id = :plan_id"),
                            {"plan_id": plan_id}
                        )
                    db_client.session.execute(
                        text("""
                            UPDATE public.store_product 
                            SET product_count = GREATEST(0, COALESCE(product_count, 0) - 1)
                            WHERE product_id = :product_id AND store_id = :store_id
                        """),
                        {"product_id": p_id, "store_id": curr_store_id}
                    )

            return {"success": True, "message": "Duplicate serial resolved successfully"}, 200
        except Exception as e:
            db_client.session.rollback()
            return {"success": False, "message": f"Error resolving duplicate: {str(e)}"}, 500


@execution_log_api_route.route('/bulk_resolve_duplicate_serials')
class BulkResolveDuplicateSerials(Resource):
    @login_required()
    def post(self):
        data = request.json or {}
        plan_id = data.get('production_plan_id')
        items = data.get('items', [])
        
        if not plan_id or not items:
            return {"success": False, "message": "production_plan_id and non-empty items are required"}, 400
            
        try:
            with db_client.session.begin():
                # --- Safeguard Validation: Only Block Dispatched Serials ---
                serial_list = [i.get('serial_number') for i in items if i.get('serial_number')]
                if serial_list:
                    check_bulk_q = text("""
                        SELECT serial_number, status, store_id 
                        FROM public.store_serialized_products
                        WHERE production_plan_id = :plan_id
                          AND serial_number IN :serials
                          AND status = 'Dispatched'
                    """).bindparams(bindparam('serials', expanding=True))
                    dispatched_entries = db_client.session.execute(check_bulk_q, {
                        "plan_id": plan_id,
                        "serials": list(set(serial_list))
                    }).fetchall()

                    if dispatched_entries:
                        dispatched = [r[0] for r in dispatched_entries]
                        return {
                            "success": False,
                            "message": f"Cannot delete serials already Dispatched on a Delivery Challan ({len(dispatched)} items: {', '.join(dispatched[:5])})."
                        }, 400

                logs_map = {}
                deleted_count = 0
                reconcile_store_map = {} # (store_id, product_id) -> count

                for item in items:
                    sn = item.get('serial_number')
                    log_id = item.get('execution_log_id')
                    if not sn:
                        continue
                    if log_id:
                        del_q = text("""
                            DELETE FROM public.store_serialized_products 
                            WHERE id = (
                                SELECT id FROM public.store_serialized_products
                                WHERE production_plan_id = :plan_id
                                  AND serial_number = :serial_number
                                  AND execution_log_id = :execution_log_id
                                LIMIT 1
                            )
                            RETURNING id, store_id, product_id
                        """)
                        res = db_client.session.execute(del_q, {
                            "plan_id": plan_id,
                            "serial_number": sn,
                            "execution_log_id": log_id
                        }).fetchone()
                        if res:
                            deleted_count += 1
                            logs_map.setdefault(log_id, []).append(sn)
                            if res[1] is not None and res[2] is not None:
                                key = (res[1], res[2])
                                reconcile_store_map[key] = reconcile_store_map.get(key, 0) + 1
                    else:
                        del_q = text("""
                            DELETE FROM public.store_serialized_products
                            WHERE id = (
                                SELECT id FROM public.store_serialized_products
                                WHERE production_plan_id = :plan_id AND serial_number = :serial_number
                                ORDER BY id DESC
                                LIMIT 1
                            )
                            RETURNING execution_log_id, store_id, product_id
                        """)
                        res = db_client.session.execute(del_q, {
                            "plan_id": plan_id,
                            "serial_number": sn
                        }).fetchone()
                        if res:
                            deleted_count += 1
                            if res[0]:
                                logs_map.setdefault(res[0], []).append(sn)
                            if res[1] is not None and res[2] is not None:
                                key = (res[1], res[2])
                                reconcile_store_map[key] = reconcile_store_map.get(key, 0) + 1

                for log_id, serials_to_remove in logs_map.items():
                    log_row = db_client.session.execute(
                        text("SELECT serialized_units FROM public.execution_log WHERE id = :log_id"),
                        {"log_id": log_id}
                    ).fetchone()
                    
                    if log_row and log_row[0]:
                        try:
                            units = json.loads(log_row[0]) if isinstance(log_row[0], str) else log_row[0]
                            if isinstance(units, list):
                                new_units = []
                                removed_count = 0
                                remaining_serials = list(serials_to_remove)
                                
                                for u in units:
                                    serial_val = None
                                    for k in ['serial_number', 'Serial No', 'Serial Number', 'serial_no']:
                                        if k in u:
                                            serial_val = u[k]
                                            break
                                    if not serial_val and u:
                                        serial_val = list(u.values())[0]
                                        
                                    if serial_val in remaining_serials:
                                        remaining_serials.remove(serial_val)
                                        removed_count += 1
                                        continue
                                    new_units.append(u)
                                
                                if removed_count > 0:
                                    db_client.session.execute(
                                        text("UPDATE public.execution_log SET serialized_units = :new_units, outward_qty = GREATEST(0, outward_qty - :cnt) WHERE id = :log_id"),
                                        {
                                            "new_units": json.dumps(new_units),
                                            "cnt": removed_count,
                                            "log_id": log_id
                                        }
                                    )
                        except Exception as json_err:
                            pass

                # If items were in store, reconcile store inventory and plan moved_quantity
                if reconcile_store_map:
                    pp_check_q = text("""
                        SELECT COALESCE(moved_quantity, 0) 
                        FROM public.production_plan 
                        WHERE production_plan_id = :plan_id
                    """)
                    pp_moved = db_client.session.execute(pp_check_q, {"plan_id": plan_id}).scalar() or 0
                    
                    total_to_deduct = min(pp_moved, sum(reconcile_store_map.values()))
                    if total_to_deduct > 0:
                        db_client.session.execute(
                            text("UPDATE public.production_plan SET moved_quantity = GREATEST(0, moved_quantity - :cnt) WHERE production_plan_id = :plan_id"),
                            {"cnt": total_to_deduct, "plan_id": plan_id}
                        )
                    for (st_id, prod_id), cnt in reconcile_store_map.items():
                        db_client.session.execute(
                            text("""
                                UPDATE public.store_product 
                                SET product_count = GREATEST(0, COALESCE(product_count, 0) - :cnt)
                                WHERE product_id = :product_id AND store_id = :store_id
                            """),
                            {"cnt": cnt, "product_id": prod_id, "store_id": st_id}
                        )
                            
            return {
                "success": True,
                "message": f"Successfully resolved {deleted_count} duplicate serial records",
                "deleted_count": deleted_count
            }, 200
        except Exception as e:
            db_client.session.rollback()
            return {"success": False, "message": f"Error in bulk duplicate resolve: {str(e)}"}, 500

