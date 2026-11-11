import datetime

from flask import request
from sqlalchemy import func, and_, text

from .errorhandling import map_sqlalchemy_error_to_http_status, get_current_user
from .. import db_client,ipss_db
from ..models.planning import ProdPlans, PlanDetails, PlanTargets, InvRegistry, ProductionPlanProducts
from .helper import add_cc,updated_extract_order,update_record
def post_helper(values=[]):
    error = ''
    plan_unique = None
    for data in values:
        targets = data.pop('targets', [])+data.pop('hourly_target',[])
        details = data.pop('details', [])
        products = data.pop('products', [])
        compcode = request.args.get('current_user', {})
        funCall = True if data.get('status') == 'Approved' and data.get('is_done',False) == False else False
        total_count = db_client.session.query(func.count(ProdPlans.production_plan_id)) \
                          .filter(and_(
                                       ProdPlans.compcode == compcode.get('company_id'))) \
                          .scalar() + 1
        db_client.session.close()
        data['plan_unique']='PLN-'+ str(total_count).zfill(6)
        data['compcode'] = compcode.get('company_id')
        data['created_on'] = datetime.datetime.now()
        plan_unique = data['plan_unique']
        
        valid_keys = [c.name for c in ProdPlans.__table__.columns]
        insert_data = {k: v for k, v in data.items() if k in valid_keys}
        
        try:
            with db_client.session.begin():

                result = ipss_db.insert_record(model=ProdPlans, values=insert_data, commit=False)
                pkey = result.get('primary_key_id')[0] if result.get('success') else None
                if not pkey:
                    db_client.session.rollback()
                    return result
                targets = add_cc(targets, pkey='production_plan_id', p_value=pkey)
                details = add_cc(details, pkey='production_plan_id', p_value=pkey)
                products = add_cc(products, pkey='production_plan_id', p_value=pkey)
                if targets:
                    db_client.session.bulk_insert_mappings(mapper=PlanTargets, mappings=targets)

                if details:
                    db_client.session.bulk_insert_mappings(mappings=details, mapper=PlanDetails)
                    if funCall:
                        db_client.engine.execute(updated_extract_order(), details)
                if products:
                    db_client.session.bulk_insert_mappings(mapper=ProductionPlanProducts, mappings=products)

        except Exception as e:
            error = str(e)
            db_client.session.rollback()
            return {
                'success': False,
                'message': "There is an Error",
                'error': error,
            }
        # success = False if error else True
        # if success:
        #     message = "Records created Successfully"
        # else:
        #     message = "There is an Error"
    return {
        'success': True,
        'message': "Records created Successfully",
        'error': error,
        'production_plan_id': pkey,
        'plan_unique': plan_unique
    }
