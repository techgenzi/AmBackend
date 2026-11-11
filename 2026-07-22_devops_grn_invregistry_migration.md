# Database Migration: Backfill Completed GRN Inward Movements to invregistry

**Date**: 2026-07-22  
**Target Tables**: `invregistry` (inserts), `grnotes`, `grnlineitems` (reads)  
**Objective**: Backfill inventory inward transaction logs for historical Goods Receipt Notes (GRN) that have already been moved to store (`is_moved = true`) but lack corresponding logs in the `invregistry` table.

---

## 1. Audit Query (Run First to Verify)

Use this query to preview the records that will be migrated and check the resolved `store_id`:

```sql
SELECT 
    gn.grn_no AS ref_id,
    gln.product_id,
    p.product_code,
    p.product_name,
    COALESCE(NULLIF(gln.non_damaged_quantity, '')::numeric, gln.received_quantity) AS approved_amount,
    gn.created_on AS transaction_date,
    gn.compcode AS tenant_id,
    gn.created_by AS user_name,
    COALESCE(
        (SELECT MIN(sp.store_id) 
         FROM store_product sp 
         WHERE sp.product_id = gln.product_id 
           AND sp.compcode = gn.compcode 
           AND sp.deleted IS NOT TRUE),
        (SELECT MIN(store_id) 
         FROM store_location 
         WHERE compcode = gn.compcode 
           AND deleted IS NOT TRUE)
    ) AS resolved_store_id
FROM grnotes gn
JOIN grnlineitems gln ON gln.grnotesid = gn.grnotesid
LEFT JOIN products p ON p.product_id = gln.product_id
WHERE gn.is_moved = true 
  AND gn.deleted IS NOT TRUE 
  AND gln.deleted IS NOT TRUE
  AND NOT EXISTS (
      SELECT 1 
      FROM invregistry ir 
      WHERE ir.ref_id = gn.grn_no 
        AND ir.product_id = gln.product_id
  )
ORDER BY gn.created_on DESC;
```

---

## 2. Migration Execution Query

Run this query to backfill the missing `invregistry` records:

```sql
INSERT INTO invregistry (
    product_id, 
    requested_amount, 
    approved_amount, 
    action, 
    ref_id, 
    status, 
    is_dispatch, 
    store_id, 
    compcode, 
    userid, 
    approval_id, 
    approval_date, 
    created_on, 
    created_by, 
    type, 
    deleted
)
SELECT 
    gln.product_id,
    COALESCE(NULLIF(gln.non_damaged_quantity, '')::numeric, gln.received_quantity) AS requested_amount,
    COALESCE(NULLIF(gln.non_damaged_quantity, '')::numeric, gln.received_quantity) AS approved_amount,
    'Inward' AS action,
    gn.grn_no AS ref_id,
    'Approved' AS status,
    false AS is_dispatch,
    COALESCE(
        (SELECT MIN(sp.store_id) 
         FROM store_product sp 
         WHERE sp.product_id = gln.product_id 
           AND sp.compcode = gn.compcode 
           AND sp.deleted IS NOT TRUE),
        (SELECT MIN(store_id) 
         FROM store_location 
         WHERE compcode = gn.compcode 
           AND deleted IS NOT TRUE)
    ) AS store_id,
    gn.compcode,
    gn.user_id AS userid,
    gn.user_id AS approval_id,
    gn.created_on AS approval_date,
    gn.created_on,
    gn.created_by,
    'GRN' AS type,
    false AS deleted
FROM grnotes gn
JOIN grnlineitems gln ON gln.grnotesid = gn.grnotesid
WHERE gn.is_moved = true 
  AND gn.deleted IS NOT TRUE 
  AND gln.deleted IS NOT TRUE
  AND NOT EXISTS (
      SELECT 1 
      FROM invregistry ir 
      WHERE ir.ref_id = gn.grn_no 
        AND ir.product_id = gln.product_id
  );
```
