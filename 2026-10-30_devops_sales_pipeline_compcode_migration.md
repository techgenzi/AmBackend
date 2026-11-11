# DevOps Database Migration Guide: Compcode Isolation for Sales & Lead Pipeline

**Date**: 2026-10-30  
**Service**: Vendors & Sales Pipeline (`/am-vendors/pipeline/*`) & Customer Purchase (`customer_purchase`)  
**Repositories**: `AmNonOvens` & `Fabrico360-BE`  
**Target Tables**: `pipeline_stages`, `sales_lead_pipelines`  

---

## 1. Why This Migration Is Required

Previously, `pipeline_stages` had a global `UNIQUE (key)` constraint and neither `pipeline_stages` nor `sales_lead_pipelines` had a `compcode` column. As a result:
1. All `compcode`s and tenants shared the same global pipeline stages.
2. Leads created in one `compcode` appeared on the pipeline board of other `compcode`s (showing up as `Customer #<id>` when the customer belonged to another company).

This migration:
- Adds `compcode BIGINT` to `pipeline_stages` and `sales_lead_pipelines`.
- Replaces the global `pipeline_stages_key_key` unique constraint with a composite `UNIQUE (compcode, key)` constraint (`uq_pipeline_stages_compcode_key`).
- Backfills `sales_lead_pipelines.compcode` from the linked `vendor.compcode` (for `EXISTING` customers) or `customer_purchase.compcode` (via `tally_invoice_number` / `order_unique`).
- Clones the stage definitions per active `compcode` and re-points existing leads to their respective `compcode`'s stage `id` so no existing lead loses its stage position.

---

## 2. Pre-Migration Backup (Recommended)

Before running the migration, take a quick snapshot of the two pipeline tables:

```sql
CREATE TABLE IF NOT EXISTS backup_20261030_pipeline_stages AS SELECT * FROM pipeline_stages;
CREATE TABLE IF NOT EXISTS backup_20261030_sales_lead_pipelines AS SELECT * FROM sales_lead_pipelines;
```

---

## 3. SQL Migration Script (Idempotent)

Run the following SQL block in PostgreSQL on the target environment database(s):