def update_model(values=[]):
    error = ''
    for data in values:
        pkey = data.pop('production_plan_id', None)
        funCall = True if data.get('status') == 'Approved' and data.get('is_done',False) == False else False
        targets = data.pop('targets', [])+data.pop('hourly_target',[])
        details = data.pop('details', [])
        products = data.pop('products', [])
        error = ''
        
        valid_keys = [c.name for c in ProdPlans.__table__.columns]
        update_data = {k: v for k, v in data.items() if k in valid_keys}
        is_rejected = update_data.get('status') == 'Rejected'
        if is_rejected:
            update_data['is_done'] = True
            if not update_data.get('execution_end_date'):
                update_data['execution_end_date'] = datetime.datetime.now()
        
        try:
            with db_client.session.begin():
                result = update_record(model=ProdPlans, values=update_data, condition=ProdPlans.production_plan_id == pkey)
                # pkey = result.get('primary_key_id')[0] if result.get('success') else None
                # print(result, "result")
                status_code = 200

                if isinstance(result, tuple):
                    result, status_code = result
                if not result.get('success'):
                    db_client.session.rollback()
                    return result, status_code

                if is_rejected and pkey:
                    # Release any reserved raw material allocations for this rejected plan
                    db_client.session.execute(text('''
                        UPDATE products p
                        SET allocated_quantity = GREATEST(0, COALESCE(p.allocated_quantity::numeric, 0) - sub.leftover)
                        FROM (
                            SELECT product_id, SUM(allocated_amount) as leftover
                            FROM plan_allocation
                            WHERE prod_plan_id = :production_plan_id
                              AND deleted IS NOT TRUE
                            GROUP BY product_id
                        ) sub
                        WHERE p.product_id = sub.product_id;
                    '''), {'production_plan_id': pkey})
                    db_client.session.execute(
                        text('DELETE FROM plan_allocation WHERE prod_plan_id = :production_plan_id'),
                        {'production_plan_id': pkey}
                    )
                targets = add_cc(targets, pkey='production_plan_id', p_value=pkey)
                details = add_cc(details, pkey='production_plan_id', p_value=pkey)
                
                # Update production plan products mapping
                if products:
                    db_client.session.execute(
                        text('UPDATE production_plan_products SET deleted=true WHERE production_plan_id=:plan_id'),
                        {'plan_id': pkey}
                    )
                    products = add_cc(products, pkey='production_plan_id', p_value=pkey)
                    db_client.session.bulk_insert_mappings(mapper=ProductionPlanProducts, mappings=products)

                # target_post_data = [i for i in targets if not i.get('plan_target_id')]
                # details_post_data = [i for i in details if not i.get('plan_details_id')]
                target_post_data = [targets.pop(i) for i in range(len(targets) - 1, -1, -1) if
                                    not targets[i].get('plan_target_id',None)]
                details_post_data = [details.pop(i) for i in range(len(details) - 1, -1, -1) if
                                    not details[i].get('plan_details_id',None)]
                if targets:
                    db_client.session.bulk_update_mappings(mapper=PlanTargets, mappings=targets)
                if target_post_data:
                    db_client.session.bulk_insert_mappings(mappings=target_post_data, mapper=PlanTargets)
                if details_post_data:
                    db_client.session.bulk_insert_mappings(mappings=details_post_data, mapper=PlanDetails)
                    if not is_rejected:
                        db_client.session.execute(updated_extract_order(), details_post_data)
                if details:
                    db_client.session.bulk_update_mappings(mappings=details, mapper=PlanDetails)
                    if not is_rejected:
                        db_client.session.execute(updated_extract_order(), details)

                if is_rejected and pkey:
                    # Recalculate order_items_extract.quantity_planned excluding rejected/deleted plans
                    db_client.session.execute(text('''
                        UPDATE order_items_extract oie
                        SET quantity_planned = COALESCE((
                            SELECT SUM(pd.plan_quantity)
                            FROM plan_details pd
                            JOIN production_plan pp ON pp.production_plan_id = pd.production_plan_id
                            WHERE pd.order_extract_id = oie.extract_id
                              AND pd.deleted IS NOT TRUE
                              AND pp.deleted IS NOT TRUE
                              AND COALESCE(pp.status, '') <> 'Rejected'
                        ), 0)
                        WHERE oie.extract_id IN (
                            SELECT DISTINCT pd2.order_extract_id
                            FROM plan_details pd2
                            WHERE pd2.production_plan_id = :plan_id
                        )
                    '''), {'plan_id': pkey})

        except Exception as e:
            error = str(e)
            db_client.session.rollback()
            return {
                'success': False,
                'message': "There is an Error",
                'error': error,
            }
        # success = False if error else True
        # if success:
        #     message = "Records created Successfully"
        # else:
        #     message = "There is an Error"
    return {
        'success': True,
        'message': "Records created Successfully",
        'error': error,
    }


