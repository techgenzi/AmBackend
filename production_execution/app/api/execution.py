import datetime
from flask import request, session
from flask_restx import Resource, abort
# from .. import ipss_db
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger, bindparam, NUMERIC, String, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.functions import coalesce

from ..api_doc import searc_filters
# from ..api_doc import prod_exes_roles_fields
from ..models.execution import ProdExecution
from ipss_utils.decorators import login_required

from ..routes.execution import prod_exe_api_route, prod_exe_list_response, create_prod_exe_response, \
    update_prod_exe_model, update_prod_exe_response, bulk_data_post, data_move_model
# from sqlalchemy import and_, text
from ..routes.execution import create_prod_exe_model, get_prod_exe_response
from .. import ipss_db, db_client

# Primary p_key name

primary_key = 'id'
def product_query():
    return text('''
    WITH cte AS (
    SELECT 
        ipss_asset_id,title,asset_identifier, 
        jsonb_object_agg(ca.external_name, 
            CASE 
                WHEN jsonb_typeof(attr.value) = 'array' THEN 
                    (attr.value->0->>'name')::text  -- Extract name and ensure it's text
                ELSE 
                    TRIM(BOTH '\"' FROM attr.value::text)  -- Remove any extraneous quotes
            END) AS attributes
    FROM 
        ipss_assets ia
    JOIN LATERAL 
        jsonb_each(ia.asset_attributes::jsonb) AS attr(key, value) 
    ON 
        ia.asset_attributes IS NOT NULL 
        AND ia.asset_attributes::jsonb IS NOT NULL
    JOIN config_attributes ca ON ca.unique_id = attr.key
    WHERE 
        jsonb_typeof(ia.asset_attributes::jsonb) = 'object'  -- Ensure it's a JSON object
    GROUP BY 
        ia.ipss_asset_id
    ORDER BY 
        ia.ipss_asset_id DESC
)
    ''')

def upadte_stages(data=[]):
    updqte_query = text('''
    update production_plan set current_stage=:stage_id
    where id=:prod_plan_id
    ''').bindparams(
        stage_id=bindparam('stage_id', type_=BigInteger),
        prod_plan_id=bindparam('prod_plan_id', type_=String)
    )
    error = ''
    try:
        sql_query = db_client.engine.execute(updqte_query, data)
        return
    except SQLAlchemyError as e:
        error = str(e)
        db_client.session.flush()
        return abort(409, "Failed to update production_plans Stage")


@prod_exe_api_route.route('/')
class ProdExecutionApi(Resource):
    per_page = 20

    @prod_exe_api_route.marshal_with(prod_exe_list_response)
    @prod_exe_api_route.doc(params={**list_api_params, **searc_filters})
    @login_required()
    def get(self):
        """
        List of prod_exe with pagination
        TODO: Search
        :return:
        """
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        compcode = request.args.get('current_user').get('company_id', None)
        sql_condition = ""
        if request.args.get('id'):
            sql_condition += ' and pe.id=:id '
        if request.args.get('stage_id'):
            sql_condition += ' and ps.stage_id=:stage_id '
        if request.args.get('prod_plan_id'):
            sql_condition += ' and pe.prod_plan_id=:prod_plan_id '
        if request.args.get('status'):
            sql_condition += ' and pp.status=:status '
        if request.args.get('operation_date'):
            sql_condition += ' and pp.plan_date = :operation_date '
        # if request.args.get('is_material_recieved'):
        #     sql_condition += ' and pe.is_material_recieved = :is_material_recieved '

        paginate = " order by pe.id desc " \
                   " limit  :limit offset :offset "
        total_results_query = text(f"""
                                    select pe.*,s.stage_name,ps.rank_id,p.product_code,p.product_name from prod_execution pe
                                    join production_stages as ps on ps.id = pe.stage_id
                                    join stage s on s.stage_id = ps.stage_id 
                                    join production_plan pp on pp.production_plan_id = pe.prod_plan_id
                                    join products p on p.product_id = pe.product_id
                                    where pe.compcode=:c_code and pe.deleted is not true
                                        {sql_condition}
                                        """)

        total_results_list = query_to_dict(db_client.engine.execute(total_results_query,
                                                                    status=request.args.get('status'),
                                                                    is_material_recieved=request.args.get('is_material_recieved'),
                                                                    c_code=compcode,
                                                                    prod_plan_id=request.args.get('prod_plan_id'),
                                                                    stage_id=request.args.get('stage_id'),
                                                                    id=request.args.get('id'),
                                                                    operation_date=request.args.get('operation_date')
                                                                    ))

        prod_exec_query = text(str(total_results_query) + paginate)

        prod_exec_results = query_to_dict(db_client.engine.execute(prod_exec_query,
                                                                   c_code=compcode,
                                                                   is_material_recieved=request.args.get('is_material_recieved'),
                                                                   status=request.args.get('status'),
                                                                   prod_plan_id=request.args.get('prod_plan_id'),
                                                                   stage_id=request.args.get('stage_id'),
                                                                   id=request.args.get('id'),
                                                                   operation_date=request.args.get('operation_date'),
                                                                   limit=results_per_page,
                                                                   offset=offset
                                                                   ))

        return {
            "primary_key": primary_key,
            "total_results": len(total_results_list),
            "page": paged,
            "results_per_page": results_per_page,
            "results": prod_exec_results
        }

    @login_required()
    @prod_exe_api_route.expect(bulk_data_post)
    @prod_exe_api_route.marshal_with(create_prod_exe_response)
    def post(self):
        """
        Create prod_exe record and return inserted id
        :return:
        """
        data = request.json
        data = data.get('data')
        result = ipss_db.bulk_upload(db_client=db_client, data=data, model=ProdExecution)
        # if result.get('success'):
        #     upadte_stages(data=data)
        return result


