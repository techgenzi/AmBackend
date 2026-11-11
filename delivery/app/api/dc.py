import datetime
from .helper import customer_order_update, order_over_all_updated
from ipss_utils.redis.ipss_redis import query_to_dict
from .. import db_client, ipss_db
from sqlalchemy.exc import SQLAlchemyError
from flask import request, jsonify
from flask_restx import Resource, marshal
from ipss_utils.decorators import login_required
from sqlalchemy import text, insert, update, and_
from .. import db_client
from ..api_doc import search_types, report_filter

from ..models.dc import DeliveryModel, DeliveryLineItems, DeliverySerializedItems
from ..routes.dc import delivery_get_model, delivery_api_route, delivery_get_all_model, delivery_post_model, \
    create_delivery_response, update_delivery_response, items_model, delivery_report_list


@delivery_api_route.route('/')
class Delivery(Resource):

    @delivery_api_route.marshal_with(delivery_get_all_model)
    @delivery_api_route.doc(params=search_types)
    @login_required()
    # @login_required(permissions='delivery.list')
    def get(self):
        """
        List of delivery with pagination
        TODO: Search delivery
        :return:
        """
        current_user = request.args.get('current_user',{})
        ccode = current_user.get('company_id')
        sql_condition = ""
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 0
        offset = (paged - 1) * results_per_page
        sq_con=''
        if request.args.get('deliveryid'):
            sq_con+=' and d.deliveryid=:deliveryid '
        if request.args.get('vendorid'):
            sq_con+=' and d.vendorid=:vendorid '
        if request.args.get('status'):
            sq_con+=' and d.status=:status '
        if request.args.get('is_drafted'):
            sq_con+=' and d.is_drafted=:is_drafted '
        if request.args.get('delivery_date'):
            sq_con+=' and d.delivery_date=:delivery_date '
        if request.args.get('customerid'):
            sq_con+=' and d.customerid=:customerid '
        sql_query=text(f'''
        select d.*,json_agg(dli) as items from delivery as d
        join delivery_line_items as dli on dli.deliveryid=d.deliveryid
        where d.deleted is not true and dli.deleted is not true and 
        d.compcode=:ccode {sq_con}
        group by d.deliveryid
        order by d.deliveryid desc
        limit :limit offset :offset
        ''')
        sql_query=query_to_dict(db_client.engine.execute(sql_query,
                                                         deliveryid=request.args.get('deliveryid'),
                                                         vendorid=request.args.get('vendorid'),
                                                         status=request.args.get('status'),
                                                         is_drafted=request.args.get('is_drafted'),
                                                         delivery_date=request.args.get('delivery_date'),
                                                         customerid=request.args.get('customerid'),
                                                         ccode=ccode,
                                                         limit=results_per_page,
                                                         offset=offset))
        sql_count=text(f'''
        select count(distinct d.deliveryid)
        from delivery as d
        join delivery_line_items as dli on dli.deliveryid=d.deliveryid
        where d.deleted is not true and dli.deleted is not true and d.compcode=:ccode {sq_con}
        ''')
        sql_count=query_to_dict(db_client.engine.execute(sql_count,
                                                         deliveryid=request.args.get('deliveryid'),
                                                         vendorid=request.args.get('vendorid'),
                                                         status=request.args.get('status'),
                                                         is_drafted=request.args.get('is_drafted'),
                                                         delivery_date=request.args.get('delivery_date'),
                                                         customerid=request.args.get('customerid'),
                                                         ccode=ccode,
                                                         ))
        return {
            "total_results": sql_count[0].get('count',0) if sql_count else 0,
                "page": paged,
                "results_per_page": results_per_page,
                "results": sql_query
        }

    @login_required(permissions='delivery.add')
    @delivery_api_route.expect(delivery_post_model)
    @delivery_api_route.marshal_with(create_delivery_response)
    def post(self):
        """
        Create delivery record and return inserted id
        :return:
        """
        current_user = request.args.get('current_user')
        ccode = current_user.get('company_id')
        user = current_user.get('userid', None)
        username = current_user.get('username', None)
        data = request.json
        val = text("select count(deliveryid) from delivery where compcode=:ccode")
        result = query_to_dict(db_client.engine.execute(val, ccode=ccode))
        print("result", result[0]['count'])
        suf = str(result[0]['count'] + 1).zfill(6)
        prod_code = "DC-" + suf
        print(prod_code)
        data['userid'] = user
        data['created_by'] = username
        data['created_on'] = datetime.datetime.now()
        data['deliveryno'] = prod_code
        data['compcode'] = ccode
        data.pop('deliveryid', None)
        items = data.pop('items', None)

        error = ""
        primary_key_id = 0
        s = db_client.session
        try:
            with db_client.session.begin():
                stmt = (
                    insert(DeliveryModel)
                    .values(**data)
                )
                result = s.execute(stmt)
                primary_key_id = result.inserted_primary_key[0]
                inserted_line_ids = []
                manage_stock = True
                try:
                    config_q = text('''
                        SELECT config_data FROM custome_config 
                        WHERE compcode = :ccode 
                          AND module_name = 'inventory' 
                          AND config_type = 'settings' 
                          AND deleted IS NOT TRUE
                        LIMIT 1
                    ''')
                    res_config = s.execute(config_q, {'ccode': ccode}).fetchone()
                    if res_config:
                        config_data = res_config[0]
                        if isinstance(config_data, str):
                            import json
                            try:
                                config_data = json.loads(config_data)
                            except Exception:
                                config_data = {}
                        if isinstance(config_data, dict):
                            manage_stock = config_data.get('manage_stock', True)
                except Exception as e:
                    print("Error checking tenant config:", e)

                for item in items:
                    item['deliveryid'] = primary_key_id
                    item['created_by'] = username
                    item['created_on'] = datetime.datetime.now()
                    
                    # Ensure defaults for rejection fields if not provided in payload
                    item.setdefault('rejected_quantity', 0)
                    item.setdefault('is_rejected', False)
                    item.setdefault('rejection_action', None)
                    item.setdefault('rejection_store_id', None)

                    # Pop serial numbers
                    serial_numbers = item.pop('serial_numbers', []) or []
                    
                    # Pop store_id as it's not in DeliveryLineItems model
                    store_id = item.pop('store_id', None)
                    lot_no = item.get('production_lot_no', None)
                    
                    # Insert DeliveryLineItems row
                    stmt_item = insert(DeliveryLineItems).values(**item)
                    result_item = s.execute(stmt_item)
                    line_item_id = result_item.inserted_primary_key[0]
                    inserted_line_ids.append(line_item_id)
                    
                    # Execute customer order status update
                    s.execute(customer_order_update(), item)
                    
                    qty = item.get('quantity')
                    line_id = item.get('workOrderLineId')
                    
                    find_q = text('''
                        SELECT cpi.product_id
                        FROM customer_purchase_items cpi
                        WHERE cpi.items_id = :line_id
                        LIMIT 1
                    ''')
                    res_find = s.execute(find_q, {'line_id': line_id}).fetchone()
                    if res_find:
                        prod_id = res_find[0]
                        
                        if manage_stock and qty and float(qty) > 0 and not store_id:
                            raise ValueError(f"Store selection is missing for delivery item {line_id}")
                        
                        # Handle Rejection Quantities
                        rejected_qty = item.get('rejected_quantity', 0)
                        is_rejected = item.get('is_rejected', False)
                        rejection_action = item.get('rejection_action')
                        rejection_store_id = item.get('rejection_store_id')

                        if is_rejected and rejected_qty and float(rejected_qty) > 0:
                            if manage_stock and not store_id:
                                raise ValueError(f"Store selection is missing for delivery item {line_id}")
                            if manage_stock and rejection_action in ['Return to Store', 'Rework', 'Return to Vendor'] and not rejection_store_id:
                                raise ValueError(f"Rejection store selection is missing for action '{rejection_action}' in item {line_id}")

                        if prod_id:
                            if store_id and manage_stock and qty and float(qty) > 0:
                                upd_store = text('''
                                    UPDATE store_product 
                                    SET product_count = COALESCE(product_count, 0) - :qty
                                    WHERE product_id = :prod_id AND store_id = :store_id AND COALESCE(lot_no, '') = :lot_no AND compcode = :ccode AND deleted IS NOT TRUE
                                ''')
                                s.execute(upd_store, {'qty': qty, 'prod_id': prod_id, 'store_id': store_id, 'lot_no': lot_no or '', 'ccode': ccode})

                                ins_registry = text('''
                                    INSERT INTO invregistry (
                                        product_id, requested_amount, approved_amount, action, ref_id, 
                                        status, is_dispatch, store_id, lot_no, compcode, userid, approval_id, 
                                        approval_date, created_on, created_by, type, deleted
                                    ) VALUES (
                                        :product_id, :qty, :qty, 'Outward', :ref_id, 
                                        'Approved', true, :store_id, :lot_no, :compcode, :userid, :userid, 
                                        NOW(), NOW(), :username, 'Delivery', false
                                    )
                                ''')
                                s.execute(ins_registry, {
                                    'product_id': prod_id,
                                    'qty': qty,
                                    'ref_id': prod_code,
                                    'store_id': store_id,
                                    'lot_no': lot_no,
                                    'compcode': ccode,
                                    'userid': user,
                                    'username': username
                                })
                            
                            if is_rejected and rejected_qty and float(rejected_qty) > 0:
                                if store_id and manage_stock:
                                    upd_source_store = text('''
                                        UPDATE store_product 
                                        SET product_count = COALESCE(product_count, 0) - :rejected_qty
                                        WHERE product_id = :prod_id AND store_id = :store_id AND COALESCE(lot_no, '') = :lot_no AND compcode = :ccode AND deleted IS NOT TRUE
                                    ''')
                                    s.execute(upd_source_store, {
                                        'rejected_qty': rejected_qty,
                                        'prod_id': prod_id,
                                        'store_id': store_id,
                                        'lot_no': lot_no or '',
                                        'ccode': ccode
                                    })
                                    
                                    ins_rejection_outward = text('''
                                        INSERT INTO invregistry (
                                            product_id, requested_amount, approved_amount, action, ref_id, 
                                            status, is_dispatch, store_id, lot_no, compcode, userid, approval_id, 
                                            approval_date, created_on, created_by, type, deleted
                                        ) VALUES (
                                            :product_id, :rejected_qty, :rejected_qty, 'Outward', :ref_id, 
                                            'Approved', true, :store_id, :lot_no, :compcode, :userid, :userid, 
                                            NOW(), NOW(), :username, 'Delivery', false
                                        )
                                    ''')
                                    s.execute(ins_rejection_outward, {
                                        'product_id': prod_id,
                                        'rejected_qty': rejected_qty,
                                        'ref_id': prod_code,
                                        'store_id': store_id,
                                        'lot_no': lot_no,
                                        'compcode': ccode,
                                        'userid': user,
                                        'username': username
                                    })

                                if rejection_action in ['Return to Store', 'Rework', 'Return to Vendor'] and rejection_store_id:
                                    if manage_stock:
                                        check_store_q = text('''
                                            SELECT EXISTS (
                                                SELECT 1 FROM store_product 
                                                WHERE product_id = :prod_id AND store_id = :rejection_store_id AND COALESCE(lot_no, '') = :lot_no AND compcode = :ccode AND deleted IS NOT TRUE
                                            )
                                        ''')
                                        exists = s.execute(check_store_q, {'prod_id': prod_id, 'rejection_store_id': rejection_store_id, 'lot_no': lot_no or '', 'ccode': ccode}).scalar()
                                        if exists:
                                            upd_rej_store = text('''
                                                UPDATE store_product 
                                                SET product_count = COALESCE(product_count, 0) + :rejected_qty
                                                WHERE product_id = :prod_id AND store_id = :rejection_store_id AND COALESCE(lot_no, '') = :lot_no AND compcode = :ccode AND deleted IS NOT TRUE
                                            ''')
                                            s.execute(upd_rej_store, {
                                                'rejected_qty': rejected_qty,
                                                'prod_id': prod_id,
                                                'rejection_store_id': rejection_store_id,
                                                'lot_no': lot_no or '',
                                                'ccode': ccode
                                            })
                                        else:
                                            ins_rej_store = text('''
                                                INSERT INTO store_product (product_id, store_id, lot_no, product_count, compcode, created_on, created_by)
                                                VALUES (:prod_id, :rejection_store_id, :lot_no, :rejected_qty, :ccode, NOW(), :username)
                                            ''')
                                            s.execute(ins_rej_store, {
                                                'prod_id': prod_id,
                                                'rejection_store_id': rejection_store_id,
                                                'lot_no': lot_no,
                                                'rejected_qty': rejected_qty,
                                                'ccode': ccode,
                                                'username': username
                                            })

                                        ins_rejection_inward = text('''
                                            INSERT INTO invregistry (
                                                product_id, requested_amount, approved_amount, action, ref_id, 
                                                status, is_dispatch, store_id, lot_no, compcode, userid, approval_id, 
                                                approval_date, created_on, created_by, type, deleted
                                            ) VALUES (
                                                :product_id, :rejected_qty, :rejected_qty, 'Inward', :ref_id, 
                                                'Approved', false, :rejection_store_id, :lot_no, :compcode, :userid, :userid, 
                                                NOW(), NOW(), :username, 'Delivery', false
                                            )
                                        ''')
                                        s.execute(ins_rejection_inward, {
                                            'product_id': prod_id,
                                            'rejected_qty': rejected_qty,
                                            'ref_id': prod_code,
                                            'rejection_store_id': rejection_store_id,
                                            'lot_no': lot_no,
                                            'compcode': ccode,
                                            'userid': user,
                                            'username': username
                                        })
                            
                            
                            check_ser_q = text('''
                                SELECT EXISTS (
                                    SELECT 1 FROM products p
                                    WHERE p.product_id = :prod_id 
                                      AND p.compcode = :ccode
                                      AND p.is_serializable = TRUE
                                )
                            ''')
                            is_serialized = s.execute(check_ser_q, {'prod_id': prod_id, 'ccode': ccode}).scalar()
                            
                            if is_serialized:
                                if len(serial_numbers) != int(qty):
                                    raise ValueError(f"Product {prod_id} requires exactly {qty} serial numbers, but {len(serial_numbers)} were provided.")
                                
                                for sn in serial_numbers:
                                    validate_sn_q = text('''
                                        SELECT id FROM store_serialized_products
                                        WHERE product_id = :prod_id 
                                          AND store_id = :store_id
                                          AND (serial_number = :sn OR (serial_number IS NULL AND (unit_data->>'Serial No' = :sn OR unit_data->>'serial_number' = :sn OR unit_data->>'Serial Number' = :sn OR unit_data->>'serial_no' = :sn)))
                                          AND status = 'Available'
                                          AND deleted IS NOT TRUE
                                          AND compcode = :ccode
                                    ''')
                                    sn_res = s.execute(validate_sn_q, {'prod_id': prod_id, 'store_id': store_id, 'sn': sn, 'ccode': ccode}).fetchone()
                                    if not sn_res:
                                        raise ValueError(f"Serial number '{sn}' for product {prod_id} is invalid or not available in store.")
                                    
                                    sn_id = sn_res[0]
                                    
                                    # Insert into delivery_serialized_items
                                    dsi_stmt = insert(DeliverySerializedItems).values(
                                        deliveryid=primary_key_id,
                                        delivery_line_item_id=line_item_id,
                                        serial_number=sn,
                                        compcode=ccode,
                                        created_on=datetime.datetime.now(),
                                        created_by=username
                                    )
                                    s.execute(dsi_stmt)
                                    
                                    # Update status to 'Dispatched'
                                    upd_sn_status = text('''
                                        UPDATE store_serialized_products
                                        SET status = 'Dispatched', updated_at = :now
                                        WHERE id = :sn_id
                                    ''')
                                    s.execute(upd_sn_status, {'sn_id': sn_id, 'now': datetime.datetime.now()})

                ids = tuple(set(i.get('workOrderLineId') for i in items))
                print("SDfsdfdf",ids)
                db_client.session.execute(order_over_all_updated(),{'ids': ids})
                print("SDfrgrwsr")
                # s.commit()
        except Exception as e:
            error = str(e)
            db_client.session.rollback()
            db_client.session.flush()
            # s.flush()
            
            if "check_column_positive" in error:
                error = "Insufficient stock available for one or more products. Please check the current stock before delivering."

        success = False if error else True

        return {
            "success": success,
            "error": error,
            "message": "Record created successfully" if success else ("Insufficient Stock" if "Insufficient stock" in error else "Check Error"),
            "primary_key": 'deliveryid',
            "inserted_id": primary_key_id
        }