def close_internal_orders_for_plan(production_plan_id, s=db_client.session):
    orders = s.execute(text('''
        SELECT DISTINCT cp.customer_purchase_id
        FROM production_plan pp
        JOIN plan_details pd ON pd.production_plan_id = pp.production_plan_id
        JOIN order_items_extract oie ON oie.extract_id = pd.order_extract_id
        JOIN customer_purchase_items cpi ON cpi.items_id = oie.order_items_id
        JOIN customer_purchase cp ON cp.customer_purchase_id = cpi.customer_purchase_id
        WHERE pp.production_plan_id = :production_plan_id
          AND cp.order_type = 'Internal'
          AND cp.status = 'Pending'
    '''), {'production_plan_id': production_plan_id}).fetchall()

    for row in orders:
        cp_id = row[0]
        items = s.execute(text('''
            SELECT 
                cpi.items_id,
                cpi.quantity_ordered,
                COALESCE(SUM(pp.moved_quantity), 0) AS total_moved
            FROM customer_purchase_items cpi
            LEFT JOIN order_items_extract oie ON oie.order_items_id = cpi.items_id
            LEFT JOIN plan_details pd ON pd.order_extract_id = oie.extract_id
            LEFT JOIN production_plan pp ON pp.production_plan_id = pd.production_plan_id AND pp.deleted IS NOT TRUE
            WHERE cpi.customer_purchase_id = :customer_purchase_id
              AND cpi.deleted IS NOT TRUE
            GROUP BY cpi.items_id, cpi.quantity_ordered
        '''), {'customer_purchase_id': cp_id}).fetchall()

        all_closed = True
        for item in items:
            items_id, qty_ordered, total_moved = item
            if total_moved >= qty_ordered:
                s.execute(text('''
                    UPDATE customer_purchase_items
                    SET status = 'Closed', quantity_produced = :total_moved
                    WHERE items_id = :items_id
                '''), {'items_id': items_id, 'total_moved': total_moved})
            else:
                all_closed = False

        if all_closed and items:
            s.execute(text('''
                UPDATE customer_purchase
                SET status = 'Closed'
                WHERE customer_purchase_id = :customer_purchase_id
            '''), {'customer_purchase_id': cp_id})


