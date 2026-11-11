import datetime
from collections import defaultdict
from pprint import pprint

from flask import request, session
from flask_restx import Resource, abort
# from .. import ipss_db
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, func, distinct, BigInteger, insert, update
from sqlalchemy.exc import SQLAlchemyError

from ..api_doc import search_filters
# from ..api_doc import production_requirmentss_roles_fields
from ..models.bom import BOM,BOMComponent
from ipss_utils.decorators import login_required

from ..routes.bom import bom_api_route, bom_single_get_model, bom_get_all_model, bom_patch_model, create_bom_response, \
    update_bom_response, product_service_list_response, multiple_bom_get_model
# from sqlalchemy import and_, text
# from ..routes.bom import create_production_requirments_model, get_production_requirments_response
from .. import ipss_db, db_client
from .errorhandling import map_sqlalchemy_error_to_http_status

# Primary p_key name

primary_key = 'id'


def duplicate_control(product_id=None, ids=None, model=None, fkey=None):
    if product_id and model:
        current_user = request.args.get('current_user')
        ccode = current_user.get('company_id')
        # sort_no=sort_no.replace(' ','').upper()
        user_query = model.query.filter(model.product_id == product_id,
                                        # func.replace(func.upper(func.trim(ProductionData.sort_no)), ' ', '') == sort_no,
                                        model.compcode == ccode, model.deleted == False)
        if ids:
            user_query = user_query.filter(model.id != ids)
        if fkey:
            user_query = user_query.fliter(model.production_id == fkey)
        user = user_query.first()
        if user:
            return abort(409, 'Record Already Exists')
        else:
            return
    else:
        return

def format(results):
    bom_dict = defaultdict(lambda: {'data': []})

    for row in results:
        bom_id = row['bom_id']
        if 'bom_product_id' not in bom_dict[bom_id]:
            bom_dict[bom_id].update({
                'bom_id': bom_id,
                'bom_product_id': row['bom_product_id'],
                'bom_product_name': row['bom_product_name'],
                'bom_product_code': row['bom_product_code'],
                'description': row['description'],
            })
        bom_dict[bom_id]['data'].append({
            'bom_component_id': row['bom_component_id'],
            'product_id': row['product_id'],
            'product_name': row['product_name'],
            'product_code': row['product_code'],
            'is_mark_data': row['is_mark_data'],
            'product_group_id': row['product_group_id'],
            'product_group_name': row['product_group_name'],
            'sku_id':row['sku_id'],
            'quantity': row['quantity'],
            'notes': row['notes']
        })

    output = list(bom_dict.values())
    pprint(output)
    return output


