# DevOps Migration Guide: Stock Synchronization & Soft-Delete Trigger Fix

This guide outlines the database migration steps required to deploy the stock synchronization fixes and soft-delete trigger fixes to the production environment.

---

## 1. Database Schema Migration (Trigger Update)
The database trigger function `update_product_count_on_delivery_items` must be updated on the production PostgreSQL database to resolve a bug where soft-deleting a dispatch item decrements stock instead of incrementing it back.

Execute the following SQL DDL query on the production database:

```sql
CREATE OR REPLACE FUNCTION public.update_product_count_on_delivery_items()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Case 1: New delivery item is inserted
    IF TG_OP = 'INSERT' THEN
        -- If the item is marked as deleted, increase the product count
        IF NEW.deleted = TRUE THEN
            UPDATE products  
            SET product_count = product_count + NEW.quantity  
            FROM customer_purchase_items  
            WHERE products.product_id = customer_purchase_items.product_id  
            AND customer_purchase_items.items_id = NEW."workOrderLineId";
        -- Otherwise, decrease the product count
        ELSE
            UPDATE products  
            SET product_count = product_count - NEW.quantity  
            FROM customer_purchase_items  
            WHERE products.product_id = customer_purchase_items.product_id  
            AND customer_purchase_items.items_id = NEW."workOrderLineId";
        END IF;

    -- Case 2: Quantity is updated (adjust the difference)
    ELSIF TG_OP = 'UPDATE' AND NEW.quantity IS DISTINCT FROM OLD.quantity THEN
        UPDATE products  
        SET product_count = product_count + (NEW.quantity - OLD.quantity)  
        FROM customer_purchase_items  
        WHERE products.product_id = customer_purchase_items.product_id  
        AND customer_purchase_items.items_id = NEW."workOrderLineId"
        AND NEW.deleted = FALSE; -- Only affect active items

    -- Case 3: Marking as deleted (increase product_count back)
    ELSIF TG_OP = 'UPDATE' AND OLD.deleted = FALSE AND NEW.deleted = TRUE THEN
        UPDATE products  
        SET product_count = product_count + OLD.quantity  
        FROM customer_purchase_items  
        WHERE products.product_id = customer_purchase_items.product_id  
        AND customer_purchase_items.items_id = OLD."workOrderLineId";
    END IF;

    RETURN NEW;
END;
$function$;
```

---

## 2. Pre-Migration Audit (Check Discrepancy Counts by Tenant)
Before running the synchronization scripts, DevOps can execute these audit queries to identify the number of out-of-sync products across different tenants (`compcode`).

### Query 1: Total Count of Out-of-Sync Products Grouped by Tenant
This query displays the number of distinct products where the global stock in the `products` table does not match the sum of stock across all stores in `store_product`, grouped by tenant (`compcode`):

```sql
SELECT p.compcode AS tenant_id,
       COUNT(p.product_id) AS out_of_sync_product_count
FROM products p
LEFT JOIN (
    SELECT product_id, compcode, COALESCE(SUM(product_count), 0) AS store_sum_count
    FROM store_product
    WHERE deleted IS NOT TRUE
    GROUP BY product_id, compcode
) sp ON sp.product_id = p.product_id AND sp.compcode = p.compcode
WHERE p.deleted IS NOT TRUE
  AND p.product_count <> COALESCE(sp.store_sum_count, 0)
GROUP BY p.compcode
ORDER BY p.compcode;
```

### Query 2: Detailed List of Discrepancies for a Specific Tenant
To see the exact details of which products are out of sync for a specific tenant (e.g., tenant `186`), run the following:

```sql
SELECT p.product_id, 
       p.product_code, 
       p.product_name, 
       p.product_count AS global_count, 
       COALESCE(SUM(sp.product_count), 0) AS store_sum_count,
       ABS(p.product_count - COALESCE(SUM(sp.product_count), 0)) AS difference
FROM products p
LEFT JOIN store_product sp ON sp.product_id = p.product_id AND sp.deleted IS NOT TRUE
WHERE p.deleted IS NOT TRUE 
  AND p.compcode = 186 -- Filter by Tenant ID
GROUP BY p.product_id, p.product_code, p.product_name, p.product_count
HAVING p.product_count <> COALESCE(SUM(sp.product_count), 0)
ORDER BY difference DESC;
```

---

## 3. Inventory / Stock Synchronization
If the production environment has drifted stock levels between the `products` table and `store_product` table due to previous dispatches, run the synchronization logic to bring them into alignment.

### Single-Store Products Sync
For products linked to only one store row, set the `store_product` stock to match the `products` global stock:

```sql
UPDATE store_product sp
SET product_count = p.product_count
FROM products p
WHERE sp.product_id = p.product_id
  AND sp.deleted IS NOT TRUE
  AND p.deleted IS NOT TRUE
  AND p.product_id IN (
      SELECT product_id 
      FROM store_product 
      WHERE deleted IS NOT TRUE 
      GROUP BY product_id 
      HAVING COUNT(*) = 1
  );
```

### Multi-Store Products Sync (Proportional Scaling)
For products distributed across multiple stores, scale their store counts proportionally to match the global product count:

```sql
WITH store_sums AS (
    SELECT product_id, SUM(product_count) as total_store_count
    FROM store_product
    WHERE deleted IS NOT TRUE
    GROUP BY product_id
),
scaled_counts AS (
    SELECT sp.store_product_id, 
           ROUND(sp.product_count * (p.product_count / NULLIF(ss.total_store_count, 0))) as new_count
    FROM store_product sp
    JOIN products p ON p.product_id = sp.product_id
    JOIN store_sums ss ON ss.product_id = sp.product_id
    WHERE sp.deleted IS NOT TRUE 
      AND p.deleted IS NOT TRUE 
      AND ss.total_store_count > 0
      AND p.product_count <> ss.total_store_count
)
UPDATE store_product sp
SET product_count = sc.new_count
FROM scaled_counts sc
WHERE sp.store_product_id = sc.store_product_id;
```

---

## 4. Backend Deployment
Deploy the updated code in `delivery/app/api/dc.py` containing:
1. The removal of manual `products` stock decrement on delivery creation (since the database trigger handles it).
2. The refactored `delete()` endpoint which soft-deletes both the dispatch and line items and restores stock.
