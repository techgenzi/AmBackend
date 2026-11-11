-- =============================================================================
-- DEVOPS MIGRATION: Rejected Raw Material Virtual Store
-- Feature  : Track QC-rejected raw materials in a separate virtual store
-- Date     : 2026-06-11
-- Author   : Antigravity (AI Pair Programmer)
-- Services : return_material (new table), qualityCheck (auto-insert), invregistry (new column)
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 1 — Create the rejected_material table
-- This is the core table that acts as the "virtual rejection store".
-- It mirrors the return_material table structure but captures QC rejections.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS rejected_material (
    rejected_material_id  BIGSERIAL PRIMARY KEY,
    unique_id             VARCHAR(50),               -- e.g. RJT-000001
    grnotesid             BIGINT,                    -- FK → grnotes.grnotesid
    grnlineid             BIGINT,                    -- FK → grnlineitems.grnlineid
    product_id            BIGINT,                    -- FK → products.product_id
    rejected_quantity     NUMERIC,                   -- = damaged_quantity from QC form
    rejection_reason      JSONB,                     -- {thickness, size, color} from QC checkbox
    rejection_remark      TEXT,                      -- free-text remark from QC form
    image_attachment      JSONB,                     -- image from QC form
    action                VARCHAR(50) DEFAULT 'Return to Store',
                                                     -- User-selected: Return to Store | Write Off | Re-inspect | Return to Vendor | Rework
    store_id              BIGINT,                    -- Target store selected by user in QC form
    status                VARCHAR(50) DEFAULT 'Pending',
                                                     -- Pending | Completed
    action_date           TIMESTAMP,                 -- When action was executed
    compcode              BIGINT,
    created_on            TIMESTAMP DEFAULT NOW(),
    created_by            VARCHAR(100),
    modified_on           TIMESTAMP,
    modified_by           VARCHAR(100),
    deleted               BOOLEAN DEFAULT FALSE,
    deleted_at            TIMESTAMP
);

-- Index for fast lookup by GRN and product
CREATE INDEX IF NOT EXISTS idx_rejected_material_grnotesid  ON rejected_material (grnotesid);
CREATE INDEX IF NOT EXISTS idx_rejected_material_product_id ON rejected_material (product_id);
CREATE INDEX IF NOT EXISTS idx_rejected_material_compcode   ON rejected_material (compcode);
CREATE INDEX IF NOT EXISTS idx_rejected_material_status     ON rejected_material (status);

-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 2 — Alter existing return_material table for production rejection
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE return_material ADD COLUMN IF NOT EXISTS is_rejected BOOLEAN DEFAULT FALSE;
ALTER TABLE return_material ADD COLUMN IF NOT EXISTS rejection_action VARCHAR(50);
ALTER TABLE return_material ADD COLUMN IF NOT EXISTS rejection_store_id BIGINT;

-- Note on existing tables:
-- ✅ grnlineitems     — no structural change; existing columns (damaged_quantity,
--                       reason, remark, image_attachment) are read by the new logic
-- ✅ grnotes          — no structural change; is_qc_done already exists
-- ✅ products         — no structural change; product_count is unaffected
-- ✅ store_product    — no structural change; stock count is unaffected
-- ✅ invregistry      — no structural change; new rejected_qty is computed at query time
--
-- The new rejected_quantity data is stored ONLY in rejected_material.
-- It is NEVER added to products.product_count or store_product.product_count.
-- This keeps normal stock counts clean and accurate.
-- ─────────────────────────────────────────────────────────────────────────────

-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 3 — Verification queries (run after migration to confirm success)
-- ─────────────────────────────────────────────────────────────────────────────

-- Confirm table created:
SELECT table_name FROM information_schema.tables
WHERE table_name = 'rejected_material';

-- Confirm indexes:
SELECT indexname FROM pg_indexes
WHERE tablename = 'rejected_material';

-- Confirm table is empty (should be 0 for fresh install):
SELECT count(*) FROM rejected_material;

-- ─────────────────────────────────────────────────────────────────────────────
-- ROLLBACK (if needed — drops only the new table, no existing data affected)
-- ─────────────────────────────────────────────────────────────────────────────
-- DROP TABLE IF EXISTS rejected_material;