@bom_api_route.route('/')
class BOMApi(Resource):
    per_page = 20

    @bom_api_route.marshal_with(bom_get_all_model)
    @bom_api_route.doc(params={**search_filters, **list_api_params})
    # @login_required(permissions='production_requirements.list||production_requirements.edit||'
    #                             'production_requirements.view||production_requirements.delete')
    @login_required(permissions='bom.list||bom.add')
    def get(self):
        """
        List of production_requirments with pagination
        TODO: Search
        :return:
        """
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page if (paged - 1) * results_per_page else 0
        product_id = request.args.get('product_id', None)
        bom_id = request.args.get('bom_id', None)
        sql_condition = ''
        if bom_id:
            sql_condition += ' b.bom_id=:bom_id and '
        if product_id:
            sql_condition += ' b.product_id=:product_id and '
    #     sql_query = text(f'''
    #         WITH paginated_bom AS (
    #     SELECT b.bom_id, b.product_id AS bom_product_id, p.product_name AS bom_product_name,
    #     p.product_code as bom_product_code,
    #     b.description,
    #     p.sku_id,
    #     u.uom
    #     FROM bom AS b
    #     LEFT JOIN products AS p ON p.product_id = b.product_id
    #     left join uom as u on u.id = p.uom_id
    #     WHERE b.deleted IS NOT TRUE AND b.compcode =:compcode and {sql_condition} 1=1
    #     ORDER BY b.bom_id DESC
    #     LIMIT :limit OFFSET :offset
    # )
    # SELECT
    #     pb.bom_id,
    #     pb.bom_product_id,
    #     pb.bom_product_name,
    #     pb.bom_product_code,
    #     pb.description,
    #     bc.bom_component_id,
    #     bc.product_id,
	# 	cp.product_group_id,
    #     cp.product_name,
    #     cp.product_code,
    #     bc.quantity,
    #     cp.sku_id,
    #     bc.notes,
    #     pg.group_name as product_group_name
    # FROM paginated_bom AS pb
    # LEFT JOIN bom_component AS bc ON pb.bom_id = bc.bom_id AND bc.deleted IS NOT TRUE
    # LEFT JOIN products AS cp ON cp.product_id = bc.product_id
    # left join product_group as pg on pg.product_group_id = cp.product_group_id
    # order by pb.bom_id desc
    #     ''')
        sql_query = text(f'''
        WITH paginated_bom AS (
    SELECT b.bom_id, b.product_id AS bom_product_id, p.product_name AS bom_product_name,
           p.product_code AS bom_product_code, b.description, p.sku_id, u.uom,p.uom_id
    FROM bom AS b
    LEFT JOIN products AS p ON p.product_id = b.product_id
    LEFT JOIN uom AS u ON u.id = p.uom_id
    WHERE b.deleted IS NOT TRUE AND p.deleted IS NOT TRUE AND b.compcode = :compcode AND {sql_condition} 1=1
    ORDER BY b.bom_id DESC
    LIMIT :limit OFFSET :offset
)
SELECT pb.bom_id, pb.bom_product_id, pb.bom_product_name, pb.bom_product_code,
       pb.description, pb.uom,pb.uom_id,pb.sku_id,
       SUM(bc.quantity::numeric) AS total_quantity,
       json_agg(
           json_build_object(
               'bom_component_id', bc.bom_component_id,
               'product_id', bc.product_id,
               'stage_id', bc.stage_id,
               'stage_name', s.stage_name,
               'product_name', cp.product_name,
               'product_code', cp.product_code,
               'product_group_id', cp.product_group_id,
               'is_mark_data' , coalesce(bc.is_mark_data, False),
               'product_group_name', pg.group_name,
               'sku_id', cp.sku_id,
               'quantity', bc.quantity,
               'uom_id', u.id,
               'uom', u.uom,
               'notes', bc.notes
           )
       ) AS data
FROM paginated_bom AS pb
LEFT JOIN bom_component AS bc ON pb.bom_id = bc.bom_id AND bc.deleted IS NOT TRUE
LEFT JOIN stage AS s ON s.stage_id = bc.stage_id
LEFT JOIN products AS cp ON cp.product_id = bc.product_id AND cp.deleted IS NOT TRUE
LEFT JOIN uom AS u ON u.id = cp.uom_id
LEFT JOIN product_group AS pg ON pg.product_group_id = cp.product_group_id
GROUP BY pb.bom_id,pb.sku_id, pb.bom_product_id, pb.bom_product_name, pb.bom_product_code, pb.description, pb.uom, pb.uom_id
ORDER BY pb.bom_id DESC;
        ''')
        sql_con = text(f'''
    SELECT count(b.bom_id)
    FROM bom AS b
    LEFT JOIN products AS p ON p.product_id = b.product_id
    WHERE b.deleted IS NOT TRUE AND p.deleted IS NOT TRUE AND b.compcode =:compcode and {sql_condition} 1=1
        ''')

        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           product_id=product_id,
                                                           bom_id=bom_id,
                                                           limit=results_per_page,
                                                           compcode=ccode,
                                                           offset=offset))
        sql_count = query_to_dict(db_client.engine.execute(sql_con,
                                                           product_id=product_id,
                                                           bom_id=bom_id,
                                                           compcode=ccode))

        pprint(sql_query)
        return {
            "total_results": sql_count[0].get('count') if len(sql_count) else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query}

    # @login_required(permissions='production_requirements.add')
    @login_required(permissions='bom.add')
    @bom_api_route.expect(bom_single_get_model)
    @bom_api_route.marshal_with(create_bom_response)
    def post(self):
        """
        Create production_requirments record and return inserted id
        :return:
        """
        data = request.json
        items = data.pop('data', None)
        data.pop('bom_id', None)
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now()
              }

        for i in items:
            if not i.get('stage_id'):
                i['stage_id'] = None

        itemdata = [{**i, **cc} for i in items]
        error = ''
        success = False
        try:
            with db_client.session.begin():
                stmt = (
                    insert(BOM).values(**data, **cc).returning(BOM.bom_id)
                )
                result = db_client.session.execute(stmt)
                primary_key_id = result.scalar()
                print('wer', primary_key_id)
                if primary_key_id:
                    if itemdata:
                        itemdata = [{**i, **{"bom_id": primary_key_id}} for i in itemdata]
                        db_client.session.bulk_insert_mappings(mapper=BOMComponent, mappings=itemdata)
                success = True

        except SQLAlchemyError as e:
            error = str(e)
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


