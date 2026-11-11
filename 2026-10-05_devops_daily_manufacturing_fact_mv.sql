-- ==============================================================================
-- DevOps Database Migration: Create Unified Daily Manufacturing Fact Table
-- Date: 2026-10-05
-- Description:
--   Creates a Materialized View to act as the Single Source of Truth for all 
--   costing and production dashboards.
--   Provides a unified grain for Labour Cost, Material Cost, and Production Cost.
-- ==============================================================================

BEGIN;

-- Drop existing if recreating
DROP MATERIALIZED VIEW IF EXISTS mv_daily_manufacturing_fact;

-- 1. Create the Materialized View using UNION ALL (Kimball Fact approach)
CREATE MATERIALIZED VIEW mv_daily_manufacturing_fact AS

WITH hourly_wage AS (
    SELECT 
        hremploymastid AS emp_id,
        COALESCE(
            CASE
                WHEN daily_wages = TRUE THEN round((NULLIF(trim(ctc_amount), '')::numeric / 8), 2)
                ELSE round((NULLIF(trim(ctc_amount), '')::numeric / (30 * 8)), 2)
            END,
            0
        ) AS hourly_rate
    FROM hremploymast
),
log_with_apportion AS (
    SELECT 
        el.id,
        el.emp_id,
        el.line_id,
        el.target_id,
        el.stage_id,
        el.process_id,
        el.outward_qty,
        el.opertaion_start_date,
        -- Apportion hourly wage across all active logs by the employee in that hour slot
        (hw.hourly_rate / COUNT(*) OVER(
            PARTITION BY el.emp_id, el.opertaion_start_date::date, el.hour_config_id
        )) AS apportioned_wage_cost
    FROM execution_log el
    JOIN hourly_wage hw ON hw.emp_id = el.emp_id
    WHERE el.deleted IS NOT TRUE AND COALESCE(el.outward_qty, 0) > 0
)

-- LABOUR & PRODUCTION GRAIN
SELECT 
    l.opertaion_start_date::date AS execution_date,
    COALESCE(pp.compcode, 0) AS compcode,
    CASE 
        WHEN lc.line_name = 'Medline Cutting Line 1' THEN 2
        WHEN lc.line_name LIKE 'LV240%' OR lc.line_name LIKE '048%' OR lc.line_name LIKE '%Nada%' OR lc.line_name LIKE 'Patient Gown%' THEN 1
        WHEN lc.line_name LIKE 'IG 27SMS2%' OR lc.line_name LIKE 'EP Line%' OR lc.line_name LIKE 'Labcoat%' OR lc.line_name LIKE 'Medline%' OR lc.line_name LIKE 'Pillow%' OR lc.line_name LIKE 'Shorts%' THEN 3
        ELSE COALESCE(pp.floor_id, 0)
    END AS floor_id,
    pp.production_plan_id AS production_plan_id,
    COALESCE(pt.product_id, pp.product_id, 0) AS product_id,
    COALESCE(l.stage_id, 0) AS stage_id,
    COALESCE(l.emp_id, 0) AS emp_id,
    0::bigint AS material_id,
    SUM(COALESCE(l.outward_qty, 0)) AS outward_qty,
    
    -- Labour Costs: Uses wage apportionment matching WIP Labour Cost Report & Customer Excel
    SUM(COALESCE(l.apportioned_wage_cost, 0)) AS actual_labour_cost,
    -- Standard Stage Labour Cost: Credited for the last process of each stage (outward_qty * stage standard rate)
    SUM(CASE 
        WHEN (slp.last_process_id IS NULL OR l.process_id IS NULL OR l.process_id = slp.last_process_id)
        THEN COALESCE((l.outward_qty * CAST(slr.stage_standard_rate AS numeric)), 0) 
        ELSE 0 
    END) AS estimated_labour_cost,
    
    -- Material Costs
    0::numeric AS actual_material_cost,
    0::numeric AS estimated_material_cost

FROM log_with_apportion l
JOIN plan_targets pt ON l.target_id = pt.plan_target_id
JOIN production_plan pp ON pt.production_plan_id = pp.production_plan_id
LEFT JOIN line_config lc ON lc.line_config_id = l.line_id
-- Safely identify the last process per (product_id, stage_id)
LEFT JOIN (
    SELECT DISTINCT ON (ps.product_id, ps.stage_id)
           ps.product_id,
           ps.stage_id,
           asm.config_id AS last_process_id
    FROM production_stages ps
    JOIN activity_stage_map asm ON asm.production_stage_id = ps.id AND asm.deleted IS NOT TRUE
    WHERE ps.deleted IS NOT TRUE
    ORDER BY ps.product_id, ps.stage_id, asm.is_final_process DESC, asm.config_id DESC
) slp ON slp.product_id = COALESCE(pt.product_id, pp.product_id)
      AND slp.stage_id = l.stage_id
-- Resolve stage-level standard labour piece rate
LEFT JOIN (
    SELECT 
        lc.product_id,
        (elem->>'stage_id')::bigint AS stage_id,
        COALESCE(
            NULLIF(elem->>'rate_per_piece', '')::numeric,
            NULLIF(elem->>'rate', '')::numeric,
            0
        ) AS stage_standard_rate
    FROM labour_cost lc
    CROSS JOIN LATERAL json_array_elements(COALESCE(lc.add_attribute::json, '[]'::json)) AS elem
    WHERE lc.deleted IS NOT TRUE
) slr ON slr.product_id = COALESCE(pt.product_id, pp.product_id)
     AND slr.stage_id = l.stage_id
