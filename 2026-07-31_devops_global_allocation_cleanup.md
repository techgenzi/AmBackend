# DevOps Database Migration: Global Allocation Deduplication and Synchronization (2026-07-31)

This migration deduplicates records in the `plan_allocation` table (caused by PostgreSQL treating `NULL` values as distinct in unique constraints) and synchronizes the global `allocated_quantity` counter in the `products` table across all SKUs.

---

## 1. Pre-Migration Audit Queries

Run these queries to identify the scope of mismatches and duplicate records before performing the cleanup:

### A. Find Mismatches between Products and Active Allocations
```sql
SELECT 
    p.product_id,
    p.sku_id,
    p.product_name,
    p.allocated_quantity AS current_global_count,
    COALESCE(pa_sum.total_allocated, 0) AS actual_allocated_sum
FROM products p
LEFT JOIN (
    SELECT product_id, SUM(allocated_amount) AS total_allocated
    FROM plan_allocation
    WHERE deleted IS NOT TRUE
    GROUP BY product_id
) pa_sum ON p.product_id = pa_sum.product_id
WHERE p.allocated_quantity::numeric != COALESCE(pa_sum.total_allocated, 0)
ORDER BY p.product_id;
```

### B. List Duplicate Allocations (where store_id is NULL)
```sql
SELECT 
    product_id, 
    prod_plan_id, 
    COUNT(*), 
    SUM(allocated_amount) as total_amount
FROM plan_allocation
WHERE store_id IS NULL
GROUP BY product_id, prod_plan_id
HAVING COUNT(*) > 1;
```

---

## 2. Cleanup & Sync Script

Run the following script in your PostgreSQL interface within a transaction block:

```sql
BEGIN;

-- Step 1: Clean up duplicate plan_allocation records.
-- Deletes duplicate rows for any combination of product_id and prod_plan_id where store_id is NULL,
-- retaining only the oldest (first inserted) record.
DELETE FROM plan_allocation
WHERE store_id IS NULL
  AND plan_allocation_id NOT IN (
      SELECT MIN(plan_allocation_id)
      FROM plan_allocation
      WHERE store_id IS NULL
      GROUP BY product_id, prod_plan_id
  );

-- Step 2: Ensure the remaining plan_allocation records match the actual approved amount in invregistry.
-- This queries the approved amount from invregistry and updates the single remaining plan_allocation record.
UPDATE plan_allocation pa
SET allocated_amount = inv.total_approved,
    modified_on = NOW(),
    modified_by = 'global_allocation_dedup'
FROM (
    SELECT 
        product_id, 
        prod_plan_id, 
        SUM(COALESCE(approved_amount::numeric, 0)) AS total_approved
    FROM invregistry
    WHERE status = 'Approved'
      AND action = 'Outward'
      AND deleted IS NOT TRUE
      AND prod_plan_id IS NOT NULL
    GROUP BY product_id, prod_plan_id
) inv
WHERE pa.product_id = inv.product_id 
  AND pa.prod_plan_id = inv.prod_plan_id
  AND pa.store_id IS NULL
  AND pa.deleted IS NOT TRUE;

-- Step 3: Synchronize the global products.allocated_quantity with the plan_allocation table.
-- This ensures the global counter exactly reflects the sum of all valid active allocations.
UPDATE products p
SET allocated_quantity = COALESCE(pa_sum.total_allocated, 0)
FROM (
    SELECT product_id, SUM(allocated_amount) AS total_allocated
    FROM plan_allocation
    WHERE deleted IS NOT TRUE
    GROUP BY product_id
) pa_sum
WHERE p.product_id = pa_sum.product_id;

-- Step 4: Reset any product's allocated_quantity to 0 if it has no active allocations.
-- Uses NOT EXISTS to avoid standard SQL NULL comparison bugs inside NOT IN blocks.
UPDATE products p
SET allocated_quantity = 0
WHERE NOT EXISTS (
    SELECT 1 
    FROM plan_allocation pa 
    WHERE pa.product_id = p.product_id 
      AND pa.deleted IS NOT TRUE
);

COMMIT;
```

---

## 3. Post-Migration Verification Queries

Verify that all product allocation counts are perfectly aligned by running the audit query again:

```sql
SELECT 
    COUNT(*) AS mismatch_count
FROM products p
LEFT JOIN (
    SELECT product_id, SUM(allocated_amount) AS total_allocated
    FROM plan_allocation
    WHERE deleted IS NOT TRUE
    GROUP BY product_id
) pa_sum ON p.product_id = pa_sum.product_id
WHERE p.allocated_quantity::numeric != COALESCE(pa_sum.total_allocated, 0);
```
*(This should return `0` mismatches).*
