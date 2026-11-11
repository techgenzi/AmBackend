import datetime
from pprint import pprint

from flask import request, session
from flask_restx import Resource, abort

from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger, bindparam, NUMERIC, Integer, DateTime, String
from sqlalchemy.exc import SQLAlchemyError

from .. import ipss_db, db_client
from ..api_doc import line_search
from ..models.line_process import LineProcess
from ipss_utils.decorators import login_required
from ..routes.line_process import line_process_list_response, post_model, line_process_api_route, \
    create_record_response_model, line_stage_process_model
from .errorhandling import map_sqlalchemy_error_to_http_status, update_local


@line_process_api_route.route('/line_process')
class LineMachineApi(Resource):
    per_page = 20

    @line_process_api_route.marshal_with(line_process_list_response)
    @line_process_api_route.doc(params={**list_api_params,**line_search})
    @login_required(permissions='line_process.list')
    # @login_required()
    def get(self):

        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        compcode = request.args.get('current_user', {}).get('company_id', None)
        sql_con = ''
        sql_con2 = ''
        line_config_id = request.args.get('line_config_id', None)
        stage_id = request.args.get('stage_id', None)
        process_id = request.args.get('process_id', None)
        ids = None
        if process_id:
            ids = tuple(map(int, process_id.split(',')))

        if line_config_id:
            sql_con += ' and lc.line_config_id=:line_config_id '
        if stage_id:
            sql_con += ' and lp.stage_id=:stage_id '
        if process_id:
            sql_con += ' and lp.process_id in :ids '

        sql_query = text(f'''
        		WITH stage_max AS (
    SELECT 
        lp.line_config_id, 
        lp.stage_id, 
        s.stage_name, 
        MAX(lp.line_process_id) AS stage_max,
        COALESCE(MAX(lp.rank_id), 1) AS rank_id
    FROM line_process lp
    LEFT JOIN stage s ON lp.stage_id = s.stage_id
    WHERE lp.deleted IS NOT TRUE
    GROUP BY lp.line_config_id, lp.stage_id, s.stage_name
)
SELECT 
    lp.line_config_id,
    lc.line_name,
    MAX(sm.stage_max) AS max_line_process_id,  -- Ensure overall max
    jsonb_agg(
        jsonb_build_object(
            'stage_id', sm.stage_id,
            'stage_name', sm.stage_name,
            'line_process_id', sm.stage_max, -- Attach max line_process_id per stage
            'rank_id', sm.rank_id,
            'process', (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'line_process_id', sp.line_process_id,
                        'process_id', sp.process_id, 
                        'process_name', pc.process_name
                    )
                    ORDER BY sp.line_process_id  -- Order processes within each stage
                )
                FROM line_process sp 
                LEFT JOIN process_config pc ON pc.process_id = sp.process_id
                WHERE sp.stage_id = sm.stage_id 
                AND sp.line_config_id = sm.line_config_id
                AND sp.deleted IS NOT TRUE
            )
        )
        ORDER BY sm.rank_id ASC  -- Sort `stages` JSON by rank_id
    ) AS stages,
    COUNT(*) OVER() AS total_count
FROM stage_max sm
JOIN line_process lp ON sm.stage_id = lp.stage_id AND sm.stage_max = lp.line_process_id
LEFT JOIN line_config lc ON lp.line_config_id = lc.line_config_id
WHERE lp.deleted IS NOT TRUE {sql_con}
AND lp.compcode =:compcode
GROUP BY lp.line_config_id, lc.line_name
ORDER BY max_line_process_id DESC
limit :limit offset :offset
        ''')
        result = query_to_dict(db_client.engine.execute(sql_query,
                                                        compcode=compcode,
                                                        line_config_id=line_config_id,
                                                        stage_id=stage_id,
                                                        ids=ids,
                                                        limit=results_per_page,
                                                        offset=offset
                                                        ))

        pprint(result)

        return {
            'total_results': result[0].get('total_count') if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }

    # @login_required(permissions='line_map_material.add')
    @login_required(permissions='line_process.add')
    @line_process_api_route.expect(line_stage_process_model)
    @line_process_api_route.marshal_with(create_record_response_model)
    def post(self):
        """
        Create inventoryRegistry record and line_map inserted id
        :line_map:
        """
        data = request.json

        line_config_id = data.get('line_config_id')
        compcode = request.args.get('current_user', {}).get('company_id')
        username = request.args.get('current_user', {}).get('username')

        cc = {
            "compcode": compcode,
            "created_on": datetime.datetime.now(),
            "created_by": username
        }

        s = db_client.session
        line_config_id = data.get('line_config_id')
        stages = data.get('stages', [])
        try:
            items = []
            for stage in stages:
                stage_id = stage["stage_id"]
                rank_id = stage.get("rank_id", 1)
                for process in stage.get("process", []):
                    items.append({
                        "line_config_id": line_config_id,
                        "stage_id": stage_id,
                        "process_id": process["process_id"],
                        "rank_id": rank_id,
                        **cc
                    })

            s.bulk_insert_mappings(LineProcess, items)
            s.commit()
            success = True
            message = "Records created successfully"

        except SQLAlchemyError as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {"success": success, "message": message}


