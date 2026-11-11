-- Migration: Support CPO Item Lots, Inventory Lots, and Production Moved Date
-- Date: 2026-11-06
-- Related: PR #2346 (Brahadeesh BE - Release 258)

-- 1. Create cpo_item_lots table
CREATE TABLE IF NOT EXISTS cpo_item_lots (
    id BIGSERIAL PRIMARY KEY,
    customer_purchase_id BIGINT NOT NULL,
    cpo_item_id BIGINT NOT NULL,
    lot_number VARCHAR(100) NOT NULL,
    lot_qty NUMERIC(12, 2) NOT NULL DEFAULT 0,
    compcode VARCHAR(50),
    deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_cpo_item_lots_cpo_id 
    ON cpo_item_lots(customer_purchase_id) WHERE deleted IS NOT TRUE;

CREATE INDEX IF NOT EXISTS idx_cpo_item_lots_item_id 
    ON cpo_item_lots(cpo_item_id) WHERE deleted IS NOT TRUE;

CREATE INDEX IF NOT EXISTS idx_cpo_item_lots_lot_no 
    ON cpo_item_lots(lot_number);

CREATE INDEX IF NOT EXISTS idx_invregistry_lot_no 
    ON invregistry(lot_no) WHERE lot_no IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_production_plan_lot_number 
    ON production_plan(lot_number) WHERE lot_number IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_plan_details_lot_number 
    ON plan_details(lot_number) WHERE lot_number IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_grnotes_grn_no 
    ON grnotes(grn_no);

CREATE INDEX IF NOT EXISTS idx_grnlineitems_grnotesid_product 
    ON grnlineitems(grnotesid, product_id);

CREATE INDEX IF NOT EXISTS idx_joline_items_lot_no 
    ON joline_items(lot_no) WHERE lot_no IS NOT NULL;

-- 2. Add lot_no to store_product and invregistry
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'store_product' AND column_name = 'lot_no'
    ) THEN
        ALTER TABLE public.store_product ADD COLUMN lot_no VARCHAR(100);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'invregistry' AND column_name = 'lot_no'
    ) THEN
        ALTER TABLE public.invregistry ADD COLUMN lot_no VARCHAR(100);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'product_variant' AND column_name = 'lot_no'
    ) THEN
        ALTER TABLE public.product_variant ADD COLUMN lot_no VARCHAR(100);
    END IF;
END $$;

-- 3. Add moved_date & lot columns to production tables
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'production_plan' AND column_name = 'moved_date'
    ) THEN
        ALTER TABLE public.production_plan ADD COLUMN moved_date TIMESTAMP WITHOUT TIME ZONE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'production_plan' AND column_name = 'lot_number'
    ) THEN
        ALTER TABLE public.production_plan ADD COLUMN lot_number VARCHAR(100);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'production_plan_products' AND column_name = 'moved_date'
    ) THEN
        ALTER TABLE public.production_plan_products ADD COLUMN moved_date TIMESTAMP WITHOUT TIME ZONE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'plan_details' AND column_name = 'lot_number'
    ) THEN
        ALTER TABLE public.plan_details ADD COLUMN lot_number VARCHAR(100);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'plan_details' AND column_name = 'cpo_item_lot_id'
    ) THEN
        ALTER TABLE public.plan_details ADD COLUMN cpo_item_lot_id BIGINT;
    END IF;
END $$;

-- 4. Add lot_no & product_details to joline_items (if not already existing)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'joline_items' AND column_name = 'lot_no'
    ) THEN
        ALTER TABLE public.joline_items ADD COLUMN lot_no VARCHAR(100);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'joline_items' AND column_name = 'product_details'
    ) THEN
        ALTER TABLE public.joline_items ADD COLUMN product_details JSONB;
    END IF;
END $$;

