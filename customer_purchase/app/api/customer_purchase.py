import datetime
import time
from logging import error

from flask import request
from flask_restx import Resource
from ipss_utils.ipss_api_doc import list_api_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import update, text, func, and_
from sqlalchemy.exc import SQLAlchemyError
from .helper import data_extract_from_package, order_extract
from ..api_doc import data_filters, serach_filters
from ..model.customer_purchase import CustomerOrder, CustomerOrderItems, CPOItemLots
from ..routes.customer_purchae import customerPurchaseRoute, aggricatedModel, orderModelResponse, ItemModelResponse, \
    plan_cost_response_model, planed_qty_response_model
from .helper import get_labour_cost, get_material_cost, get_estimated_labour_cost, get_estimated_material_cost, get_estimated_labour_cost_bulk, get_estimated_material_cost_bulk, get_material_cost_bulk, get_labour_cost_bulk
from ipss_utils.decorators import login_required
from .. import ipss_db, db_client
from .errorhandling import map_sqlalchemy_error_to_http_status
primary_key='customer_purchase_id'
@customerPurchaseRoute.route('/customerOrderItems/')
class CustomerPurchaseData(Resource):
    @customerPurchaseRoute.marshal_with(ItemModelResponse)
    @customerPurchaseRoute.doc(params={**list_api_params,**serach_filters})
    @login_required(permissions='customerpurchase.list')
    def get(self):
        primary_key='items_id'
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        compcode = request.args.get('current_user').get('company_id', None)
        sql_condition = ""
        limit_con = " limit :limit offset :offset "
        if request.args.get('customer_purchase_id', None):
            sql_condition+=' and cpi.customer_purchase_id=:customer_purchase_id '
            limit_con = ""
        if request.args.get('order_type', None):
            sql_condition += ' and cpi.order_type=:order_type '
        if request.args.get('items_id', None):
            sql_condition += ' and cpi.items_id=:items_id '
        if request.args.get('product_id', None):
            sql_condition += ' and cpi.product_id=:product_id '
        sql_query=text(f'''
        with target_items as (
            select cpi.*
            from customer_purchase_items cpi
            where cpi.compcode = :ccode and cpi.deleted is not true {sql_condition}
            order by cpi.items_id desc
            {limit_con}
        ),
        target_produced as (
            select oie.order_items_id,
                   round(sum(case when asm.is_final_process is true or asm.activity_stage_map_id is null then el.outward_qty else 0 end), 2) as produced_qty
            from target_items ti
            join order_items_extract oie on oie.order_items_id = ti.items_id and oie.deleted is not true
            join plan_details pd on pd.order_extract_id = oie.extract_id and pd.deleted is not true
            join production_plan pp on pp.production_plan_id = pd.production_plan_id and pp.deleted is not true and (pp.compcode = :ccode or pp.compcode is null)
            join (
                select product_id, max(rank_id) as max_rank_id
                from production_stages
                where deleted is not true and (compcode = :ccode or compcode is null)
                group by product_id
            ) ps_max on ps_max.product_id = pp.product_id
            left join production_stages ps on ps.product_id = pp.product_id and ps.rank_id = ps_max.max_rank_id and ps.deleted is not true and (ps.compcode = :ccode or ps.compcode is null)
            left join stage s on s.stage_id = ps.stage_id and (s.compcode = :ccode or s.compcode is null)
            left join plan_targets pt on pt.production_plan_id = pp.production_plan_id and pt.deleted is not true and (pt.compcode = :ccode or pt.compcode is null)
            left join execution_log el on el.target_id = pt.plan_target_id and el.stage_id = s.stage_id and el.deleted is not true and (el.compcode = :ccode or el.compcode is null)
            left join activity_stage_map asm on asm.production_stage_id = ps.id and asm.config_id = el.process_id and asm.deleted is not true and (asm.compcode = :ccode or asm.compcode is null)
            group by oie.order_items_id
        )
        select ti.*,
         COALESCE(tp.produced_qty, ti.quantity_produced, 0) as quantity_produced,
         p.product_code,p.product_name,p.sku_id,p.product_count,u.uom,
         ss.store_stocks,
         COALESCE(p.is_serializable, FALSE) AS is_serialized,
         lots.lot_breakdown,
         COALESCE(lots.single_lot_number, ti.target_production_lot_no) as lot_no
        from target_items ti
        left join target_produced tp on tp.order_items_id = ti.items_id
        join products p on p.product_id = ti.product_id
        left join uom as u on p.uom_id = u.id
        left join (
            select cil.cpo_item_id,
                   json_agg(json_build_object('id', cil.id, 'lot_number', cil.lot_number, 'lot_qty', cil.lot_qty)) as lot_breakdown,
                   case when count(cil.id) = 1 then max(cil.lot_number) else concat(count(cil.id), ' Lots') end as single_lot_number
            from cpo_item_lots cil
            where cil.deleted is not true and (cast(cil.compcode as varchar) = cast(:ccode as varchar) or cil.compcode is null)
            group by cil.cpo_item_id
        ) lots on lots.cpo_item_id = ti.items_id
        left join (
            select sp.product_id, json_agg(json_build_object('store_id', sp.store_id, 'store_name', s.store_name, 'product_count', sp.product_count, 'lot_no', sp.lot_no)) as store_stocks
            from store_product sp
            join store_location s on s.store_id = sp.store_id
            where sp.deleted is not true and s.deleted is not true 
              and (sp.compcode = :ccode or sp.compcode is null) and (s.compcode = :ccode or s.compcode is null) 
              and sp.product_count > 0
            group by sp.product_id
        ) ss on ss.product_id = ti.product_id
        order by ti.items_id desc
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,
                                                         ccode=compcode,
                                                         customer_purchase_id=request.args.get('customer_purchase_id'),
                                                         order_type=request.args.get('order_type'),
                                                         items_id=request.args.get('items_id'),
                                                         product_id=request.args.get('product_id'),
                                                         limit=results_per_page,
                                                         offset=offset
                                                         ))
        sql_count=text(f'''
        select count(items_id)
        from customer_purchase_items cpi 
        where cpi.compcode=:ccode and cpi.deleted is not true {sql_condition}
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,
                                                         ccode=compcode,
                                                         customer_purchase_id=request.args.get('customer_purchase_id'),
                                                         order_type=request.args.get('order_type'),
                                                         items_id=request.args.get('items_id'),
                                                         product_id=request.args.get('product_id')
                                                         ))
        return {
            'primary_key': primary_key,
            'total_results': sql_count[0].get('count',0) if sql_count else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }

        # response = ipss_db.paginated_results(
        #     model=CustomerOrderItems,
        #     query=query,
        #     primary_key=primary_key
        # )
        # return response