@line_process_api_route.route('/line_process/<line_process_id>')
class LineMapRoute(Resource):

    @login_required(permissions='line_process.delete')
    def delete(self, line_process_id):

        # result = update_local(
        #     model=LineProcess,
        #     condition=LineProcess.line_process_id == line_process_id,
        #     values={
        #         'deleted': True,
        #         'deleted_at': datetime.datetime.now()
        #     }
        # )

        s = db_client.session
        try:
            delete_query = text("""
                                WITH updated_line_process AS (
                                    UPDATE line_process
                                    SET deleted = TRUE
                                    WHERE line_process_id = :line_process_id
                                    RETURNING line_process_id
                                ), updated_line_map AS (
                                    UPDATE line_map
                                    SET deleted = TRUE
                                    WHERE line_process_id IN (SELECT line_process_id FROM updated_line_process)
                                    AND deleted IS NOT TRUE
                                    RETURNING line_map_id
                                )
                                UPDATE employee_line
                                SET deleted = TRUE
                                WHERE line_map_id IN (SELECT line_map_id FROM updated_line_map);
                            """)
            s.execute(delete_query, {'line_process_id': line_process_id})
            s.commit()
        except Exception as e:
            s.rollback()
            s.flush()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': 'Delete Successfully'
        }


@line_process_api_route.route('/line_process/line_id/<line_config_id>')
class LineDeleteRoute(Resource):

    @login_required(permissions='line_process.edit')
    @line_process_api_route.expect(line_stage_process_model)
    def put(self, line_config_id):
        data = request.json.get('stages', [])
        s = db_client.session
        cur = request.args.get('current_user', {})

        # Get company details
        compcode = cur.get('company_id', None)
        created_by = cur.get('username', None)
        cc = {
            "compcode": compcode,
            "created_on": datetime.datetime.now(),
            "created_by": created_by
        }

        try:
            # Collect existing records to prevent duplication
            existing_query = text("""
                   SELECT line_process_id, stage_id, process_id 
                   FROM line_process 
                   WHERE line_config_id = :line_config_id AND deleted IS NOT TRUE
               """)
            existing_records = {
                (row.stage_id, row.process_id): row.line_process_id
                for row in s.execute(existing_query, {"line_config_id": line_config_id}).fetchall()
            }

            new_entries = []
            update_entries = []
            received_ids = set()

            # Process incoming JSON
            for stage in data:
                stage_id = stage.get('stage_id')
                rank_id = stage.get('rank_id', 1)
                for process in stage.get('process', []):
                    process_id = process.get('process_id')
                    key = (stage_id, process_id)

                    if key in existing_records:
                        line_process_id = existing_records[key]
                        received_ids.add(line_process_id)  # Keep track of existing entries
                        update_entries.append({
                            "line_process_id": line_process_id,
                            "rank_id": rank_id,
                            "modified_on": datetime.datetime.now(),
                            "modified_by": created_by
                        })
                    else:
                        # New entry: Insert it
                        new_entries.append({
                            "line_config_id": line_config_id,
                            "stage_id": stage_id,
                            "process_id": process_id,
                            "rank_id": rank_id,
                            **cc
                        })
            ids_tuple = tuple(received_ids) if received_ids else None
            # Soft delete missing records (not in received JSON)
            con = ''
            if ids_tuple:
                con += 'AND (:ids IS NULL OR line_process_id NOT IN :ids)'
            delete_query = text(f"""
                    WITH updated_line_process AS (
                        UPDATE line_process
                        SET deleted = TRUE
                        WHERE line_config_id = :line_config_id {con}
                        RETURNING line_process_id
                    ), updated_line_map AS (
                        UPDATE line_map
                        SET deleted = TRUE
                        WHERE line_process_id IN (SELECT line_process_id FROM updated_line_process)
                        AND deleted IS NOT TRUE
                        RETURNING line_map_id
                    )
                    UPDATE employee_line
                    SET deleted = TRUE
                    WHERE line_map_id IN (SELECT line_map_id FROM updated_line_map);
                """)
            s.execute(delete_query, {'line_config_id': line_config_id, 'ids': ids_tuple})

            # Bulk update existing records
            if update_entries:
                s.bulk_update_mappings(LineProcess, update_entries)

            # Bulk insert new records
            if new_entries:
                s.bulk_insert_mappings(LineProcess, new_entries)

            s.commit()
        except Exception as e:
            s.flush()
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': 'Update successfully'
        }, 200

    @login_required(permissions='line_process.delete')
    def delete(self, line_config_id):

        # result = update_local(
        #     model=LineProcess,
        #     condition=LineProcess.line_config_id == line_config_id,
        #     values={
        #         'deleted': True,
        #         'deleted_at': datetime.datetime.now()
        #     }
        # )
        s = db_client.session
        try:
            delete_query = text("""
                                WITH updated_line_process AS (
                                    UPDATE line_process
                                    SET deleted = TRUE
                                    WHERE line_config_id = :line_config_id and deleted is not true
                                    RETURNING line_process_id
                                ), updated_line_map AS (
                                    UPDATE line_map
                                    SET deleted = TRUE
                                    WHERE line_process_id IN (SELECT line_process_id FROM updated_line_process)
                                    AND deleted IS NOT TRUE
                                    RETURNING line_map_id
                                )
                                UPDATE employee_line
                                SET deleted = TRUE
                                WHERE line_map_id IN (SELECT line_map_id FROM updated_line_map)
                                """)
            s.execute(delete_query, {'line_config_id': line_config_id})
            s.commit()
        except Exception as e:
            s.rollback()
            s.flush()
            return map_sqlalchemy_error_to_http_status(e)

        return {
            'success': True,
            'message': 'Delete Successfully'
        }