```sql
BEGIN;

-- ============================================================================
-- STEP 1: Add compcode columns to pipeline_stages and sales_lead_pipelines
-- ============================================================================
ALTER TABLE pipeline_stages
    ADD COLUMN IF NOT EXISTS compcode BIGINT NULL;

ALTER TABLE sales_lead_pipelines
    ADD COLUMN IF NOT EXISTS compcode BIGINT NULL;

-- ============================================================================
-- STEP 2: Replace global UNIQUE(key) with composite UNIQUE(compcode, key)
-- ============================================================================
ALTER TABLE pipeline_stages
    DROP CONSTRAINT IF EXISTS pipeline_stages_key_key;

ALTER TABLE pipeline_stages
    DROP CONSTRAINT IF EXISTS uq_pipeline_stages_compcode_key;

ALTER TABLE pipeline_stages
    ADD CONSTRAINT uq_pipeline_stages_compcode_key UNIQUE (compcode, key);

-- ============================================================================
-- STEP 3: Backfill compcode on existing sales_lead_pipelines
-- ============================================================================

-- 3a. From linked vendor (Customer Master) where customer_id is present
UPDATE sales_lead_pipelines slp
SET compcode = v.compcode
FROM vendor v
WHERE slp.customer_id = v.vendorid
  AND slp.compcode IS NULL
  AND v.compcode IS NOT NULL;

-- 3b. From linked customer_purchase order where tally_invoice_number matches order_unique
UPDATE sales_lead_pipelines slp
SET compcode = cp.compcode
FROM customer_purchase cp
WHERE slp.tally_invoice_number = cp.order_unique
  AND COALESCE(TRIM(slp.tally_invoice_number), '') <> ''
  AND cp.deleted IS NOT TRUE
  AND slp.compcode IS NULL
  AND cp.compcode IS NOT NULL;

-- 3c. Fallback for any remaining unmapped leads (assign to primary/default compcode = 1)
UPDATE sales_lead_pipelines
SET compcode = COALESCE(
    (SELECT gtcompmastid FROM gtcompmast ORDER BY gtcompmastid ASC LIMIT 1),
    1
)
WHERE compcode IS NULL;

-- ============================================================================
-- STEP 4: Assign existing global pipeline_stages to the primary compcode
--         and clone stages for all other compcodes that have leads
-- ============================================================================
DO $$
DECLARE
    primary_cc BIGINT;
    rec_cc RECORD;
BEGIN
    -- Determine primary compcode (prefer compcode that already has stages, then most leads, then gtcompmast, else 1)
    SELECT COALESCE(
        (SELECT compcode FROM pipeline_stages WHERE compcode IS NOT NULL GROUP BY compcode ORDER BY COUNT(*) DESC, compcode ASC LIMIT 1),
        (SELECT compcode FROM sales_lead_pipelines WHERE compcode IS NOT NULL GROUP BY compcode ORDER BY COUNT(*) DESC, compcode ASC LIMIT 1),
        (SELECT gtcompmastid FROM gtcompmast ORDER BY gtcompmastid ASC LIMIT 1),
        1
    ) INTO primary_cc;

    -- If the backend already auto-seeded stages for any compcode before migration ran,
    -- re-point leads from NULL-compcode stages to matching existing compcode stages first
    UPDATE sales_lead_pipelines slp
    SET stage_id = existing_ps.id
    FROM pipeline_stages null_ps
    JOIN pipeline_stages existing_ps
      ON existing_ps.key = null_ps.key
    WHERE slp.stage_id = null_ps.id
      AND null_ps.compcode IS NULL
      AND existing_ps.compcode = slp.compcode;

    -- Assign non-conflicting NULL-compcode stages to primary_cc
    UPDATE pipeline_stages ps
    SET compcode = primary_cc
    WHERE ps.compcode IS NULL
      AND NOT EXISTS (
          SELECT 1 FROM pipeline_stages existing
          WHERE existing.compcode = primary_cc
            AND existing.key = ps.key
      );

    -- Re-point any remaining leads referencing leftover NULL-compcode stages to primary_cc's stages
    UPDATE sales_lead_pipelines slp
    SET stage_id = target_ps.id
    FROM pipeline_stages null_ps
    JOIN pipeline_stages target_ps
      ON target_ps.key = null_ps.key
     AND target_ps.compcode = primary_cc
    WHERE slp.stage_id = null_ps.id
      AND null_ps.compcode IS NULL;

    -- Remove any redundant NULL-compcode stages that were superseded
    DELETE FROM pipeline_stages
    WHERE compcode IS NULL;

    -- For every other distinct compcode present in sales_lead_pipelines,
    -- ensure matching stages exist for that compcode
    FOR rec_cc IN (
        SELECT DISTINCT compcode
        FROM sales_lead_pipelines
        WHERE compcode IS NOT NULL AND compcode <> primary_cc
    ) LOOP
        -- Clone stages from primary_cc into rec_cc.compcode if not already present
        INSERT INTO pipeline_stages (id, compcode, name, key, sequence_order, is_system, color_code, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            rec_cc.compcode,
            ps.name,
            ps.key,
            ps.sequence_order,
            ps.is_system,
            ps.color_code,
            NOW(),
            NOW()
        FROM pipeline_stages ps
        WHERE ps.compcode = primary_cc
        ON CONFLICT (compcode, key) DO NOTHING;
    END LOOP;

    -- Re-point any leads across all compcodes whose stage belongs to a different compcode
    UPDATE sales_lead_pipelines slp
    SET stage_id = target_ps.id
    FROM pipeline_stages old_ps
    JOIN pipeline_stages target_ps
      ON target_ps.key = old_ps.key
    WHERE slp.stage_id = old_ps.id
      AND target_ps.compcode = slp.compcode
      AND old_ps.compcode <> slp.compcode;
END $$;

-- ============================================================================
-- STEP 5: Enforce NOT NULL & defaults, and create performance indexes
-- ============================================================================
ALTER TABLE pipeline_stages
    ALTER COLUMN compcode SET DEFAULT 1,
    ALTER COLUMN compcode SET NOT NULL;

ALTER TABLE sales_lead_pipelines
    ALTER COLUMN compcode SET DEFAULT 1,
    ALTER COLUMN compcode SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pipeline_stages_compcode
    ON pipeline_stages (compcode);

CREATE INDEX IF NOT EXISTS idx_sales_lead_pipelines_compcode
    ON sales_lead_pipelines (compcode);

COMMIT;
```

---

## 4. Post-Migration Verification Queries

Run these queries after applying the migration to verify schema integrity and data isolation:

```sql
-- 1. Verify compcode column exists on both tables
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name IN ('pipeline_stages', 'sales_lead_pipelines')
  AND column_name = 'compcode';

-- 2. Verify composite unique constraint (compcode, key) on pipeline_stages
SELECT conname, pg_get_constraintdef(oid) AS constraint_def
FROM pg_constraint
WHERE conrelid = 'pipeline_stages'::regclass;

-- 3. Check stage counts per compcode (no NULL compcodes should remain)
SELECT compcode, COUNT(*) AS stage_count
FROM pipeline_stages
GROUP BY compcode
ORDER BY compcode;

-- 4. Check lead counts per compcode and verify all leads point to a stage in the SAME compcode
SELECT
    slp.compcode AS lead_compcode,
    ps.compcode AS stage_compcode,
    ps.name AS stage_name,
    COUNT(*) AS lead_count
FROM sales_lead_pipelines slp
JOIN pipeline_stages ps ON ps.id = slp.stage_id
GROUP BY slp.compcode, ps.compcode, ps.name
ORDER BY slp.compcode, ps.name;
```

> [!NOTE]
> For any brand-new `compcode` that has 0 stages in `pipeline_stages`, the backend API (`GET /am-vendors/pipeline/stages`) now automatically seeds the 3 default system stages (`Order Placed`, `Dispatched`, `Completed`) on first access.

