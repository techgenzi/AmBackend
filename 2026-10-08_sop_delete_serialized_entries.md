# Standard Operating Procedure (SOP): Deleting Serialized Production Entries

## Overview
When serialized finished goods are entered into the system during production execution, records are created across two primary layers:
1. **`public.store_serialized_products`**: Physical inventory table storing the individual serial numbers, statuses (`Available`, `Dispatched`, etc.), store locations, and links to `execution_log_id` and `production_plan_id`.
2. **`public.execution_log`**: Manufacturing log recording the shift/hourly production. It holds:
   - `outward_qty`: Total units produced in that execution block.
   - `serialized_units`: A JSON array of the scanned/entered serial objects (e.g. `[{"Serial No": "...", ...}]`).
3. **`public.mv_daily_manufacturing_fact`**: Materialized view aggregating `el.outward_qty` for production dashboards and labour costing.

Because `execution_log.outward_qty` derives directly from the serialized entries, deleting serialized records requires cleaning both `store_serialized_products` and `execution_log`, followed by refreshing `mv_daily_manufacturing_fact`.

---

## Step-by-Step Deletion Procedure

### Step 1: Identify the Execution Log & Target Plan
Locate the `execution_log_id`, plan, and product details:

```sql
SELECT 
    el.id AS execution_log_id,
    pp.plan_unique,
    pp.production_plan_id,
    COALESCE(el.product_id, pt.product_id, pp.product_id) AS product_id,
    p.product_code,
    p.product_name,
    el.opertaion_start_date,
    el.outward_qty,
    jsonb_array_length(
        CASE 
            WHEN jsonb_typeof(el.serialized_units::jsonb) = 'array' 
            THEN el.serialized_units::jsonb 
            ELSE '[]'::jsonb 
        END
    ) AS json_serial_count
FROM public.execution_log el
JOIN public.plan_targets pt ON pt.plan_target_id = el.target_id
JOIN public.production_plan pp ON pp.production_plan_id = pt.production_plan_id
LEFT JOIN public.products p ON p.product_id = COALESCE(el.product_id, pt.product_id, pp.product_id)
WHERE pp.plan_unique = '<PLAN_UNIQUE>' -- e.g. 'PLN-000044'
  AND el.opertaion_start_date::date = '<DATE>'::date; -- e.g. '2026-10-01'
```

---

### Step 2: Check Serial Numbers in Store Inventory
Verify the records in `store_serialized_products` by status:

```sql
SELECT 
    status,
    COUNT(*) AS total_entries,
    production_plan_id,
    execution_log_id,
    product_id
FROM public.store_serialized_products
WHERE execution_log_id = <EXECUTION_LOG_ID> -- e.g. 1178
GROUP BY status, production_plan_id, execution_log_id, product_id;
```

> [!WARNING]
> If any entries have status `Dispatched`, check whether dispatch orders / delivery notes reference them before proceeding.

---

### Step 3: Delete Serialized Entries & Reset Execution Log

Run the cleanup:

```sql
BEGIN;

-- 1. Optional: Remove delivery serialization references if mapped
DELETE FROM public.delivery_serialized_items
WHERE serial_number IN (
    SELECT serial_number 
    FROM public.store_serialized_products 
    WHERE execution_log_id = <EXECUTION_LOG_ID>
);

-- 2. Delete entries from store_serialized_products
DELETE FROM public.store_serialized_products 
WHERE execution_log_id = <EXECUTION_LOG_ID>;

-- 3. Reset execution_log outward_qty and serialized_units
UPDATE public.execution_log 
SET 
    outward_qty = 0,
    serialized_units = '[]'
WHERE id = <EXECUTION_LOG_ID>;

-- 4. If legacy item_serial_registry is a physical table in your database, clean it as well
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
          AND table_name = 'item_serial_registry' 
          AND table_type = 'BASE TABLE'
    ) THEN
        DELETE FROM public.item_serial_registry 
        WHERE execution_log_id = <EXECUTION_LOG_ID>;
    END IF;
END $$;

COMMIT;
```

---

### Step 4: Refresh Dashboards & Costing Facts
Ensure downstream analytics reflect the updated `outward_qty`:

```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_manufacturing_fact;
```

---

### Step 5: Verification
Confirm that zero remaining records exist:

```sql
-- 1. Should return 0
SELECT COUNT(*) AS remaining_serials 
FROM public.store_serialized_products 
WHERE execution_log_id = <EXECUTION_LOG_ID>;

-- 2. Should return outward_qty = 0 and serialized_units = []
SELECT id, outward_qty, serialized_units 
FROM public.execution_log 
WHERE id = <EXECUTION_LOG_ID>;
```
