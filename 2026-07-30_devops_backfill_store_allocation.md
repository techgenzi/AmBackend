# DevOps Database Backfill: Store Allocation Sync (2026-07-30)

This document provides the backfill script to align historical records in the `plan_allocation` table. Since raw material requests are approved without selecting a store, some `plan_allocation` rows are initialized with `store_id = NULL`. 

The script below links already-dispatched allocations to their corresponding dispatch records to restore store-level transaction visibility.

---

## 1. Pre-Migration Audit Queries

Run these queries **before** running the backfill script to identify the initial state and verify records that will be updated.

### A. Count of Allocations with NULL Store
This shows the number of allocation rows currently missing store associations:
```sql
SELECT 
    COUNT(*) AS total_null_rows,
    COALESCE(SUM(allocated_amount), 0) AS total_null_volume
FROM plan_allocation
WHERE store_id IS NULL;
```

### B. List of target records to be resolved
This lists the allocation records that will be patched and the store IDs they will resolve to:
```sql
SELECT 
    pa.plan_allocation_id,
    pa.prod_plan_id,
    pa.product_id,
    pa.allocated_amount,
    dp.store_id AS resolved_store_id
FROM plan_allocation pa
JOIN (
    SELECT DISTINCT ON (inv.prod_plan_id, inv.product_id) 
           inv.prod_plan_id, inv.product_id, d.store_id
    FROM dispatch d
    JOIN invregistry inv ON d.releseid = inv.releseid
    WHERE d.store_id IS NOT NULL
) dp ON pa.prod_plan_id = dp.prod_plan_id AND pa.product_id = dp.product_id
WHERE pa.store_id IS NULL;
```

---

## 2. Backfill SQL Script

Run the following query in your PostgreSQL interface to align the store IDs:

```sql
DO $$
DECLARE
    r RECORD;
    total_null_amount NUMERIC;
    target_plan_alloc_id BIGINT;
BEGIN
    FOR r IN 
        SELECT DISTINCT ON (inv.prod_plan_id, inv.product_id) 
               inv.prod_plan_id, inv.product_id, dp.store_id
        FROM dispatch dp
        JOIN invregistry inv ON dp.releseid = inv.releseid
        WHERE dp.store_id IS NOT NULL
    LOOP
        -- Calculate the sum of allocated amounts for the NULL store rows
        SELECT COALESCE(SUM(allocated_amount), 0)
        INTO total_null_amount
        FROM plan_allocation
        WHERE prod_plan_id = r.prod_plan_id 
          AND product_id = r.product_id 
          AND store_id IS NULL;

        IF total_null_amount > 0 THEN
            -- Check if a row with the target store already exists
            SELECT plan_allocation_id
            INTO target_plan_alloc_id
            FROM plan_allocation 
            WHERE prod_plan_id = r.prod_plan_id 
              AND product_id = r.product_id 
              AND store_id = r.store_id
            LIMIT 1;

            IF target_plan_alloc_id IS NOT NULL THEN
                -- Merge: add amount from NULL store rows into the existing store row
                UPDATE plan_allocation
                SET allocated_amount = allocated_amount + total_null_amount,
                    modified_on = NOW(),
                    modified_by = 'devops_backfill_merge'
                WHERE plan_allocation_id = target_plan_alloc_id;
            ELSE
                -- Find one NULL row to convert to the target store
                SELECT plan_allocation_id
                INTO target_plan_alloc_id
                FROM plan_allocation
                WHERE prod_plan_id = r.prod_plan_id 
                  AND product_id = r.product_id 
                  AND store_id IS NULL
                LIMIT 1;

                -- Update this single row to have target store and the sum of all NULL rows
                UPDATE plan_allocation
                SET store_id = r.store_id,
                    allocated_amount = total_null_amount,
                    modified_on = NOW(),
                    modified_by = 'devops_backfill'
                WHERE plan_allocation_id = target_plan_alloc_id;
            END IF;

            -- Delete all other/remaining NULL store rows for this product & plan
            DELETE FROM plan_allocation 
            WHERE prod_plan_id = r.prod_plan_id 
              AND product_id = r.product_id 
              AND store_id IS NULL
              AND plan_allocation_id != COALESCE(target_plan_alloc_id, -1);
        END IF;
    END LOOP;
END $$;
```

---

## 3. Post-Migration Verification Queries

Run these queries **after** running the backfill script to verify updates.

### A. Confirm NULL count is resolved
The count of NULL rows should be `0` (or reduced to only those allocations that have not had any dispatches yet):
```sql
SELECT 
    COUNT(*) AS total_null_rows,
    COALESCE(SUM(allocated_amount), 0) AS total_null_volume
FROM plan_allocation
WHERE store_id IS NULL;
```

### B. List updated migration records
This returns the records modified by the migration, confirming correct target stores and metadata updates:
```sql
SELECT 
    plan_allocation_id, 
    prod_plan_id, 
    product_id, 
    store_id, 
    allocated_amount, 
    modified_by,
    modified_on
FROM plan_allocation
WHERE modified_by IN ('devops_backfill', 'devops_backfill_merge')
ORDER BY modified_on DESC;
```
