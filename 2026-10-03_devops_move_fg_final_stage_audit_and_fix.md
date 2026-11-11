# DevOps Instruction: Fix & Audit Move FG to Store (Final Stage Final Process Enforcement)

**Date:** 2026-10-03  
**Module:** Production Execution / Finished Goods Inventory (`/productionexecution/list/move/:id`)  
**Components:**
- Frontend: `ProductionExecution/src/components/MoveToInventoryMultiStore.js`
- Backend API Endpoint: `GET /am-prod_plans/plan_to_stock?production_plan_id=<id>`
- Backend Target Service: `am-prod_plans` (Production Plan Service)

---

## 1. Executive Summary & Root Cause

### Business Rule
Only items that have completed the **absolute final stage** (`MAX(rank_id)`) and its **final process** (`is_final_process = TRUE`) represent Finished Goods (FG) eligible for transfer to Store Inventory.

### Issue Discovered (e.g., Plan `1764` / `PLN-001335`)
- Product `403` (`FG W U Shirt`) has stages:
  1. Stitching (`stage_id = 49`, `rank_id = 1`) -> `Dot` (is_final_process: true)
  2. Helper (`stage_id = 73`, `rank_id = 2`)
  3. QC Checking (`stage_id = 75`, `rank_id = 3`)
  4. Pouch Packing (`stage_id = 53`, `rank_id = 4`)
  5. Box Packing (`stage_id = 54`, `rank_id = 5`) -> `Box Packing` (is_final_process: true)
- Only **Stitching** was executed (`935` pcs). Pouch Packing and Box Packing had **`0`** recorded.
- The backend `/am-prod_plans/plan_to_stock` endpoint previously fetched the latest executed stage (Stitching `935`) instead of strictly requiring the **Final Stage** (Box Packing).
- Consequently, `935` pcs of stitched shirts were permitted to be moved into store (`moved_quantity: 935`), displaying that all produced quantity has already been moved, before packing was even carried out.

---

## 2. Frontend Fix Applied

In `ProductionExecution/src/components/MoveToInventoryMultiStore.js`:
- Imported `getPlan` to fetch the configured routing stages (`all_stages`) for the plan.
- Added `finalStageInfo` computation using `useMemo` to identify the product's highest rank stage (`max(rank_id)`) and its `is_final_process` activity.
- Displayed the **Final FG Stage & Process** clearly in the plan header:
  `Final FG Stage: Box Packing (Box Packing)`.
- Unified data refreshing via `loadPlanData` after every stock transfer or revert action.

---

## 3. Backend Fix (`/am-prod_plans/plan_to_stock`)

The backend SQL query constructing `outward_qty` in `plan_to_stock` strictly queries the maximum rank stage and its final process scoped by `compcode`.