def update_quantity(values, production_plan_id, s=db_client.session, commit=True):

    if not s:
        s = db_client.session
    con_list = []
    moved_quantity = values.get('moved_quantity')
    moved_date = values.get('moved_date') or datetime.datetime.now()
    execution_end_date = values.get('execution_end_date')
    store_id = values.get('store_id')
    product_id = values.get('product_id')
    lot_no = values.get('production_lot_no') or values.get('lot_no') or None
    
    if not product_id:
        res = s.execute(text('select product_id from production_plan where production_plan_id = :production_plan_id'),
                        {'production_plan_id': production_plan_id}).fetchone()
        product_id = res[0] if res else None

    if not product_id and moved_quantity:
        ppp_res = s.execute(text('select product_id from production_plan_products where production_plan_id = :production_plan_id and deleted is not true'),
                            {'production_plan_id': production_plan_id}).fetchall()
        if len(ppp_res) == 1:
            product_id = ppp_res[0][0]

    params = {'production_plan_id': production_plan_id}
    if values.get('is_done'):
        con_list.append('is_done = True')
    if moved_quantity:
        con_list.append('moved_quantity = Coalesce(moved_quantity, 0) + :moved_quantity')
        con_list.append('moved_date = :moved_date')
        params['moved_quantity'] = moved_quantity
        params['moved_date'] = moved_date
    if execution_end_date:
        con_list.append('execution_end_date = :execution_end_date')
        params['execution_end_date'] = execution_end_date
    if not con_list:
        return {
            'success': True,
            'message': 'Nothing to update'
        }

    try:
        if moved_quantity:
            if not product_id:
                return {
                    'success': False,
                    'message': 'product_id is required to move stock to warehouse'
                }, 400

            query1 = text('''       
                    WITH updated AS (
            -- Step 1: Get product_id and update the product_count
            UPDATE products
            SET product_count = COALESCE(product_count, 0) + :moved_quantity
            WHERE product_id = :product_id
            RETURNING product_id, compcode-- Capture the product_id updated
        )
        -- Step 2: Insert into invregistry using returned product_id
        INSERT INTO invregistry (action, prod_plan_id, manual_count, created_by, created_on, product_id, compcode, store_id, sub_location, lot_no)
        SELECT 
            'plan_stock_addition',
            :production_plan_id,
            :moved_quantity,
            :created_by,
            :created_on,
            product_id, -- Captured from CTE
            compcode,
            :store_id,
            :sub_location,
            :lot_no
        FROM updated;
            ''')

            check_store = text('''
                SELECT EXISTS (
                    SELECT 1 FROM store_product 
                    WHERE product_id = :product_id AND store_id = :store_id AND COALESCE(sub_location, '') = COALESCE(:sub_location, '') AND COALESCE(lot_no, '') = COALESCE(:lot_no, '') AND deleted IS NOT TRUE
                )
            ''')
            exists = s.execute(check_store, {'product_id': product_id, 'store_id': store_id, 'sub_location': values.get('sub_location'), 'lot_no': lot_no}).scalar()

            if exists:
                query2 = text('''
                    UPDATE store_product 
                    SET product_count = COALESCE(product_count, 0) + :moved_quantity,
                        modified_by = :created_by,
                        modified_on = :created_on
                    WHERE product_id = :product_id AND store_id = :store_id AND COALESCE(sub_location, '') = COALESCE(:sub_location, '') AND COALESCE(lot_no, '') = COALESCE(:lot_no, '') AND deleted IS NOT TRUE
                ''')
            else:
                query2 = text('''
                    INSERT INTO store_product (store_id, product_id, sub_location, lot_no, product_count, compcode, created_by, created_on, deleted)
                    VALUES (:store_id, :product_id, :sub_location, :lot_no, :moved_quantity,
                    (SELECT compcode FROM production_plan WHERE production_plan_id = :production_plan_id), :created_by, :created_on, FALSE)
                ''')

            s.execute(query1, {'production_plan_id': production_plan_id,
                               'moved_quantity': moved_quantity,
                               'product_id': product_id,
                               'store_id': store_id,
                               'sub_location': values.get('sub_location'),
                               'lot_no': lot_no,
                               'created_by': get_current_user(),
                               'created_on': datetime.datetime.now()
                               })
          #   store_update = text(f'''
          #                                       INSERT INTO store_product (product_id, store_id, product_count,compcode)
          #                       VALUES (:product_id, :store_id, :product_count,:compcode)
          #                       ON CONFLICT (product_id, store_id)
          #                       DO UPDATE SET product_count = COALESCE(store_product.product_count, 0) + EXCLUDED.product_count;
          #           ''')
          #   print("dfdsvsd",values)
          #   compcode = request.args.get('current_user', {})
          #   s.execute(store_update,{**values,**{"compcode": compcode.get('company_id'),
          # "created_on": datetime.datetime.now(),
          #                                       'product_count':values.get('moved_quantity')
          # }})

            s.execute(query2, {'production_plan_id': production_plan_id,
                               'store_id': store_id,
                               'product_id': product_id,
                               'sub_location': values.get('sub_location'),
                               'lot_no': lot_no,
                               'moved_quantity': moved_quantity,
                               'created_by': get_current_user(),
                               'created_on': datetime.datetime.now()
                                 })
            
            # Update moved_quantity and moved_date in production_plan_products mapping for multi-product plans
            s.execute(text('''
                UPDATE production_plan_products 
                SET moved_quantity = COALESCE(moved_quantity, 0) + :moved_quantity,
                    moved_date = :moved_date
                WHERE production_plan_id = :production_plan_id AND product_id = :product_id AND deleted IS NOT TRUE
            '''), {
                'production_plan_id': production_plan_id,
                'product_id': product_id,
                'moved_quantity': moved_quantity,
                'moved_date': moved_date
            })

        # Update production_plan table (only update production_plan.moved_quantity if NOT a multi-product plan)
        plan_is_multi = s.execute(text('SELECT is_multi_product FROM production_plan WHERE production_plan_id = :production_plan_id'),
                                  {'production_plan_id': production_plan_id}).fetchone()
        if plan_is_multi and plan_is_multi[0] is True and 'moved_quantity' in params:
            # For multi-product plan, remove moved_quantity from main production_plan update query, but retain moved_date
            con_filtered = [c for c in con_list if not c.startswith('moved_quantity')]
            if con_filtered:
                query_str = ', '.join(con_filtered)
                s.execute(text(f'UPDATE production_plan SET {query_str} WHERE production_plan_id=:production_plan_id'),
                          {k: v for k, v in params.items() if k != 'moved_quantity'})
        else:
            query_str = ', '.join(con_list)
            s.execute(text(f'UPDATE production_plan SET {query_str} WHERE production_plan_id=:production_plan_id'), params)

        if moved_quantity:
            close_internal_orders_for_plan(production_plan_id, s)
        if commit:
            s.commit()

    except Exception as e:
        s.rollback()
        s.flush()
        return map_sqlalchemy_error_to_http_status(e)

    return {
        'success': True,
        'message': 'Update Successfully'
    }


