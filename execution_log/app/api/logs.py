import datetime
from pprint import pprint
import threading
import uuid
import os
import tempfile
import openpyxl

from flask import request, session, current_app, send_file
from flask_restx import Resource
# from .. import ipss_db
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger
from sqlalchemy.exc import SQLAlchemyError
from ..api.errorhandling import map_sqlalchemy_error_to_http_status
# from ..api_doc import execution_logs_roles_fields
from ..models.logs import ExecutionLog
from ipss_utils.decorators import login_required

from ..routes.logs import execution_log_api_route, execution_log_list_response, create_execution_log_response, \
    update_execution_log_model, update_execution_log_response, bulk_update, bulk_post_log_model, \
    employee_report_model_response, nested_head_fields_model
# from sqlalchemy import and_, text
from ..routes.logs import create_execution_log_model, get_execution_log_response
from .. import ipss_db, db_client
from ..api_doc import log_filters, employee_filter

# Primary p_key name

primary_key = 'id'


@execution_log_api_route.route('/')
class ExecutionLogApi(Resource):
    @execution_log_api_route.expect(bulk_update)
    @execution_log_api_route.marshal_with(create_execution_log_response)
    @login_required()
    def patch(self):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        data = data.get('data', [])
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now(),
              }
        postData = [
            {**data.pop(i), **cc} for i in range(len(data) - 1, -1, -1)
            if not data[i].get('id')
        ]
        # Resolve product_id for new logs
        for log in postData:
            if not log.get('product_id') and log.get('target_id'):
                res = db_client.session.execute(
                    text("SELECT product_id FROM plan_targets WHERE plan_target_id = :target_id"),
                    {"target_id": log.get('target_id')}
                ).fetchone()
                if res and res[0]:
                    log['product_id'] = res[0]
        
        error = ''
        success = False
        try:
            with db_client.session.begin():
                db_client.session.bulk_insert_mappings(mapper=ExecutionLog, mappings=postData)
                db_client.session.bulk_update_mappings(mapper=ExecutionLog, mappings=data)
                success = True

        except SQLAlchemyError as e:
            db_client.session.flush()
            db_client.session.rollback()
            return map_sqlalchemy_error_to_http_status(e)
        if success:
            message = "Records created Successfully"
        else:
            message = "There is an Error"
        return {
            'success': success,
            'message': message,
            'error': error,
        }


    per_page = 20
    @execution_log_api_route.marshal_with(execution_log_list_response)
    @execution_log_api_route.doc(params={**list_api_params,**log_filters})
    @login_required()
    def get(self):
        """
        List of execution_log with pagination
        TODO: Search
        :return:
        """
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con = ''
        if request.args.get('production_plan_id'):
            sql_con += ' and pp.production_plan_id=:production_plan_id '
        if request.args.get('stage_id'):
            sql_con += ' and el.stage_id=:stage_id '
        if request.args.get('target_id'):
            sql_con += ' and el.target_id=:target_id '
        if request.args.get('is_outsource'):
            sql_con += ' and el.is_outsource=:is_outsource '
        if request.args.get('product_id'):
            sql_con += ' and COALESCE(el.product_id, pt.product_id, pp.product_id) =:product_id '
        if request.args.get('hour_config_id'):
            sql_con += ' and el.hour_config_id=:hour_config_id '
        if request.args.get('operation_date'):
            sql_con += ''' and
            el.opertaion_start_date >= cast(:operation_date as date)
  AND cast(:operation_date as date) <= COALESCE(el.opertaion_end_date, el.opertaion_start_date)
            '''
        sql_query = text(f'''
                select el.*,pp.plan_unique,s.stage_name,cm.process_name as 
                config_name,concat(h.fname,' ',h.lname) as emp_name,
                hc.time_value,
                jo.joborderno as job_order_no, v.companyname as vendor_name
                from execution_log el
                join plan_targets pt on pt.plan_target_id =el.target_id 
                left join hour_config as hc on hc.record_id=el.hour_config_id
                join stage s on s.stage_id=el.stage_id
                join production_plan pp on pp.production_plan_id =pt.production_plan_id 
                left join process_config cm on cm.process_id = el.process_id
                left join hremploymast h on h.hremploymastid=el.emp_id
                left join joborder jo on jo.joborderid = el.job_order_id and jo.deleted is not true
                left join vendor v on v.vendorid = el.vendor_id and v.deleted is not true
                where el.deleted is not true and el.compcode=:ccode {sql_con}
                order by id desc
                limit :limit offset :offset
                ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           ccode=ccode,
                                                           hour_config_id=request.args.get('hour_config_id'),
                                                           operation_date=request.args.get('operation_date'),
                                                           product_id=request.args.get('product_id'),
                                                           is_outsource=request.args.get('is_outsource'),
                                                           target_id=request.args.get('target_id'),
                                                           stage_id=request.args.get('stage_id'),
                                                           production_plan_id=request.args.get('production_plan_id')
                                                           ))
        sql_count = text(f''' select count(*)
                from execution_log el
                join plan_targets pt on pt.plan_target_id =el.target_id 
                join production_plan pp on pp.production_plan_id =pt.production_plan_id 
                left join process_config cm on cm.process_id = el.process_id
                where el.deleted is not true and el.compcode=:ccode {sql_con}
                ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count, ccode=ccode,
                                                           operation_date=request.args.get('operation_date'),
                                                           product_id=request.args.get('product_id'),
                                                           is_outsource=request.args.get('is_outsource'),
                                                           hour_config_id=request.args.get('hour_config_id'),
                                                           target_id=request.args.get('target_id'),
                                                           stage_id=request.args.get('stage_id'),
                                                           production_plan_id=request.args.get('production_plan_id')
                                                           ))
        return {
            "total_results": sql_count[0].get('count', 0) if len(sql_count) else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query
        }

    @login_required()
    @execution_log_api_route.expect(create_execution_log_model)
    @execution_log_api_route.marshal_with(create_execution_log_response)
    def post(self):
        """
        Create execution_log record and return inserted id
        :return:
        """
        data = request.json
        # remove primary p_key if exists
        data.pop(primary_key, None)
        if not data.get('product_id') and data.get('target_id'):
            res = db_client.session.execute(
                text("SELECT product_id FROM plan_targets WHERE plan_target_id = :target_id"),
                {"target_id": data.get('target_id')}
            ).fetchone()
            if res and res[0]:
                data['product_id'] = res[0]
        result = ipss_db.insert_record(
            model=ExecutionLog,
            values=data
        )

        return ipss_db.created_response(
            result=result,
            message="Record has been created successfully",
            primary_key=primary_key
            )