### Target SQL Logic for Backend:
```sql
WITH plan_products AS (
    SELECT 
        ppp.production_plan_id,
        ppp.product_id,
        COALESCE(ppp.planned_quantity, pp.planed_quantity) AS planned_quantity,
        COALESCE(ppp.moved_quantity, 0) AS moved_quantity
    FROM production_plan_products ppp
    JOIN production_plan pp ON pp.production_plan_id = ppp.production_plan_id
    WHERE pp.compcode = :compcode AND pp.deleted IS NOT TRUE AND ppp.deleted IS NOT TRUE

    UNION ALL

    SELECT 
        pp.production_plan_id,
        pp.product_id,
        pp.planed_quantity AS planned_quantity,
        COALESCE(pp.moved_quantity, 0) AS moved_quantity
    FROM production_plan pp
    WHERE pp.compcode = :compcode AND pp.deleted IS NOT TRUE AND pp.product_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM production_plan_products ppp 
          WHERE ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
      )
),
final_stage_def AS (
    -- Identify the highest rank stage and final process per product scoped by tenant (compcode)
    SELECT DISTINCT ON (ps.product_id)
        ps.product_id,
        ps.stage_id AS final_stage_id,
        ps.rank_id AS final_rank_id,
        asm.config_id AS final_process_id
    FROM production_stages ps
    JOIN activity_stage_map asm ON asm.production_stage_id = ps.id AND asm.deleted IS NOT TRUE
    WHERE ps.deleted IS NOT TRUE 
      AND ps.compcode = :compcode 
      AND asm.is_final_process IS TRUE
    ORDER BY ps.product_id, ps.rank_id DESC NULLS LAST
),
outward_summary AS (
    -- Sum outward_qty ONLY for the final stage & final process execution log entries
    SELECT 
        pt.production_plan_id,
        COALESCE(el.product_id, pt.product_id, pp.product_id) AS product_id,
        COALESCE(SUM(el.outward_qty), 0) AS outward_qty
    FROM execution_log el
    JOIN plan_targets pt ON pt.plan_target_id = el.target_id AND pt.deleted IS NOT TRUE
    JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
    JOIN final_stage_def fsd ON fsd.product_id = COALESCE(el.product_id, pt.product_id, pp.product_id)
        AND el.stage_id = fsd.final_stage_id
        AND el.process_id = fsd.final_process_id
    WHERE el.deleted IS NOT TRUE AND pp.deleted IS NOT TRUE AND pp.compcode = :compcode
    GROUP BY pt.production_plan_id, COALESCE(el.product_id, pt.product_id, pp.product_id)
)
SELECT 
    pp.production_plan_id,
    pp.plan_unique,
    p.product_id,
    p.product_code,
    p.product_name,
    p.sku_id,
    COALESCE(prod.planned_quantity, pp.planed_quantity) AS planed_quantity,
    COALESCE(prod.moved_quantity, 0) AS moved_quantity,
    COALESCE(ow.outward_qty, 0) AS outward_qty,
    COUNT(*) OVER() AS total_results
FROM production_plan pp
JOIN plan_products prod ON prod.production_plan_id = pp.production_plan_id
JOIN products p ON p.product_id = prod.product_id AND p.deleted IS NOT TRUE
LEFT JOIN outward_summary ow ON ow.production_plan_id = pp.production_plan_id AND ow.product_id = prod.product_id
WHERE pp.deleted IS NOT TRUE AND pp.compcode = :compcode
ORDER BY pp.production_plan_id DESC;
```
*(Crucial: Never fall back to lower rank stages like Stitching/Cutting when `outward_qty` is 0 or null).*

---

## 4. Database Audit & Correction Scripts (PostgreSQL)

Save or run these scripts to audit and correct plans where premature moves occurred.

### 4.1 Audit Script: Identify Plans Moved Before Final Stage Execution
```sql
-- Audit: Find plans where moved_quantity > 0, but final stage has 0 or less output recorded
WITH plan_products AS (
    SELECT 
        ppp.production_plan_id,
        ppp.product_id,
        COALESCE(ppp.moved_quantity, 0) AS moved_quantity
    FROM production_plan_products ppp
    JOIN production_plan pp ON pp.production_plan_id = ppp.production_plan_id
    WHERE pp.compcode = :compcode AND pp.deleted IS NOT TRUE AND ppp.deleted IS NOT TRUE

    UNION ALL

    SELECT 
        pp.production_plan_id,
        pp.product_id,
        COALESCE(pp.moved_quantity, 0) AS moved_quantity
    FROM production_plan pp
    WHERE pp.compcode = :compcode AND pp.deleted IS NOT TRUE AND pp.product_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM production_plan_products ppp 
          WHERE ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
      )
),
final_stage_definition AS (
    SELECT DISTINCT ON (ps.product_id)
        ps.product_id,
        ps.stage_id,
        asm.config_id AS final_process_id
    FROM production_stages ps
    JOIN activity_stage_map asm ON asm.production_stage_id = ps.id AND asm.deleted IS NOT TRUE
    WHERE ps.deleted IS NOT TRUE
      AND ps.compcode = :compcode
      AND asm.is_final_process IS TRUE
    ORDER BY ps.product_id, ps.rank_id DESC NULLS LAST
),
actual_final_produced AS (
    SELECT 
        pt.production_plan_id,
        COALESCE(el.product_id, pt.product_id, pp.product_id) AS product_id,
        COALESCE(SUM(el.outward_qty), 0) AS actual_packed_qty
    FROM execution_log el
    JOIN plan_targets pt ON pt.plan_target_id = el.target_id AND pt.deleted IS NOT TRUE
    JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
    JOIN final_stage_definition fsd ON fsd.product_id = COALESCE(el.product_id, pt.product_id, pp.product_id)
        AND el.stage_id = fsd.stage_id 
        AND el.process_id = fsd.final_process_id
    WHERE el.deleted IS NOT TRUE AND pp.deleted IS NOT TRUE AND pp.compcode = :compcode
    GROUP BY pt.production_plan_id, COALESCE(el.product_id, pt.product_id, pp.product_id)
)
SELECT 
    pp.production_plan_id,
    pp.plan_unique,
    p.product_id,
    p.product_code,
    p.sku_id,
    prod.moved_quantity,
    COALESCE(afp.actual_packed_qty, 0) AS final_stage_produced_qty,
    (prod.moved_quantity - COALESCE(afp.actual_packed_qty, 0)) AS excess_moved_qty
FROM production_plan pp
JOIN plan_products prod ON prod.production_plan_id = pp.production_plan_id
JOIN products p ON p.product_id = prod.product_id AND p.deleted IS NOT TRUE
LEFT JOIN actual_final_produced afp ON afp.production_plan_id = pp.production_plan_id AND afp.product_id = prod.product_id
WHERE pp.compcode = :compcode
  AND pp.deleted IS NOT TRUE
  AND prod.moved_quantity > COALESCE(afp.actual_packed_qty, 0)
ORDER BY pp.production_plan_id DESC;
```

