import datetime
from flask import request, session
from flask_restx import Resource
# from .. import ipss_db
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger
from sqlalchemy.exc import SQLAlchemyError
from .errorhandling import map_sqlalchemy_error_to_http_status
# from ..api_doc import activity_stage_maps_roles_fields
from ..models.activity_stage_map import ActivityStageMap, ProcessIncentiveSlabs
from ipss_utils.decorators import login_required

import io
import pandas as pd
from flask import send_file

from ..routes.activity_stage_map import activity_stage_map_api_route, activity_stage_map_list_response, \
    create_activity_stage_map_response, update_activity_stage_map_response, \
    bulk_create_activity_stage_map_model, nested_product_model
# from sqlalchemy import and_, text
from ..routes.activity_stage_map import create_activity_stage_map_model
from .. import ipss_db, db_client
from ..api_doc import activity_filters

# Primary p_key name

primary_key = 'activity_stage_map_id'


@activity_stage_map_api_route.route('/')
class ActivityStageMapApi(Resource):
    per_page = 20
    @activity_stage_map_api_route.marshal_with(activity_stage_map_list_response)
    @activity_stage_map_api_route.doc(params={**list_api_params,**activity_filters})
    @login_required()
    def get(self):
        """
        List of activity_stage_map with pagination
        TODO: Search
        :return:
        """
        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id', None)
        result_per_page = request.args.get('results_per_page', 20)
        page = request.args.get("page", 1)
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0
        sql_con = ''
        if request.args.get('activity_stage_map_id'):
            sql_con+=' and asm.activity_stage_map_id=:activity_stage_map_id '
        if request.args.get('config_id'):
            sql_con += ' and asm.config_id=:config_id '
        if request.args.get('production_stage_id'):
            sql_con += ' and asm.production_stage_id=:production_stage_id '
        if request.args.get('product_id'):
            sql_con += ' and ps.product_id=:product_id '
        if request.args.get('is_final_process'):
            sql_con += ' and asm.is_final_process=:is_final_process '
        result=text(f'''
        select asm.*,process_name as config_name,s.stage_name,s.stage_id,
         p.product_id,product_code,product_name,p.sku_id
         from activity_stage_map as asm
        join process_config as cm on cm.process_id=asm.config_id
        join production_stages as ps on ps.id=asm.production_stage_id
        join stage as s on s.stage_id=ps.stage_id
        join products p on p.product_id=ps.product_id
        where asm.compcode=:compcode and asm.deleted is not true and
        cm.deleted is not true and ps.deleted is not true and s.deleted is not true {sql_con}
        order by asm.activity_stage_map_id desc
        limit :limit offset :offset
        ''')
        result=query_to_dict(db_client.engine.execute(result,
                                                      activity_stage_map_id=request.args.get('activity_stage_map_id'),
                                                      config_id=request.args.get('config_id'),
                                                      is_final_process=request.args.get('is_final_process'),
                                                      product_id=request.args.get('product_id'),
                                                      production_stage_id=request.args.get('production_stage_id'),
                                                      compcode=compcode,
                                                      limit=result_per_page,
                                                      offset=offset))
        sql_count=text(f'''
        select count(*)
        from activity_stage_map as asm
        join process_config as cm on cm.process_id=asm.config_id
        join production_stages as ps on ps.id=asm.production_stage_id
        join stage as s on s.stage_id=ps.stage_id
        where asm.compcode=:compcode and asm.deleted is not true and
        cm.deleted is not true and ps.deleted is not true and s.deleted is not true 
{sql_con}
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,
                                                      activity_stage_map_id=request.args.get('activity_stage_map_id'),
                                                      config_id=request.args.get('config_id'),
                                                         is_final_process=request.args.get('is_final_process'),
                                                         product_id=request.args.get('product_id'),

                                                      production_stage_id=request.args.get('production_stage_id'),
                                                      compcode=compcode,
                                                      limit=result_per_page,
                                                      offset=offset))
        return {
            'total_results': sql_count[0].get('count', 0) if sql_count else 0,
            'page': page,
            'results_per_page': result_per_page,
            "results": result
        }


    @login_required()
    @activity_stage_map_api_route.expect(bulk_create_activity_stage_map_model)
    @activity_stage_map_api_route.marshal_with(create_activity_stage_map_response)
    def post(self):
        """
        Create activity_stage_map record and return inserted id
        :return:
        """
        data = request.json
        data = data.get('data', None)
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": str(datetime.datetime.now()),
              "created_by": compcode.get('username')
              # "product_id": pkey if pkey else result.get('primary_key_id')[0]
              }
        updateData = [{**data.pop(i), **cc} for i in range(len(data) - 1, -1, -1) if
                      data[i].get('activity_stage_map_id')]
        data = [{**i, **cc} for i in data]
        error = ''
        message = None
        try:
            with db_client.session.begin():

                if updateData:
                    db_client.session.bulk_update_mappings(mapper=ActivityStageMap, mappings=updateData)
                if data:
                    db_client.session.bulk_insert_mappings(mapper=ActivityStageMap, mappings=data)
        except SQLAlchemyError as e:
            # error = str(e)
            db_client.session.rollback()
            db_client.session.flush()
            res = map_sqlalchemy_error_to_http_status(e)
            return res
        success = False if error else True
        if success:
            message = "Records created Successfully"
        return {
            'success': success,
            'message': message,
            'error': error,
        }


@activity_stage_map_api_route.route('/<activity_stage_map_id>/')
class EmployeeUpdateApi(Resource):
    @activity_stage_map_api_route.marshal_with(update_activity_stage_map_response)
    @login_required()
    def delete(self, activity_stage_map_id):
        """
        Soft delete ActivityStageMap record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=ActivityStageMap,
            condition=ActivityStageMap.activity_stage_map_id == activity_stage_map_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

######################################################################

@activity_stage_map_api_route.route('/nested-model')
class ActivityStageMapModel(Resource):
    per_page = 20
    @activity_stage_map_api_route.marshal_with(nested_product_model)
    @activity_stage_map_api_route.doc(params={**list_api_params,**activity_filters})
    @login_required()
    def get(self):
        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id', None)
        result_per_page = request.args.get('results_per_page', 20)
        page = request.args.get("page", 1)
        offset = (page - 1) * result_per_page if (page - 1) * result_per_page else 0
        sql_con = ''
        if request.args.get('activity_stage_map_id'):
            sql_con += ' and asm.activity_stage_map_id=:activity_stage_map_id '
        if request.args.get('config_id'):
            sql_con += ' and asm.config_id=:config_id '
        if request.args.get('production_stage_id'):
            sql_con += ' and asm.production_stage_id=:production_stage_id '
        if request.args.get('product_id'):
            sql_con += ' and ps.product_id=:product_id '
        if request.args.get('is_final_process'):
            sql_con += ' and asm.is_final_process=:is_final_process '
        result = text(f'''
                select p.product_id,product_code,product_name,p.sku_id,
                jsonb_agg(jsonb_build_object(
                'stage_name',s.stage_name,
                'stage_id',s.stage_id,
                'target_per_hour',asm.target_per_hour,
                'config_name',cm.process_name,
                'is_final_process',COALESCE(asm.is_final_process,false),
                'config_id',asm.config_id,
                'production_stage_id',asm.production_stage_id
                )) as stage_data
                
                from products p 
                join production_stages ps on ps.product_id=p.product_id and ps.deleted is not true 
                join stage s on s.stage_id=ps.stage_id and ps.deleted is not true
                join activity_stage_map asm on asm.production_stage_id=ps.id and asm.deleted is not true
                join process_config as cm on cm.process_id=asm.config_id and cm.deleted is not true
                where asm.compcode=:compcode and asm.deleted is not true and
                cm.deleted is not true and ps.deleted is not true and s.deleted is not true {sql_con}
                group by p.product_id,product_code,product_name,p.sku_id
                limit :limit offset :offset
                ''')
        result = query_to_dict(db_client.engine.execute(result,
                                                        activity_stage_map_id=request.args.get('activity_stage_map_id'),
                                                        config_id=request.args.get('config_id'),
                                                        product_id=request.args.get('product_id'),
                                                        production_stage_id=request.args.get('production_stage_id'),
                                                        is_final_process=request.args.get('is_final_process'),
                                                        compcode=compcode,
                                                        limit=result_per_page,
                                                        offset=offset))
        sql_count = text(f'''
                select count(distinct p.product_id)
                 from products p 
                join production_stages ps on ps.product_id=p.product_id and ps.deleted is not true 
                join stage s on s.stage_id=ps.stage_id and ps.deleted is not true
                join activity_stage_map asm on asm.production_stage_id=ps.id and asm.deleted is not true
                join process_config as cm on cm.process_id=asm.config_id and cm.deleted is not true
                where asm.compcode=:compcode and asm.deleted is not true and
                cm.deleted is not true and ps.deleted is not true and s.deleted is not true {sql_con}
                ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           activity_stage_map_id=request.args.get(
                                                               'activity_stage_map_id'),
                                                           config_id=request.args.get('config_id'),
                                                           product_id=request.args.get('product_id'),
                                                           production_stage_id=request.args.get('production_stage_id'),
                                                           is_final_process=request.args.get('is_final_process'),
                                                           compcode=compcode,
                                                           limit=result_per_page,
                                                           offset=offset))
        return {
            'total_results': sql_count[0].get('count', 0) if sql_count else 0,
            'page': page,
            'results_per_page': result_per_page,
            "results": result
        }

    

