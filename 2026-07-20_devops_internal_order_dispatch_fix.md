# DevOps Instruction Manual: Internal Order Dispatch Fix & Schema Migration
**Date:** 2026-07-20

This manual outlines the steps required to audit the existing internal order dispatch data, apply the database schema migrations for Option A (introducing `quantity_produced`), and update the backend services.

---

## 1. Data Audit Phase
Before applying the migration, run these audit queries to identify discrepancies between the stored quantities (`quantity_delivered` which currently represents inwarded/produced stock) and actual customer dispatches.

### Query A: Dispatched Quantity Audit
Run this query to view all active internal orders, their ordered quantities, the current `quantity_delivered` (which tracks inwarded stock), and the actual customer dispatches tracked in the delivery system:

```sql
SELECT 
    cp.customer_purchase_id,
    cp.order_unique,
    cp.status AS order_status,
    cpi.items_id,
    cpi.product_id,
    cpi.quantity_ordered,
    cpi.quantity_delivered AS current_quantity_delivered_stored,
    COALESCE(SUM(dli.quantity), 0) AS actual_dispatched_qty
FROM customer_purchase cp
JOIN customer_purchase_items cpi 
  ON cpi.customer_purchase_id = cp.customer_purchase_id
LEFT JOIN delivery_line_items dli 
  ON dli."workOrderLineId" = cpi.items_id 
 AND dli.deleted IS NOT TRUE
WHERE cp.order_type = 'Internal'
  AND cp.deleted IS NOT TRUE
  AND cpi.deleted IS NOT TRUE
GROUP BY 
    cp.customer_purchase_id, 
    cp.order_unique, 
    cp.status, 
    cpi.items_id, 
    cpi.product_id, 
    cpi.quantity_ordered, 
    cpi.quantity_delivered
ORDER BY cp.customer_purchase_id DESC;
```

---

## 2. Database Migration Phase
Run the following SQL statements on the production database (`ipss_db`) to introduce the new column and migrate existing data.

### Step 1: Schema Update (DDL)
Add the `quantity_produced` column to the `customer_purchase_items` table.
```sql
ALTER TABLE customer_purchase_items 
ADD COLUMN IF NOT EXISTS quantity_produced NUMERIC DEFAULT 0;
```

### Step 2: Data Migration (DML)
1. **Copy stored/produced quantities into the new column**:
   For all existing internal orders, copy the value from `quantity_delivered` (which represented store inwarding/produced stock) to `quantity_produced`.
   ```sql
   UPDATE customer_purchase_items cpi
   SET quantity_produced = COALESCE(cpi.quantity_delivered, 0)
   FROM customer_purchase cp
   WHERE cp.customer_purchase_id = cpi.customer_purchase_id
     AND cp.order_type = 'Internal';
   ```

2. **Recompute actual customer delivery numbers**:
   Update `quantity_delivered` to reflect only the sum of quantities actually dispatched via the delivery line items.
   ```sql
   UPDATE customer_purchase_items cpi
   SET quantity_delivered = COALESCE(
       (SELECT SUM(dli.quantity)
        FROM delivery_line_items dli
        WHERE dli."workOrderLineId" = cpi.items_id
          AND dli.deleted IS NOT TRUE), 0
   )
   FROM customer_purchase cp
   WHERE cp.customer_purchase_id = cpi.customer_purchase_id
     AND cp.order_type = 'Internal';
   ```

---

## 3. Code Modifications

### A. Production Plans Microservice (Backend)
Modify [post_module.py](file:///Users/rajkumarmuthuramalingam/Work/AmNonOvens/production_plans/app/api/post_module.py#L158-L161) inside the `close_internal_orders_for_plan` function:

```diff
        for item in items:
            items_id, qty_ordered, total_moved = item
            if total_moved >= qty_ordered:
                s.execute(text('''
                    UPDATE customer_purchase_items
-                   SET status = 'Closed', quantity_delivered = :total_moved
+                   SET status = 'Closed', quantity_produced = :total_moved
                    WHERE items_id = :items_id
                '''), {'items_id': items_id, 'total_moved': total_moved})
```

---

## 4. Verification Plan
* **Production Inwarding**: Ensure that moving finished goods to the store increments `quantity_produced` and closes the internal order.
* **Dispatch Panel**: Open the dispatch panel. The completed/closed internal orders should now show up with `Yet to Dispatch = quantity_ordered - quantity_delivered` showing the correct non-zero pending amounts.
