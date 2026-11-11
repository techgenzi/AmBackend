import datetime
import time
from pprint import pprint

from flask import request, session
from flask_restx import Resource, abort

from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger, bindparam, NUMERIC, Integer, DateTime, String
from sqlalchemy.exc import SQLAlchemyError

from .. import ipss_db, db_client
from ..api_doc import employee_filter, employee_report_filter, line_config_filter
from ..models.employee_line import EmployeeLine
from ipss_utils.decorators import login_required
from ..routes.empoyee_line import employee_line_api_route, create_record_response_model, employee_post_model, \
    employee_list_response, employee_response, delete_model, employee_resport_list
from .errorhandling import map_sqlalchemy_error_to_http_status, update_local




@employee_line_api_route.route('/employee_line_map')
class EmployeeMachineApi(Resource):
    per_page = 20

    @employee_line_api_route.marshal_with(employee_list_response)
    @employee_line_api_route.doc(params=list_api_params)
    # @login_required(permissions='line_map_material.list')
    @login_required()
    def get(self):
        """
        List of inventoryRegistry with pagination
        TODO: Search Notification_manage
        :line_map:
        """
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        compcode = request.args.get('current_user', {}).get('company_id', None)
        sql_query = text(f'''
            select 
            lc.line_name,
            json_agg(
            json_build_object(
                'line_map_id',lm.line_map_id,
            'emp_name',concat(emp.fname,'',emp.mname,' ',emp.lname),
            'config_name',cm.config_name
            )
            ) as data,
            count(*) over() as total_count
            from employee_line as el 
            left join hremploymast as emp on emp.hremploymastId = el.employee_id
            left join line_map as lm on el.line_map_id = lm.line_map_id 
            left join line_config as lc on lc.line_config_id = lm.line_id
            left join config_master as cm on cm.config_id = lm.config_id
            where el.compcode=:compcode and el.deleted is not true and emp.deleted is not true and lc.deleted is not true
            and cm.deleted is not true
            group by lc.line_name
            limit :limit offset :offset
        ''')
        result = query_to_dict(db_client.engine.execute(sql_query,
                                                        compcode=compcode,
                                                        limit=results_per_page,
                                                        offset=offset
                                                        ))
        return {
            'total_results': result[0].get('total_count') if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }

    # @login_required(permissions='line_map_material.add')
    @login_required()
    @employee_line_api_route.expect(employee_post_model)
    @employee_line_api_route.marshal_with(create_record_response_model)
    def post(self):
        """
        Create inventoryRegistry record and line_map inserted id
        :line_map:
        """
        data = request.json
        data = data.get('data')
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        cc = {
            "compcode": compcode,
            "created_on": datetime.datetime.now(),
            'created_by': cur.get('username', None)
        }
        data = [{**i, **cc} for i in data]
        error = ''
        s = db_client.session
        try:
            with s.begin():
                s.bulk_insert_mappings(mapper=EmployeeLine, mappings=data)
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

    @login_required()
    @employee_line_api_route.expect(delete_model)
    def delete(self):
        s = db_client.session
        data = request.json
        ids = set(data.get('data'))
        try:
            query = text(f'''
                        update employee_line
                        set deleted = True, deleted_at = now()
                        where employee_line_id in :ids
                        ''')
            s.execute(query, {'ids': tuple(ids)})
            s.commit()
        except Exception as e:
            s.flush()
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': 'Bulk Delete successfully'
        }


@employee_line_api_route.route('/employee_line/reset')
class EmployeeRest(Resource):

    @login_required()
    @employee_line_api_route.doc(params=line_config_filter)
    def delete(self):
        s = db_client.session
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id', None)
        line_config_id = request.args.get('line_config_id', None)
        sql_con = ''
        if line_config_id:
            line_config_id = tuple(line_config_id.split(','))
            sql_con += ' and lp.line_config_id in :line_config_ids '

        start_time = time.time()
        try:
            reset_query = text(f'''
update employee_line el1 set deleted = 'True'
from line_process as lp
join line_map as lm on lp.line_process_id = lm.line_process_id and lp.compcode=:compcode and lp.deleted is not true and lm.deleted is not true
where el1.line_map_id = lm.line_map_id and el1.deleted is not true {sql_con}
            ''')
            s.execute(reset_query, {'compcode': compcode, 'line_config_ids': line_config_id})
            s.commit()
            end_time = time.time()
            print(f"Query executed in {end_time - start_time} seconds")
            return {
                'success': True,
                'message': 'Reset Successfully'
            }
        except Exception as e:
            s.flush()
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)