@activity_stage_map_api_route.route('/<activity_stage_map_id>/slabs')
class ProcessIncentiveSlabsApi(Resource):
    @login_required()
    def get(self, activity_stage_map_id):
        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id', None)
        
        sql = text('''
            SELECT id, activity_stage_map_id, from_qty, to_qty, incentive_amount
            FROM process_incentive_slabs
            WHERE activity_stage_map_id = :map_id AND compcode = :compcode AND deleted IS NOT TRUE
            ORDER BY from_qty ASC
        ''')
        
        results = query_to_dict(db_client.engine.execute(sql, map_id=activity_stage_map_id, compcode=compcode))
        
        # Convert Decimals to floats to fix JSON serialization error
        for result in results:
            if result.get('from_qty') is not None:
                result['from_qty'] = float(result['from_qty'])
            if result.get('to_qty') is not None:
                result['to_qty'] = float(result['to_qty'])
            if result.get('incentive_amount') is not None:
                result['incentive_amount'] = float(result['incentive_amount'])
        
        return {
            'success': True,
            'results': results
        }

    @login_required()
    def post(self, activity_stage_map_id):
        data = request.json
        slabs_data = data.get('slabs', [])
        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id', None)
        username = curr.get('username')
        
        error = ''
        try:
            with db_client.session.begin():
                # Hard delete existing slabs for this map_id to replace them
                db_client.session.execute(
                    text("DELETE FROM process_incentive_slabs WHERE activity_stage_map_id = :map_id AND compcode = :compcode"),
                    {'map_id': activity_stage_map_id, 'compcode': compcode}
                )
                
                # Insert new ones
                insert_data = []
                for s in slabs_data:
                    insert_data.append(ProcessIncentiveSlabs(
                        activity_stage_map_id=activity_stage_map_id,
                        from_qty=s.get('from_qty'),
                        to_qty=s.get('to_qty'),
                        incentive_amount=s.get('incentive_amount'),
                        compcode=compcode,
                        modified_by=username,
                        created_on=datetime.datetime.now()
                    ))
                
                if insert_data:
                    db_client.session.bulk_save_objects(insert_data)
                    
        except SQLAlchemyError as e:
            db_client.session.rollback()
            return map_sqlalchemy_error_to_http_status(e)
            
        return {
            'success': True,
            'message': 'Incentive slabs updated successfully'
        }