@delivery_api_route.route('/<deliveryid>')
class DeliveryUpdateApi(Resource):

    @delivery_api_route.marshal_with(delivery_post_model)
    @login_required(permissions='delivery.view||delivery.edit')
    #@login_required()
    def get(self, deliveryid):

        delivery = DeliveryModel.query.filter_by(deliveryid=deliveryid).first()
        line = DeliveryLineItems.query.filter(and_(DeliveryLineItems.deliveryid == deliveryid,
                                                   DeliveryLineItems.deleted != True)).all()
        delivery_res = marshal(delivery,delivery_get_model)
        
        items = []
        for i in line:
            ser_q = text('''
                SELECT serial_number FROM delivery_serialized_items
                WHERE delivery_line_item_id = :line_item_id AND deleted IS NOT TRUE
            ''')
            ser_res = db_client.session.execute(ser_q, {'line_item_id': i.id}).fetchall()
            serial_numbers = [r[0] for r in ser_res]
            
            marshaled_item = marshal(i, items_model)
            marshaled_item['serial_numbers'] = serial_numbers
            items.append(marshaled_item)

        delivery_res['items'] = items
        return delivery_res

    @delivery_api_route.expect(delivery_post_model)
    @delivery_api_route.marshal_with(update_delivery_response)
    @login_required(permissions='delivery.edit')
    def patch(self, deliveryid):
        """
        Partial Update delivery record
        :return:
        """
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        username = current_user.get('username')
        data = request.json
        items = data.pop('items', None)
        data.pop('deliveryid', None)
        try:
            if data:
                que = (update(DeliveryModel).where(DeliveryModel.deliveryid == deliveryid).values(data))
                db_client.engine.execute(que)
            if items:
                s = db_client.session
                with s.begin():
                    for item in items:
                        if 'id' not in item:
                            raise ValueError("Each item must contain 'id' for the update.")
                    
                    items_to_update = []
                    for item in items:
                        item_copy = dict(item)
                        line_item_id = item_copy['id']
                        serial_numbers = item_copy.pop('serial_numbers', None)
                        items_to_update.append(item_copy)
                        
                        if serial_numbers is not None:
                            qty = item_copy.get('quantity')
                            if qty is None:
                                qty = s.execute(text("SELECT quantity FROM delivery_line_items WHERE id = :id"), {'id': line_item_id}).scalar()
                            
                            work_order_line_id = item_copy.get('workOrderLineId')
                            if work_order_line_id is None:
                                work_order_line_id = s.execute(text('SELECT "workOrderLineId" FROM delivery_line_items WHERE id = :id'), {'id': line_item_id}).scalar()
                            
                            find_q = text('''
                                SELECT cpi.product_id
                                FROM customer_purchase_items cpi
                                WHERE cpi.items_id = :line_id
                                LIMIT 1
                            ''')
                            res_find = s.execute(find_q, {'line_id': work_order_line_id}).fetchone()
                            if res_find:
                                prod_id = res_find[0]
                                
                                check_ser_q = text('''
                                      SELECT EXISTS (
                                          SELECT 1 FROM products p
                                          WHERE p.product_id = :prod_id 
                                            AND p.compcode = :ccode
                                            AND p.is_serializable = TRUE
                                      )
                                  ''')
                                is_serialized = s.execute(check_ser_q, {'prod_id': prod_id, 'ccode': ccode}).scalar()
                                
                                if is_serialized:
                                    if len(serial_numbers) != int(qty):
                                        raise ValueError(f"Product {prod_id} requires exactly {qty} serial numbers, but {len(serial_numbers)} were provided.")
                                    
                                    find_existing_q = text('''
                                        SELECT serial_number FROM delivery_serialized_items
                                        WHERE delivery_line_item_id = :line_item_id AND deleted IS NOT TRUE
                                    ''')
                                    existing_serials = [row[0] for row in s.execute(find_existing_q, {'line_item_id': line_item_id}).fetchall()]
                                    
                                    if existing_serials:
                                        revert_ssp_q = text('''
                                            UPDATE store_serialized_products
                                            SET status = 'Available', updated_at = :now
                                            WHERE serial_number IN :serials AND deleted IS NOT TRUE
                                        ''')
                                        s.execute(revert_ssp_q, {'serials': tuple(existing_serials), 'now': datetime.datetime.now()})
                                        
                                        del_dsi_q = text('''
                                            UPDATE delivery_serialized_items
                                            SET deleted = TRUE, deleted_at = :now
                                            WHERE delivery_line_item_id = :line_item_id AND deleted IS NOT TRUE
                                        ''')
                                        s.execute(del_dsi_q, {'line_item_id': line_item_id, 'now': datetime.datetime.now()})
                                    
                                    for sn in serial_numbers:
                                        validate_sn_q = text('''
                                            SELECT id FROM store_serialized_products
                                            WHERE product_id = :prod_id 
                                              AND store_id = :store_id
                                              AND (serial_number = :sn OR (serial_number IS NULL AND (unit_data->>'Serial No' = :sn OR unit_data->>'serial_number' = :sn OR unit_data->>'Serial Number' = :sn OR unit_data->>'serial_no' = :sn)))
                                              AND status = 'Available'
                                              AND deleted IS NOT TRUE
                                              AND compcode = :ccode
                                        ''')
                                        sn_res = s.execute(validate_sn_q, {'prod_id': prod_id, 'store_id': store_id, 'sn': sn, 'ccode': ccode}).fetchone()
                                        if not sn_res:
                                            raise ValueError(f"Serial number '{sn}' for product {prod_id} is invalid or not available in store.")
                                        
                                        sn_id = sn_res[0]
                                        
                                        dsi_stmt = insert(DeliverySerializedItems).values(
                                            deliveryid=deliveryid,
                                            delivery_line_item_id=line_item_id,
                                            serial_number=sn,
                                            compcode=ccode,
                                            created_on=datetime.datetime.now(),
                                            created_by=username
                                        )
                                        s.execute(dsi_stmt)
                                        
                                        upd_sn_status = text('''
                                            UPDATE store_serialized_products
                                            SET status = 'Dispatched', updated_at = :now
                                            WHERE id = :sn_id
                                        ''')
                                        s.execute(upd_sn_status, {'sn_id': sn_id, 'now': datetime.datetime.now()})

                    db_client.session.bulk_update_mappings(DeliveryLineItems, items_to_update)
                    ids = tuple(set(i.get('workOrderLineId') for i in items_to_update if i.get('workOrderLineId') is not None))
                    if ids:
                        db_client.session.execute(order_over_all_updated(), {'ids': ids})
                        db_client.session.execute(customer_order_update())
            return {
                'success': True,
                'message': 'Bulk update successful'
                }, 200
        except Exception as e:
            error = str(e)
            db_client.session.rollback()
            return {
                'success': False,
                'message': 'Bulk update failed',
                'error':error
                }, 500

    @delivery_api_route.marshal_with(update_delivery_response)
    @login_required(permissions='delivery.delete')
    def delete(self, deliveryid):
        """
        Soft delete record, restore stock in products and store_product,
        and revert purchase order statuses.
        """
        current_user = request.args.get('current_user')
        ccode = current_user.get('company_id') if current_user else None
        
        error = ""
        s = db_client.session
        try:
            with db_client.session.begin():
                # 1. Fetch all active (not already deleted) delivery line items for this delivery
                items_q = text('''
                    SELECT id, "workOrderLineId", quantity, compcode
                    FROM delivery_line_items
                    WHERE deliveryid = :deliveryid AND deleted IS NOT TRUE
                ''')
                items = s.execute(items_q, {'deliveryid': deliveryid}).fetchall()
                
                # 2. Revert inventory stock for store_product and update customer purchase items/orders
                for item in items:
                    line_id = item[1]
                    qty = item[2]
                    item_ccode = item[3] or ccode
                    
                    # Trace store_id and product_id for the line item
                    find_q = text('''
                        SELECT cpi.product_id, fg.store_id
                        FROM customer_purchase_items cpi
                        LEFT JOIN order_items_extract oie ON oie.order_items_id = cpi.items_id
                        LEFT JOIN plan_details pd ON pd.order_extract_id = oie.extract_id
                        LEFT JOIN fg_to_store_log fg ON fg.production_plan_id = pd.production_plan_id AND fg.deleted IS NOT TRUE
                        WHERE cpi.items_id = :line_id
                        ORDER BY fg.log_id DESC
                        LIMIT 1
                    ''')
                    res_find = s.execute(find_q, {'line_id': line_id}).fetchone()
                    if res_find:
                        prod_id = res_find[0]
                        store_id = res_find[1]
                        
                        if not store_id:
                            fallback_q = text('''
                                SELECT store_id FROM store_product 
                                WHERE product_id = :prod_id AND compcode = :ccode AND deleted IS NOT TRUE 
                                LIMIT 1
                            ''')
                            res_fallback = s.execute(fallback_q, {'prod_id': prod_id, 'ccode': item_ccode}).fetchone()
                            if res_fallback:
                                store_id = res_fallback[0]
                        
                        if prod_id and store_id:
                            # Increment store_product stock count
                            upd_store = text('''
                                UPDATE store_product 
                                SET product_count = COALESCE(product_count, 0) + :qty
                                WHERE product_id = :prod_id AND store_id = :store_id AND compcode = :ccode AND deleted IS NOT TRUE
                            ''')
                            s.execute(upd_store, {'qty': qty, 'prod_id': prod_id, 'store_id': store_id, 'ccode': item_ccode})
                    
                    # Decrement quantity_delivered on customer_purchase_items and reset status to 'Pending' if needed
                    upd_cpi = text('''
                        UPDATE customer_purchase_items 
                        SET 
                            quantity_delivered = COALESCE(quantity_delivered, 0.0) - :qty,
                            status = CASE 
                                WHEN quantity_ordered > (COALESCE(quantity_delivered, 0.0) - :qty) THEN 'Pending' 
                                ELSE status 
                            END  
                        WHERE items_id = :line_id
                    ''')
                    s.execute(upd_cpi, {'qty': qty, 'line_id': line_id})
                    
                    # Revert parent customer_purchase status back to 'Pending' if it was closed
                    upd_cp = text('''
                        UPDATE customer_purchase
                        SET status = 'Pending'
                        WHERE customer_purchase_id IN (
                            SELECT customer_purchase_id
                            FROM customer_purchase_items
                            WHERE items_id = :line_id
                        ) AND status = 'Closed'
                    ''')
                    s.execute(upd_cp, {'line_id': line_id})
                
                # 3. Soft delete delivery line items (This triggers public.update_product_count_on_delivery_items)
                upd_dli = text('''
                    UPDATE delivery_line_items
                    SET deleted = TRUE, deleted_at = :now
                    WHERE deliveryid = :deliveryid AND deleted IS NOT TRUE
                ''')
                s.execute(upd_dli, {'deliveryid': deliveryid, 'now': datetime.datetime.now()})
                
                # 4. Soft delete delivery
                upd_del = text('''
                    UPDATE delivery
                    SET deleted = TRUE, deleted_at = :now
                    WHERE deliveryid = :deliveryid
                ''')
                s.execute(upd_del, {'deliveryid': deliveryid, 'now': datetime.datetime.now()})

                # 5. Revert serialized items status and soft-delete mapping
                find_serials_q = text('''
                    SELECT serial_number FROM delivery_serialized_items
                    WHERE deliveryid = :deliveryid AND deleted IS NOT TRUE
                ''')
                mapped_serials = [row[0] for row in s.execute(find_serials_q, {'deliveryid': deliveryid}).fetchall()]
                
                if mapped_serials:
                    revert_ssp_q = text('''
                        UPDATE store_serialized_products
                        SET status = 'Available', updated_at = :now
                        WHERE serial_number IN :serials AND deleted IS NOT TRUE
                    ''')
                    s.execute(revert_ssp_q, {'serials': tuple(mapped_serials), 'now': datetime.datetime.now()})
                    
                    del_dsi_q = text('''
                        UPDATE delivery_serialized_items
                        SET deleted = TRUE, deleted_at = :now
                        WHERE deliveryid = :deliveryid AND deleted IS NOT TRUE
                    ''')
                    s.execute(del_dsi_q, {'deliveryid': deliveryid, 'now': datetime.datetime.now()})

        except Exception as e:
            error = str(e)
            db_client.session.rollback()
            db_client.session.flush()
            
        success = False if error else True
        return {
            "success": success,
            "error": error,
            "message": "Record deleted successfully" if success else "Deletion failed"
        }




