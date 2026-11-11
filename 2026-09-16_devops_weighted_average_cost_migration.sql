-- Database Migration: Weighted Average Cost (WAC) Support & Backfill
-- Date: 2026-09-16
-- Target Tables: products, grnotes, grnlineitems

-- ============================================================================
-- 1. SCHEMA MIGRATION: Add moving_avg_cost column to products table
-- ============================================================================
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS moving_avg_cost NUMERIC(15, 4) DEFAULT 0.0000;

-- Optional index for faster cost lookups/filters
CREATE INDEX IF NOT EXISTS idx_products_moving_avg_cost ON products (moving_avg_cost) WHERE deleted IS NOT TRUE;

-- ============================================================================
-- 2. AUDIT QUERY (Run to preview calculated WAC before backfill)
-- ============================================================================
/*
WITH grn_totals AS (
    SELECT 
        gli.product_id,
        gn.compcode,
        SUM(COALESCE(gli.received_quantity, 0)) AS total_qty,
        SUM(
            COALESCE(gli.received_quantity, 0) * 
            COALESCE(NULLIF(regexp_replace(gli.rate_per_item, '[^0-9.]', '', 'g'), '')::numeric, 0)
        ) AS total_val
    FROM grnlineitems gli
    JOIN grnotes gn ON gn.grnotesid = gli.grnotesid
    WHERE gn.deleted IS NOT TRUE 
      AND gli.deleted IS NOT TRUE
      AND gn.is_moved = true
    GROUP BY gli.product_id, gn.compcode
)
SELECT 
    p.product_id,
    p.product_code,
    p.product_name,
    p.compcode,
    COALESCE(p.cost, 0) AS standard_cost,
    COALESCE(gt.total_qty, 0) AS total_grn_qty,
    COALESCE(gt.total_val, 0) AS total_grn_val,
    CASE 
        WHEN COALESCE(gt.total_qty, 0) > 0 
        THEN ROUND(gt.total_val / gt.total_qty, 4)
        ELSE COALESCE(p.cost, 0)
    END AS calculated_weighted_avg_cost
FROM products p
LEFT JOIN grn_totals gt ON gt.product_id = p.product_id AND gt.compcode = p.compcode
WHERE p.deleted IS NOT TRUE;
*/

-- ============================================================================
-- 3. DATA MIGRATION: Backfill moving_avg_cost for all products
-- ============================================================================
WITH grn_calc AS (
    SELECT 
        gli.product_id,
        gn.compcode,
        CASE 
            WHEN SUM(COALESCE(gli.received_quantity, 0)) > 0 
            THEN ROUND(
                SUM(
                    COALESCE(gli.received_quantity, 0) * 
                    COALESCE(NULLIF(regexp_replace(gli.rate_per_item, '[^0-9.]', '', 'g'), '')::numeric, 0)
                ) / SUM(COALESCE(gli.received_quantity, 0)), 
                4
            )
            ELSE 0 
        END AS wac_rate
    FROM grnlineitems gli
    JOIN grnotes gn ON gn.grnotesid = gli.grnotesid
    WHERE gn.deleted IS NOT TRUE 
      AND gli.deleted IS NOT TRUE
      AND gn.is_moved = true
    GROUP BY gli.product_id, gn.compcode
)
UPDATE products p
SET moving_avg_cost = COALESCE(
    NULLIF(gc.wac_rate, 0),
    NULLIF(p.cost, 0),
    0
)
FROM grn_calc gc
WHERE p.product_id = gc.product_id 
  AND p.compcode = gc.compcode;

-- Fallback for products with no GRN history: set moving_avg_cost from existing p.cost
UPDATE products
SET moving_avg_cost = COALESCE(cost, 0)
WHERE (moving_avg_cost IS NULL OR moving_avg_cost = 0)
  AND cost IS NOT NULL 
  AND cost > 0
  AND deleted IS NOT TRUE;
