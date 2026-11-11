from flask import request
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text
from .. import db_client
from ..routes.rm_purchase import orderReportsAPIRoutes
from ipss_utils.ipss_api_doc import list_api_params

@orderReportsAPIRoutes.route('/order-lifecycle-report')
class OrderLifecycleReport(Resource):

    @login_required()
    @orderReportsAPIRoutes.doc(params={
        **list_api_params,
        "start_date": {"type": str, "description": "Filter by order start date (YYYY-MM-DD)"},
        "end_date": {"type": str, "description": "Filter by order end date (YYYY-MM-DD)"},
        "order_unique": {"type": str, "description": "Filter by unique order number"}
    })
    def get(self):
        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')

        # Pagination
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get('results_per_page') else 20
        offset = (paged - 1) * results_per_page

        # Filters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        order_unique = request.args.get('order_unique')

        sql_con = ""
        params = {
            "compcode": compcode,
            "limit": results_per_page,
            "offset": offset
        }

        if start_date:
            sql_con += " AND CAST(cp.order_date AS date) >= CAST(:start_date AS date) "
            params["start_date"] = start_date
        if end_date:
            sql_con += " AND CAST(cp.order_date AS date) <= CAST(:end_date AS date) "
            params["end_date"] = end_date
        if order_unique:
            sql_con += " AND cp.order_unique = :order_unique "
            params["order_unique"] = order_unique

        query_str = f"""
        SELECT 
            cp.customer_purchase_id,
            cp.order_unique AS order_number,
            cp.order_type,
            cp.status AS order_status,
            cp.order_date::text AS order_date,
            cp.expected_receiving_date::text AS expected_receiving_date,
            cpi.items_id AS order_item_id,
            cpi.quantity_ordered,
            cpi.quantity_delivered,
            cpi.status AS item_status,
            p_fg.product_name AS finished_good_name,
            p_fg.product_code AS finished_good_code,

            pp.production_plan_id,
            pp.plan_unique AS plan_number,
            pp.planed_quantity AS planned_quantity,
            pp.status AS plan_status,
            pp.created_on::text AS plan_created_date,
            pp.moved_quantity AS fg_moved_quantity,

            COALESCE(
                (SELECT json_agg(json_build_object(
                    'ref_id', ir.ref_id,
                    'material_name', p_rm.product_name,
                    'material_code', p_rm.product_code,
                    'requested_qty', ir.requested_amount,
                    'approved_qty', ir.approved_amount,
                    'request_status', ir.status,
                    'requested_on', ir.created_on::text,
                    'issued_on', ir.issued_date::text
                ))
                 FROM invregistry ir
                 JOIN products p_rm ON p_rm.product_id = ir.product_id
                 WHERE ir.prod_plan_id = pp.production_plan_id 
                   AND ir.action = 'Outward' 
                   AND ir.ref_id LIKE 'REQ-%' 
                   AND ir.deleted IS NOT TRUE
                ), '[]'::json
            ) AS material_requests,

            COALESCE(
                (SELECT json_agg(json_build_object(
                    'stage_id', pe.stage_id,
                    'stage_name', s.stage_name,
                    'inward_qty', pe.inward_qty,
                    'outward_qty', pe.outward_qty,
                    'wastage', pe.wastage,
                    'status', pe.status
                 ))
                 FROM prod_execution pe
                 JOIN production_stages ps ON ps.id = pe.stage_id
                 JOIN stage s ON s.stage_id = ps.stage_id
                 WHERE pe.prod_plan_id = pp.production_plan_id 
                   AND pe.deleted IS NOT TRUE
                ), '[]'::json
            ) AS execution_stages,

            COALESCE(
                (SELECT json_agg(json_build_object(
                    'dc_number', d.deliveryno,
                    'delivery_qty', dli.quantity,
                    'dc_status', d.status,
                    'dispatched_on', d.created_on::text
                 ))
                 FROM delivery_line_items dli
                 JOIN delivery d ON d.deliveryid = dli.deliveryid
                 WHERE dli."workOrderLineId" = cpi.items_id 
                   AND d.deleted IS NOT TRUE
                ), '[]'::json
            ) AS deliveries

        FROM customer_purchase cp
        JOIN customer_purchase_items cpi ON cpi.customer_purchase_id = cp.customer_purchase_id
        JOIN products p_fg ON p_fg.product_id = cpi.product_id
        LEFT JOIN order_items_extract oie ON oie.order_items_id = cpi.items_id
        LEFT JOIN plan_details pd ON pd.order_extract_id = oie.extract_id
        LEFT JOIN production_plan pp ON pp.production_plan_id = pd.production_plan_id AND pp.deleted IS NOT TRUE
        WHERE cp.compcode = :compcode AND cp.deleted IS NOT TRUE {sql_con}
        ORDER BY cp.created_on DESC
        LIMIT :limit OFFSET :offset
        """

        count_str = f"""
        SELECT COUNT(*) 
        FROM customer_purchase cp
        JOIN customer_purchase_items cpi ON cpi.customer_purchase_id = cp.customer_purchase_id
        LEFT JOIN order_items_extract oie ON oie.order_items_id = cpi.items_id
        LEFT JOIN plan_details pd ON pd.order_extract_id = oie.extract_id
        LEFT JOIN production_plan pp ON pp.production_plan_id = pd.production_plan_id AND pp.deleted IS NOT TRUE
        WHERE cp.compcode = :compcode AND cp.deleted IS NOT TRUE {sql_con}
        """

        results = query_to_dict(db_client.engine.execute(text(query_str), **params))
        total_count = query_to_dict(db_client.engine.execute(text(count_str), **params))
        total = total_count[0].get('count', 0) if len(total_count) else 0

        return {
            "total_results": total,
            "page": paged,
            "results_per_page": results_per_page,
            "results": results
        }
