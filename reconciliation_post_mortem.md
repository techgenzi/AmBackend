# Post-Mortem: Stock & Allocation Reconciliation Report

**Date**: 2026-08-17  
**Client**: Feston (compcode: 155, tenant_id: 115)  
**Objective**: Reconcile allocation leaks and physical stock discrepancies for historical dispatches.

---

## 1. Summary of Actions Taken

1. **Allocation Cleanup (Successful)**:
   * Reconciled and soft-deleted **188 stale allocation leak rows** (dispatched leaks, rejected leaks, and orphaned allocations).
   * Reset global allocation counts on **510 product items** back to `0.0`.
   * Verified that the global mismatch query (Audit 1.1) now returns **0 rows**, confirming perfect synchronization.

2. **Codebase Hardening (Successful)**:
   * **Dispatched Leaks**: Patched `dispatch.py` to automatically soft-delete allocation rows when their quantities drop to `0` or below.
   * **Duplicate Allocations**: Patched `invregistry.py` to lookup existing records in Python before inserting, bypassing the PostgreSQL `NULL` unique constraint limitation.
   * **Serialized Store Tracking**: Patched `invregistry.py` to automatically update the `store_id` of serialized entries in `store_serialized_products` when a "Move FG to Store" action is completed.
   * **Dynamic Store Resolution**: Patched `exeraw.py` to resolve fallback store IDs dynamically based on active tenant store listings instead of using a hardcoded `store_id = 1`.

---

## 2. Explanation of Skipped Retroactive Stock Deductions

During the audit of **Material Issue Leaks** (Audit 2.1), we identified historical outward dispatches (`REQ-000002` through `REQ-000006`) processed between May 5, 2026, and May 9, 2026, which had missing `store_id` values and bypassed store stock deductions.

### Why Step 7 (Retroactive Stock Deduction) was Skipped:
* **The Finding**: An audit of `invregistry` transactions revealed that between June 15, 2026, and August 13, 2026, the store manager (`mr@festonsev.com` / `rajkumar`) performed multiple **`manual_addition`** transactions to manually correct the physical store counts for these products.
* **The Risk**: If we had run the retroactive stock deduction query (Step 7), it would have decremented the stock for these dispatches *again*, overriding the manager's manual adjustments and creating new physical inventory shortages.
* **The Decision**: We explicitly omitted the retroactive stock deduction step. The historical bypasses listed in Audit 6 are **permanently documented as resolved via manual adjustments** and require no further database updates.

---

## 3. Reference: Affected Products & Mapped Manual Adjustments

The following products were affected by the missing `store_id` dispatches and were successfully corrected via manual adjustments:

* **Product Group A (Hexaspacers & Foam)**:
  * `121`, `122` (Male & Female Hexaspacer)
  * `181` (EPE Top Foam), `184` (EPE Bottom Foam)
  * `179` (EPE Top Foam), `182` (EPE Bottom Foam)
* **Product Group B (PCBA & Cables)**:
  * `5` (Main Board), `12` (Control Board), `20` (Display Board), `18` (Wifi Board)
  * `208` (Positive Cable), `209` (Negative Cable), `380` (Communication Cable)
* **Product Group C (Mechanical & Packaging)**:
  * `129` (Top Cover), `136` (AC Top Plate), `139` (AC Top Plate Gasket), `152` (Heat Sink), `158` (Heatsink Gasket)
  * `263` (Product Label), `265` (PP White Plain Label)
  * `97`, `98`, `101`, `104`, `105`, `106`, `108`, `294`, `295` (Philips Pan / Screws / Nuts)
