# Database Migration & Root Cause Analysis: Dispatch Store Stock Update Fix

**Date**: 2026-08-07  
**Target Tables**: `store_product`, `dispatch`, `invregistry`  
**Related Components**: `dispatch` (Backend REST service)  

---

## 1. Problem Statement & Analysis

### Symptom
For production plan material requests (e.g. `REQ-000002` through `REQ-000006`, and `REQ-000033`), the **Stock Movement History** on the UI correctly displayed the outward material transactions (dispatches), but the **Stock Report** and **Stock List** current stock counts did not update (remain at their pre-issue counts), leading to a stock discrepancy.

### Root Cause
1. **Frontend Request Payload**: During material request creation on the frontend, `store_id` is omitted/null in the payload because requirements are requested globally for a plan rather than at a store-specific level.
2. **Backend Stock Update Condition**: In `dispatch/app/api/dispatch.py`, the stock update in the store's inventory (`store_product` table) was wrapped inside a conditional block checking for a valid `store_id`:
   ```python
   # From: dispatch/app/api/dispatch.py
   if store_id:
       s.execute(update_store, val)
   ```
3. **The Bypass**: Since `store_id` was `null` on the dispatch request, the backend skipped the store stock update query (`update_store`), causing the transaction to write to the ledger without adjusting the physical store product count.

---

## 2. Permanent Architecture Fix

We implemented a permanent fix in the backend at [dispatch/app/api/dispatch.py](file:///Users/rajkumarmuthuramalingam/Work/AmNonOvens/dispatch/app/api/dispatch.py#L275-L287) by adding fallback logic:

If `store_id` is null/None in the request and the parent release registry record:
1. We query the `store_product` table to find the first store containing this product.
2. If found, we use it to execute the stock deduction, preventing any future bypasses.

```python
# Fallback Store ID Resolution in post()
product_id = pro[0].get('product_id', None)
prod_plan_id = pro[0].get('prod_plan_id', None)
store_id = i.get('store_id') or pro[0].get('store_id', None)
if not store_id and product_id:
    store_record = s.execute(
        text("SELECT store_id FROM store_product WHERE product_id = :product_id AND deleted IS NOT TRUE LIMIT 1"),
        {"product_id": product_id}
    ).fetchone()
    if store_record:
        store_id = store_record[0]
```

---

## 3. Database Audit & Correction Queries

### A. Audit Query (Run First to Verify)
This query previews all outward dispatch entries that were processed but bypassed the store stock deduction (where `store_id` on the inventory registry request was `NULL`):

```sql
SELECT 
    ir.ref_id,
    ir.releseid,
    ir.product_id,
    p.sku_id,
    p.product_name,
    d.dispatch_amount,
    COALESCE(ir.store_id, 1) AS target_store_id,
    sp.product_count AS current_store_product_count
FROM dispatch d
JOIN invregistry ir ON ir.releseid = d.releseid
JOIN products p ON p.product_id = ir.product_id
LEFT JOIN store_product sp ON sp.product_id = ir.product_id AND sp.store_id = COALESCE(ir.store_id, 1) AND sp.compcode = d.compcode
WHERE ir.action = 'Outward'
  AND ir.status = 'Approved'
  AND ir.store_id IS NULL;
```

### B. Stock Correction Script (Update)
This query retroactively deducts the dispatched quantities from the `store_product` table for all bypassed transactions, ensuring the count never drops below zero (to prevent check constraint violations):

```sql
UPDATE store_product sp
SET product_count = GREATEST(0, COALESCE(sp.product_count, 0) - d.dispatch_amount)
FROM dispatch d
JOIN invregistry ir ON ir.releseid = d.releseid
WHERE ir.action = 'Outward'
  AND ir.status = 'Approved'
  AND ir.store_id IS NULL
  AND sp.product_id = ir.product_id
  AND sp.store_id = COALESCE(ir.store_id, 1)
  AND sp.compcode = d.compcode;
```
