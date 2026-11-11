-- ==============================================================================
-- DevOps Database Migration: Cost Reports Query Performance Optimization
-- Date: 2026-09-28
-- Description:
--   Creates specialized composite and partial indexes to optimize the 3 primary
--   cost reports:
--     1. Production Cost Report (/customer_purchase/plan_cost)
--     2. WIP Material Cost Report (/production_plans/fg_cost_report)
--     3. WIP Labour Cost Plan-Wise Report (/labour/labour_cost)
-- ==============================================================================

BEGIN;

-- 1. Optimizing Date-Range Filtering on execution_log for Plan Cost and Labour Cost
-- Used when filtering production plans by operation date range
CREATE INDEX IF NOT EXISTS idx_exec_log_target_op_date
ON execution_log (target_id, opertaion_start_date)
WHERE deleted IS NOT TRUE;

-- 2. Optimizing Plan Targets to Production Plan mapping
CREATE INDEX IF NOT EXISTS idx_plan_targets_prod_plan_target
ON plan_targets (production_plan_id, plan_target_id)
WHERE deleted IS NOT TRUE;

-- 3. Optimizing FG to Store Log (used by WIP Material Cost Report: /fg_cost_report)
-- Accelerates date filtering and plan-wise outward lookups
CREATE INDEX IF NOT EXISTS idx_fsl_compcode_plan_created
ON fg_to_store_log (compcode, production_plan_id, created_on);

-- 4. Optimizing Plan Allocation bulk queries in Actual Material calculation
CREATE INDEX IF NOT EXISTS idx_plan_allocation_plan_prod_active
ON plan_allocation (prod_plan_id, product_id, created_on)
WHERE deleted IS NOT TRUE;

-- 5. Optimizing Invregistry & Dispatch lookups in Material Cost calculation
CREATE INDEX IF NOT EXISTS idx_invregistry_prod_plan_release
ON invregistry (prod_plan_id, releseid);

CREATE INDEX IF NOT EXISTS idx_dispatch_release_created
ON dispatch (releseid, created_on);

-- 6. Optimizing Material Return lookups in Material Cost calculation
CREATE INDEX IF NOT EXISTS idx_return_material_plan_prod_status
ON return_material (prod_plan_id, product_id, created_on)
WHERE status = 'Moved';

-- 7. Optimizing Labour Cost JSON lookup by product_id
CREATE INDEX IF NOT EXISTS idx_labour_cost_product_compcode
ON labour_cost (compcode, product_id)
WHERE deleted IS NOT TRUE;

COMMIT;
