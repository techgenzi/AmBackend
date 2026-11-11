from sqlalchemy import text, bindparam, Boolean,Integer,NUMERIC

# --    --and COALESCE(:is_drafted,false) is true and COALESCE(:deleted,false) is not true
def order_over_all_updated():
    return text('''
    UPDATE customer_purchase
SET status = 'Closed'
WHERE customer_purchase_id IN (
    SELECT customer_purchase_id
    FROM customer_purchase_items
    WHERE customer_purchase_id IN (
        SELECT customer_purchase_id
        FROM customer_purchase_items
        WHERE items_id in :ids and deleted is not true
    ) and deleted is not true
    GROUP BY customer_purchase_id
    HAVING COUNT(*) = SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END)
);
    ''')
def customer_order_update(oper='+'):
    return text(f'''
    UPDATE customer_purchase_items 
SET 
    quantity_delivered = COALESCE(quantity_delivered, 0.0) {oper} :quantity,
    status = CASE 
        WHEN quantity_ordered<=COALESCE(quantity_delivered,0.0) + CAST(:quantity AS numeric) THEN 'Closed' 
        ELSE status 
    END  
WHERE items_id = :workOrderLineId;

    ''').bindparams(
                    workOrderLineId=bindparam('workOrderLineId', type_=Integer),
                    # is_drafted=bindparam('is_drafted', type_=Boolean),
        # deleted=bindparam('deleted', type_=Boolean),
        quantity=bindparam('quantity',type_=NUMERIC)
                )
def inventory_update(oper='-'):
    return text(f'''
    update sku_manage set prod_count = prod_count {oper} :prod_count 
where sku_id =:product_id
    ''').bindparams(
                    prod_count=bindparam('prod_count', type_=NUMERIC),
                    product_id=bindparam('product_id', type_=Integer)
                )
