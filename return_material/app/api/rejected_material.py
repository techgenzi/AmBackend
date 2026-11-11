import datetime

from flask import request
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .. import db_client
from ..models.rejected_material import RejectedMaterial
from ..routes.rejected_material import (
    return_api_route,
    rejected_list_model,
    rejected_item_model,
    rejected_patch_model,
    rejected_patch_response,
)
from .errorhandling import map_sqlalchemy_error_to_http_status


# ── GET /am-returnMaterial/rejected/ ─────────────────────────────────────────

@return_api_route.route('/rejected/')
class RejectedMaterialList(Resource):

    @return_api_route.marshal_with(rejected_list_model)
    @login_required()
    def get(self):
        """
        List rejected raw materials (from QC) with optional filters.
        Query params: status, action, product_id, grnotesid, unique_id
        """
        cur        = request.args.get('current_user', {})
        compcode   = cur.get('company_id')
        paged      = int(request.args.get('paged', 1))
        rpp        = int(request.args.get('results_per_page', 20))
        offset     = (paged - 1) * rpp

        status     = request.args.get('status', None)
        action     = request.args.get('action', None)
        product_id = request.args.get('product_id', None)
        grnotesid  = request.args.get('grnotesid', None)
        unique_id  = request.args.get('unique_id', None)

        sql_con = ''
        if status:
            sql_con += ' and rm.status=:status '
        if action:
            sql_con += ' and rm.action=:action '
        if product_id:
            sql_con += ' and rm.product_id=:product_id '
        if grnotesid:
            sql_con += ' and rm.grnotesid=:grnotesid '
        if unique_id:
            sql_con += ' and rm.unique_id=:unique_id '

        query = text(f'''
            select
                rm.rejected_material_id,
                rm.unique_id,
                rm.grnotesid,
                rm.grnlineid,
                rm.product_id,
                rm.rejected_quantity,
                rm.rejection_reason,
                rm.rejection_remark,
                rm.image_attachment,
                rm.action,
                rm.store_id,
                rm.status,
                rm.action_date,
                rm.created_on,
                rm.created_by,
                p.sku_id,
                p.product_code,
                p.product_name,
                u.uom,
                sl.store_name,
                grn.grn_no,
                count(*) over() as total_results
            from rejected_material as rm
            left join products as p   on p.product_id = rm.product_id
            left join uom as u        on u.id = p.uom_id
            left join store_location as sl on sl.store_id = rm.store_id
            left join grnotes as grn  on grn.grnotesid = rm.grnotesid
            where rm.deleted is not true and rm.compcode=:compcode
            {sql_con}
            order by rm.rejected_material_id desc
            limit :limit offset :offset
        ''')

        result = query_to_dict(db_client.engine.execute(
            query,
            compcode=compcode,
            status=status,
            action=action,
            product_id=product_id,
            grnotesid=grnotesid,
            unique_id=unique_id,
            limit=rpp,
            offset=offset,
        ))

        return {
            'total_results': result[0].get('total_results', 0) if result else 0,
            'page': paged,
            'results_per_page': rpp,
            'results': result,
        }


# ── PATCH /am-returnMaterial/rejected/<id>/ ──────────────────────────────────

@return_api_route.route('/rejected/<int:rejected_material_id>/')
class RejectedMaterialDetail(Resource):

    @return_api_route.marshal_with(rejected_item_model)
    @login_required()
    def get(self, rejected_material_id):
        """Single rejected material record with product + store details."""
        compcode = request.args.get('current_user', {}).get('company_id')
        query = text('''
            select
                rm.*,
                p.sku_id, p.product_code, p.product_name,
                u.uom,
                sl.store_name,
                grn.grn_no
            from rejected_material as rm
            left join products as p   on p.product_id = rm.product_id
            left join uom as u        on u.id = p.uom_id
            left join store_location as sl on sl.store_id = rm.store_id
            left join grnotes as grn  on grn.grnotesid = rm.grnotesid
            where rm.rejected_material_id=:id and rm.compcode=:compcode
              and rm.deleted is not true
        ''')
        result = query_to_dict(db_client.engine.execute(
            query, id=rejected_material_id, compcode=compcode
        ))
        return result[0] if result else {}

    @return_api_route.expect(rejected_patch_model)
    @return_api_route.marshal_with(rejected_patch_response)
    @login_required()
    def patch(self, rejected_material_id):
        """
        Mark a rejected material record as Completed.
        For Re-inspect: also re-adds quantity to stock via stock-managing endpoint.
        The frontend calls stock-managing separately for Re-inspect.
        """
        cur      = request.args.get('current_user', {})
        compcode = cur.get('company_id')
        username = cur.get('username')
        data     = request.json

        s = db_client.session
        try:
            with s.begin():
                update_q = text('''
                    update rejected_material
                    set status      = :status,
                        action_date = :action_date,
                        modified_by = :modified_by,
                        modified_on = :modified_on
                    where rejected_material_id = :id
                      and compcode = :compcode
                ''')
                s.execute(update_q, {
                    'status':      data.get('status', 'Completed'),
                    'action_date': datetime.datetime.now(),
                    'modified_by': username,
                    'modified_on': datetime.datetime.now(),
                    'id':          rejected_material_id,
                    'compcode':    compcode,
                })
        except SQLAlchemyError as e:
            return map_sqlalchemy_error_to_http_status(e)

        return {'success': True, 'message': 'Updated successfully', 'error': ''}