WHERE pp.deleted IS NOT TRUE
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8

UNION ALL

-- MATERIAL GRAIN
SELECT 
    el.opertaion_start_date::date AS execution_date,
    COALESCE(pp.compcode, 0) AS compcode,
    CASE 
        WHEN lc.line_name = 'Medline Cutting Line 1' THEN 2
        WHEN lc.line_name LIKE 'LV240%' OR lc.line_name LIKE '048%' OR lc.line_name LIKE '%Nada%' OR lc.line_name LIKE 'Patient Gown%' THEN 1
        WHEN lc.line_name LIKE 'IG 27SMS2%' OR lc.line_name LIKE 'EP Line%' OR lc.line_name LIKE 'Labcoat%' OR lc.line_name LIKE 'Medline%' OR lc.line_name LIKE 'Pillow%' OR lc.line_name LIKE 'Shorts%' THEN 3
        ELSE COALESCE(pp.floor_id, 0)
    END AS floor_id,
    pp.production_plan_id AS production_plan_id,
    COALESCE(el.product_id, pt.product_id, pp.product_id, 0) AS product_id,
    COALESCE(el.stage_id, 0) AS stage_id,
    0::bigint AS emp_id,
    COALESCE(bc.product_id, 0) AS material_id,
    0 AS outward_qty, -- Avoid double counting outward qty
    
    -- Labour Costs
    0::numeric AS actual_labour_cost,
    0::numeric AS estimated_labour_cost,
    
    -- Material Costs (Scoped to stage's last process to prevent duplicate consumption across machine passes)
    SUM(CASE 
        WHEN (slp.last_process_id IS NULL OR el.process_id IS NULL OR el.process_id = slp.last_process_id)
        THEN COALESCE((
            el.outward_qty 
            * CAST(NULLIF(bc.quantity, '')::numeric AS numeric) 
            * mc.cost
        ), 0)
        ELSE 0
    END) AS actual_material_cost,
    SUM(CASE 
        WHEN (slp.last_process_id IS NULL OR el.process_id IS NULL OR el.process_id = slp.last_process_id)
        THEN COALESCE((
            el.outward_qty 
            * CAST(NULLIF(bc.quantity, '')::numeric AS numeric) 
            * mc.cost
        ), 0)
        ELSE 0
    END) AS estimated_material_cost

FROM execution_log el
JOIN plan_targets pt ON el.target_id = pt.plan_target_id
JOIN production_plan pp ON pt.production_plan_id = pp.production_plan_id
LEFT JOIN line_config lc ON lc.line_config_id = el.line_id
JOIN bom b ON b.product_id = COALESCE(el.product_id, pt.product_id, pp.product_id) AND b.deleted IS NOT TRUE
LEFT JOIN (
    SELECT DISTINCT ON (product_id) product_id, stage_id as target_stage_id
    FROM production_stages
    WHERE deleted IS NOT TRUE
    ORDER BY product_id, rank_id DESC, stage_id DESC
) final_stage ON final_stage.product_id = COALESCE(el.product_id, pt.product_id, pp.product_id)
JOIN bom_component bc ON bc.bom_id = b.bom_id AND bc.deleted IS NOT TRUE 
    AND (
        (bc.stage_id IS NOT NULL AND bc.stage_id = el.stage_id)
        OR (bc.stage_id IS NULL AND el.stage_id = final_stage.target_stage_id)
    )
    -- Prevent double-counting manufactured sub-assemblies (e.g. cutting parts) that have their own BOMs and plans
    AND bc.product_id NOT IN (
        SELECT product_id FROM bom WHERE deleted IS NOT TRUE AND product_id IS NOT NULL
    )
LEFT JOIN material_cost mc ON mc.product_id = bc.product_id
LEFT JOIN (
    SELECT DISTINCT ON (ps.product_id, ps.stage_id)
           ps.product_id,
           ps.stage_id,
           asm.config_id AS last_process_id
    FROM production_stages ps
    JOIN activity_stage_map asm ON asm.production_stage_id = ps.id AND asm.deleted IS NOT TRUE
    WHERE ps.deleted IS NOT TRUE
    ORDER BY ps.product_id, ps.stage_id, asm.is_final_process DESC, asm.config_id DESC
) slp ON slp.product_id = COALESCE(el.product_id, pt.product_id, pp.product_id)
      AND slp.stage_id = el.stage_id
WHERE el.deleted IS NOT TRUE
  AND pp.deleted IS NOT TRUE
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8;

-- 2. Create Unique Index Required for Concurrent Refresh (Plain column names only, NO expressions!)
CREATE UNIQUE INDEX uidx_mv_daily_mfg_pk ON mv_daily_manufacturing_fact (
    execution_date,
    compcode,
    floor_id,
    production_plan_id,
    product_id,
    stage_id,
    emp_id,
    material_id
);

-- 3. Create Supporting Indices for High Performance Filters
CREATE INDEX idx_mv_exec_date ON mv_daily_manufacturing_fact(execution_date);
CREATE INDEX idx_mv_compcode ON mv_daily_manufacturing_fact(compcode);
CREATE INDEX idx_mv_prod_plan ON mv_daily_manufacturing_fact(production_plan_id);
CREATE INDEX idx_mv_material ON mv_daily_manufacturing_fact(material_id);
CREATE INDEX idx_mv_stage_emp ON mv_daily_manufacturing_fact(stage_id, emp_id);

COMMIT;
