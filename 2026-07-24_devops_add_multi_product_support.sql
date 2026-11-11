-- Database Migration: Add Multi-Product support to Production Plans and Execution logs
-- Date: 2026-07-24
-- Target Tables: production_plan, plan_targets, execution_log, production_plan_products

-- 1. Add column is_multi_product to production_plan if it does not exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'production_plan' AND column_name = 'is_multi_product'
    ) THEN
        ALTER TABLE production_plan ADD COLUMN is_multi_product BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- 2. Add column product_id to plan_targets if it does not exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'plan_targets' AND column_name = 'product_id'
    ) THEN
        ALTER TABLE plan_targets ADD COLUMN product_id BIGINT DEFAULT NULL;
    END IF;
END $$;

-- 3. Add column product_id to execution_log if it does not exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'execution_log' AND column_name = 'product_id'
    ) THEN
        ALTER TABLE execution_log ADD COLUMN product_id BIGINT DEFAULT NULL;
    END IF;
END $$;

-- 4. Create table production_plan_products if it does not exist
CREATE TABLE IF NOT EXISTS production_plan_products (
    id BIGSERIAL PRIMARY KEY,
    production_plan_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    planned_quantity NUMERIC NOT NULL,
    moved_quantity NUMERIC DEFAULT 0,
    compcode BIGINT NOT NULL,
    created_on TIMESTAMP DEFAULT NOW(),
    modified_on TIMESTAMP DEFAULT NOW(),
    deleted BOOLEAN DEFAULT FALSE
);

-- 5. Create index on production_plan_products for performance
CREATE INDEX IF NOT EXISTS idx_ppp_plan_id ON production_plan_products(production_plan_id);
CREATE INDEX IF NOT EXISTS idx_ppp_product_id ON production_plan_products(product_id);

-- 6. One-time data fix: Reset order_items_extract.quantity_planned
--    to recalculate from only non-deleted plan_details.
--    This is needed because deleted plans were not resetting quantity_planned,
--    causing "Yet to Plan" to stay 0 even after plan deletion.
UPDATE order_items_extract oie
SET quantity_planned = COALESCE((
    SELECT SUM(pd.plan_quantity)
    FROM plan_details pd
    WHERE pd.order_extract_id = oie.extract_id
      AND pd.deleted IS NOT TRUE
), 0)
WHERE EXISTS (
    SELECT 1 FROM plan_details pd2
    WHERE pd2.order_extract_id = oie.extract_id
);

