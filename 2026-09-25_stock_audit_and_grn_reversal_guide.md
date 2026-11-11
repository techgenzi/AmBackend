# Stock Audit, Ledger Reconciliation & GRN Reversal Architecture Guide

**Date**: 2026-09-25  
**Company / Tenant**: Feston SEV Technologies (`compcode = 155`, `company_id = 155`, `tenant_id = 115`)  
**Target Tables**: `invregistry`, `store_product`, `grnotes`, `grnlineitems`, `dispatch`, `fg_to_store_log`

---

## 1. Executive Summary

A comprehensive inventory audit was performed for **Feston SEV Technologies**. The objective was to audit the double-entry transactional ledger (`invregistry`) against the physical warehouse stock cache (`store_product`), identify root causes of numerical drift, enhance the GRN reversal system with full auditability, and reconcile the ledger with physical inventory.

### Key Audit Findings
1. **Initial Discrepancies**: High variances were initially observed on high-volume items (e.g., Product 97 had a +190,906 variance; Product 99 had -40,530 ledger stock vs +26,852 physical stock).
2. **First Root Cause (`manual_addition` in `manual_count`)**:
   - Stock adjustments executed through the Manual Stock Adjustment UI were correctly written to `store_product.product_count`, but in `invregistry` they were recorded with `action = 'manual_addition'` and their quantities stored as strings in `manual_count` (e.g. `'+139156'`) with `status = NULL` and `approved_amount = NULL`.
   - Naive audit queries filtering only for `status = 'Approved'` and `SUM(approved_amount)` completely ignored all manual adjustments.
3. **Second Root Cause (Unrecorded Initial / Opening Balances)**:
   - For remaining items (e.g. Hexaspacers, Cable Harnesses, Screws, Covers), physical stock was seeded directly into `store_product` during warehouse go-live (January 2026) without recording initial Inward or Manual Addition transactions in `invregistry`.
   - When subsequent production dispatches occurred, the ledger went negative because zero initial inward had been registered.
4. **GRN Reversal Verification**:
   - Auditing confirmed that **no GRNs were deleted or reversed** for Feston.
   - However, an architectural review of the GRN reversal implementation revealed missing audit trails (lack of reason tracking and child line item cleanup), which was promptly patched.

---

## 2. GRN Reversal Architecture & Bug Fix

### Implementation Gap Identified
When a GRN was deleted/reversed:
1. `grnotes` was marked `deleted = true`, but the `grn_reason` field remained empty and `modified_by` was not populated.
2. `grnlineitems` were left untouched (`deleted = false`), causing orphaned line items in the database.
3. `invregistry` soft-deleted the inward entry without capturing the reason, timestamp, or acting user.

### Code Fix Applied
The following files were updated:
- `grnotes/app/api/helper.py`
- `grnotes/app/api/grnotes.py`

#### Key Improvements:
* **Captured Reversal Reason**: The `delete()` endpoint now extracts `reason` from the request and passes it to `delete_func()`.
* **Header & Line Item Cascade**: `grnotes` and `grnlineitems` are both updated with `deleted = true`, `deleted_at = now`, `grn_reason = reason`, `modified_by = username`, and `modified_on = now`.
* **Auditable Ledger Cleanup**: `invregistry` soft-deletes the inward log while setting `reason = 'GRN Reversed: <reason>'`, `deleted_at = now`, `modified_by = username`, and `modified_on = now`.

---

## 3. Comprehensive Audit SQL Query

Use this production-grade SQL query to audit ledger stock versus physical store stock across all transaction channels (`invregistry`, `store_transfer`, `fg_to_store_log`, `dispatch`, and `manual_addition`):

