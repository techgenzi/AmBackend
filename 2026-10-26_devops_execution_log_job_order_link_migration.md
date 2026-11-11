# DevOps DB Migration & Deployment Guide: Stage-Level Job Order Association in Production Execution

**Date:** 2026-10-26  
**File:** `2026-10-26_devops_execution_log_job_order_link_migration.sql`  
**Target Database:** `AmNonOvens` PostgreSQL  

---

## 1. Overview & Objective
In production execution (`/productionexecution/execute/:id` and `/productionexecution/delay/:id`), stages can now be fulfilled directly via approved external **Job Orders** (Subcontracting).

To enable stage-level traceability between execution logs and outsourced Job Orders without disrupting standard in-house employee/machine execution, this migration adds nullable linkage fields and indexes to `public.execution_log`.

---

## 2. Changes Summary

| Table | Column Added | Type | Constraints / Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `execution_log` | `job_order_id` | `BIGINT` | `NULL` | Foreign key referencing `public.joborder(joborderid)`. |
| `execution_log` | `vendor_id` | `BIGINT` | `NULL` | Foreign key referencing `public.vendor(vendorid)`. |
| `execution_log` | `is_outsource` | `BOOLEAN` | `DEFAULT FALSE` | Flag identifying outsourced stage executions (idempotent check). |

### Indexes Created:
- `idx_execution_log_job_order_id` on `execution_log (compcode, job_order_id) WHERE job_order_id IS NOT NULL`
- `idx_execution_log_vendor_id` on `execution_log (compcode, vendor_id) WHERE vendor_id IS NOT NULL`

---

## 3. Migration Execution

Run the SQL migration script against the production database:

```bash
psql -h <DB_HOST> -U <DB_USER> -d <DB_NAME> -f 2026-10-26_devops_execution_log_job_order_link_migration.sql
```

---

## 4. Verification Queries

```sql
-- 1. Verify columns exist on execution_log
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'execution_log' 
  AND column_name IN ('job_order_id', 'vendor_id', 'is_outsource');

-- 2. Verify indexes exist
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'execution_log' 
  AND indexname IN ('idx_execution_log_job_order_id', 'idx_execution_log_vendor_id');
```

---

## 5. Rollback Script (If Needed)

> [!CAUTION]
> Note: `is_outsource` is an existing column used by core application reporting. Do **NOT** drop `is_outsource` if it was already present prior to this migration.

```sql
DROP INDEX IF EXISTS public.idx_execution_log_job_order_id;
DROP INDEX IF EXISTS public.idx_execution_log_vendor_id;

ALTER TABLE public.execution_log 
DROP COLUMN IF EXISTS job_order_id,
DROP COLUMN IF EXISTS vendor_id;
```
