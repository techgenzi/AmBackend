# Database Migration: Sales / Lead Pipeline and Configurable Stages (Compcode-Scoped)

**Date**: 2026-10-30  
**Target Tables**: `pipeline_stages`, `sales_lead_pipelines`  
**Objective**: Scope pipeline stages and sales leads at the `compcode` (`gtcompmastid` / `company_id`) level so each company branch maintains isolated stages and leads.

---

## 1. Migration Schema Changes (Existing Databases)

Run the following SQL DDL statements to migrate existing `pipeline_stages` and `sales_lead_pipelines` tables to `compcode`-level isolation:

```sql
BEGIN;

-- 1. Add compcode column (BIGINT matching vendor.compcode / gtcompmastid)
ALTER TABLE pipeline_stages
    ADD COLUMN IF NOT EXISTS compcode BIGINT NULL;

ALTER TABLE sales_lead_pipelines
    ADD COLUMN IF NOT EXISTS compcode BIGINT NULL;

-- 2. Backfill existing leads with their linked customer's compcode, order's compcode, or default to 1
UPDATE sales_lead_pipelines slp
SET compcode = v.compcode
FROM vendor v
WHERE slp.customer_id = v.vendorid
  AND slp.compcode IS NULL
  AND v.compcode IS NOT NULL;

UPDATE sales_lead_pipelines slp
SET compcode = cp.compcode
FROM customer_purchase cp
WHERE slp.tally_invoice_number = cp.order_unique
  AND COALESCE(TRIM(slp.tally_invoice_number), '') <> ''
  AND cp.deleted IS NOT TRUE
  AND slp.compcode IS NULL
  AND cp.compcode IS NOT NULL;

UPDATE sales_lead_pipelines
SET compcode = 1
WHERE compcode IS NULL;

-- If backend already auto-seeded stages before migration ran, re-point leads from NULL-compcode stages first
UPDATE sales_lead_pipelines slp
SET stage_id = existing_ps.id
FROM pipeline_stages null_ps
JOIN pipeline_stages existing_ps
  ON existing_ps.key = null_ps.key
WHERE slp.stage_id = null_ps.id
  AND null_ps.compcode IS NULL
  AND existing_ps.compcode = slp.compcode;

UPDATE pipeline_stages ps
SET compcode = 1
WHERE ps.compcode IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM pipeline_stages existing
      WHERE existing.compcode = 1 AND existing.key = ps.key
  );

UPDATE sales_lead_pipelines slp
SET stage_id = target_ps.id
FROM pipeline_stages null_ps
JOIN pipeline_stages target_ps
  ON target_ps.key = null_ps.key
 AND target_ps.compcode = 1
WHERE slp.stage_id = null_ps.id
  AND null_ps.compcode IS NULL;

DELETE FROM pipeline_stages
WHERE compcode IS NULL;

-- 3. Replace global unique constraint on (key) with composite unique constraint on (compcode, key)
ALTER TABLE pipeline_stages
    DROP CONSTRAINT IF EXISTS pipeline_stages_key_key;

ALTER TABLE pipeline_stages
    DROP CONSTRAINT IF EXISTS uq_pipeline_stages_compcode_key;

-- Ensure any distinct compcodes in sales_lead_pipelines have matching stages and remapped stage_id
INSERT INTO pipeline_stages (compcode, name, key, sequence_order, is_system, color_code)
SELECT DISTINCT slp.compcode, ps.name, ps.key, ps.sequence_order, ps.is_system, ps.color_code
FROM sales_lead_pipelines slp
CROSS JOIN pipeline_stages ps
WHERE ps.compcode = 1
  AND slp.compcode <> 1
  AND NOT EXISTS (
      SELECT 1 FROM pipeline_stages existing
      WHERE existing.compcode = slp.compcode AND existing.key = ps.key
  );

UPDATE sales_lead_pipelines slp
SET stage_id = target_ps.id
FROM pipeline_stages old_ps
JOIN pipeline_stages target_ps
  ON target_ps.key = old_ps.key
WHERE slp.stage_id = old_ps.id
  AND target_ps.compcode = slp.compcode
  AND old_ps.compcode <> slp.compcode;

ALTER TABLE pipeline_stages
    ALTER COLUMN compcode SET DEFAULT 1,
    ALTER COLUMN compcode SET NOT NULL;

ALTER TABLE sales_lead_pipelines
    ALTER COLUMN compcode SET DEFAULT 1,
    ALTER COLUMN compcode SET NOT NULL;

ALTER TABLE pipeline_stages
    ADD CONSTRAINT uq_pipeline_stages_compcode_key UNIQUE (compcode, key);

-- 4. Create indexes for fast compcode filtering
CREATE INDEX IF NOT EXISTS idx_pipeline_stages_compcode ON pipeline_stages (compcode);
CREATE INDEX IF NOT EXISTS idx_sales_lead_pipelines_compcode ON sales_lead_pipelines (compcode);

COMMIT;
```

---

## 2. Fresh Table Creation DDL (New Environments)

```sql
-- 1. Create pipeline_stages table for configurable stages per compcode
CREATE TABLE IF NOT EXISTS pipeline_stages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    compcode BIGINT NOT NULL DEFAULT 1,
    name VARCHAR(100) NOT NULL,
    key VARCHAR(100) NOT NULL,
    sequence_order INTEGER NOT NULL,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    color_code VARCHAR(7) NOT NULL DEFAULT '#6B7280',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pipeline_stages_compcode_key UNIQUE (compcode, key)
);

-- 2. Create sales_lead_pipelines table to track leads per compcode
CREATE TABLE IF NOT EXISTS sales_lead_pipelines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    compcode BIGINT NOT NULL DEFAULT 1,
    customer_type VARCHAR(20) NOT NULL CHECK (customer_type IN ('NEW', 'EXISTING')),
    customer_id BIGINT REFERENCES vendor(vendorid) ON DELETE SET NULL,
    new_customer_name VARCHAR(255),
    new_customer_contact VARCHAR(50),
    new_customer_email VARCHAR(255),
    new_customer_address TEXT,
    stage_id UUID NOT NULL REFERENCES pipeline_stages(id),
    tally_invoice_number VARCHAR(100),
    delivery_method VARCHAR(50) CHECK (delivery_method IN ('PICKUP', 'SUPPLIER_DELIVERED')),
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. Automatic Stage Seeding Behavior

When `GET /am-vendors/pipeline/stages` is called for any `compcode`, `ensure_default_stages_for_compcode(compcode)` automatically seeds the 3 default system stages (`order_placed`, `dispatched`, `completed`) for that `compcode` if it has 0 stages configured.