---

### 4.2 Correction Script Option A: Reset Prematurely Moved Plan Quantity
Use this if the stock was never physically in the FG warehouse (only Stitching was completed) and the move was a phantom ledger entry:

```sql
BEGIN;

-- 1. Create backup table before update
CREATE TABLE IF NOT EXISTS backup_premature_fg_moves_20261003 AS
SELECT 
    production_plan_id, 
    moved_quantity, 
    NOW() as backup_time
FROM production_plan
WHERE production_plan_id = 1764;

-- If multi-product table exists:
CREATE TABLE IF NOT EXISTS backup_premature_fg_moves_products_20261003 AS
SELECT 
    production_plan_id, 
    product_id, 
    moved_quantity, 
    NOW() as backup_time
FROM production_plan_products
WHERE production_plan_id = 1764;

-- 2. Reset moved_quantity for Plan 1764 to 0 so packing can be executed and moved properly
UPDATE production_plan
SET moved_quantity = 0
WHERE production_plan_id = 1764;

-- If multi-product table exists:
UPDATE production_plan_products
SET moved_quantity = 0
WHERE production_plan_id = 1764 AND product_id = 403;

-- 3. Also adjust the physical store inventory table if a stock ledger entry was generated
-- (Replace store_id and inventory table name according to your schema):
-- UPDATE stock_inventory 
-- SET available_qty = available_qty - 935 
-- WHERE product_id = 403 AND production_plan_id = 1764;

COMMIT;
```

---

### 4.3 Correction Script Option B: Backfill Box Packing Execution Log
If the 935 shirts were indeed physically completed and packed, but operators forgot to enter the **Box Packing** entries in the system:

```sql
BEGIN;

-- Insert execution log entry for Plan 1764, Box Packing stage (stage_id = 54, process_id = 27)
-- Note: Replace target_id, compcode, and emp_id with valid plan_target_id and tenant compcode
INSERT INTO execution_log (
    target_id,
    product_id,
    stage_id,
    process_id,
    outward_qty,
    opertaion_start_date,
    created_on,
    compcode,
    deleted
) VALUES (
    530546, -- relevant plan_target_id for stage 54
    403,
    54,     -- Box Packing stage_id
    27,     -- Box Packing process_id
    935,
    '2026-10-01 00:00:00',
    NOW(),
    1,      -- compcode
    FALSE
);

COMMIT;
```

---

## 5. Verification Checklist

1. **Verify Backend Response**:
   ```bash
   curl -s --url 'https://am-stagingapi.techgenzi.com/am-prod_plans/plan_to_stock?production_plan_id=1764' \
     -H 'Authorization: Bearer <TOKEN>' | jq .
   ```
   - Before Box Packing is executed: `outward_qty` must be `0`.
   - After Box Packing is executed: `outward_qty` must match the Box Packing quantity.
2. **Verify Frontend UI**:
   - Open `/productionexecution/list/move/1764`.
   - Check that the header displays: `Final FG Stage: Box Packing (Box Packing)`.
   - "Total Produced" reflects only the Box Packing output.
   - Movements cannot be submitted until the final packing stage produces output.