@bom_api_route.route('/<bom_id>/')
class EmployeeUpdateApi(Resource):
    @staticmethod
    def update_record(data, bom_id):
        data.pop('bom_id', None)
        items = data.pop('data', None)
        success = False
        error = ''
        with db_client.session.begin():
            try:
                stmt = (
                    update(BOM)
                    .where(BOM.bom_id == bom_id)
                    .values(**data)
                )
                db_client.session.execute(stmt)
                compcode = request.args.get('current_user', {})
                cc = {"compcode": compcode.get('company_id'),
                      "modified_on": datetime.datetime.now()
                      }
                updateitemData = []
                for i in range(len(items) - 1, -1, -1):
                    item = items[i]
                    if not item.get('stage_id'):
                        item['stage_id'] = None
                    if item.get('bom_component_id'):
                        items.pop(i)
                        dict_item = {
                            'bom_component_id': item.get('bom_component_id'),
                            'stage_id': item.get('stage_id'),
                            **cc
                        }
                        if 'quantity' in item and item.get('quantity') is not None:
                            dict_item['quantity'] = item.get('quantity')
                        if 'product_id' in item and item.get('product_id') is not None:
                            dict_item['product_id'] = item.get('product_id')
                        if 'notes' in item and item.get('notes') is not None:
                            dict_item['notes'] = item.get('notes')
                        if 'deleted' in item:
                            dict_item['deleted'] = str(item.get('deleted')).lower() == 'true'
                        updateitemData.append(dict_item)

                itemdata = [{**i, **{"bom_id": bom_id}, **cc} for i in items]
                if updateitemData:
                    db_client.session.bulk_update_mappings(mapper=BOMComponent, mappings=updateitemData)
                if itemdata:
                    db_client.session.bulk_insert_mappings(mapper=BOMComponent, mappings=itemdata)
                success = True
            except SQLAlchemyError as e:
                error = str(e)
                db_client.session.flush()

        return {
            'success': success,
            'message': "update successfully" if success else "error in updation",
            'error': error
        }

    @staticmethod
    def put_record(data, bom_id):
        data.pop('bom_id', None)
        product_data = {key: data[key] for key in ('product_id', 'uom', 'description') if key in data}
        items = data.pop('data', None)
        success = False
        error = ''

        try:
            with db_client.session.begin():
                compcode = request.args.get('current_user', {})
                cc = {
                    "compcode": compcode.get('company_id'),
                    "modified_on": datetime.datetime.now()
                }
                new_cc = {
                    "compcode": compcode.get('company_id'),
                    "created_on": datetime.datetime.now()
                }

                updateitemData = []
                itemdata = []
                current_ids = set()

                for item in items:
                    if not item.get('stage_id'):
                        item['stage_id'] = None
                    if item.get('bom_component_id'):
                        dict = {}
                        dict['bom_component_id'] = item.get('bom_component_id')
                        if item.get('quantity', None):
                            dict['quantity'] = item.get('quantity', None)
                        dict['stage_id'] = item.get('stage_id')
                        if item.get('product_id', None):
                            dict['product_id'] = item.get('product_id', None)
                        if item.get('notes', None):
                            dict['notes'] = item.get('notes', None)
                        updateitemData.append({**dict, **cc, 'deleted': False})
                    else:
                        itemdata.append({**item, **new_cc, "bom_id": bom_id, "deleted": False})
                    if item.get('bom_component_id'):
                        current_ids.add(item.get('bom_component_id'))
                existing_records = db_client.session.query(BOMComponent).filter(
                    BOMComponent.bom_id == bom_id,
                    BOMComponent.deleted != True
                ).all()

                existing_ids = {record.bom_component_id for record in existing_records}

                to_delete_ids = existing_ids - current_ids

                print(to_delete_ids)

                if product_data:
                    stmt = (
                        update(BOM)
                        .where(BOM.bom_id == bom_id)
                        .values(**product_data)
                    )
                    db_client.session.execute(stmt)

                if to_delete_ids:
                    db_client.session.query(BOMComponent).filter(
                        BOMComponent.bom_component_id.in_(to_delete_ids)
                    ).update({"deleted": True}, synchronize_session=False)

                if updateitemData:
                    db_client.session.bulk_update_mappings(mapper=BOMComponent, mappings=updateitemData)
                if itemdata:
                    db_client.session.bulk_insert_mappings(mapper=BOMComponent, mappings=itemdata)

                success = True

        except SQLAlchemyError as e:
            import traceback
            traceback.print_exc()
            error = f"Database error: {str(e)}"
            db_client.session.rollback()
            return map_sqlalchemy_error_to_http_status(e)
        except Exception as e:
            import traceback
            traceback.print_exc()
            error = f"General error: {str(e)}"
            db_client.session.rollback()
            return {
                'success': False,
                'message': "Error in update",
                'error': error
            }, 500

        return {
            'success': success,
            'message': "Update successful" if success else "Error in update",
            'error': error
        }
    @bom_api_route.marshal_with(bom_single_get_model)
    # @login_required(permissions='production_requirements.view')
    @login_required(permissions='bom.view')
    def get(self, bom_id):
        """
        Read user record / single record
        :param id:
        :return:
        """
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        sql_query = text('''
                select
                 b.bom_id,b.product_id as bom_product_id,
                p.product_name as bom_product_name,
                p.product_code as bom_product_code,
				json_agg(
				jsonb_build_object(
                    'bom_component_id', bc.bom_component_id,
                    'bom_id', bc.bom_id,
                    'product_id', bc.product_id,
                    'quantity', bc.quantity,
                    'uom', bc.uom,
                    'notes', bc.notes,
                    'stage_id', bc.stage_id,
                    'stage_name', s.stage_name,
                    'is_mark_data', bc.is_mark_data,
                    'compcode', bc.compcode
                )
				) as data
                from bom as b
                 left join bom_component as bc on b.bom_id = bc.bom_id
                 left join stage as s on s.stage_id = bc.stage_id
                left join products as p on p.product_id = b.product_id
                where b.deleted is not true and p.deleted is not true and bc.deleted is not true and b.compcode=:ccode and b.bom_id=:bom_id
				group by b.bom_id,bom_product_id,bom_product_name,bom_product_code
                ''')

        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           bom_id=bom_id,
                                                           ccode=ccode))


        return sql_query

    @bom_api_route.expect(bom_patch_model)
    @bom_api_route.marshal_with(update_bom_response)
    # @login_required(permissions='production_requirements.edit')
    @login_required(permissions='bom.edit')
    def put(self, bom_id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.put_record(data, bom_id)
        return response

    @bom_api_route.expect(bom_single_get_model)
    @bom_api_route.marshal_with(update_bom_response)
    # @login_required(permissions='production_requirements.edit')
    @login_required(permissions='bom.edit')
    def patch(self, bom_id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, bom_id)
        return response

    @bom_api_route.marshal_with(update_bom_response)
    # @login_required(permissions='production_requirements.delete')
    @login_required(permissions='bom.delete')
    def delete(self, bom_id):
        """
        Soft delete ProductionData record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=BOM,
            condition=BOM.bom_id == bom_id,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result


@bom_api_route.route('/pakage_id/<id>')
class ProductGetField(Resource):
    @login_required()
    @bom_api_route.marshal_with(product_service_list_response)
    def get(self, id):

        query1 = text('''
            with cte1 as (
            with cte as(
            select coalesce(pi.product_id,p.product_id) as product_id,sum(pi.needded_count) as count from products as p 
            left join package_items as pi on pi.pakage_id =p.product_id and pi.deleted is not true
            where p.product_id =:id
            group by coalesce(pi.product_id,p.product_id)
            )
            select cte.product_id,sum(cte.count),bc.product_id as finised_id,sum(bc.quantity::numeric) as quantity  from cte 
            left join bom as b on b.product_id = cte.product_id
            left join bom_component as bc on bc.bom_id = b.bom_id
            group by cte.product_id,bc.product_id
            )
            select cte1.finised_id as raw_id,p1.product_code,p1.sku_id,cte1.quantity,(cte1.quantity*mc.cost) as cost from cte1 
            left join material_cost as mc on mc.product_id = cte1.finised_id
            left join products as p1 on cte1.finised_id = p1.product_id
        ''')
        result = query_to_dict(db_client.engine.execute(query1, id=id))
        grant_cost = sum(i.get('cost', 0) or 0 for i in result)
        return {'grant_cost': grant_cost, "results": result}


@bom_api_route.route('/multiple_bom/<int:customer_purchase_id>')
class MultipleBom(Resource):

    @login_required()
    @bom_api_route.marshal_with(multiple_bom_get_model)
    # @bom_api_route.doc(params={'bom_ids': 'Comma separated BOM IDs to fetch BOMs'})
    def get(self, customer_purchase_id):

        # start_time = datetime.datetime.now()
        sql_query = text('''
WITH RECURSIVE latest_bom AS (
    SELECT bom_id, product_id
    FROM (
        SELECT b.bom_id, b.product_id, ROW_NUMBER() OVER(PARTITION BY b.product_id ORDER BY b.bom_id DESC) as rn
        FROM bom b
        LEFT JOIN products p ON p.product_id = b.product_id
        WHERE b.deleted IS NOT TRUE AND p.deleted IS NOT TRUE
    ) sub
    WHERE rn = 1
),
cte AS (
    SELECT 
        cpi.items_id,
        cpi.product_id,
        b.bom_id,
        cil.id AS lot_id,
        COALESCE(cil.lot_number, 'All Lots') AS lot_number,
        COALESCE(cil.lot_qty, cpi.quantity_ordered) AS quantity_ordered
    FROM customer_purchase cp
    JOIN customer_purchase_items cpi 
           ON cpi.customer_purchase_id = cp.customer_purchase_id 
          AND cpi.deleted IS NOT TRUE
    LEFT JOIN latest_bom b 
           ON b.product_id = cpi.product_id 
    LEFT JOIN cpo_item_lots cil 
           ON cil.cpo_item_id = cpi.items_id 
          AND cil.deleted IS NOT TRUE
    WHERE cp.customer_purchase_id = :customer_purchase_id
),
bom_tree AS (
    -- Anchor
    SELECT 
        b.bom_id,
        cte.items_id,
        cte.lot_id,
        cte.lot_number,
        cte.quantity_ordered AS lot_qty,
        b.product_id AS parent_product_id,
        bc.product_id AS child_product_id,
        bc.quantity::numeric AS component_quantity,
        (cte.quantity_ordered * bc.quantity::numeric) AS effective_quantity,
        1 AS level,
        ARRAY[b.product_id, bc.product_id] AS path
    FROM cte
    JOIN latest_bom b ON b.bom_id = cte.bom_id
    JOIN bom_component bc ON b.bom_id = bc.bom_id
    WHERE bc.deleted IS NOT TRUE

    UNION ALL

    -- Recursive
    SELECT 
        b.bom_id,
        bt.items_id,
        bt.lot_id,
        bt.lot_number,
        bt.lot_qty,
        b.product_id AS parent_product_id,
        bc.product_id AS child_product_id,
        bc.quantity::numeric AS component_quantity,
        (bt.effective_quantity * bc.quantity::numeric) AS effective_quantity,
        bt.level + 1,
        bt.path || bc.product_id
    FROM bom_tree bt
    JOIN latest_bom b ON bt.child_product_id = b.product_id
    JOIN bom_component bc ON b.bom_id = bc.bom_id
    WHERE NOT bc.product_id = ANY(bt.path)
      AND bc.deleted IS NOT TRUE
),
already_procured AS (
    SELECT 
        jli.rawmaterialsid AS product_id,
        SUM(jli.quandity) AS total_procured_quantity
    FROM joborder j
    JOIN joline_items jli 
        ON jli.jo_id = j.joborderid
    WHERE j.deleted IS NOT TRUE
      AND jli.deleted IS NOT TRUE
      AND j.jo_status NOT IN ('Cancelled', 'Rejected')
      AND j.customer_purchase_id = :customer_purchase_id
      AND jli.deleted IS NOT TRUE
    GROUP BY jli.rawmaterialsid
),
lot_procured AS (
    SELECT 
        jli.rawmaterialsid AS product_id,
        jli.lot_no,
        SUM(jli.quandity) AS lot_procured_qty
    FROM joborder j
    JOIN joline_items jli 
        ON jli.jo_id = j.joborderid
    WHERE j.jo_status <> 'Cancelled'
      AND j.customer_purchase_id = :customer_purchase_id
      AND jli.deleted IS NOT TRUE
    GROUP BY jli.rawmaterialsid, jli.lot_no
),
raw_material_lot_breakdown AS (
    SELECT 
        bt.child_product_id as product_id,
        p.product_name, p.product_code, p.product_group_id, p.sku_id, p.product_count, p.allocated_quantity, u.uom,
        bt.lot_id,
        bt.lot_number,
        bt.lot_qty,
        SUM(bt.effective_quantity) AS lot_required_qty,
        COALESCE(ap.total_procured_quantity, 0) AS already_procured_quantity,
        'CONFIGURED' AS bom_status
    FROM bom_tree as bt
    JOIN products as p on p.product_id = bt.child_product_id AND p.deleted IS NOT TRUE
    JOIN uom as u on u.id = p.uom_id
    LEFT JOIN already_procured ap ON ap.product_id = bt.child_product_id
    GROUP BY bt.child_product_id, p.product_name, p.product_code, p.product_group_id, p.sku_id,
             p.product_count, p.allocated_quantity, u.uom, ap.total_procured_quantity, bt.lot_id, bt.lot_number, bt.lot_qty
    
    UNION ALL
    
    SELECT 
        p.product_id, p.product_name, p.product_code, p.product_group_id, p.sku_id, p.product_count, p.allocated_quantity, u.uom,
        cte.lot_id, cte.lot_number, cte.quantity_ordered AS lot_qty,
        NULL::numeric AS lot_required_qty,
        COALESCE(ap.total_procured_quantity, 0) AS already_procured_quantity,
        'NOT CONFIGURED' AS bom_status
    FROM cte
    JOIN products as p on p.product_id = cte.product_id and cte.bom_id is null AND p.deleted IS NOT TRUE
    JOIN uom as u on u.id = p.uom_id
    LEFT JOIN already_procured ap ON ap.product_id = p.product_id
)
SELECT * FROM raw_material_lot_breakdown
ORDER BY product_id, lot_number
                        ''')

        raw_rows = query_to_dict(db_client.engine.execute(sql_query, customer_purchase_id=customer_purchase_id))

        # Query existing lot-wise procured quantities for this CPO
        lot_procured_query = text('''
            SELECT 
                jli.rawmaterialsid AS product_id,
                jli.lot_no,
                SUM(jli.quandity) AS procured_qty
            FROM joborder j
            JOIN joline_items jli ON jli.jo_id = j.joborderid
            WHERE j.jo_status <> 'Cancelled'
              AND j.customer_purchase_id = :customer_purchase_id
              AND jli.deleted IS NOT TRUE
            GROUP BY jli.rawmaterialsid, jli.lot_no
        ''')
        lot_proc_rows = query_to_dict(db_client.engine.execute(lot_procured_query, customer_purchase_id=customer_purchase_id))

        # Consolidate into 1 row per Raw Material product_id, aggregating lot_options
        materials_map = {}
        for row in raw_rows:
            pid = row['product_id']
            if pid not in materials_map:
                materials_map[pid] = {
                    'product_id': row['product_id'],
                    'product_name': row['product_name'],
                    'product_code': row['product_code'],
                    'product_count': row['product_count'],
                    'product_group_id': row['product_group_id'],
                    'sku_id': row['sku_id'],
                    'uom': row['uom'],
                    'allocated_quantity': row['allocated_quantity'],
                    'total_required_quantity': 0,
                    'already_procured_quantity': row['already_procured_quantity'],
                    'bom_status': row['bom_status'],
                    'lot_options': []
                }
            
            req_qty = float(row['lot_required_qty'] or 0)
            materials_map[pid]['total_required_quantity'] += req_qty
            
            # Check how much has been procured for this specific lot
            lot_name = row['lot_number']
            lot_procured_qty = 0.0
            for lp in lot_proc_rows:
                if lp['product_id'] == pid and lp['lot_no']:
                    proc_lots = [s.strip().upper() for s in lp['lot_no'].split(',') if s.strip()]
                    if lot_name and lot_name.strip().upper() in proc_lots:
                        # Avoid double-counting when multiple lots share the line item quantity
                        split_factor = len(proc_lots) if len(proc_lots) > 0 else 1
                        lot_procured_qty += float(lp['procured_qty'] or 0) / split_factor

            is_fully_procured = (req_qty > 0 and lot_procured_qty >= req_qty)

            materials_map[pid]['lot_options'].append({
                'lot_id': row['lot_id'],
                'lot_number': lot_name,
                'lot_qty': float(row['lot_qty'] or 0),
                'required_quantity': req_qty,
                'procured_quantity': lot_procured_qty,
                'is_procured': is_fully_procured
            })

        # Format total_required_quantity and add 'All Lots' option if multiple lots exist
        final_results = []
        for pid, mat in materials_map.items():
            tot_req = mat['total_required_quantity']
            mat['total_required_quantity'] = str(round(tot_req, 4))
            
            lots = mat['lot_options']
            has_specific_lots = any(l['lot_id'] is not None for l in lots)
            if has_specific_lots:
                all_lots_opt = {
                    'lot_id': None,
                    'lot_number': 'All Lots',
                    'lot_qty': sum(l['lot_qty'] for l in lots),
                    'required_quantity': tot_req,
                    'procured_quantity': sum(l['procured_quantity'] for l in lots),
                    'is_procured': all(l['is_procured'] for l in lots)
                }
                mat['lot_options'] = [all_lots_opt] + lots

            final_results.append(mat)

        return {'results': final_results}



######################################################################