### only for AM if you want to add in omniplus think for the multi level hierarchy bom based order
@delivery_api_route.route('/report')
class DeliverReport(Resource):

    @login_required()
    @delivery_api_route.doc(params=report_filter)
    @delivery_api_route.marshal_with(delivery_report_list)
    def get(self):

        current_user = request.args.get('current_user', {})
        compcode = current_user.get('company_id')
        # paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        # results_per_page = int(request.args.get('results_per_page')) if request.args.get(
        #     'results_per_page') else 20
        # offset = (paged - 1) * results_per_page
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page if (paged - 1) * results_per_page else 0

        customer_id = request.args.get('customer_id', None)
        customer_purchase_id = request.args.get('customer_purchase_id', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        product_id = request.args.get('product_id', None)
        sql_con = ''
        sql_con2 = ''
        if customer_id:
            sql_con += ' and COALESCE(cp.customer_id, d.customerid)=:customer_id '
        if customer_purchase_id:
            sql_con += ' and cp.customer_purchase_id=:customer_purchase_id '
        if start_date:
            sql_con += ' and d.delivery_date::date between :start_date '
            if end_date:
                sql_con += ' and :end_date '
            else:
                sql_con += ' and :start_date '

        if product_id:
            sql_con2 += ' and cte1.product_id=:product_id '

        query = text(f'''
        with cte as (
    select cpi.customer_purchase_id,oie.product_id,
    round(sum(case when asm.is_final_process is true or asm.activity_stage_map_id is null then el.outward_qty 
           else 0 end),2) as produced_qty 
           from customer_purchase_items cpi
    left join order_items_extract oie on oie.order_items_id = cpi.items_id
    left join plan_details pd on pd.order_extract_id = oie.extract_id
    left join production_plan pp on pp.production_plan_id = pd.production_plan_id
    JOIN (
        SELECT product_id, MAX(rank_id) AS max_rank_id
        FROM production_stages
        where deleted is not true and compcode =:compcode
        GROUP BY product_id
    ) ps_max ON ps_max.product_id = pp.product_id
    LEFT JOIN production_stages ps ON ps.product_id = pp.product_id AND ps.rank_id = ps_max.max_rank_id and ps.deleted is not true
    left join stage s on s.stage_id =ps.stage_id 
    LEFT JOIN plan_targets pt ON pt.production_plan_id = pp.production_plan_id 
    LEFT JOIN execution_log el ON el.target_id = pt.plan_target_id and el.stage_id=s.stage_id
    left join activity_stage_map asm on asm.production_stage_id =ps.id and asm.config_id=el.process_id
    where cpi.deleted is not true and cpi.compcode =:compcode
    group  by cpi.customer_purchase_id,oie.product_id
    ),
        cte1 as (
        select cp.customer_purchase_id,cp.order_unique,v.companyname,cp.expected_receiving_date,
        COALESCE(cp.customer_id, d.customerid) as customer_id,cp.status,cpi.product_id,p.product_name,
        p.product_code,p.sku_id,cpi.quantity_ordered,
        sum(dli.quantity) as quantity_delivered,
        coalesce(json_agg(
            json_build_object(
                'delivery_no',d.deliveryno,
                'delivery_date',d.delivery_date,
                'driver_name', d.driver_name,
                'driver_number', d.driver_number,
                'vechicle_number', d.vehicle_number,
                'delivered_quantity',dli.quantity,
                'production_lot_no', dli.production_lot_no,
                'rejected_qty', dli.rejected_quantity,
                'is_rejected', dli.is_rejected,
                'rejection_action', dli.rejection_action,
                'rejection_store_id', dli.rejection_store_id,
                'rejection_store_name', (select store_name from store_location where store_id = dli.rejection_store_id)
            )
        ) filter (where d.deliveryid is not null), '[]'::json) as data
         from customer_purchase as cp 
        left join customer_purchase_items as cpi on cpi.customer_purchase_id = cp.customer_purchase_id
        left join delivery_line_items as dli on dli."workOrderLineId" = cpi.items_id
        left join delivery as d on d.deliveryid = dli.deliveryid
        left join products as p on p.product_id = cpi.product_id
        left join vendor as v on v.vendorid = COALESCE(cp.customer_id, d.customerid)
        where cp.deleted is not true and cp.compcode =:compcode {sql_con}
        group by cp.customer_purchase_id,cp.order_unique,v.companyname,cp.expected_receiving_date,
        cp.customer_id,d.customerid,cp.status,cpi.product_id,p.product_name,p.product_code,p.sku_id,cpi.quantity_ordered
			)
			select cte1.customer_purchase_id,
			cte1.order_unique,cte1.companyname,
			cte1.expected_receiving_date,cte1.status,
			json_agg(
			json_build_object(
			    'product_id',cte1.product_id,
				'product_name', cte1.product_name,
				'product_code', cte1.product_code,
				'sku_id', cte1.sku_id,
				'quantity_ordered', cte1.quantity_ordered,
				'quantity_delivered',cte1.quantity_delivered,
                'quantity_produced', coalesce(cte.produced_qty,0),
				'delivery' , cte1.data
			)) as data,
			count(*) over() as total_results
			from cte1
			left join cte on cte.customer_purchase_id=cte1.customer_purchase_id and cte.product_id=cte1.product_id
			where 1=1 {sql_con2}
			group by cte1.customer_purchase_id,cte1.order_unique,cte1.companyname,cte1.expected_receiving_date,cte1.status
			order by cte1.customer_purchase_id desc
            limit :limit offset :offset
        ''')

        result = query_to_dict(db_client.engine.execute(query,
                                                        compcode=compcode,
                                                        limit=results_per_page,
                                                        offset=offset,
                                                        customer_id=customer_id,
                                                        customer_purchase_id=customer_purchase_id,
                                                        start_date=start_date,
                                                        end_date=end_date,
                                                        product_id=product_id
                                                        ))

        return {
            'total_results': result[0].get('total_results') if result else 0,
            'page': offset,
            'results_per_page': results_per_page,
            'results': result
        }