@prod_exe_api_route.route('/<id>/')
class EmployeeUpdateApi(Resource):
    @staticmethod
    def update_record(data, id):
        data.pop('id', None)

        result = ipss_db.update_record(
            model=ProdExecution,
            condition=ProdExecution.id == id,
            values=data
        )
        return result

    @prod_exe_api_route.marshal_with(get_prod_exe_response)
    @login_required()
    def get(self, id):
        """
        Read user record / single record
        :param id:
        :return:
        """

        user = ProdExecution.query.filter_by(id=int(id)).first()
        return user

    @prod_exe_api_route.expect(update_prod_exe_model)
    @prod_exe_api_route.marshal_with(update_prod_exe_response)
    @login_required()
    def put(self, id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, id)
        return response

    @prod_exe_api_route.expect(update_prod_exe_model)
    @prod_exe_api_route.marshal_with(update_prod_exe_response)
    @login_required()
    def patch(self, id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, id)
        return response

    @prod_exe_api_route.marshal_with(update_prod_exe_response)
    @login_required()
    def delete(self, id):
        """
        Soft delete ProdExecution record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=ProdExecution,
            condition=ProdExecution.id == id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result


######################################################################

@prod_exe_api_route.route('/stage-move')
class StageMoving(Resource):
    @login_required()
    @prod_exe_api_route.expect(data_move_model)
    @prod_exe_api_route.marshal_with(create_prod_exe_response)
    def put(self):
        data = request.json
        error = ''
        try:
            stmt = (
                update(ProdExecution)
                .where(ProdExecution.id == int(data.get('id', 0)))
                .values(outward_qty=coalesce(ProdExecution.outward_qty, 0) + data.get('outward_qty'),
                        is_material_recieved=data.get('is_material_recieved',False),
                        wastage=data.get('wastage',0)))
            result = db_client.session.execute(stmt)
            db_client.session.commit()
        except SQLAlchemyError as e:
            error = str(e)
            db_client.session.flush()
        result = ({
            'success': False if error else True,
            "message": "Failed to Move next Stage" if error else 'Registered Successfully.',
            'error': error,
        })

        # result = ipss_db.update_record(
        #     model=ProdExecution,
        #     condition=ProdExecution.id == int(data.get('id',0)),
        #     values={
        #         'outward_qty': data.get('outward_qty'),
        #         'wastage': data.get('wastage')
        #     }
        # )
        data['inward_qty'] = data.pop('outward_qty',None)
        data['status'] = 'pending'
        # sql_query=text('''
        # select ps1.id  from production_stages ps
        # join production_stages as ps1 on ps1.ref_id =ps.id
        # where ps.product_id =:product_id and ps1.rank_id =cast(:rank_id as int)+1
        # ''')
        # sql_query=query_to_dict(db_client.engine.execute(sql_query,
        #                                                  product_id=data.get('product_id'),
        #                                                  rank_id=data.get('rank_id',0)))

        sql_query = text('''
                WITH cte AS (
            SELECT ps.product_id, ps1.id, ps1.rank_id  
            FROM production_stages ps 
            JOIN production_stages ps1 ON ps1.ref_id = ps.id
            WHERE ps1.id = :stage_id and ps1.deleted is not true and 
            ps.deleted is not true
        )
        SELECT ps1.id  
        FROM production_stages ps 
        JOIN production_stages ps1 ON ps1.ref_id = ps.id
        JOIN cte ON ps.product_id = cte.product_id
        WHERE ps1.rank_id = cte.rank_id + 1
        and ps1.deleted is not true and 
            ps.deleted is not true;
        ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query, stage_id=data.get('stage_id')))
        if result.get('success') and len(sql_query):
            data['stage_id'] = sql_query[0].get('id')
            sql_query = text('''
            select id from prod_execution as pe
            where deleted is not true and prod_plan_id=:prod_plan_id
            and stage_id=:stage_id
            ''')
            sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                               stage_id=data.get('stage_id'),
                                                               prod_plan_id=data.get('prod_plan_id')))
            # data.pop('product_id', None)
            data.pop('rank_id', None)
            data.pop('id', None)
            data1=data.copy()
            data1.pop('wastage')
            if not len(sql_query):
                result = ipss_db.insert_record(model=ProdExecution, values=data1)
                result = ipss_db.created_response(
                    result=result,
                    message="Record has been created successfully",
                    primary_key=primary_key
                )
                result = result[0]

            else:
                # result = ipss_db.update_record(
                #     model=ProdExecution,
                #     condition=ProdExecution.id == int(sql_query[0].pop('id', 0)),
                #     values=data
                # )
                error = ''
                try:
                    stmt = (
                        update(ProdExecution)
                        .where(ProdExecution.id == int(sql_query[0].pop('id', 0)))
                        .values(inward_qty=ProdExecution.inward_qty + data.get('inward_qty')))
                    result = db_client.session.execute(stmt)
                    db_client.session.commit()
                except SQLAlchemyError as e:
                    error = str(e)
                    db_client.session.flush()
                result = ({
                    'success': False if error else True,
                    "message": "Failed to Move next Stage" if error else 'Registered Successfully.',
                    'error': error,
                })

            if not result.get('success'):
                result['message'] = 'Failed to Move next Stage'
            print(result)
        return result
