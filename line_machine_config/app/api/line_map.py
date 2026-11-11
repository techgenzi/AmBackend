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
from ..api_doc import line_search
from ..models.line_map import LineMap
from ipss_utils.decorators import login_required
from ..routes.line_map import line_map_list_response, post_model, line_map_api_route, create_record_response_model
from .errorhandling import map_sqlalchemy_error_to_http_status, update_local

primary_key = 'releseid'


def build_recursive_tree(data):
    tree = {}
    lookup = {}

    # Initialize all nodes in lookup
    for entry in data:
        parent = entry["parent_name"]
        child = entry["child_name"]

        if parent not in lookup:
            lookup[parent] = {}
        if child and child not in lookup:
            lookup[child] = {}

        # Assign child inside parent
        lookup[parent][child] = lookup[child]

    # Find the root (entries that are never a child)
    all_children = {entry["child_name"] for entry in data}
    roots = [entry["parent_name"] for entry in data if entry["parent_name"] not in all_children]

    # Build the tree from roots
    for root in roots:
        tree[root] = lookup[root]

    return tree


@line_map_api_route.route('/line_map')
class LineMachineApi(Resource):
    per_page = 20

    @line_map_api_route.marshal_with(line_map_list_response)
    @line_map_api_route.doc(params={**list_api_params,**line_search})
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
        sql_con = ''
        line_config_id = request.args.get('line_config_id', None)
        if line_config_id:
            sql_con += ' and lc.line_config_id=:line_config_id '
        start_time = time.time()
        sql_query = text(f'''
            select lc.line_config_id,lc.line_name,
            max(lm.line_map_id),
            json_agg(
            json_build_object(
            'line_map_id',lm.line_map_id,
                'line_process_id',lp.line_process_id,
                'config_map_id' , lm.config_map_id,
                'process_name', pc.process_name,
                'stage_id', lp.stage_id,
                'stage_name', s.stage_name,
                'process_id', pc.process_id,
                'machine_id', cma1.config_id,
                'activity_id', cma2.config_id,
                'machine_name', cma1.config_name,
                'activity_name', cma2.config_name,
                'count', lm.count,
                'deleted', lm.deleted
            )
            ) as data,
            count(*) over() as total
            from line_map as lm
            left join line_process as lp on lp.line_process_id = lm.line_process_id
            left join line_config as lc on lc.line_config_id = lp.line_config_id
            left join process_config as pc on pc.process_id = lp.process_id
            left join stage as s on s.stage_id = lp.stage_id
            left join config_map as cm on lm.config_map_id = cm.config_map_id
            left join config_master as cma1 on cm.ref_id = cma1.config_id
            left join config_master as cma2 on cm.config_id = cma2.config_id
            where lm.compcode =:compcode and lm.deleted is not true {sql_con}
            group by lc.line_config_id, lc.line_name
            order by max desc
            limit :limit offset :offset
        ''')
        result = query_to_dict(db_client.engine.execute(sql_query,
                                                        compcode=compcode,
                                                        line_config_id=line_config_id,
                                                        limit=results_per_page,
                                                        offset=offset
                                                        ))

        end_time = time.time()

        print(f"Query executed in {end_time - start_time} seconds")
        return {
            'total_results': result[0].get('total') if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }

    # @login_required(permissions='line_map_material.add')
    @login_required()
    @line_map_api_route.expect(post_model)
    @line_map_api_route.marshal_with(create_record_response_model)
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
                s.bulk_insert_mappings(mapper=LineMap, mappings=data)
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


@line_map_api_route.route('/line_map/<line_map_id>')
class LineMapRoute(Resource):

    @login_required()
    def delete(self, line_map_id):

        s = db_client.session
        try:
            delete_query = text("""
                            WITH updated_line_map AS (
                                UPDATE line_map
                                SET deleted = TRUE
                                WHERE line_map_id =:line_map_id
                                RETURNING line_map_id
                            )
                            UPDATE employee_line
                            SET deleted = TRUE
                            WHERE line_map_id IN (SELECT line_map_id FROM updated_line_map)
                        """)
            s.execute(delete_query, {'line_map_id': line_map_id})
            s.commit()
        except Exception as e:
            s.rollback()
            s.flush()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': 'Delete Successfully'
        }

@line_map_api_route.route('/line_id')
class LineDeleteRoute(Resource):

    @login_required()
    @line_map_api_route.expect(post_model)
    def put(self):
        data = request.json.get('data', None)
        s = db_client.session
        post_data = []
        update_data = []
        ids = set()
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        cc = {
            "compcode": compcode,
            "created_on": datetime.datetime.now(),
            'created_by': cur.get('username', None)
        }
        try:
            for i in data:
                if i.get('line_map_id'):
                    ids.add(i.get('line_map_id'))
                    update_data.append(i)
                else:
                    post_data.append({**i, **cc})

            # Insert new records
            if post_data:
                s.bulk_insert_mappings(mapper=LineMap, mappings=post_data)

            # Update existing records & track deleted line_map_ids
            deleted_line_map_ids = set()
            if update_data:
                for record in update_data:
                    if record.get('deleted') is True:  # If deleted is explicitly set to True
                        deleted_line_map_ids.add(record['line_map_id'])

                s.bulk_update_mappings(mapper=LineMap, mappings=update_data)

            # Cascade delete for employee_line if line_map is deleted
            if deleted_line_map_ids:
                delete_employee_line_query = text("""
                    UPDATE employee_line
                    SET deleted = TRUE
                    WHERE line_map_id IN :line_map_ids
                """)
                s.execute(delete_employee_line_query, {'line_map_ids': tuple(deleted_line_map_ids)})

            s.commit()

        except Exception as e:
            s.flush()
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': 'Update successfully'
        }, 200