@execution_log_api_route.route('/<id>/')
class EmployeeUpdateApi(Resource):
    @staticmethod
    def update_record(data, id):
        data.pop('id', None)

        result = ipss_db.update_record(
            model=ExecutionLog,
            condition=ExecutionLog.id == id,
            values=data
        )
        return result

    @execution_log_api_route.marshal_with(get_execution_log_response)
    @login_required()
    def get(self, id):
        """
        Read user record / single record
        :param id:
        :return:
        """

        user = ExecutionLog.query.filter_by(id=int(id)).first()
        return user

    @execution_log_api_route.expect(update_execution_log_model)
    @execution_log_api_route.marshal_with(update_execution_log_response)
    @login_required()
    def put(self, id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, id)
        return response

    @execution_log_api_route.expect(update_execution_log_model)
    @execution_log_api_route.marshal_with(update_execution_log_response)
    @login_required()
    def patch(self, id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, id)
        return response

    @execution_log_api_route.marshal_with(update_execution_log_response)
    @login_required()
    def delete(self, id):
        """
        Soft delete ExecutionLog record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=ExecutionLog,
            condition=ExecutionLog.id == id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################
@execution_log_api_route.route('/bulkpost-execution_log')
class BulkPost(Resource):
    @login_required()
    @execution_log_api_route.expect(bulk_post_log_model)
    @execution_log_api_route.marshal_with(create_execution_log_response)
    def post(self):
        """
        Create execution_log record and return inserted id
        :return:
        """
        data = request.json
        data = data.get('data', [])
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now(),
              }
        postData = [
            {**data.pop(i), **cc} for i in range(len(data) - 1, -1, -1)
            if not data[i].get('id')
        ]
        # Resolve product_id for new logs
        for log in postData:
            if not log.get('product_id') and log.get('target_id'):
                res = db_client.session.execute(
                    text("SELECT product_id FROM plan_targets WHERE plan_target_id = :target_id"),
                    {"target_id": log.get('target_id')}
                ).fetchone()
                if res and res[0]:
                    log['product_id'] = res[0]
        
        error = ''
        success = False
        try:
            with db_client.session.begin():
                db_client.session.bulk_insert_mappings(mapper=ExecutionLog, mappings=postData)
                db_client.session.bulk_update_mappings(mapper=ExecutionLog, mappings=data)
                success = True

        except SQLAlchemyError as e:
            db_client.session.flush()
            db_client.session.rollback()
            return map_sqlalchemy_error_to_http_status(e)
        if success:
            message = "Records created Successfully"
        else:
            message = "There is an Error"
        return {
            'success': success,
            'message': message,
            'error': error,
        }


@execution_log_api_route.route('/bulk_backlog_metadata')
class BulkBacklogMetadata(Resource):
    @login_required()
    def get(self):
        """
        Consolidated fetch endpoint for Bulk Backlog Entry grid data.
        Returns stage parameters and existing execution logs in 1 single response.
        """
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        plan_id = request.args.get('production_plan_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not plan_id or not start_date or not end_date:
            return {"success": False, "message": "production_plan_id, start_date, and end_date are required"}, 400

        try:
            # 1. Fetch stage parameters joining stage_params and config_params
            sql_params = text("""
                SELECT sp.stage_id, sp.stage_param_id, sp.parameter_id, cp.parameter_name, cp.parameter_type
                FROM stage_params sp
                JOIN config_params cp ON cp.parameter_id = sp.parameter_id
                WHERE sp.deleted IS NOT TRUE AND sp.compcode = :ccode
            """)
            params_res = query_to_dict(db_client.engine.execute(sql_params, ccode=ccode))

            # 2. Fetch existing execution logs for this plan in date range
            sql_logs = text("""
                SELECT el.*, pp.plan_unique, s.stage_name, cm.process_name AS config_name,
                       CONCAT(h.fname, ' ', h.lname) AS emp_name, hc.time_value
                FROM execution_log el
                JOIN plan_targets pt ON pt.plan_target_id = el.target_id
                LEFT JOIN hour_config hc ON hc.record_id = el.hour_config_id
                JOIN stage s ON s.stage_id = el.stage_id
                JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
                LEFT JOIN process_config cm ON cm.process_id = el.process_id
                LEFT JOIN hremploymast h ON h.hremploymastid = el.emp_id
                WHERE el.deleted IS NOT TRUE 
                  AND el.compcode = :ccode
                  AND pt.production_plan_id = :plan_id
                  AND el.opertaion_start_date >= CAST(:start_date AS DATE)
                  AND el.opertaion_start_date <= CAST(:end_date AS DATE)
                ORDER BY el.id DESC
            """)
            logs_res = query_to_dict(db_client.engine.execute(
                sql_logs, ccode=ccode, plan_id=plan_id, start_date=start_date, end_date=end_date
            ))

            return {
                "success": True,
                "parameters": params_res,
                "logs": logs_res
            }, 200
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    
@execution_log_api_route.route('/employee_efficiency-log_report')
class EmployeeReport(Resource):
    @login_required()
    @execution_log_api_route.doc(params={**list_api_params,**employee_filter})
    @execution_log_api_route.marshal_with(nested_head_fields_model)
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        compcode = current_user.get('company_id', None)
        sql_con = ''
        el_filter = ''
        if request.args.get('emp_id'):
            sql_con+=' and el.emp_id=:emp_id '
            el_filter += " and el.emp_id=:emp_id"
        if request.args.get('product_id'):
            sql_con+=' and p.product_id=:product_id '
        if request.args.get('line_id'):
            sql_con+=' and el.line_id=:line_id '
            el_filter += " and el.line_id=:line_id"
        # date = ''
        end_date=request.args.get('start_date') if not request.args.get('end_date') else request.args.get('end_date')
        if request.args.get('start_date'):
            # sql_con+=' and el.opertaion_start_date::date between cast(:start_date as date) and cast(:end_date as date) '
            sql_con += " and el.operation_range && tsrange(cast(:start_date as timestamp), cast(:end_date as timestamp), '[]') "
            el_filter += " and el.operation_range && tsrange(cast(:start_date as timestamp), cast(:end_date as timestamp), '[]') "
        # start_time = datetime.datetime.now()
        query1 = text(f'''
        select distinct emp_id from execution_log el
        where el.compcode=:compcode {el_filter}
        ''')

        result1 = query_to_dict(db_client.engine.execute(query1,compcode=compcode,
                                                         start_date=request.args.get('start_date'),
                                                        end_date=end_date
                                                        ))

        query2 = text(f'''
        select h.hremploymastid,concat(h.fname,' ',h.lname) as employee_name,h.idcardno from hremploymast h
        where h.compcode=:compcode and h.hremploymastid IN :ids
        ''')

        ids = tuple([r['emp_id'] for r in result1])
        if not ids:
            employees = []
        else:
            employees = db_client.engine.execute(query2,
                                             compcode=compcode,
                                                ids=ids)
        employee_map = {r['hremploymastid']: {"employee_name": r['employee_name'], "idcardno": r['idcardno']} for r in employees}

        # print("Employees: ", employee_map)
        sql_query=text(f'''
                        with cte as (
                        select el.opertaion_start_date::date,
                        el.emp_id,
                        p.product_name,p.product_code,p.sku_id,pc.process_name,s.stage_name,hc.time_value,pt.target_quantity,lc.line_name,
                        round((60*60)/asm.target_per_hour) as sec_per_pcs,
                        pp.plan_unique,
                        pp.production_plan_id,
                        asm.target_per_hour as asm_target_per_hour,
                        asm.activity_stage_map_id as activity_stage_map_id,
                        sum(el.outward_qty) as outward_qty,
                        max(erom.stage_param_value) as remarks
                        from execution_log as el
                        join line_config lc on lc.line_config_id=el.line_id and lc.deleted is not true
                        join plan_targets pt on pt.plan_target_id =el.target_id and pt.deleted is not true 
                        join production_plan pp on pp.production_plan_id =pt.production_plan_id and pp.deleted is not true
                        join products p on p.product_id =COALESCE(el.product_id, pt.product_id, pp.product_id) and p.deleted is not true
                        left join process_config pc on pc.process_id =el.process_id and pc.deleted is not true
                        join stage s on s.stage_id =el.stage_id and s.deleted is not true
                        join production_stages ps on ps.stage_id =s.stage_id and ps.product_id=p.product_id and ps.deleted is not true
                        left join activity_stage_map asm on asm.production_stage_id =ps.id and 
                        (el.process_id IS NULL or asm.config_id = el.process_id)
                        and asm.deleted is not true
                        join hour_config hc on hc.record_id =el.hour_config_id and hc.deleted is not true
                        left join (
                            select execution_id, max(stage_param_value) as stage_param_value
                            from execution_rawmaterials
                            where deleted is not true 
                              and parameter_id in (select parameter_id from config_params where deleted is not true and lower(parameter_name) = 'remarks')
                            group by execution_id
                        ) erom on erom.execution_id = el.id
                        where el.deleted is not true and el.compcode=:compcode {sql_con}
                        group by el.opertaion_start_date::date,el.emp_id,
                        p.product_name,p.product_code,p.sku_id,pc.process_name,s.stage_name,hc.time_value,target_quantity,(60*60)/asm.target_per_hour,
                        lc.line_name,pp.plan_unique,pp.production_plan_id,asm.target_per_hour,asm.activity_stage_map_id),
                        cte2 AS (select opertaion_start_date,emp_id,
                        product_name,product_code,sku_id,process_name,stage_name,
                        sum(coalesce(outward_qty,0)) as total_outward,
                        line_name,	
                        plan_unique,
                        (SELECT string_agg(distinct cp.order_unique, ', ') 
                         FROM plan_details pd 
                         JOIN order_items_extract oie on oie.extract_id=pd.order_extract_id
                         JOIN customer_purchase_items cpi on cpi.items_id=oie.order_items_id
                         JOIN customer_purchase cp on cp.customer_purchase_id=cpi.customer_purchase_id 
                         WHERE pd.production_plan_id = cte.production_plan_id) as order_unique,
                        sec_per_pcs,
                        jsonb_object_agg(time_value,outward_qty) as production,
                        jsonb_object_agg(time_value,round((outward_qty*sec_per_pcs)/60)) as efficiency,
                        jsonb_object_agg(time_value, coalesce(remarks, '')) as remarks,
                        jsonb_object_agg(time_value, coalesce((
                            SELECT pis.incentive_amount 
                            FROM process_incentive_slabs pis 
                            WHERE pis.activity_stage_map_id = cte.activity_stage_map_id 
                              AND (cte.outward_qty - cte.asm_target_per_hour) >= pis.from_qty 
                              AND (pis.to_qty IS NULL OR (cte.outward_qty - cte.asm_target_per_hour) <= pis.to_qty)
                              AND pis.deleted IS NOT TRUE
                              AND pis.compcode = :compcode
                            ORDER BY pis.from_qty DESC 
                            LIMIT 1
                        ), 0)) as incentive
                        from cte
                        group by opertaion_start_date,emp_id,
                        product_name,product_code,sku_id,process_name,stage_name,sec_per_pcs,line_name,plan_unique,production_plan_id)
                        SELECT opertaion_start_date,emp_id,
                        count(*) over() as total_count,
                        jsonb_agg(json_build_object(
                        'product_name',product_name,
                        'product_code',product_code,
                        'sku_id',sku_id,
                        'line_name',line_name,
                        'plan_unique',plan_unique,
                        'order_unique',order_unique,
                        'process_name',process_name,
                        'stage_name',stage_name,
                        'sec_per_pcs',sec_per_pcs,
                        'production',production,
                        'efficiency',efficiency,
                        'remarks',remarks,
                        'incentive',incentive
                        )) as products
                        FROM cte2
                        group by opertaion_start_date,emp_id
                        limit :limit offset :offset

''')


        sql_query=query_to_dict(db_client.engine.execute(sql_query,
                                                         ccode=ccode,
                                                         limit=results_per_page,
                                                         start_date=request.args.get('start_date'),
                                                        end_date=end_date,
                                                         product_id=request.args.get('product_id'),
                                                         emp_id=request.args.get('emp_id'),
                                                         compcode=compcode,
                                                         line_id=request.args.get('line_id'),
                                                         offset=offset))

        # print("Time taken to execute query: ", (datetime.datetime.now() - start_time).total_seconds())
        from .helper import calculate_avg_efficiency
        sql_query=calculate_avg_efficiency(sql_query,employee_map)

        return {
            "total_results": sql_query[0].get('total_count', 0) if len(sql_query) else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query
        }


def generate_efficiency_excel(app, ccode, compcode, sql_con, el_filter, start_date, end_date, product_id, emp_id, line_id, user_id):
    with app.app_context():
        try:
            # Execute query1 to get employee IDs
            query1 = text(f'''
            select distinct emp_id from execution_log el
            where el.compcode=:compcode {el_filter}
            ''')
            
            result1 = query_to_dict(db_client.engine.execute(query1, compcode=compcode,
                                                            start_date=start_date,
                                                            end_date=end_date))
                                                            
            query2 = text(f'''
            select h.hremploymastid,concat(h.fname,' ',h.lname) as employee_name,h.idcardno from hremploymast h
            where h.compcode=:compcode and h.hremploymastid IN :ids
            ''')

            ids = tuple([r['emp_id'] for r in result1]) if result1 else tuple()
            employees = db_client.engine.execute(query2, compcode=compcode, ids=ids) if ids else []
            employee_map = {r['hremploymastid']: {"employee_name": r['employee_name'], "idcardno": r['idcardno']} for r in employees}

            sql_query = text(f'''
                            with cte as (
                            select el.opertaion_start_date::date,
                            el.emp_id,
                            p.product_name,p.product_code,p.sku_id,pc.process_name,s.stage_name,hc.time_value,pt.target_quantity,lc.line_name,
                            round((60*60)/asm.target_per_hour) as sec_per_pcs,
                            pp.plan_unique,
                            pp.production_plan_id,
                            asm.target_per_hour as asm_target_per_hour,
                            asm.activity_stage_map_id as activity_stage_map_id,
                            sum(el.outward_qty) as outward_qty,
                            max(erom.stage_param_value) as remarks
                            from execution_log as el
                            join line_config lc on lc.line_config_id=el.line_id and lc.deleted is not true
                            join plan_targets pt on pt.plan_target_id =el.target_id and pt.deleted is not true 
                            join production_plan pp on pp.production_plan_id =pt.production_plan_id and pp.deleted is not true
                            join products p on p.product_id =COALESCE(el.product_id, pt.product_id, pp.product_id) and p.deleted is not true
                            left join process_config pc on pc.process_id =el.process_id and pc.deleted is not true
                            join stage s on s.stage_id =el.stage_id and s.deleted is not true
                            join production_stages ps on ps.stage_id =s.stage_id and ps.product_id=p.product_id and ps.deleted is not true
                            left join activity_stage_map asm on asm.production_stage_id =ps.id and 
                            (el.process_id IS NULL or asm.config_id = el.process_id)
                            and asm.deleted is not true
                            join hour_config hc on hc.record_id =el.hour_config_id and hc.deleted is not true
                            left join (
                                select execution_id, max(stage_param_value) as stage_param_value
                                from execution_rawmaterials
                                where deleted is not true 
                                  and parameter_id in (select parameter_id from config_params where deleted is not true and lower(parameter_name) = 'remarks')
                                group by execution_id
                            ) erom on erom.execution_id = el.id
                            where el.deleted is not true and el.compcode=:compcode {sql_con}
                            group by el.opertaion_start_date::date,el.emp_id,
                            p.product_name,p.product_code,p.sku_id,pc.process_name,s.stage_name,hc.time_value,target_quantity,(60*60)/asm.target_per_hour,
                            lc.line_name,pp.plan_unique,pp.production_plan_id,asm.target_per_hour,asm.activity_stage_map_id),
                            cte2 AS (select opertaion_start_date,emp_id,
                            product_name,product_code,sku_id,process_name,stage_name,
                            sum(coalesce(outward_qty,0)) as total_outward,
                            line_name,	
                            plan_unique,
                            (SELECT string_agg(distinct cp.order_unique, ', ') 
                             FROM plan_details pd 
                             JOIN order_items_extract oie on oie.extract_id=pd.order_extract_id
                             JOIN customer_purchase_items cpi on cpi.items_id=oie.order_items_id
                             JOIN customer_purchase cp on cp.customer_purchase_id=cpi.customer_purchase_id 
                             WHERE pd.production_plan_id = cte.production_plan_id) as order_unique,
                            sec_per_pcs,
                            jsonb_object_agg(time_value,outward_qty) as production,
                            jsonb_object_agg(time_value,round((outward_qty*sec_per_pcs)/60)) as efficiency,
                            jsonb_object_agg(time_value, coalesce(remarks, '')) as remarks,
                            jsonb_object_agg(time_value, coalesce((
                                SELECT pis.incentive_amount 
                                FROM process_incentive_slabs pis 
                                WHERE pis.activity_stage_map_id = cte.activity_stage_map_id 
                                  AND (cte.outward_qty - cte.asm_target_per_hour) >= pis.from_qty 
                                  AND (pis.to_qty IS NULL OR (cte.outward_qty - cte.asm_target_per_hour) <= pis.to_qty)
                                  AND pis.deleted IS NOT TRUE
                                  AND pis.compcode = :compcode
                                ORDER BY pis.from_qty DESC 
                                LIMIT 1
                            ), 0)) as incentive
                            from cte
                            group by opertaion_start_date,emp_id,
                            product_name,product_code,sku_id,process_name,stage_name,sec_per_pcs,line_name,plan_unique,production_plan_id)
                            SELECT opertaion_start_date,emp_id,
                            count(*) over() as total_count,
                            jsonb_agg(json_build_object(
                            'product_name',product_name,
                            'product_code',product_code,
                            'sku_id',sku_id,
                            'line_name',line_name,
                            'plan_unique',plan_unique,
                            'order_unique',order_unique,
                            'process_name',process_name,
                            'stage_name',stage_name,
                            'sec_per_pcs',sec_per_pcs,
                            'production',production,
                            'efficiency',efficiency,
                            'remarks',remarks,
                            'incentive',incentive
                            )) as products
                            FROM cte2
                            group by opertaion_start_date,emp_id
            ''')
            
            sql_res = query_to_dict(db_client.engine.execute(sql_query,
                                                             ccode=ccode,
                                                             start_date=start_date,
                                                             end_date=end_date,
                                                             product_id=product_id,
                                                             emp_id=emp_id,
                                                             compcode=compcode,
                                                             line_id=line_id))
                                                             
            from .helper import calculate_avg_efficiency
            data = calculate_avg_efficiency(sql_res, employee_map)

            # Generate Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Employee Efficiency Report'
            
            unique_hours = set()
            for row in data:
                for p in row.get('products', []):
                    if p.get('production'):
                        unique_hours.update(p['production'].keys())
            
            sorted_hours = sorted(list(unique_hours))
            
            headers = [
                "S.No", "Production Date", "Employee ID", "Employee Name", "Plan ID",
                "Product Name", "Line Name", "Stage & Process", "Label"
            ] + sorted_hours + ["Day's Total"]
            
            ws.append(headers)
            
            sno = 1
            for row in data:
                date_str = str(row.get('opertaion_start_date', ''))
                emp_id_val = row.get('idcardno', '----')
                emp_name = row.get('employee_name', '')
                
                for p in row.get('products', []):
                    plan_id = p.get('plan_unique', '')
                    prod_name = f"{p.get('sku_id', '')} - {p.get('product_code', '')}"
                    line_name = p.get('line_name', '')
                    stage_proc = f"{p.get('stage_name', '')} ({p.get('process_name', '')})"
                    sec_per_pcs = p.get('sec_per_pcs') or 1
                    
                    target_row = [sno, date_str, emp_id_val, emp_name, plan_id, prod_name, line_name, stage_proc, 'Target']
                    sno += 1
                    for h in sorted_hours:
                        target_row.append(round(3600 / sec_per_pcs))
                    target_row.append('-')
                    ws.append(target_row)
                    
                    actual_row = [sno, date_str, emp_id_val, emp_name, plan_id, prod_name, line_name, stage_proc, 'Actual']
                    sno += 1
                    total_prod = 0
                    for h in sorted_hours:
                        prod = p.get('production', {}).get(h, 0)
                        actual_row.append(prod)
                        total_prod += prod
                    actual_row.append(total_prod)
                    ws.append(actual_row)
                    
                    eff_row = [sno, date_str, emp_id_val, emp_name, plan_id, prod_name, line_name, stage_proc, 'Efficiency']
                    sno += 1
                    total_eff = 0
                    eff_count = 0
                    for h in sorted_hours:
                        eff = p.get('efficiency', {}).get(h, 0)
                        eff_row.append(eff)
                        if eff is not None:
                            total_eff += eff
                            eff_count += 1
                    eff_row.append(round(total_eff / max(1, eff_count), 2))
                    ws.append(eff_row)
                    
                    rem_row = [sno, date_str, emp_id_val, emp_name, plan_id, prod_name, line_name, stage_proc, 'Remarks']
                    sno += 1
                    for h in sorted_hours:
                        rem_row.append(p.get('remarks', {}).get(h, ''))
                    rem_row.append('-')
                    ws.append(rem_row)
                    
                    inc_row = [sno, date_str, emp_id_val, emp_name, plan_id, prod_name, line_name, stage_proc, 'Incentive (₹)']
                    sno += 1
                    total_inc = 0
                    for h in sorted_hours:
                        inc = p.get('incentive', {}).get(h, 0)
                        inc_row.append(inc)
                        total_inc += inc
                    inc_row.append(total_inc)
                    ws.append(inc_row)
                    
                overall_row = [sno, date_str, emp_id_val, emp_name, '', '', '', '', 'Overall Efficiency']
                sno += 1
                for h in sorted_hours:
                    overall_row.append(row.get('average_efficiency', {}).get(h, 0))
                overall_row.append(row.get('overall_efficiency', 0))
                ws.append(overall_row)
            
            filename = f"Employee_Efficiency_Report_{uuid.uuid4().hex}.xlsx"
            filepath = os.path.join(tempfile.gettempdir(), filename)
            wb.save(filepath)

            # Emit socket event using Redis message queue targeted to specific user room
            try:
                from flask_socketio import SocketIO
                redis_url = os.getenv("REDIS_DB_URL", "redis://localhost:6379/0")
                socketio_client = SocketIO(message_queue=redis_url, channel="notification-service")
                download_url = f"/execution_log/download/report/{filename}"
                payload = {'url': download_url, 'user_id': user_id}
                if user_id:
                    target_room = f"user_{user_id}"
                    socketio_client.emit('excel_export_ready', payload, to=target_room)
                else:
                    socketio_client.emit('excel_export_ready', payload)
            except Exception as e:
                print(f"Socket IO emission failed: {e}")

        except Exception as e:
            print(f"Background export failed: {e}")

@execution_log_api_route.route('/employee_efficiency-log_report/background_export')
class EmployeeReportExport(Resource):
    @login_required()
    @execution_log_api_route.doc(params={**employee_filter})
    def get(self):
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        compcode = ccode
        user_id = current_user.get('userid') or current_user.get('user_id')
        
        sql_con = ''
        el_filter = ''
        if request.args.get('emp_id'):
            sql_con+=' and el.emp_id=:emp_id '
            el_filter += " and el.emp_id=:emp_id"
        if request.args.get('product_id'):
            sql_con+=' and p.product_id=:product_id '
        if request.args.get('line_id'):
            sql_con+=' and el.line_id=:line_id '
            el_filter += " and el.line_id=:line_id"
            
        end_date = request.args.get('start_date') if not request.args.get('end_date') else request.args.get('end_date')
        if request.args.get('start_date'):
            sql_con += " and el.operation_range && tsrange(cast(:start_date as timestamp), cast(:end_date as timestamp), '[]') "
            el_filter += " and el.operation_range && tsrange(cast(:start_date as timestamp), cast(:end_date as timestamp), '[]') "

        thread = threading.Thread(target=generate_efficiency_excel, args=(
            current_app._get_current_object(),
            ccode, compcode, sql_con, el_filter, 
            request.args.get('start_date'), end_date, 
            request.args.get('product_id'), request.args.get('emp_id'), 
            request.args.get('line_id'), user_id
        ))
        thread.start()

        return {"message": "Background export initiated"}, 200

@execution_log_api_route.route('/download/report/<filename>')
class DownloadReport(Resource):
    def get(self, filename):
        filepath = os.path.join(tempfile.gettempdir(), filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name="Employee_Efficiency_Report.xlsx")
        return {"message": "File not found"}, 404