@activity_stage_map_api_route.route('/incentives/export')
class ExportIncentivesApi(Resource):
    @login_required()
    def get(self):
        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id', None)
        
        # 1. Fetch all mappings and their existing slabs
        sql = text('''
            SELECT 
                asm.activity_stage_map_id,
                p.sku_id as "SKU",
                p.product_code as "Product",
                s.stage_name as "Stage",
                cm.process_name as "Process",
                asm.target_per_hour as "Target",
                pis.from_qty, pis.to_qty, pis.incentive_amount
            FROM activity_stage_map asm
            JOIN process_config cm ON cm.process_id = asm.config_id
            JOIN production_stages ps ON ps.id = asm.production_stage_id
            JOIN stage s ON s.stage_id = ps.stage_id
            JOIN products p ON p.product_id = ps.product_id
            LEFT JOIN process_incentive_slabs pis ON pis.activity_stage_map_id = asm.activity_stage_map_id AND pis.deleted IS NOT TRUE
            WHERE asm.compcode = :compcode 
              AND asm.deleted IS NOT TRUE
              AND cm.deleted IS NOT TRUE 
              AND ps.deleted IS NOT TRUE 
              AND s.deleted IS NOT TRUE
            ORDER BY p.sku_id, s.stage_name, cm.process_name, pis.from_qty ASC
        ''')
        
        raw_data = query_to_dict(db_client.engine.execute(sql, compcode=compcode))
        
        # 2. Process data to horizontal format (max 10 slabs)
        processed_data = {}
        for row in raw_data:
            map_id = row['activity_stage_map_id']
            if map_id not in processed_data:
                processed_data[map_id] = {
                    'activity_stage_map_id': map_id,
                    'SKU': row['SKU'],
                    'Product': row['Product'],
                    'Stage': row['Stage'],
                    'Process': row['Process'],
                    'Target': row['Target']
                }
                for i in range(1, 11):
                    processed_data[map_id][f'Slab {i} From'] = ''
                    processed_data[map_id][f'Slab {i} To'] = ''
                    processed_data[map_id][f'Slab {i} Amt'] = ''
                processed_data[map_id]['_slab_count'] = 1
            
            # If there is slab data, assign it to the next available slab slot (up to 10)
            if row['from_qty'] is not None and processed_data[map_id]['_slab_count'] <= 10:
                idx = processed_data[map_id]['_slab_count']
                processed_data[map_id][f'Slab {idx} From'] = row['from_qty']
                processed_data[map_id][f'Slab {idx} To'] = row['to_qty']
                processed_data[map_id][f'Slab {idx} Amt'] = row['incentive_amount']
                processed_data[map_id]['_slab_count'] += 1
                
        # Remove tracking variable and convert to list
        final_list = []
        for v in processed_data.values():
            v.pop('_slab_count', None)
            final_list.append(v)
            
        df = pd.DataFrame(final_list)
        
        # 3. Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Incentive Slabs')
            workbook = writer.book
            worksheet = writer.sheets['Incentive Slabs']
            
            # Add formatting for headers
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#1976d2',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                
            # Set column widths
            worksheet.set_column('A:A', None, None, {'hidden': True}) # Hide map_id column
            worksheet.set_column('B:B', 15) # SKU
            worksheet.set_column('C:C', 50) # Product (increased to 50)
            worksheet.set_column('D:E', 25) # Stage, Process (increased)
            worksheet.set_column('F:F', 12) # Target
            worksheet.set_column('G:AJ', 15) # Slabs
            
            # Freeze the first row (headers) so it stays fixed on scroll
            worksheet.freeze_panes(1, 6)
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='Incentive_Slabs_Template.xlsx'
        )

