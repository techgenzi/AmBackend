# Database Migration: Unify Inventory Registry Ledger

**Date**: 2026-07-24  
**Target Table**: `public.invregistry` (Inserts)  
**Source Tables**: `public.delivery`, `public.delivery_line_items`, `public.customer_purchase_items`, `public.return_material`  

---

## 1. Pre-Migration Audit Queries

Execute these queries **before** running the backfill to record baseline counts.

```sql
-- Audit 1: Total count & quantity of customer deliveries to backfill
SELECT 
    COUNT(*) AS total_delivery_rows,
    COALESCE(SUM(dli.quantity), 0) AS total_delivery_qty
FROM delivery_line_items dli
JOIN delivery d ON d.deliveryid = dli.deliveryid
JOIN customer_purchase_items cpi ON cpi.items_id = dli."workOrderLineId"
WHERE dli.deleted IS NOT TRUE;

-- Audit 2: Total count & quantity of material returns to backfill
SELECT 
    COUNT(*) AS total_return_rows,
    COALESCE(SUM(rm.return_amount), 0) AS total_return_qty
FROM return_material rm
WHERE rm.deleted IS NOT TRUE 
  AND rm.status = 'Moved' 
  AND rm.is_rejected IS NOT TRUE;
```

---

## 2. Migration Execution Script

Run the following transactions to backfill delivery and return logs into `invregistry`.

```sql
BEGIN;

-- 1. Backfill Finished Goods Customer Deliveries (Outward)
INSERT INTO invregistry (
    product_id, requested_amount, approved_amount, action, ref_id, 
    status, is_dispatch, store_id, compcode, userid, approval_id, 
    approval_date, created_on, created_by, type, deleted
)
SELECT 
    cpi.product_id,
    dli.quantity AS requested_amount,
    dli.quantity AS approved_amount,
    'Outward' AS action,
    d.deliveryno AS ref_id,
    'Approved' AS status,
    true AS is_dispatch,
    COALESCE(
        (SELECT sp.store_id FROM store_product sp WHERE sp.product_id = cpi.product_id LIMIT 1),
        1
    ) AS store_id,
    dli.compcode,
    d.userid,
    d.userid AS approval_id,
    d.created_on AS approval_date,
    dli.created_on,
    dli.created_by,
    'Delivery' AS type,
    false AS deleted
FROM delivery_line_items dli
JOIN delivery d ON d.deliveryid = dli.deliveryid
JOIN customer_purchase_items cpi ON cpi.items_id = dli."workOrderLineId"
LEFT JOIN invregistry ir ON ir.ref_id = d.deliveryno AND ir.product_id = cpi.product_id AND ir.type = 'Delivery'
WHERE dli.deleted IS NOT TRUE AND ir.releseid IS NULL;

-- 2. Backfill Material Returns (Inward)
INSERT INTO invregistry (
    product_id, requested_amount, approved_amount, action, ref_id, 
    status, is_dispatch, store_id, compcode, userid, approval_id, 
    approval_date, created_on, created_by, type, deleted
)
SELECT 
    rm.product_id,
    rm.return_request_amount AS requested_amount,
    rm.return_amount AS approved_amount,
    'Inward' AS action,
    rm.unique_id AS ref_id,
    'Approved' AS status,
    false AS is_dispatch,
    rm.store_id,
    rm.compcode,
    rm.user_id AS userid,
    rm.user_id AS approval_id,
    rm.moved_date AS approval_date,
    rm.created_on,
    rm.created_by,
    'Return' AS type,
    false AS deleted
FROM return_material rm
LEFT JOIN invregistry ir ON ir.ref_id = rm.unique_id AND ir.product_id = rm.product_id AND ir.type = 'Return'
WHERE rm.deleted IS NOT TRUE AND rm.status = 'Moved' AND rm.is_rejected IS NOT TRUE AND ir.releseid IS NULL;

COMMIT;
```

---

## 3. Post-Migration Audit Queries

Execute these queries **after** running the backfill to verify that the ledger entries match the baseline counts exactly.

```sql
-- Audit 1: Compare backfilled Delivery records in invregistry
SELECT 
    COUNT(*) AS backfilled_delivery_rows,
    COALESCE(SUM(approved_amount), 0) AS backfilled_delivery_qty
FROM invregistry
WHERE type = 'Delivery' AND deleted IS NOT TRUE;

-- Audit 2: Compare backfilled Return records in invregistry
SELECT 
    COUNT(*) AS backfilled_return_rows,
    COALESCE(SUM(approved_amount), 0) AS backfilled_return_qty
FROM invregistry
WHERE type = 'Return' AND deleted IS NOT TRUE;
```

*Note: The `backfilled_delivery_rows` and `backfilled_delivery_qty` must exactly match the values from the pre-migration Audit 1. The `backfilled_return_rows` and `backfilled_return_qty` must exactly match the values from pre-migration Audit 2.*
