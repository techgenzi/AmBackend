# DevOps Migration Guide: Cost Reports Performance Optimization

- **Date:** 2026-09-28
- **Author:** Antigravity Engineering
- **Affected Services:**
  - `customer_purchase` (Production Cost Report: `/am-customer-purchase-order/plan_cost`)
  - `production_plans` (WIP Material Cost Report: `/am-prod_plans/fg_cost_report`)
  - `labour` (WIP Labour Cost Plan-Wise Report: `/am-labour/labour_cost`)
- **SQL Migration Script:** [`2026-09-28_devops_cost_reports_performance_indexes.sql`](file:///Users/rajkumarmuthuramalingam/Work/AmNonOvens/2026-09-28_devops_cost_reports_performance_indexes.sql)

---

## 1. Context & Objectives

Users noticed high latency and slow query execution across the three primary cost reports when filtering by date ranges:
1. `/reports/productioncostreport` (`/plan_cost`)
2. `/reports/materialcost` (`/fg_cost_report`)
3. `/reports/labourcostplanwise` (`/labour_cost`)

### Root Causes Identified
- **Date Function Suppression (`::date`):** Using expressions like `el.opertaion_start_date::date BETWEEN ...` in `WHERE` clauses prevents PostgreSQL from utilizing standard B-Tree indexes on timestamp columns.
- **Subquery Inefficiencies:** `IN (SELECT production_plan_id FROM ...)` subqueries over `execution_log` caused materialization and sequential scans over large datasets.
- **Unbounded JSON Lateral Joins:** The `/labour_cost` endpoint ran `json_array_elements` over every `labour_cost` record in the tenant, regardless of whether those products were part of the requested page of plans.
- **Missing Composite & Covering Indexes:** Heavy 4-way joins in actual material cost calculation (`plan_allocation`, `invregistry`, `dispatch`, `return_material`) lacked compound indexes covering `prod_plan_id` and `created_on`.

---

## 2. Code Changes Applied

The application layer code has been optimized as follows:
- **`customer_purchase/app/api/customer_purchase.py`:**
  - Replaced `pp.production_plan_id in (select ...::date ...)` with `EXISTS (...)` using timestamp bounds (`>= :start_date` and `< :end_date + interval '1 day'`).
- **`production_plans/app/api/planning.py`:**
  - Replaced `::date` casts with timestamp boundaries across `fsl.created_on`, `dispatch.created_on`, `return_material.created_on`, and `plan_allocation.created_on`.
- **`labour/app/api/labour.py`:**
  - Filtered `labour_cost` by joining directly to the paginated `filtered_plans` products, eliminating unnecessary JSON parsing of unrelated products.

---

## 3. Database Execution Instructions

### A. Pre-requisites
- Ensure database read/write credentials with DDL permissions.
- Running during non-peak hours is recommended, or execute concurrently if needed in high-traffic production environments.

### B. Applying the Migration via psql
```bash
# Connect to PostgreSQL and execute the migration script:
psql -h <DB_HOST> -p <DB_PORT> -U <DB_USER> -d <DB_NAME> -f 2026-09-28_devops_cost_reports_performance_indexes.sql
```

### C. Direct SQL Queries (Safe to run idempotently)
```sql
BEGIN;

-- 1. Index on execution_log for operation date filtering
CREATE INDEX IF NOT EXISTS idx_exec_log_target_op_date
ON execution_log (target_id, opertaion_start_date)
WHERE deleted IS NOT TRUE;

-- 2. Index on plan_targets for production_plan_id lookup
CREATE INDEX IF NOT EXISTS idx_plan_targets_prod_plan_target
ON plan_targets (production_plan_id, plan_target_id)
WHERE deleted IS NOT TRUE;

-- 3. Index on fg_to_store_log for WIP Material Cost Report
CREATE INDEX IF NOT EXISTS idx_fsl_compcode_plan_created
ON fg_to_store_log (compcode, production_plan_id, created_on);

-- 4. Index on plan_allocation for material consumption calculations
CREATE INDEX IF NOT EXISTS idx_plan_allocation_plan_prod_active
ON plan_allocation (prod_plan_id, product_id, created_on)
WHERE deleted IS NOT TRUE;

-- 5. Indexes on invregistry and dispatch
CREATE INDEX IF NOT EXISTS idx_invregistry_prod_plan_release
ON invregistry (prod_plan_id, releseid);

CREATE INDEX IF NOT EXISTS idx_dispatch_release_created
ON dispatch (releseid, created_on);

-- 6. Index on return_material
CREATE INDEX IF NOT EXISTS idx_return_material_plan_prod_status
ON return_material (prod_plan_id, product_id, created_on)
WHERE status = 'Moved';

-- 7. Index on labour_cost
CREATE INDEX IF NOT EXISTS idx_labour_cost_product_compcode
ON labour_cost (compcode, product_id)
WHERE deleted IS NOT TRUE;

COMMIT;
```

---

## 4. Verification & Validation Steps

1. **Verify Index Creation:**
   ```sql
   SELECT indexname, tablename
   FROM pg_indexes
   WHERE indexname IN (
       'idx_exec_log_target_op_date',
       'idx_plan_targets_prod_plan_target',
       'idx_fsl_compcode_plan_created',
       'idx_plan_allocation_plan_prod_active',
       'idx_invregistry_prod_plan_release',
       'idx_dispatch_release_created',
       'idx_return_material_plan_prod_status',
       'idx_labour_cost_product_compcode'
   );
   ```
2. **Restart/Redeploy Backend Services:**
   - Redeploy or restart containers for `customer_purchase`, `production_plans`, and `labour`.
3. **Verify API Response Times:**
   - Execute test curl calls against `/plan_cost`, `/fg_cost_report`, and `/labour_cost` with date filters (`start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`).
   - Query latency should drop by 40%–70%.

---

## 5. Rollback Procedure
If required to drop the indexes:
```sql
DROP INDEX IF EXISTS idx_exec_log_target_op_date;
DROP INDEX IF EXISTS idx_plan_targets_prod_plan_target;
DROP INDEX IF EXISTS idx_fsl_compcode_plan_created;
DROP INDEX IF EXISTS idx_plan_allocation_plan_prod_active;
DROP INDEX IF EXISTS idx_invregistry_prod_plan_release;
DROP INDEX IF EXISTS idx_dispatch_release_created;
DROP INDEX IF EXISTS idx_return_material_plan_prod_status;
DROP INDEX IF EXISTS idx_labour_cost_product_compcode;
```
