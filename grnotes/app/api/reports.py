from flask import request
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text
from ..routes.grnotes import joborder_model_list_response
from ..routes.grnotes import grnotes_api_route
from .. import db_client
from ..api_doc import report_filter
@grnotes_api_route.route('/PoReports')
class PoReports(Resource):
    @login_required()
    @grnotes_api_route.marshal_with(joborder_model_list_response)
    @grnotes_api_route.doc(params=report_filter)
    def get(self):
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        current_user = request.args.get('current_user',{})
        # print("current_user",current_user)
        ccode = current_user.get('company_id')
        sql_con=''
        if request.args.get('product_id'):
            sql_con+=' and p.product_id=:product_id '
        if request.args.get('joborderid'):
            sql_con+=' and j.joborderid=:joborderid '
        if request.args.get('grnotesid'):
            sql_con+=' and gn.grnotesid=:grnotesid '
        # if request.args.get('product_id'):
        #     sql_con+=' and p.product_id=:product_id '
        sql_query=text(f'''
        SELECT 
          j.joborderid,
          j.joborderno,
          v.vendorid,
          v.companyname,
          j.jo_date,
          j.is_done,
          j.jo_status,
          j.ordercompletiondate,
          json_agg(
            json_build_object(
              'product_code', p.product_code,
              'product_name', p.product_name,
              'sku_id', p.sku_id,
              'received_quantity', g.received_quantity,
              'damaged_quantity', g.damaged_quantity,
              'non_damaged_quantity', g.non_damaged_quantity,
              'grn_no', gn.grn_no
            )
          ) AS products,
          COUNT(*) OVER() AS total_count
        FROM joborder j
        JOIN vendor v ON v.vendorid = j.vendorid
        JOIN joline_items ji ON ji.jo_id  = j.joborderid
        JOIN grnlineitems g ON g.purchase_items_id = ji.id
        JOIN grnotes gn ON gn.grnotesid = g.grnotesid
        JOIN products p ON p.product_id = g.product_id
        where 1=1 
        and j.deleted is not true and ji.deleted is not true and g.deleted is not true 
        and gn.deleted is not true and j.compcode=:ccode {sql_con}
        GROUP BY 
          j.joborderid, j.joborderno, v.vendorid, v.companyname, 
          j.jo_date, j.is_done, j.jo_status, j.ordercompletiondate
        order by joborderid desc
        limit :limit offset :offset
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,
                                                         grnotesid=request.args.get('grnotesid'),
                                                         joborderid=request.args.get('joborderid'),
                                                         product_id=request.args.get('product_id'),
                                                         ccode=ccode,
                                                         limit=results_per_page,
                                                         offset=offset))
        return {

            # 'primary_key': primary_key,
            'total_results':sql_query[0].get('total_count') if len(sql_query) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'data': sql_query
        }
from ..routes.grnotes import response_model_grn
from ..api_doc import grn_report

@grnotes_api_route.route('/GRN-Reports')
class grnReports(Resource):
    @grnotes_api_route.marshal_with(response_model_grn)
    @grnotes_api_route.doc(params={**list_api_params,**grn_report})
    @login_required()
    def get(self):
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        current_user = request.args.get('current_user', {})
        # print("current_user",current_user)
        ccode = current_user.get('company_id')
        sql_con = ''
        end_date=request.args.get('startdate') if not request.args.get('enddate') else request.args.get('enddate')
        if request.args.get('product_id'):
            sql_con+=' and gln.product_id=:product_id '
        if request.args.get('grnotesid'):
            sql_con+=' and g.grnotesid=:grnotesid '
        if request.args.get('vendorid'):
            sql_con+=' and g.vendorid=:vendorid '
        if request.args.get('startdate'):
            sql_con+=' and g.grndate::date>=:startdate '
        if end_date:
            sql_con+=' and g.grndate::date<=:end_date '
        if request.args.get('status'):
            sql_con+=' and g.status=:status '
        sql_query=text(f'''
        with cte as(
		select g.grnotesid,g.type,g.grndate,g.inviceno,g.grn_no,g.total_item,g.total_price,
                    v.companyname,v.emailid,v.mobileno,
                    COALESCE(string_agg(DISTINCT j.joborderno, ', ') FILTER (WHERE j.joborderno IS NOT NULL AND j.joborderno != ''), 'N/A') as joborderno,
                    g.is_qc_done,g.deliverychallan_no,
                    det.items
                     from grnotes g 
                     join grnlineitems as gln on gln.grnotesid=g.grnotesid
                     left join joline_items as jli on gln.purchase_items_id = jli.id
                    left join joborder as j on j.joborderid=jli.jo_id
                     join vendor as v on v.vendorid=g.vendorid
                    join (
					select 
					gln.grnotesid,
        jsonb_agg(
            jsonb_build_object(
                'product_id', gln.product_id,
                'product_name', p.product_name,
                'product_code', p.product_code,
                'sku_id', p.sku_id,
                'quandity', jli.quandity,
                'received_quantity', gln.received_quantity,
                'damaged_quantity', gln.damaged_quantity,
                'total_price', gln.total_price,
                'quantity_delivered', jli.quantity_delivered,
                'uom', uom.uom,
                'joborderno', j.joborderno,
				'gst', gln.gst,
				'rate_per_item', gln.rate_per_item
            )
        ) AS items
    FROM grnlineitems gln
    LEFT JOIN products p ON gln.product_id = p.product_id
    LEFT JOIN uom ON uom.id = p.uom_id
    LEFT JOIN joline_items jli ON gln.purchase_items_id = jli.id
    LEFT JOIN joborder j ON j.joborderid = jli.jo_id
    WHERE gln.deleted IS NOT TRUE and gln.compcode =:compcode
    GROUP BY gln.grnotesid
					) as det on det.grnotesid=g.grnotesid
                    where g.deleted is not true 
					and g.compcode=:compcode {sql_con}
                    GROUP BY g.grnotesid, g.type, g.grndate, g.inviceno, g.grn_no, g.total_item, g.total_price,
                             v.companyname, v.emailid, v.mobileno, g.is_qc_done, g.deliverychallan_no, det.items
					)
					select *,
					 count(*) over() as total_count
					 from cte
					order by grnotesid desc
                    limit :limit offset :offset
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,
                                                         compcode=ccode,
                                                         status=request.args.get('status'),
                                                         product_id=request.args.get('product_id'),
                                                         grnotesid=request.args.get('grnotesid'),
                                                         vendorid=request.args.get('vendorid'),
                                                         startdate=request.args.get('startdate'),
                                                         end_date=end_date,
                                                         offset=offset,
                                                         limit=results_per_page))
        return {

            # 'primary_key': primary_key,
            'total_results': sql_query[0].get('total_count') if len(sql_query) else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'data': sql_query
        }