@customerPurchaseRoute.route('/')
class CustomerPurchase(Resource):
    @customerPurchaseRoute.marshal_with(orderModelResponse)
    @customerPurchaseRoute.doc(params={**data_filters,**list_api_params})
    @login_required(permissions='customerpurchase.list')
    def get(self):
        query = CustomerOrder.query.order_by(CustomerOrder.customer_purchase_id.desc())
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        ccode = request.args.get('current_user', {}).get('company_id', None)
        sql_con=''
        # Filtering by parent id (Primary Table ID)
        if request.args.get('customer_purchase_id', None):
            sql_con += 'and cp.customer_purchase_id=:customer_purchase_id '
        if request.args.get('order_date', None):
            sql_con += 'and cp.order_date=:order_date '
        if request.args.get('expected_receiving_date', None):
            sql_con += 'and cp.expected_receiving_date=:expected_receiving_date '
        if request.args.get('customer_id', None):
            sql_con += 'and cp.customer_id=:customer_id '
        if request.args.get('status', None):
            sql_con += 'and cp.status=:status '
        if request.args.get('order_type', None):
            sql_con += 'and cp.order_type=:order_type '
        sql_query=text(f'''
        select distinct on (cp.customer_purchase_id) cp.*,
        COUNT(cpi.*) FILTER (WHERE cpi.deleted is not true AND cp.compcode =:ccode) AS total_items,
        jsonb_build_object('companyname',v.companyname,
        'mobileno',v.mobileno,
        'emailid',v.emailid
        ) as customer_details
        from customer_purchase as cp 
                join customer_purchase_items cpi on cpi.customer_purchase_id=cp.customer_purchase_id
                left join vendor v on v.vendorid =cp.customer_id 
                and cpi.deleted is not true 
                where cp.deleted is not true 
                and cp.compcode =:ccode {sql_con}
                group by cp.customer_purchase_id,v.companyname,v.mobileno,v.emailid 
                order by cp.customer_purchase_id desc
        limit :limit offset :offset
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,
                                                         customer_purchase_id=request.args.get('customer_purchase_id'),
                                                         order_date=request.args.get('order_date'),
                                                         expected_receiving_date=request.args.get('expected_receiving_date'),
                                                         customer_id=request.args.get('customer_id'),
                                                         status=request.args.get('status'),
                                                         order_type=request.args.get('order_type'),
                                                         ccode=ccode,
                                                         limit=results_per_page,
                                                         offset=offset
                                                         ))
        sql_count=text(f''' select count(*)
        from customer_purchase as cp 
        left join customer_purchase_items cpi on cpi.customer_purchase_id=cp.customer_purchase_id
        and cpi.deleted is not true 
        where cp.deleted is not true and cp.compcode =:ccode {sql_con}
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,
                                                         ccode=ccode,
                                                         customer_purchase_id=request.args.get('customer_purchase_id'),
                                                         order_date=request.args.get('order_date'),
                                                         expected_receiving_date=request.args.get(
                                                             'expected_receiving_date'),
                                                         customer_id=request.args.get('customer_id'),
                                                         status=request.args.get('status'),
                                                         order_type=request.args.get('order_type')
                                                         ))
        return {
            'total_results': sql_count[0].get('count') if sql_count else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': sql_query
        }

        # response = ipss_db.paginated_results(
        #     model=CustomerOrder,
        #     query=query,
        #     primary_key=primary_key
        # )
        # return response
    @customerPurchaseRoute.expect(aggricatedModel)
    @login_required(permissions='customerpurchase.add')
    def post(self):
        data=request.json

        lineItems=data.pop('lineItems',[])
        pKey=data.get('customer_purchase_id',None)
        compcode = request.args.get('current_user', {})
        cc = {"compcode": compcode.get('company_id'),
              "created_on": datetime.datetime.now(),
              }


        error=''
        # with db_client.session.begin():

        try:
            if not data.get('customer_purchase_id'):
                from .helper import insert_record
                print("sfewf",data)
                total_count = db_client.session.query(func.count(CustomerOrder.customer_purchase_id)) \
                                  .filter(and_(CustomerOrder.order_type == data.get('order_type'),
                                               CustomerOrder.compcode == compcode.get('company_id'))) \
                                  .scalar() + 1
                # db_client.session.close()
                if data.get('order_type') == 'Internal':
                    data['order_unique'] = 'IO-' + str(total_count).zfill(6)
                else:
                    data['order_unique'] = 'CO-' + str(total_count).zfill(6)
                # data=ipss_db.generate_doc_id(tx_name=data.get('order_type'),)
                result=insert_record(model=CustomerOrder,values=data,commit=False)
                #print("freerf", result)
                success=result[0] if isinstance(result, tuple) else result
                if not success.get('success'):
                    return result
                pKey=result.get('primary_key_id',None)[0]
            else:
                stmt = (
                    update(CustomerOrder)
                    .where(CustomerOrder.customer_purchase_id == pKey)
                    .values(**data)
                )
                result = db_client.session.execute(stmt)
            # Extract lot breakdown mapped by items_id or temporary index
            existing_items_with_lots = []
            new_items_with_lots = []
            for item in lineItems:
                lots = item.pop('lot_breakdown', None)
                if item.get('items_id'):
                    if lots and isinstance(lots, list):
                        existing_items_with_lots.append({'items_id': item['items_id'], 'lots': lots})
                else:
                    new_items_with_lots.append({'item': item, 'lots': lots if isinstance(lots, list) else []})

            if existing_items_with_lots:
                db_client.session.bulk_update_mappings(CustomerOrderItems, [item for item in lineItems if item.get('items_id')])
                for lm in existing_items_with_lots:
                    db_client.session.query(CPOItemLots).filter(
                        CPOItemLots.cpo_item_id == lm['items_id'],
                        CPOItemLots.deleted != True
                    ).update({'deleted': True})
                    for lot in lm['lots']:
                        if lot.get('lot_number'):
                            db_client.session.add(CPOItemLots(
                                customer_purchase_id=pKey,
                                cpo_item_id=lm['items_id'],
                                lot_number=str(lot.get('lot_number')).strip(),
                                lot_qty=float(lot.get('lot_qty', 0)),
                                compcode=cc.get('compcode'),
                                created_at=datetime.datetime.now()
                            ))
            elif lineItems:
                db_client.session.bulk_update_mappings(CustomerOrderItems, [item for item in lineItems if item.get('items_id')])

            # Insert newly created items and their corresponding lots individually to map IDs safely
            for entry in new_items_with_lots:
                item_dict = entry['item']
                new_item = CustomerOrderItems(**{**item_dict, **cc, 'customer_purchase_id': pKey})
                db_client.session.add(new_item)
                db_client.session.flush()

                for lot in entry['lots']:
                    if lot.get('lot_number'):
                        db_client.session.add(CPOItemLots(
                            customer_purchase_id=pKey,
                            cpo_item_id=new_item.items_id,
                            lot_number=str(lot.get('lot_number')).strip(),
                            lot_qty=float(lot.get('lot_qty', 0)),
                            compcode=cc.get('compcode'),
                            created_at=datetime.datetime.now()
                        ))

            db_client.session.commit()

            extData = data_extract_from_package(customer_purchase_id=pKey)
            order_extract(extData)
        except Exception as e:
            error = str(e)
            print("CUSTOMER_PURCHASE_POST_ERROR:", error)
            db_client.session.rollback()
            db_client.session.flush()
            return map_sqlalchemy_error_to_http_status(e)
            # db_client.session.close()
        success = False if error else True
        # db_client.session.commit()
        # db_client.session.close()

        if success:
            message = "Records Updated Successfully"
        else:
            message = "There is an Error"
        #print("vfdgfdgfd",message)
        return {
            'success': success,
            'message': message,
            'error': error,
        },200 if success else 409
