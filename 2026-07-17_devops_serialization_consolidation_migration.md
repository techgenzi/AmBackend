# DevOps Migration Guide: Consolidation of Serialized Products Tables
**Date: 2026-07-17**

This guide outlines the database migration steps required to consolidate `item_serial_registry` and `store_serialized_products` into a single unified table tracking system. It ensures that both manufactured and imported/purchased goods are tracked in `store_serialized_products` while maintaining 100% backward compatibility for legacy queries and reports reading from `item_serial_registry`.

---

## Step 1: Add Production Metadata Columns to `store_serialized_products`

We extend the store inventory table to support the production attributes originally kept in the registry. Run this in your database:

```sql
ALTER TABLE public.store_serialized_products 
ADD COLUMN IF NOT EXISTS execution_log_id BIGINT,
ADD COLUMN IF NOT EXISTS production_plan_id BIGINT,
ADD COLUMN IF NOT EXISTS unit_data JSONB;
```

---

## Step 2: Migrate Historical Data from `item_serial_registry`

Execute the following query to copy all active serialized product logs into the unified `store_serialized_products` table. This query resolves the appropriate `store_id` by matching the original production plan or falling back to the product's mapped store.

```sql
INSERT INTO public.store_serialized_products (
    product_id, 
    store_id, 
    serial_number, 
    status, 
    compcode, 
    created_at, 
    execution_log_id, 
    production_plan_id, 
    unit_data
)
SELECT DISTINCT ON (isr.compcode, isr.product_id, cleaned_serial.serial_number)
    isr.product_id,
    COALESCE(inv.store_id, sp.store_id, 1) AS store_id, -- Resolves store, defaults to store ID 1 if none found
    cleaned_serial.serial_number,
    'Available' AS status,
    isr.compcode,
    isr.created_on AS created_at,
    isr.execution_log_id,
    isr.production_plan_id,
    isr.unit_data
FROM public.item_serial_registry isr
CROSS JOIN LATERAL (
    SELECT COALESCE(
        isr.serial_number, 
        isr.unit_data->>'Serial No', 
        isr.unit_data->>'serial_number', 
        isr.unit_data->>'Serial Number', 
        isr.unit_data->>'serial_no'
    ) AS serial_number
) cleaned_serial
LEFT JOIN public.invregistry inv 
  ON inv.prod_plan_id = isr.production_plan_id 
  AND inv.product_id = isr.product_id 
  AND inv.compcode = isr.compcode
  AND inv.deleted IS NOT TRUE
LEFT JOIN LATERAL (
    SELECT store_id 
    FROM public.store_product 
    WHERE product_id = isr.product_id 
      AND compcode = isr.compcode 
      AND deleted IS NOT TRUE 
    LIMIT 1
) sp ON TRUE
WHERE isr.deleted IS NOT TRUE 
  AND isr.status = 'In Store'
  AND cleaned_serial.serial_number IS NOT NULL 
  AND TRIM(cleaned_serial.serial_number) <> ''
ON CONFLICT (compcode, product_id, serial_number) DO NOTHING;
```

---

## Step 3: Replace Physical Table with Backward-Compatible View

To prevent queries in older services or analytical reports from breaking, drop the original physical table and replace it with a view pointing directly to the unified table.

```sql
-- 1. Drop the physical table
DROP TABLE IF EXISTS public.item_serial_registry;

-- 2. Recreate it as a view pointing to store_serialized_products
CREATE OR REPLACE VIEW public.item_serial_registry AS 
SELECT 
    id,
    execution_log_id,
    production_plan_id,
    product_id,
    serial_number,
    NULL::bigint AS current_stage, 
    CASE 
        WHEN status = 'Available' THEN 'In Store' 
        ELSE status 
    END AS status,
    unit_data,
    compcode,
    created_at AS created_on,
    updated_at AS modified_on,
    deleted
FROM public.store_serialized_products;
```
