# DevOps Migration Guide: Stock Synchronization & Soft-Delete Trigger Fix

This guide outlines the database migration steps required to deploy the stock synchronization fixes and soft-delete trigger fixes to the production database environment.

---

## 1. Database Schema Migration (Trigger Update)
The database trigger function `update_product_count_on_delivery_items` must be updated on the production PostgreSQL database to resolve a bug where soft-deleting a dispatch item decrements stock instead of incrementing it back. This updated trigger is tenant-aware, ensuring that if a tenant has disabled stock management (`manage_stock = false`) in the `custome_config` table, the trigger will not alter the `products.product_count` values.

Execute the following SQL DDL query on the production database:

```sql
CREATE OR REPLACE FUNCTION public.update_product_count_on_delivery_items()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_compcode bigint;
    v_manage_stock boolean := true;
BEGIN
    -- 1. Identify tenant code (compcode) from customer purchase items
    SELECT compcode INTO v_compcode 
    FROM customer_purchase_items 
    WHERE items_id = COALESCE(NEW."workOrderLineId", OLD."workOrderLineId");

    -- 2. Check if this tenant has stock management disabled in custome_config
    SELECT COALESCE((config_data->>'manage_stock')::boolean, true) INTO v_manage_stock
    FROM custome_config
    WHERE compcode = v_compcode 
      AND module_name = 'inventory' 
      AND config_type = 'settings' 
      AND deleted IS NOT TRUE;

    -- 3. If stock management is disabled for this tenant, skip modifying the stock count
    IF v_manage_stock = false THEN
        RETURN NEW;
    END IF;

    -- Case 1: New delivery item is inserted
    IF TG_OP = 'INSERT' THEN
        -- If the item is marked as deleted, increase the product count
        IF NEW.deleted = TRUE THEN
            UPDATE products  
            SET product_count = product_count + NEW.quantity  
            FROM customer_purchase_items  
            WHERE products.product_id = customer_purchase_items.product_id  
            AND products.compcode = customer_purchase_items.compcode
            AND customer_purchase_items.items_id = NEW."workOrderLineId";
        -- Otherwise, decrease the product count
        ELSE
            UPDATE products  
            SET product_count = product_count - NEW.quantity  
            FROM customer_purchase_items  
            WHERE products.product_id = customer_purchase_items.product_id  
            AND products.compcode = customer_purchase_items.compcode
            AND customer_purchase_items.items_id = NEW."workOrderLineId";
        END IF;

    -- Case 2: Quantity is updated (adjust the difference)
    ELSIF TG_OP = 'UPDATE' AND NEW.quantity IS DISTINCT FROM OLD.quantity THEN
        UPDATE products  
        SET product_count = product_count + (NEW.quantity - OLD.quantity)  
        FROM customer_purchase_items  
        WHERE products.product_id = customer_purchase_items.product_id  
        AND products.compcode = customer_purchase_items.compcode
        AND customer_purchase_items.items_id = NEW."workOrderLineId"
        AND NEW.deleted = FALSE; -- Only affect active items

    -- Case 3: Marking as deleted (increase product_count back)
    ELSIF TG_OP = 'UPDATE' AND OLD.deleted = FALSE AND NEW.deleted = TRUE THEN
        UPDATE products  
        SET product_count = product_count + OLD.quantity  
        FROM customer_purchase_items  
        WHERE products.product_id = customer_purchase_items.product_id  
        AND products.compcode = customer_purchase_items.compcode
        AND customer_purchase_items.items_id = OLD."workOrderLineId";
    END IF;

    RETURN NEW;
END;
$function$;
```

---

## 2. Pre-Migration Audit (Check Discrepancy Counts by Tenant)
Before running the synchronization scripts, execute these audit queries to identify the number of out-of-sync products across different tenants (`compcode`).

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

---

## 3. Inventory / Stock Synchronization
To reconcile the stock levels between the `products` table and `store_product` table:

### Single-Store Products Sync
For products linked to only one store row in `store_product` for a given tenant, set the `store_product` stock to match the `products` global stock:

```sql
UPDATE store_product sp
SET product_count = p.product_count
FROM products p
WHERE sp.product_id = p.product_id
  AND sp.compcode = p.compcode
  AND sp.deleted IS NOT TRUE
  AND p.deleted IS NOT TRUE
  AND (p.product_id, p.compcode) IN (
      SELECT product_id, compcode
      FROM store_product 
      WHERE deleted IS NOT TRUE 
      GROUP BY product_id, compcode
      HAVING COUNT(*) = 1
  );
```

### Multi-Store Products Sync (Proportional Scaling)
For products distributed across multiple stores for a given tenant, scale their store counts proportionally to match the global product count:

```sql
WITH store_sums AS (
    SELECT product_id, compcode, SUM(product_count) as total_store_count
    FROM store_product
    WHERE deleted IS NOT TRUE
    GROUP BY product_id, compcode
),
scaled_counts AS (
    SELECT sp.store_product_id, 
           ROUND(sp.product_count * (p.product_count / NULLIF(ss.total_store_count, 0))) as new_count
    FROM store_product sp
    JOIN products p ON p.product_id = sp.product_id AND p.compcode = sp.compcode
    JOIN store_sums ss ON ss.product_id = sp.product_id AND ss.compcode = sp.compcode
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
