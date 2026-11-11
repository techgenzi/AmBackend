# DevOps Guide: GRN QC Dynamic Attributes Database Migration

This document provides instructions for executing the database schema updates and data migration to support customer-specific and tenant-level dynamic quality attributes in the GRNQC module. 

This migration is fully backward-compatible and can be executed online on a live database with zero downtime.

---

## 1. Schema Upgrades (DDL)

Run the following SQL commands to create the quality attribute configuration and transactional measurement tables.

```sql
-- 1. Create the configuration table
CREATE TABLE IF NOT EXISTS public.quality_attributes_config (
    id BIGSERIAL PRIMARY KEY,
    compcode BIGINT NOT NULL,
    customer_id BIGINT NULL,
    raw_material_id BIGINT NULL,
    attribute_name VARCHAR(100) NOT NULL,
    attribute_type VARCHAR(50) NOT NULL DEFAULT 'boolean',
    min_value NUMERIC NULL,
    max_value NUMERIC NULL,
    is_required BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_qc_config_lookup 
ON public.quality_attributes_config(compcode, customer_id, raw_material_id);

-- 2. Create the detailed QC measurements table
CREATE TABLE IF NOT EXISTS public.grn_qc_measurements (
    id BIGSERIAL PRIMARY KEY,
    grn_line_id BIGINT NOT NULL,
    spec_id BIGINT NOT NULL REFERENCES public.quality_attributes_config(id) ON DELETE CASCADE,
    measured_value VARCHAR(255),
    is_passed BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for GRN line lookups
CREATE INDEX IF NOT EXISTS idx_grn_qc_measurements_line 
ON public.grn_qc_measurements(grn_line_id);
```

---

## 2. Seed Default Global Attributes

To ensure backward compatibility for all existing companies (`compcode`), seed the baseline global attributes (*Thickness*, *Size*, *Color*) into the config table.

```sql
-- Seed global attributes for each active company code
INSERT INTO public.quality_attributes_config (compcode, attribute_name, attribute_type)
SELECT DISTINCT compcode, 'Thickness', 'boolean' FROM public.grnlineitems
ON CONFLICT DO NOTHING;

INSERT INTO public.quality_attributes_config (compcode, attribute_name, attribute_type)
SELECT DISTINCT compcode, 'Size', 'boolean' FROM public.grnlineitems
ON CONFLICT DO NOTHING;

INSERT INTO public.quality_attributes_config (compcode, attribute_name, attribute_type)
SELECT DISTINCT compcode, 'Color', 'boolean' FROM public.grnlineitems
ON CONFLICT DO NOTHING;
```

---

## 3. Data Migration (Live Execution)

Run this query to parse historical `reason` JSON keys and map them into rows in the new `grn_qc_measurements` table:

```sql
-- Migrate Thickness records
INSERT INTO public.grn_qc_measurements (grn_line_id, spec_id, measured_value, is_passed)
SELECT 
    gl.grnlineid,
    qcfg.id,
    'true',
    FALSE -- If marked as checked in the legacy "reason", it indicates a failure.
FROM public.grnlineitems gl
JOIN public.quality_attributes_config qcfg 
  ON qcfg.compcode = gl.compcode 
  AND qcfg.attribute_name = 'Thickness'
WHERE (gl.reason->>'thickness')::boolean = TRUE;

-- Migrate Size records
INSERT INTO public.grn_qc_measurements (grn_line_id, spec_id, measured_value, is_passed)
SELECT 
    gl.grnlineid,
    qcfg.id,
    'true',
    FALSE
FROM public.grnlineitems gl
JOIN public.quality_attributes_config qcfg 
  ON qcfg.compcode = gl.compcode 
  AND qcfg.attribute_name = 'Size'
WHERE (gl.reason->>'size')::boolean = TRUE;

-- Migrate Color records
INSERT INTO public.grn_qc_measurements (grn_line_id, spec_id, measured_value, is_passed)
SELECT 
    gl.grnlineid,
    qcfg.id,
    'true',
    FALSE
FROM public.grnlineitems gl
JOIN public.quality_attributes_config qcfg 
  ON qcfg.compcode = gl.compcode 
  AND qcfg.attribute_name = 'Color'
WHERE (gl.reason->>'color')::boolean = TRUE;
```

---

## 4. Rollback Plan

If a rollback is required, execute the following commands to safely remove the new schema elements without affecting historical GRN line records (which retain their data in the legacy `reason` column):

```sql
DROP TABLE IF EXISTS public.grn_qc_measurements CASCADE;
DROP TABLE IF EXISTS public.quality_attributes_config CASCADE;
```
