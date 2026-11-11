import datetime
from logging import error

from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text, bindparam, NUMERIC, Integer, String, update
from sqlalchemy.exc import SQLAlchemyError

# from invregistry.app.api.invregistry import query
from .. import db_client


def update_purchase_order(oper='+'):
    quantity_delivered_calculations = f'''COALESCE(quantity_delivered, 0.0) {oper} COALESCE(:non_damaged_quantity, 0.0)'''

    # Returning the SQL query with correct syntax
    return text(f'''
        UPDATE joline_items 
        SET quantity_delivered = {quantity_delivered_calculations},
            status = (
                CASE 
                    WHEN quantity_ordered > {quantity_delivered_calculations} THEN 'Partial'
                    WHEN {quantity_delivered_calculations} = 0 THEN status
                    ELSE 'Completed'
                END
            )
        WHERE id = :purchase_items_id 
    ''').bindparams(
            non_damaged_quantity=bindparam('non_damaged_quantity', type_=NUMERIC),
            purchase_items_id=bindparam('purchase_items_id', type_=Integer),
            # action=bindparam('action',type_=String),
            # status=bindparam('status', type_=String)
        )
def delete_func(model, condition, pkey=None, fkey='', reason='GRN Reversal', user_info=None):
    error = ''
    username = (user_info or {}).get('username') or 'System'
    now = datetime.datetime.now()
    try:
        with db_client.session.begin():
            stmt = (
                update(model)
                .where(condition)  # Filter by GRNotes_id
                .values(
                    deleted=True, 
                    deleted_at=now,
                    grn_reason=reason,
                    modified_by=username,
                    modified_on=now
                )  # Set 'deleted', 'deleted_at', and audit values
                .returning(model.grn_no, model.is_moved, model.compcode)  # Return key attributes
            )
            result = db_client.session.execute(stmt)
            grn_row = result.fetchone()

            # Soft delete child grnlineitems
            if pkey:
                db_client.session.execute(text('''
                    UPDATE grnlineitems 
                    SET deleted = true, deleted_at = :now, modified_by = :modified_by, modified_on = :now
                    WHERE grnotesid = :grnotesid AND deleted IS NOT TRUE
                '''), {'grnotesid': pkey, 'now': now, 'modified_by': username})
            elif fkey:
                db_client.session.execute(text('''
                    UPDATE grnlineitems 
                    SET deleted = true, deleted_at = :now, modified_by = :modified_by, modified_on = :now
                    WHERE grnlineid = :grnlineid AND deleted IS NOT TRUE
                '''), {'grnlineid': fkey, 'now': now, 'modified_by': username})

            sql_con = ''
            params = {}
            if pkey:
                sql_con = 'and grnotesid=:grnotesid '
                params['grnotesid'] = pkey
            if fkey:
                sql_con = 'and grnlineid=:grnlineid '
                params['grnlineid'] = fkey
            sql_query = text(f'''
            select * from grnlineitems 
            where 1=1 {sql_con}
            ''')
            db_res = db_client.session.execute(sql_query, params)
            sql_query = []
            for row in db_res:
                if row is not None:
                    if hasattr(row, '_mapping'):
                        sql_query.append(dict(row._mapping))
                    elif hasattr(row, 'keys'):
                        sql_query.append({key: getattr(row, key) for key in row.keys()})
                    else:
                        sql_query.append(dict(row))

            if grn_row:
                grn_no, is_moved, compcode = grn_row

                for item in sql_query:
                    product_id = item.get('product_id')
                    if not product_id:
                        continue

                    qty_to_reverse = float(item.get('non_damaged_quantity') or item.get('received_quantity') or 0.0)

                    # 1. Check BOM
                    bom_check = db_client.session.execute(text('''
                        select 1 from bom where product_id = :product_id and deleted is not true limit 1
                    '''), {"product_id": product_id}).fetchone()
                    if bom_check:
                        raise Exception(f"Product ID {product_id} has a BOM configured and cannot be reversed.")

                    # 2. Check Allocation
                    product_stock = db_client.session.execute(text('''
                        select product_count, allocated_quantity from products where product_id = :product_id and deleted is not true limit 1
                    '''), {"product_id": product_id}).fetchone()
                    if product_stock:
                        product_count = float(product_stock[0] or 0.0)
                        allocated_qty = float(product_stock[1] or 0.0)
                        available_qty = product_count - allocated_qty
                        if available_qty < qty_to_reverse:
                            raise Exception(f"Product ID {product_id} has active allocations and insufficient available stock (Available: {available_qty}, Required: {qty_to_reverse}) to reverse.")

                    # 3. Check and Deduct Store Stock
                    if is_moved and qty_to_reverse > 0:
                        # Find store_id from invregistry inward log
                        registry_log = db_client.session.execute(text('''
                            select store_id from invregistry 
                            where ref_id = :ref_id and product_id = :product_id and action = 'Inward' and deleted is not true limit 1
                        '''), {"ref_id": grn_no, "product_id": product_id}).fetchone()

                        if not registry_log:
                            # Fallback to the first store containing product stock
                            store_product_check = db_client.session.execute(text('''
                                select store_id, product_count from store_product 
                                where product_id = :product_id and compcode = :compcode and deleted is not true limit 1
                            '''), {"product_id": product_id, "compcode": compcode}).fetchone()
                            if store_product_check:
                                store_id = store_product_check[0]
                                store_count = float(store_product_check[1] or 0.0)
                            else:
                                raise Exception(f"No inventory registry or store record found for product ID {product_id}.")
                        else:
                            store_id = registry_log[0]
                            store_stock = db_client.session.execute(text('''
                                select product_count from store_product 
                                where store_id = :store_id and product_id = :product_id and deleted is not true limit 1
                            '''), {"store_id": store_id, "product_id": product_id}).fetchone()
                            store_count = float(store_stock[0] or 0.0) if store_stock else 0.0

                        if store_count < qty_to_reverse:
                            raise Exception(f"Insufficient stock in store (Available: {store_count}, Required: {qty_to_reverse}) to reverse.")

                        # Deduct store stock
                        db_client.session.execute(text('''
                            update store_product set product_count = product_count - :qty 
                            where store_id = :store_id and product_id = :product_id
                        '''), {"qty": qty_to_reverse, "store_id": store_id, "product_id": product_id})

                        # Deduct global stock
                        db_client.session.execute(text('''
                            update products set product_count = product_count - :qty 
                            where product_id = :product_id
                        '''), {"qty": qty_to_reverse, "product_id": product_id})

                        # Mark registry entries deleted with reversal audit details
                        reversal_reason_note = f"GRN Reversed: {reason}" if reason else "GRN Reversed"
                        db_client.session.execute(text('''
                            update invregistry 
                            set deleted = true, 
                                deleted_at = :now,
                                reason = :reason,
                                modified_by = :modified_by,
                                modified_on = :now
                            where ref_id = :ref_id and product_id = :product_id and action = 'Inward'
                        '''), {
                            "ref_id": grn_no, 
                            "product_id": product_id,
                            "reason": reversal_reason_note,
                            "modified_by": username,
                            "now": now
                        })

            db_client.session.execute(update_purchase_order('-'), sql_query)
    except Exception as e:
        error = str(e)
        db_client.session.rollback()
    return {
        'success': False if error else True,
        'error': error,
    }