```sql
WITH consolidated_transactions AS (
    -- 1. Manual Adjustments, Store Transfers, & Direct GRN Inward
    SELECT 
        inv.product_id,
        CASE 
            WHEN inv.action = 'manual_addition' AND inv.manual_count LIKE '+%' 
                THEN CAST(SUBSTRING(inv.manual_count FROM 2) AS NUMERIC)
            WHEN inv.action = 'store_transfer' AND inv.is_dispatch IS NOT TRUE 
                THEN COALESCE(inv.approved_amount, 0)
            WHEN inv.action IN ('Inward', 'GRN', 'GRN Inward') AND inv.status = 'Approved' 
                THEN COALESCE(inv.approved_amount, 0)
            ELSE 0 
        END AS inward_qty,
        CASE 
            WHEN inv.action = 'manual_addition' AND inv.manual_count LIKE '-%' 
                THEN CAST(SUBSTRING(inv.manual_count FROM 2) AS NUMERIC)
            WHEN inv.action = 'store_transfer' AND inv.is_dispatch IS TRUE 
                THEN COALESCE(inv.approved_amount, 0)
            WHEN inv.action = 'Outward' AND inv.type = 'Delivery' AND inv.status = 'Approved' 
                THEN COALESCE(inv.approved_amount, 0)
            ELSE 0 
        END AS outward_qty
    FROM invregistry inv
    WHERE inv.deleted IS NOT TRUE 
      AND inv.compcode = 155

    UNION ALL

    -- 2. Finished Goods Additions
    SELECT 
        pp.product_id,
        fg.moved_quantity AS inward_qty,
        0 AS outward_qty
    FROM fg_to_store_log fg
    JOIN production_plan pp ON pp.production_plan_id = fg.production_plan_id
    WHERE fg.deleted IS NOT TRUE 
      AND fg.compcode = 155

    UNION ALL

    -- 3. Production Dispatches
    SELECT 
        ir.product_id,
        0 AS inward_qty,
        dp.dispatch_amount AS outward_qty
    FROM dispatch dp
    JOIN invregistry ir ON ir.releseid = dp.releseid
    WHERE dp.deleted IS NOT TRUE 
      AND dp.compcode = 155
),
ledger_totals AS (
    SELECT 
        ct.product_id,
        SUM(ct.inward_qty) - SUM(ct.outward_qty) AS net_ledger_stock
    FROM consolidated_transactions ct
    GROUP BY ct.product_id
),
physical_totals AS (
    SELECT 
        sp.product_id,
        MIN(sp.store_id) AS primary_store_id,
        SUM(COALESCE(sp.product_count, 0)) AS total_physical_stock
    FROM store_product sp
    WHERE sp.deleted IS NOT TRUE 
      AND sp.compcode = 155
    GROUP BY sp.product_id
)
SELECT 
    p.product_id,
    p.product_code,
    p.product_name,
    COALESCE(pt.primary_store_id, 1) AS store_id,
    COALESCE(lt.net_ledger_stock, 0) AS current_ledger_stock,
    COALESCE(pt.total_physical_stock, 0) AS physical_stock,
    (COALESCE(pt.total_physical_stock, 0) - COALESCE(lt.net_ledger_stock, 0)) AS audit_variance,
    CASE 
        WHEN (COALESCE(pt.total_physical_stock, 0) - COALESCE(lt.net_ledger_stock, 0)) >= 0 
            THEN '+' || (COALESCE(pt.total_physical_stock, 0) - COALESCE(lt.net_ledger_stock, 0))::text
        ELSE '-' || ABS(COALESCE(pt.total_physical_stock, 0) - COALESCE(lt.net_ledger_stock, 0))::text
    END AS manual_count_needed
FROM products p
LEFT JOIN ledger_totals lt ON p.product_id = lt.product_id
LEFT JOIN physical_totals pt ON p.product_id = pt.product_id
WHERE p.compcode = 155
  AND p.deleted IS NOT TRUE
  AND (COALESCE(lt.net_ledger_stock, 0) <> COALESCE(pt.total_physical_stock, 0))
ORDER BY ABS(COALESCE(pt.total_physical_stock, 0) - COALESCE(lt.net_ledger_stock, 0)) DESC;
```