@employee_line_api_route.route('/employee_assign')
class Employeeget(Resource):

    @login_required()
    @employee_line_api_route.marshal_with(employee_response)
    @employee_line_api_route.doc(params=employee_filter)
    def get(self):

        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id')
        page = int(request.args.get('paged')) if request.args.get('paged') else 1
        result_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0

        assigned = request.args.get('assigned', None)

        line_map_id = request.args.get('line_map_id', None)

        config_id = request.args.get('config_id', None)

        activity_id = request.args.get('activity_id', None)

        line_config_id = request.args.get('line_config_id', None)

        process_id = request.args.get('process_id', None)

        stage_id = request.args.get('stage_id', None)

        know_activity_id = request.args.get('know_activity_id', None)

        emp_id = request.args.get('emp_id', None)

        ids = None
        if process_id:
            ids = tuple(map(int, process_id.split(',')))

        ids2 = None
        if stage_id:
            ids2 = tuple(map(int, stage_id.split(',')))

        sql_con = ''
        con1 = ''
        filter1 = ''

        # print(assigned)
        print(f"Value: {assigned}, Type: {type(assigned)}")

        if assigned == 'true':
            sql_con += ' and el.employee_id is not null  and el.deleted is not true'
        elif assigned == 'false':
            sql_con += ' and el.employee_id is null '
        if line_map_id and assigned == 'true':
            con1 += ' and cte1.line_map_id=:line_map_id '
        if activity_id:
            con1 += ' and cte1.activity_id=:activity_id '
        if line_config_id:
            sql_con += ' and lc.line_config_id=:line_config_id '
        if process_id:
            sql_con += ' and pc.process_id in :ids '
        if stage_id:
            con1 += ' and cte1.stage_id in :ids2 '

        if know_activity_id:
            con1 += ' and cte2.hr_activity_id=:know_activity_id '
            # filter1 = ' and cm.config_id=:know_activity_id '
        if emp_id:
            sql_con += ' and hr.hremploymastid=:emp_id '

        # start_time = time.time()
        query = text(f'''        
        with cte1 as(
		SELECT distinct on (hr.hremploymastid) hr.hremploymastid , lc.line_config_id,
            fname,mname,lname,idcardno,
            el.employee_line_id,
			pc.process_name,
			s.stage_id,
			s.stage_name,
			pc.process_id,
			lm.line_map_id,
	        cm2.config_id activity_id,
	        cm3.config_id machine_id,
        	lc.line_name,cm2.config_name activity_name,cm3.config_name machine_name,
            CASE 
            WHEN el.employee_id IS NOT NULL and el.deleted is not true THEN TRUE
            ELSE FALSE 
            END AS assigned,
            EXISTS (
                SELECT 1 FROM execution_log AS ex 
                WHERE ex.emp_id = hr.hremploymastid 
                  AND ex.opertaion_end_date IS NULL 
                  AND ex.deleted IS NOT TRUE
                  AND ex.compcode = :compcode
            ) AS in_execution
            FROM hremploymast AS hr
            left join employee_line AS el ON el.employee_id = hr.hremploymastid and (:line_map_id is null or el.line_map_id = cast(:line_map_id as bigint)) and el.compcode=:compcode and el.deleted is not true and hr.deleted is not true and hr.compcode =:compcode
            left join line_map as lm on lm.line_map_id = COALESCE(el.line_map_id, cast(:line_map_id as bigint))
            left join line_process lp on lp.line_process_id =lm.line_process_id 
            left join stage as s on s.stage_id = lp.stage_id
	        left join process_config as pc on pc.process_id = lp.process_id
			left join line_config lc on lc.line_config_id =lp.line_config_id 
			left join config_map cm on cm.config_map_id =lm.config_map_id 
			left join config_master cm2 ON cm2.config_id =cm.config_id 
			left join config_master cm3 on cm3.config_id =cm.ref_id
            where 1=1 {sql_con}
            order by hr.hremploymastid, assigned desc
			),
			cte2 as (
			select ecm.hremploymastid as maped_emp_id,cm.config_id as hr_activity_id,c.config_name as hr_activity_name from hremploymast as hr
			join employee_config_map as ecm on hr.hremploymastid = ecm.hremploymastid and hr.compcode=:compcode
		    join config_map as cm on cm.config_map_id = ecm.config_map_id 
			join config_master as c on c.config_id = cm.config_id and c.deleted is not true
			where 1=1 {filter1}
			)
			select 
			cte1.*,COUNT(*) OVER() AS total_count,
			COALESCE(json_agg(
			json_build_object(
			'maped_emp_id',cte2.maped_emp_id,
				'hr_activity_id', cte2.hr_activity_id,
				'hr_activity_name', cte2.hr_activity_name
			)
			) FILTER (WHERE cte2.maped_emp_id IS NOT NULL), '[]') as data
			 from cte1
			left join cte2 on cte1.hremploymastid = cte2.maped_emp_id
            where 1=1 {con1}
            group by cte1.hremploymastid, cte1.line_config_id,
			cte1.fname, cte1.mname, cte1.lname, cte1.idcardno, cte1.line_map_id, cte1.employee_line_id,cte1.stage_id,cte1.stage_name, cte1.process_id, cte1.activity_id, 
			cte1.machine_id, cte1.process_name, cte1.line_name, cte1.activity_name, cte1.machine_name, cte1.assigned, cte1.in_execution
            limit :limit offset :offset
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        compcode=compcode,
                                                        line_map_id=line_map_id,
                                                        config_id=config_id,
                                                        activity_id=activity_id,
                                                        line_config_id=line_config_id,
                                                        ids=ids,
                                                        ids2=ids2,
                                                        emp_id=emp_id,
                                                        know_activity_id=know_activity_id,
                                                        limit=result_per_page,
                                                        offset=offset))

        # end_time = time.time()
        #
        # print(f"Query executed in {end_time - start_time} seconds")

        return {
            "total_results": result[0].get('total_count', 0) if result else 0,
            "page": page,
            "results_per_page": result_per_page,
            "results": result
        }

@employee_line_api_route.route('/employee_line_report')
class EmployeeReport(Resource):

    @login_required()
    @employee_line_api_route.marshal_with(employee_resport_list)
    @employee_line_api_route.doc(params=employee_report_filter)
    def get(self):

        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id')
        page = int(request.args.get('paged')) if request.args.get('paged') else 1
        result_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0

        date = request.args.get('date', datetime.datetime.today())
        query = text('''
            with cte1 as (
            select hr.hremploymastid,hr.idcardno,el.*,lc.line_name,cm.config_name,
            CASE 
                        WHEN el.employee_id IS NOT NULL and el.deleted is not true THEN TRUE 
                        ELSE FALSE 
                        END AS assigned,
                hr.fname,hr.mname,hr.lname
            from hremploymast as hr
            left join employee_line as el on hr.hremploymastid = el.employee_id and el.deleted is not true
            left join line_map as lm on lm.line_map_id = el.line_map_id
            left join line_config as lc on lc.line_config_id = lm.line_id
            left join config_master as cm on cm.config_id = lm.config_id
            where hr.compcode=:compcode
            ),
            cte2 as (
            select hrm.idcardno,a.*, True as att
                from att as a
            left join hremploymast as hrm on a.hremploymastid = hrm.hremploymastid
            where a.raw_attdate=:date
            )
            select cte1.*,coalesce(cte2.att ,False::Boolean) as att,cte2.*,COUNT(*) OVER() AS total_count
            from cte1 
            left join cte2 on cte1.hremploymastid = cte2.hremploymastid
            limit :limit offset :offset
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        compcode=compcode,
                                                        date=date,
                                                        limit=result_per_page,
                                                        offset=offset))

        return {
            "total_results": result[0].get('total_count', 0) if result else 0,
            "page": page,
            "results_per_page": result_per_page,
            "results": result
        }