@activity_stage_map_api_route.route('/incentives/import')
class ImportIncentivesApi(Resource):
    @login_required()
    def post(self):
        curr = request.args.get('current_user', {})
        compcode = curr.get('company_id', None)
        username = curr.get('username')
        
        if 'file' not in request.files:
            return {'success': False, 'message': 'No file uploaded'}, 400
            
        file = request.files['file']
        if file.filename == '':
            return {'success': False, 'message': 'No file selected'}, 400
            
        try:
            df = pd.read_excel(file)
            
            # Require activity_stage_map_id column to map it back accurately
            if 'activity_stage_map_id' not in df.columns:
                return {'success': False, 'message': 'Invalid template. Missing activity_stage_map_id column.'}, 400
                
            with db_client.session.begin():
                insert_data = []
                seen_map_ids = set()
                
                for index, row in df.iterrows():
                    map_id = row['activity_stage_map_id']
                    if pd.isna(map_id):
                        continue
                    map_id = int(map_id)
                        
                    # Delete existing slabs for this map_id once per import
                    if map_id not in seen_map_ids:
                        db_client.session.execute(
                            text("DELETE FROM process_incentive_slabs WHERE activity_stage_map_id = :map_id AND compcode = :compcode"),
                            {'map_id': map_id, 'compcode': compcode}
                        )
                        seen_map_ids.add(map_id)
                    
                    # Look for up to 10 slabs
                    for i in range(1, 11):
                        from_col = f'Slab {i} From'
                        to_col = f'Slab {i} To'
                        amt_col = f'Slab {i} Amt'
                        
                        if from_col in df.columns and amt_col in df.columns:
                            from_val = row.get(from_col)
                            to_val = row.get(to_col)
                            amt_val = row.get(amt_col)
                            
                            if not pd.isna(from_val) and str(from_val).strip() != '' and not pd.isna(amt_val) and str(amt_val).strip() != '':
                                try:
                                    f_qty = float(from_val)
                                    t_qty = float(to_val) if not pd.isna(to_val) and str(to_val).strip() != '' else None
                                    a_amt = float(amt_val)
                                    insert_data.append(ProcessIncentiveSlabs(
                                        activity_stage_map_id=map_id,
                                        from_qty=f_qty,
                                        to_qty=t_qty,
                                        incentive_amount=a_amt,
                                        compcode=compcode,
                                        modified_by=username,
                                        created_on=datetime.datetime.now()
                                    ))
                                except (ValueError, TypeError):
                                    continue
                
                if insert_data:
                    db_client.session.bulk_save_objects(insert_data)
                    
            return {'success': True, 'message': 'Incentive slabs imported successfully!'}
            
        except Exception as e:
            db_client.session.rollback()
            return {'success': False, 'message': f'Error processing file: {str(e)}'}, 500
