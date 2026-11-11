# Actual Material Cost Report Migration & Backward Compatibility Review

**Date**: 2026-11-04  
**Module**: `material_cost` (`/am-material_cost/actual_material_cost_report`)  
**Target View**: `mv_daily_manufacturing_fact` (Daily Manufacturing Kimball Fact)  
**File Modified**: `material_cost/app/api/material_cost.py`

---

## 1. Overview
The endpoint `GET /am-material_cost/actual_material_cost_report` has been updated to source actual material consumption and costs directly from the unified materialized view `mv_daily_manufacturing_fact` rather than querying `production_material_cost`. 

This unifies actual material costing across:
- **Consolidated Dashboard**
- **WIP & Execution Logs**
- **Actual Material Cost Report**

---

## 2. Backward Compatibility Matrix

| Category | Status | Details |
| :--- | :---: | :--- |
| **Response Schema** | **Compatible** | Schema matches `actual_material_cost_list_response` (`total_results`, `page`, `results_per_page`, `results`). |
| **Response Keys** | **Compatible** | Top-level: `production_plan_id`, `plan_unique`, `total`, `data`.<br>Nested `data` objects maintain identical keys: `product_code`, `product_id`, `uom`, `sku_id`, `dispatch_amount`, `return_amount`, `consumed`, `total_cost`. |
| **Request Parameters** | **Compatible** | Supports `production_plan_id`, `product_id`, `start_date`, `end_date`, `results_per_page`, and `paged`. |
| **Multi-tenancy (`compcode`)** | **Improved** | Safely filters by `mv.compcode` only when provided; joins active, company-scoped/global rates from `material_cost` (`mc.deleted IS NOT TRUE AND (:compcode IS NULL OR mc.compcode = :compcode OR mc.compcode IS NULL)`). |
| **Pagination & Ordering** | **Improved** | Sorted deterministically by `plan_unique, production_plan_id`. Uses parameterized `LIMIT :limit OFFSET :offset`. |

---

## 3. Behavioral Differences & Observations

1. **Date Range Filter Semantics (`execution_date` vs `plan_date`)**:
   - **Previously**: `start_date` and `end_date` filtered against `production_plan.plan_date`.
   - **Now**: Filters on `mv.execution_date` (the date work was performed and raw material consumed in `execution_log`).
   - **Behavioral Impact**: Ensures consistency with shift and WIP logs. Plans planned earlier but executed within the selected date window will now correctly show consumption.

2. **`dispatch_amount` and `return_amount` Values**:
   - **Previously**: Fetched from manual/legacy dispatch slips in `production_material_cost`.
   - **Now**: Emitted as `0::numeric`.
   - **Behavioral Impact**: `mv_daily_manufacturing_fact` is an execution-fact grain. If consumers rely on physical store dispatch/return slips, those values now return `0`.

3. **`consumed` Calculation**:
   - Calculated as:
     $$\text{consumed} = \text{ROUND}\left(\frac{\sum(\text{mv.actual\_material\_cost})}{\text{mc.cost}}, 2\right)$$
   - Reconstructs actual consumed quantity directly from cost and unit rate aligned with the materialized view grain.

4. **Infrastructure Dependency**:
   - Requires `mv_daily_manufacturing_fact` to exist and be regularly refreshed (`REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_manufacturing_fact`).