@customerPurchaseRoute.route('/<customer_purchase_id>/')
class MasterData(Resource):
    @login_required(permissions='customerpurchase.delete')
    def delete(self,customer_purchase_id):
        """
                Soft delete MasterData record
                TODO: Make soft delete
                :return:
                """

        result = ipss_db.update_record(
            model=CustomerOrder,
            condition=CustomerOrder.customer_purchase_id == customer_purchase_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result
@customerPurchaseRoute.route('/lineItem/<items_id>/')
class SlaveData(Resource):
    @login_required(permissions='customerpurchase.delete')
    def delete(self,items_id):
        """
                Soft delete SlaveData record
                TODO: Make soft delete
                :return:
                """

        result = ipss_db.update_record(
            model=CustomerOrderItems,
            condition=CustomerOrderItems.items_id == items_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result


@customerPurchaseRoute.route('/order_plan_employee')
class OrderPlanEmployeeReport(Resource):

    @login_required()
    def get(self):

        current_user = request.args.get('current_user')
        compcode = current_user.get('company_id', None)

        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)

        end_date = end_date if end_date else start_date

        sql_con = ''
        if start_date:
            sql_con += ' and cp.created_on >= cast(:start_date as timestamp) and cp.created_on < cast(:end_date as timestamp) + interval \'1 day\' '

        order_plan_execution_query = text(f'''
        with cte11 as(
        select COALESCE(pt.product_id, pp.product_id) as product_id,pp.production_plan_id,el.*, el.opertaion_start_date as created_date from production_plan as pp
        left join plan_targets as pt on pt.production_plan_id = pp.production_plan_id
        left join execution_log as el on el.target_id = pt.plan_target_id)
        ,cte12 as (
                    select distinct on (ps.product_id)
                    ps.product_id,ps.rank_id,ps.id,ps.stage_id,
                    asm.config_id,asm.is_final_process
                    from production_stages ps
                    left join activity_stage_map asm on asm.production_stage_id = ps.id
                    where ps.deleted is not true and asm.deleted is not true 
                    and ps.compcode=:compcode
                    order by ps.product_id,ps.rank_id desc
        ),
        cte13 as
        (select cte11.* from 
        cte11 
        join cte12 on cte11.product_id = cte12.product_id and cte11.stage_id = cte12.stage_id and (cte12.config_id is null or cte11.process_id = cte12.config_id)
        )
        ,cte1 as(
        select 
        cp.order_unique,cp.order_date,cp.expected_receiving_date,cp.status,
        cpi.product_id as product_id2,cpi.quantity_ordered,cpi.quantity_delivered,
        pp.production_plan_id,COALESCE(pp.product_id, cpi.product_id) as product_id,pp.plan_unique,pp.execution_start_date,pp.execution_end_date,pp.is_done,pp.plan_date,pp.end_date,
        pt.target_quantity,cte13.stage_id,cte13.process_id,cte13.outward_qty,cte13.created_date as created_on
        from customer_purchase as cp
        left join customer_purchase_items as cpi on cpi.customer_purchase_id = cp.customer_purchase_id
        left join order_items_extract as oie on oie.order_items_id = cpi.items_id
        left join plan_details as pd on pd.order_extract_id = oie.extract_id
        left join production_plan as pp on pp.production_plan_id = pd.production_plan_id
        left join plan_targets as pt on pt.production_plan_id = pp.production_plan_id and COALESCE(pt.product_id, pp.product_id) = cpi.product_id
        left join cte13 on pt.plan_target_id = cte13.target_id
        where cp.compcode=:compcode {sql_con}
                    ),
                    cte3 as (
                    select 
                    cte1.order_unique,cte1.order_date,cte1.expected_receiving_date,cte1.status,
                    cte1.product_id,cte1.product_id2,cte1.quantity_ordered,cte1.quantity_delivered,
                    cte1.production_plan_id,cte1.plan_unique,cte1.execution_start_date,cte1.execution_end_date,cte1.is_done,cte1.plan_date,cte1.end_date,
                    cte1.created_on::date,sum(cte1.target_quantity) as target_quantity,sum(cte1.outward_qty) as outward_qty 
                    from cte1 
                    left join cte13 on cte1.production_plan_id = cte13.production_plan_id
                    group by 
                    cte1.order_unique,cte1.order_date,cte1.expected_receiving_date,cte1.status,
                    cte1.product_id,cte1.product_id2,cte1.quantity_ordered,cte1.quantity_delivered,
                    cte1.production_plan_id,cte1.plan_unique,cte1.execution_start_date,cte1.execution_end_date,cte1.is_done,cte1.plan_date,cte1.end_date,
                    cte1.created_on::date
                    ),
                    cte4 as (
                    select 
                    cte3.order_unique,cte3.order_date,cte3.expected_receiving_date,cte3.status,
                    cte3.product_id,cte3.product_id2,cte3.quantity_ordered,cte3.quantity_delivered,
                    cte3.plan_unique,cte3.execution_start_date,cte3.execution_end_date,cte3.is_done,cte3.plan_date,cte3.end_date,
                    (sum(cte3.outward_qty)/NULLIF(sum(cte3.target_quantity), 0)) * 100 as efficiency,
                    json_agg(
                    json_build_object(
                    'created_on', cte3.created_on::text,
                        'target_quantity', cte3.target_quantity,
                        'outward_qty', cte3.outward_qty
                    )
                    ) as execution_details
                    from cte3
                    group by 
                    cte3.order_unique,cte3.order_date,cte3.expected_receiving_date,cte3.status,
                    cte3.product_id,cte3.product_id2,cte3.quantity_ordered,cte3.quantity_delivered,
                    cte3.plan_unique,cte3.execution_start_date,cte3.execution_end_date,cte3.is_done,cte3.plan_date,cte3.end_date
                    ),
                    cte5 as (
                    select 
                    cte4.order_unique,cte4.order_date,cte4.expected_receiving_date,cte4.status,
                    cte4.product_id2,cte4.quantity_ordered,cte4.quantity_delivered,
                    json_agg(
                    json_build_object(
                        'plan_unique', cte4.plan_unique,
                        'product_name', p.product_name,
                        'product_code' , p.product_code,
                        'sku_id', p.sku_id,
                        'execution_start_date', cte4.execution_start_date::text,
                        'execution_end_date', cte4.execution_end_date::text,
                        'is_done', cte4.is_done,
                        'plan_date', cte4.plan_date::text,
                        'end_date', cte4.end_date::text,
                        'effeciency', round(cte4.efficiency, 2),
                        'execution_details', cte4.execution_details
                    )
                    ) as plan_details
                    from 
                    cte4
                    left join products as p on p.product_id = cte4.product_id
                    group by 
                    cte4.order_unique,cte4.order_date,cte4.expected_receiving_date,cte4.status,
                    cte4.product_id2,cte4.quantity_ordered,cte4.quantity_delivered
                    )
                    select 
                    cte5.order_unique,cte5.order_date::text,cte5.expected_receiving_date::text,cte5.status,
                    json_agg(
                    json_build_object(
                    'product_name', p.product_name,
                        'sku_id', p.sku_id,
                        'product_code', p.product_code,
                        'quantity_ordered', cte5.quantity_ordered,
                        'quantity_delivered', cte5.quantity_delivered,
                        'plan_details', cte5.plan_details
                    )
                    ) as order_details
                    from cte5
                    left join products as p on p.product_id = cte5.product_id2
                    group by
                    cte5.order_unique,cte5.order_date,cte5.expected_receiving_date::text,cte5.status
                ''')

        order_plan_execution_result = query_to_dict(db_client.engine.execute(order_plan_execution_query,
                                                                             compcode=compcode,
                                                                             start_date=start_date,
                                                                             end_date=end_date))

        pending_order = 0
        closed_order = 0
        total_order = 0
        total_plan = 0
        pending_plan = 0
        closed_plan = 0
        delayed_start_plan = 0
        early_start_plan = 0
        on_time_start_plan = 0
        delayed_complete_plan = 0
        on_time_complete_plan = 0
        early_complete_plan = 0
        no_of_product = 0
        product_dict = {}
        fmt = "%Y-%m-%d %H:%M:%S"
        for i in order_plan_execution_result:
            total_order += 1
            if i.get('status') == "Pending":
                pending_order += 1
            else:
                closed_order += 1
            for order in i.get('order_details', []):
                sku_id = order.get('sku_id', "")
                product_dict.setdefault(sku_id, {'sku_id': sku_id, 'quantity_delivered': 0, 'quantity_ordered': 0})
                curr_quantity_ordered = order.get('quantity_ordered') or 0
                curr_quantity_delivered = order.get('quantity_delivered') or 0
                product_dict[sku_id]['quantity_delivered'] += curr_quantity_delivered
                product_dict[sku_id]['quantity_ordered'] += curr_quantity_ordered
                for plan in order.get('plan_details', []):
                    total_plan += 1
                    if plan['is_done'] is True:
                        closed_plan += 1
                    else:
                        pending_plan += 1
                    execution_start_date = time.strptime(plan.get('execution_start_date'), fmt) if plan.get(
                        'execution_start_date') else None
                    execution_end_date = time.strptime(plan.get('execution_end_date'), fmt) if plan.get(
                        'execution_end_date') else None
                    plan_date = time.strptime(plan.get('plan_date'), fmt) if plan.get('plan_date') else None
                    end_date = time.strptime(plan.get('end_date'), fmt) if plan.get('end_date') else None

                    if plan_date and execution_start_date:
                        if plan_date < execution_start_date:
                            delayed_start_plan += 1
                        elif plan_date > execution_start_date:
                            early_start_plan += 1
                        else:
                            on_time_start_plan += 1
                    if end_date and execution_end_date:
                        if end_date < execution_end_date:
                            delayed_complete_plan += 1
                        elif end_date > execution_end_date:
                            early_complete_plan += 1
                        else:
                            on_time_complete_plan += 1
        no_of_product = len(product_dict)

        result_dict = {
            'total_order': total_order,
            'closed_order': closed_order,
            'pending_order': pending_order,
            'total_plan': total_plan,
            'pending_plan': pending_plan,
            'closed_plan': closed_plan,
            'delayed_start_plan': delayed_start_plan,
            'early_start_plan': early_start_plan,
            'on_time_start_plan': on_time_start_plan,
            'delayed_complete_plan': delayed_complete_plan,
            'on_time_complete_plan': on_time_complete_plan,
            'early_complete_plan': early_complete_plan,
            'no_of_product': no_of_product,
            'product_details': product_dict
        }

        return {
            "order_summary": result_dict,
            "order_details": order_plan_execution_result
        }


@customerPurchaseRoute.route('/drop_down')
class CustomerPurchaseDropDown(Resource):
    @login_required(permissions='customerpurchase.list')
    @customerPurchaseRoute.doc(params={'start_date': {
        'type': str,
        'description': 'Filter by start date'
    },
        'end_date': {
            'type': str,
            'description': 'Filter by end date'
        },
        'customer_purchase_id': {
            'type': int,
            'description': 'Filter by customer purchase id'
        } })
    def get(self):
        """
        Get DropDown Data for Customer Purchase
        :return:
        """
        compcode = request.args.get('current_user', {}).get('company_id', None)

        customer_purchase_id = request.args.get('customer_purchase_id', None)
        # print(1111111,customer_purchase_id)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', start_date)

        sql_con = ''

        if start_date:
            sql_con += ' and el.created_on >= cast(:start_date as timestamp) and el.created_on < cast(:end_date as timestamp) + interval \'1 day\' '

        if customer_purchase_id:
            sql_con += ' and cp.customer_purchase_id=:customer_purchase_id '

        customer_orders = query_to_dict(db_client.engine.execute(
            text(f'''
            select v.vendorid,v.companyname,v.contactname,
            json_agg(
            distinct jsonb_build_object(
                'customer_purchase_id', cp.customer_purchase_id,
                'order_unique', cp.order_unique
            )
            ) as orders
            from execution_log el 
            join plan_targets pt on pt.plan_target_id = el.target_id and el.deleted is not true and el.compcode=:compcode
            join production_plan pp on pp.production_plan_id = pt.production_plan_id and pt.deleted is not true
            join plan_details pd on pd.production_plan_id = pp.production_plan_id and pp.deleted is not true
            join order_items_extract oie on oie.extract_id = pd.order_extract_id
            join customer_purchase_items cpi on cpi.items_id = oie.order_items_id
            join customer_purchase cp on cp.customer_purchase_id = cpi.customer_purchase_id and cpi.deleted is not true
            join vendor v on v.vendorid = cp.customer_id
            left JOIN style_product sp ON sp.product_id = pp.product_id
            JOIN style st ON st.style_id = sp.style_id
            JOIN products p ON p.product_id = sp.product_id
            JOIN product_variant pv ON pv.product_id = p.product_id
            JOIN variant_value vv ON vv.variant_value_id = pv.variant_value_id AND st.attribute_id = vv.variant_attribute_id
            JOIN style_category sc ON sc.style_id = st.style_id
            JOIN category c ON c.category_id = sc.category_id
            where cp.compcode =:compcode and cp.deleted is not true {sql_con}
            group by v.vendorid,v.companyname,v.contactname
            '''),
            compcode=compcode,
            customer_purchase_id=customer_purchase_id,
            start_date=start_date,
            end_date=end_date
        ))
        return {
            'customer_orders': customer_orders
        }


@customerPurchaseRoute.route('/plan_cost')
class PlanCost(Resource):

    @login_required()
    @customerPurchaseRoute.marshal_with(plan_cost_response_model)
    @customerPurchaseRoute.doc(params=list_api_params)
    def get(self):

        current_user = request.args.get('current_user') or {}
        compcode = current_user.get('company_id', None) if isinstance(current_user, dict) else None
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', start_date)
        sql_con = ''
        customer_purchase_id = request.args.get('customer_purchase_id', None)
        is_done = request.args.get('is_done', None)
        product_id = request.args.get('product_id', None)
        production_plan_id = request.args.get('production_plan_id', None)
        if customer_purchase_id:
            sql_con += ' and cp.customer_purchase_id =:customer_purchase_id '
        if is_done:
            sql_con += ' and pp.is_done =:is_done '
        if product_id:
            sql_con += ' and cpi.product_id =:product_id '
        if production_plan_id:
            sql_con += ' and pp.production_plan_id =:production_plan_id '
        el_date_con = ''
        if start_date:
            sql_con += ' and EXISTS (select 1 from execution_log el join plan_targets pt on pt.plan_target_id = el.target_id where pt.production_plan_id = pp.production_plan_id and el.opertaion_start_date >= cast(:start_date as timestamp) and el.opertaion_start_date < cast(:end_date as timestamp) + interval \'1 day\' and el.deleted is not true and pt.deleted is not true) '
            el_date_con = ' and el.opertaion_start_date >= cast(:start_date as timestamp) and el.opertaion_start_date < cast(:end_date as timestamp) + interval \'1 day\' '

        query = text(f'''
            with final_stage as (
            SELECT DISTINCT ON (ips.product_id)
            ips.product_id,
            ips.stage_id,
            asm.config_id
            FROM production_stages ips
            JOIN activity_stage_map asm
            ON asm.production_stage_id = ips.id
            AND asm.is_final_process is true
            WHERE ips.compcode =:compcode and ips.deleted IS NOT TRUE and asm.deleted is not true
            ORDER BY ips.product_id, ips.rank_id DESC
            ),
            produced_qty as (
            select pp.production_plan_id, COALESCE(pt.product_id, pp.product_id) as product_id, sum(el.outward_qty) as outward_qty
            from production_plan pp
            left join plan_targets pt on pt.production_plan_id =pp.production_plan_id 
            left join execution_log el on el.target_id =pt.plan_target_id 
            join final_stage fs on fs.product_id = COALESCE(pt.product_id, pp.product_id) and fs.stage_id = el.stage_id 
            and el.process_id = fs.config_id
            where pp.deleted is not true and pp.compcode=:compcode {el_date_con}
            group by pp.production_plan_id, COALESCE(pt.product_id, pp.product_id)
            ),
            cte as(
            select cp.customer_purchase_id,cp.order_unique,cpi.product_id,p.product_code,
            p.skU_id,u.uom,pp.production_plan_id,pp.plan_unique,pp.is_done,
            coalesce(pq.outward_qty, 0) as moved_quantity,pp.total_labour_cost,
            pp.labour_cost_per_product,pp.total_material_cost,pd.plan_quantity as planed_quantity,cpi.quantity_ordered as ordered_quantity,
            case when lower(p.product_code) like '%cutt part%' or lower(u.uom) = 'pcs' and exists (
                select 1 from customer_purchase_items cpi_parent 
                join products p_parent on p_parent.product_id = cpi_parent.product_id 
                join uom u_parent on u_parent.id = p_parent.uom_id
                where cpi_parent.customer_purchase_id = cp.customer_purchase_id 
                  and lower(u_parent.uom) like '%box%'
            ) then true else false end as is_child_component
            from production_plan pp
            join plan_details pd on pd.production_plan_id = pp.production_plan_id
            join order_items_extract oie on oie.extract_id = pd.order_extract_id
            join customer_purchase_items cpi on cpi.items_id = oie.order_items_id
            join customer_purchase cp on cp.customer_purchase_id = cpi.customer_purchase_id
            join products p on p.product_id = cpi.product_id
            join uom u on u.id = p.uom_id
            left join produced_qty pq on pq.production_plan_id = pp.production_plan_id and pq.product_id = cpi.product_id
            where pp.compcode=:compcode and pp.deleted is not true and pd.deleted is not true and oie.deleted is not true and cpi.deleted is not true and cp.deleted is not true {sql_con}
            ),
            cte2 as(
            select cte.customer_purchase_id,cte.order_unique,cte.product_id,cte.product_code,cte.sku_id,cte.uom,cte.ordered_quantity,
            cte.is_child_component,
            sum(cte.planed_quantity) as sum_planed_quantity,
            sum(cte.moved_quantity) as sum_moved_quantity,
            sum(cte.total_labour_cost) as sum_total_labour_cost,
            sum(cte.total_material_cost) as sum_total_material_cost,
            json_agg(
            json_build_object(
            'production_plan_id', cte.production_plan_id,
            'plan_unique', cte.plan_unique,
            'is_done', cte.is_done,
            'planed_quantity', cte.planed_quantity,
            'moved_quantity', cte.moved_quantity,
            'total_labour_cost', cte.total_labour_cost,
            'labour_cost_per_product', cte.labour_cost_per_product,
            'total_material_cost', cte.total_material_cost
            )
            ) as data
            from cte
            group by cte.customer_purchase_id,cte.order_unique,cte.product_id,cte.product_code,cte.sku_id,cte.uom,cte.ordered_quantity,cte.is_child_component
            )
            select cte2.customer_purchase_id,cte2.order_unique,
            json_agg(
            json_build_object(
            'product_id', cte2.product_id,
            'product_code', cte2.product_code,
            'sku_id', cte2.sku_id,
            'uom', cte2.uom,
            'ordered_quantity', cte2.ordered_quantity,
            'is_child_component', cte2.is_child_component,
            'sum_planed_quantity', cte2.sum_planed_quantity,
            'sum_moved_quantity', cte2.sum_moved_quantity,
            'sum_total_labour_cost', cte2.sum_total_labour_cost,
            'sum_total_material_cost', cte2.sum_total_material_cost,
            'data', cte2.data
            )
            ) as data,
            count(*) over() as total_results
            from cte2
            group by cte2.customer_purchase_id,cte2.order_unique
            order by cte2.customer_purchase_id desc
            limit :limit offset :offset
        ''')

        params = {
            'compcode': compcode,
            'limit': results_per_page,
            'offset': offset,
        }
        if customer_purchase_id:
            params['customer_purchase_id'] = customer_purchase_id
        if is_done:
            params['is_done'] = is_done
        if product_id:
            params['product_id'] = product_id
        if production_plan_id:
            params['production_plan_id'] = production_plan_id
        if start_date:
            params['start_date'] = start_date
            params['end_date'] = end_date
 
        result = query_to_dict(db_client.engine.execute(query, **params))
        s = db_client.session
        
        # Collect all plan IDs
        all_plan_ids = []
        for row in result:
            for product in row.get('data', []):
                for plan in product.get('data', []):
                    plan_id = plan.get('production_plan_id')
                    if plan_id is not None:
                        all_plan_ids.append(plan_id)
        all_plan_ids = list(set(all_plan_ids))
        
        # Fetch bulk costs
        estimated_labour_bulk = get_estimated_labour_cost_bulk(s, all_plan_ids, compcode, start_date=start_date, end_date=end_date)
        estimated_material_bulk = get_estimated_material_cost_bulk(s, all_plan_ids, compcode, start_date=start_date, end_date=end_date)
        actual_material_bulk = get_material_cost_bulk(all_plan_ids, start_date=start_date, end_date=end_date)
        actual_labour_bulk = get_labour_cost_bulk(s, all_plan_ids, start_date=start_date, end_date=end_date)
 
        for row in result:
            product_data = row.get('data', [])
            seen_actual_material_plans = set()
            for product in product_data:
                plans = product.get('data', [])
                for plan in plans:
                    plan_id = plan.get('production_plan_id')
                    prod_id = product.get('product_id')
                    key = (plan_id, prod_id)
                    
                    # Calculate estimated costs for all plans
                    plan['estimated_labour_cost'] = estimated_labour_bulk.get(key, 0)
                    plan['estimated_material_cost'] = estimated_material_bulk.get(key, 0)
 
                    labour_data = actual_labour_bulk.get(key, {})
                    if not plan.get('is_done'):
                        # Calculate material cost (assign once per plan to prevent duplicate cost across multiple products of the same plan)
                        if plan_id not in seen_actual_material_plans:
                            plan['total_material_cost'] = float(actual_material_bulk.get(plan_id, 0))
                            seen_actual_material_plans.add(plan_id)
                        else:
                            plan['total_material_cost'] = 0.0
                        
                        # Calculate labour cost
                        plan['total_labour_cost'] = float(labour_data.get('total_labour_cost', 0))
                        plan['labour_cost_per_product'] = float(labour_data.get('labour_cost_per_product', 0))
                    else:
                        # Fallback for completed plans where stored labour_cost_per_product was 0
                        if not plan.get('labour_cost_per_product') and labour_data.get('labour_cost_per_product'):
                            plan['labour_cost_per_product'] = float(labour_data.get('labour_cost_per_product', 0))
                        
                # Re-calculate sums for the product
                product['sum_total_material_cost'] = sum(float(p.get('total_material_cost') or 0) for p in plans)
                product['sum_total_labour_cost'] = sum(float(p.get('total_labour_cost') or 0) for p in plans)
                product['sum_estimated_material_cost'] = sum(float(p.get('estimated_material_cost') or 0) for p in plans)
                product['sum_estimated_labour_cost'] = sum(float(p.get('estimated_labour_cost') or 0) for p in plans)

        return {
            'total_results': result[0].get('total_results', 0) if result else 0,
            'page': paged,
            'results_per_page': results_per_page,
            'results': result
        }


@customerPurchaseRoute.route('/planed_qty/<customer_purchase_id>/')
class PlanedQty(Resource):

    @login_required()
    @customerPurchaseRoute.marshal_with(planed_qty_response_model)
    def get(self, customer_purchase_id):
        product_id = request.args.get('product_id', None)
        sql_con = ''

        if product_id:
            sql_con += ' and COALESCE(pp.product_id, cpi.product_id) =:product_id '
        query = text(f'''
			select COALESCE(pp.product_id, cpi.product_id) as product_id, sum(pd.plan_quantity) as total,
			json_agg(
			json_build_object(
			'plan_unique', pp.plan_unique,
			'plan_quantity', pd.plan_quantity,
			'status', pp.status
			)
			) as data
			from customer_purchase cp 
			join customer_purchase_items cpi on cpi.customer_purchase_id = cp.customer_purchase_id
			join order_items_extract oie on oie.order_items_id = cpi.items_id
			join plan_details pd on oie.extract_id = pd.order_extract_id
			join production_plan pp on pp.production_plan_id = pd.production_plan_id 
			where cp.customer_purchase_id =:customer_purchase_id 
			  and pp.status <> 'Rejected'
			  and pp.deleted is not true
			  and pd.deleted is not true
			  and oie.deleted is not true
			  and cpi.deleted is not true
			  and cp.deleted is not true
			  {sql_con}
			group by COALESCE(pp.product_id, cpi.product_id)
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                         product_id=product_id,
                                                         customer_purchase_id=customer_purchase_id))

        return {
            'results': result
        }