---

## 4. Ledger Reconciliation Migration Script

Execute this script to seed the missing opening balances into `invregistry` without modifying or double-counting `store_product`:

```sql
BEGIN;

INSERT INTO invregistry (
    product_id,
    store_id,
    action,
    manual_count,
    reason,
    ref_id,
    compcode,
    created_on,
    created_by,
    deleted
)
VALUES
(110, 1, 'manual_addition', '+12930.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(117, 1, 'manual_addition', '+12026', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(112, 1, 'manual_addition', '+11790', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(111, 1, 'manual_addition', '+10444.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(193, 1, 'manual_addition', '+10000', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(295, 1, 'manual_addition', '+9640.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(119, 1, 'manual_addition', '+9190', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(100, 1, 'manual_addition', '+6300', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(348, 1, 'manual_addition', '+4000.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(206, 1, 'manual_addition', '+3549', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(207, 1, 'manual_addition', '+3549', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(205, 1, 'manual_addition', '+3549', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(162, 1, 'manual_addition', '+3450', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(341, 1, 'manual_addition', '+3380.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(382, 1, 'manual_addition', '+3030', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(126, 1, 'manual_addition', '+2866.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(190, 1, 'manual_addition', '+2804', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(115, 1, 'manual_addition', '+2498', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(347, 1, 'manual_addition', '+2000.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(340, 1, 'manual_addition', '+1208.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(345, 1, 'manual_addition', '+1036.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(346, 1, 'manual_addition', '+1036.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(368, 1, 'manual_addition', '+1010.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(3, 1, 'manual_addition', '+1010', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(242, 1, 'manual_addition', '+1010.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(10, 1, 'manual_addition', '+1010', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(125, 1, 'manual_addition', '+998.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(336, 1, 'manual_addition', '+880.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(247, 1, 'manual_addition', '+721.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(261, 1, 'manual_addition', '+680', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(256, 1, 'manual_addition', '+600.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(16, 1, 'manual_addition', '+584.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(141, 1, 'manual_addition', '+548.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(198, 1, 'manual_addition', '+457', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(342, 1, 'manual_addition', '+420.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(216, 1, 'manual_addition', '+405', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(217, 1, 'manual_addition', '+405', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(219, 1, 'manual_addition', '+404', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(218, 1, 'manual_addition', '+404', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(12, 1, 'manual_addition', '+399.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(221, 1, 'manual_addition', '+396', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(220, 1, 'manual_addition', '+395', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(215, 1, 'manual_addition', '+394', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(214, 1, 'manual_addition', '+394', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(222, 1, 'manual_addition', '+393', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(5, 1, 'manual_addition', '+392.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(142, 1, 'manual_addition', '+235', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(186, 1, 'manual_addition', '+212', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(22, 1, 'manual_addition', '+183.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(23, 1, 'manual_addition', '+160.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(187, 1, 'manual_addition', '+135', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(145, 1, 'manual_addition', '+104', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(254, 1, 'manual_addition', '+99.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(13, 1, 'manual_addition', '+89', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(309, 1, 'manual_addition', '+84', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(6, 1, 'manual_addition', '+61', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(32, 1, 'manual_addition', '+56', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(324, 1, 'manual_addition', '+48.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(371, 1, 'manual_addition', '+25', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(39, 1, 'manual_addition', '+23', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(196, 1, 'manual_addition', '+22', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(195, 1, 'manual_addition', '+21', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(273, 1, 'manual_addition', '+20.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(274, 1, 'manual_addition', '+18', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(275, 1, 'manual_addition', '+18', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(366, 1, 'manual_addition', '+14.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(367, 1, 'manual_addition', '+13.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false),
(365, 1, 'manual_addition', '+6.0', 'Stock Audit 2026-09 Opening Balance Reconciliation', 'AUDIT-2026-09', 155, NOW(), 'Audit Admin', false);

COMMIT;
```
