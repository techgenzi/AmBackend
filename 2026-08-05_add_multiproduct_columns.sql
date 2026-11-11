-- Database Migration: Add missing columns to production_plan_products for multi-product support
-- Date: 2026-08-05

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'production_plan_products' AND column_name = 'wastage') THEN
        ALTER TABLE production_plan_products ADD COLUMN wastage NUMERIC;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'production_plan_products' AND column_name = 'wastage_per') THEN
        ALTER TABLE production_plan_products ADD COLUMN wastage_per NUMERIC;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'production_plan_products' AND column_name = 'floor_id') THEN
        ALTER TABLE production_plan_products ADD COLUMN floor_id BIGINT;
    END IF;

    -- Drop columns that mistakenly went to the product level instead of plan level
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'production_plan_products' AND column_name = 'plan_date') THEN
        ALTER TABLE production_plan_products DROP COLUMN plan_date;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'production_plan_products' AND column_name = 'end_date') THEN
        ALTER TABLE production_plan_products DROP COLUMN end_date;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'production_plan_products' AND column_name = 'is_emergency_plan') THEN
        ALTER TABLE production_plan_products DROP COLUMN is_emergency_plan;
    END IF;
END $$;