def revert_stock(values, production_plan_id, s=db_client.session, commit=True):
    if not s:
        s = db_client.session
    revert_qty = values.get('revert_quantity')
    store_id = values.get('store_id')
    product_id = values.get('product_id')
    lot_no = values.get('production_lot_no') or values.get('lot_no') or None

    if not product_id:
        res = s.execute(text('select product_id from production_plan where production_plan_id = :production_plan_id'),
                        {'production_plan_id': production_plan_id}).fetchone()
        product_id = res[0] if res else None

    if not product_id and revert_qty:
        ppp_res = s.execute(text('select product_id from production_plan_products where production_plan_id = :production_plan_id and deleted is not true'),
                            {'production_plan_id': production_plan_id}).fetchall()
        if len(ppp_res) == 1:
            product_id = ppp_res[0][0]

    if not product_id or not revert_qty or float(revert_qty) <= 0:
        return {'success': False, 'message': 'Product ID and valid Revert Quantity are required'}

    is_no_store = (store_id in (None, "", "NO_STORE", 0))
    revert_qty = float(revert_qty)
    user_name = get_current_user()
    now = datetime.datetime.now()

    try:
        if not is_no_store:
            # 1. Deduct from products table
            s.execute(text('''
                UPDATE products
                SET product_count = GREATEST(0, COALESCE(product_count, 0) - :revert_qty)
                WHERE product_id = :product_id
            '''), {'product_id': product_id, 'revert_qty': revert_qty})

            # 2. Insert audit log into invregistry
            s.execute(text('''
                INSERT INTO invregistry (action, prod_plan_id, manual_count, created_by, created_on, product_id, compcode, store_id, sub_location, lot_no)
                SELECT 'plan_stock_reversal', :production_plan_id, :revert_qty, :created_by, :created_on, :product_id, compcode, :store_id, :sub_location, :lot_no
                FROM production_plan WHERE production_plan_id = :production_plan_id
            '''), {'production_plan_id': production_plan_id, 'revert_qty': revert_qty, 'created_by': user_name, 'created_on': now, 'product_id': product_id, 'store_id': store_id, 'sub_location': values.get('sub_location'), 'lot_no': lot_no})

            # 3. Deduct from store_product table
            s.execute(text('''
                UPDATE store_product
                SET product_count = GREATEST(0, COALESCE(product_count, 0) - :revert_qty),
                    modified_by = :created_by,
                    modified_on = :created_on
                WHERE store_id = :store_id AND product_id = :product_id AND COALESCE(sub_location, '') = COALESCE(:sub_location, '') AND COALESCE(lot_no, '') = COALESCE(:lot_no, '') AND deleted IS NOT TRUE
            '''), {'store_id': store_id, 'product_id': product_id, 'sub_location': values.get('sub_location'), 'lot_no': lot_no, 'revert_qty': revert_qty, 'created_by': user_name, 'created_on': now})
        else:
            # Insert audit log for plan-only adjustment
            s.execute(text('''
                INSERT INTO invregistry (action, prod_plan_id, manual_count, created_by, created_on, product_id, compcode, lot_no)
                SELECT 'plan_stock_reversal_plan_only', :production_plan_id, :revert_qty, :created_by, :created_on, :product_id, compcode, :lot_no
                FROM production_plan WHERE production_plan_id = :production_plan_id
            '''), {'production_plan_id': production_plan_id, 'revert_qty': revert_qty, 'created_by': user_name, 'created_on': now, 'product_id': product_id, 'lot_no': lot_no})

        # Deduct from production_plan_products (if multi-product)
        s.execute(text('''
            UPDATE production_plan_products 
            SET moved_quantity = GREATEST(0, COALESCE(moved_quantity, 0) - :revert_qty)
            WHERE production_plan_id = :production_plan_id AND product_id = :product_id AND deleted IS NOT TRUE
        '''), {'production_plan_id': production_plan_id, 'product_id': product_id, 'revert_qty': revert_qty})

        # Deduct from main production_plan table
        s.execute(text('''
            UPDATE production_plan
            SET moved_quantity = GREATEST(0, COALESCE(moved_quantity, 0) - :revert_qty)
            WHERE production_plan_id = :production_plan_id
        '''), {'production_plan_id': production_plan_id, 'revert_qty': revert_qty})

        if commit:
            s.commit()
    except Exception as e:
        s.rollback()
        return map_sqlalchemy_error_to_http_status(e)

    return {'success': True, 'message': 'Inventory reverted successfully'}

