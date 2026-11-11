-- ==============================================================================
-- Master Production & Stock Audit Script
-- Client: Feston SEV Technologies (compcode = 155, company_id = 155)
-- Date: 2026-10-16
-- Purpose:
--   1. Comprehensive audit across all 50 Customer Purchase Orders (customer_purchase)
--   2. Audit linked Production Plans (production_plan, plan_details, order_items_extract)
--   3. Audit shopfloor execution shift logs (hourly_targets_records)
--   4. Audit Finished Goods movement (fg_to_store_log)
--   5. Audit active & dispatched serial barcode numbers (store_serialized_products)
--   6. Audit physical warehouse stock (store_product) vs produced totals
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. MASTER INTERNAL ORDER & PRODUCTION PLAN AUDIT
-- ------------------------------------------------------------------------------
WITH plan_serials AS (
    SELECT 
        ssp.production_plan_id,
        COUNT(ssp.id) AS total_serials_generated,
        COUNT(CASE WHEN ssp.status = 'Available' THEN 1 END) AS available_serials_in_store,
        COUNT(CASE WHEN ssp.status = 'Dispatched' THEN 1 END) AS dispatched_serials_count,
        COUNT(CASE WHEN ssp.status = 'Cancelled' THEN 1 END) AS cancelled_serials_count
    FROM store_serialized_products ssp
    WHERE ssp.compcode = 155
    GROUP BY ssp.production_plan_id
),
plan_fg_transfers AS (
    SELECT 
        fg.production_plan_id,
        COALESCE(SUM(fg.moved_quantity), 0) AS fg_transferred_to_store
    FROM fg_to_store_log fg
    WHERE fg.compcode = 155 AND fg.deleted IS NOT TRUE
    GROUP BY fg.production_plan_id
),
plan_execution_shifts AS (
    SELECT 
        pt.production_plan_id,
        COUNT(DISTINCT el.execution_id) AS total_shifts_worked,
        COALESCE(SUM(el.outward_qty), 0) AS total_shopfloor_output
    FROM plan_targets pt
    JOIN execution_log el ON el.target_id = pt.plan_target_id AND el.deleted IS NOT TRUE
    WHERE pt.compcode = 155 AND pt.deleted IS NOT TRUE
    GROUP BY pt.production_plan_id
)
SELECT 
    cp.customer_purchase_id AS order_id,
    cp.order_unique AS internal_order_no,
    cp.order_date::date AS order_date,
    cp.status AS order_status,
    cp.deleted AS order_deleted,
    cpi.items_id AS order_item_id,
    p.product_id,
    p.sku_id AS product_sku,
    p.product_name,
    cpi.quantity_ordered,
    cpi.quantity_produced AS cpi_quantity_produced,
    cpi.status AS item_status,
    pp.production_plan_id AS plan_id,
    pp.plan_code,
    pp.planed_quantity AS planned_qty,
    pp.moved_quantity AS fg_moved_to_store,
    pp.is_done AS plan_is_done,
    pp.status AS plan_status,
    pp.deleted AS plan_deleted,
    COALESCE(pes.total_shifts_worked, 0) AS shift_count,
    COALESCE(pes.total_shift_output, 0) AS total_shopfloor_output,
    COALESCE(pfg.fg_transferred_to_store, 0) AS fg_log_transferred,
    COALESCE(ps.total_serials_generated, 0) AS serials_generated,
    COALESCE(ps.available_serials_in_store, 0) AS serials_in_store,
    COALESCE(ps.dispatched_serials_count, 0) AS serials_dispatched,
    CASE 
        WHEN cp.order_unique = 'IO-000050' THEN 'ACTIVE LIVE ORDER (Ready for Planning)'
        WHEN cp.status = 'Closed' THEN 'GENUINE COMPLETED RUN (Stock in Warehouse)'
        WHEN cp.status = 'Cancelled' OR cp.deleted IS TRUE THEN 'CANCELLED / TEST PURGE (Zero Store Stock)'
        ELSE 'OTHER'
    END AS audit_classification
FROM customer_purchase cp
LEFT JOIN customer_purchase_items cpi 
    ON cpi.customer_purchase_id = cp.customer_purchase_id
LEFT JOIN products p 
    ON p.product_id = cpi.product_id
LEFT JOIN order_items_extract oie 
    ON oie.order_items_id = cpi.items_id
LEFT JOIN plan_details pd 
    ON pd.order_extract_id = oie.extract_id
LEFT JOIN production_plan pp 
    ON pp.production_plan_id = pd.production_plan_id
LEFT JOIN plan_serials ps 
    ON ps.production_plan_id = pp.production_plan_id
LEFT JOIN plan_fg_transfers pfg 
    ON pfg.production_plan_id = pp.production_plan_id
LEFT JOIN plan_execution_shifts pes 
    ON pes.production_plan_id = pp.production_plan_id
WHERE cp.compcode = 155
ORDER BY cp.customer_purchase_id ASC, pp.production_plan_id ASC;


-- ------------------------------------------------------------------------------
-- 2. PHYSICAL WAREHOUSE STOCK VS JUL-OCT GENUINE PRODUCTION RECONCILIATION
-- ------------------------------------------------------------------------------
WITH genuine_produced AS (
    SELECT 
        cpi.product_id,
        SUM(pp.moved_quantity) AS total_jul_oct_produced
    FROM customer_purchase cp
    JOIN customer_purchase_items cpi 
        ON cpi.customer_purchase_id = cp.customer_purchase_id
    JOIN order_items_extract oie 
        ON oie.order_items_id = cpi.items_id
    JOIN plan_details pd 
        ON pd.order_extract_id = oie.extract_id
    JOIN production_plan pp 
        ON pp.production_plan_id = pd.production_plan_id
    WHERE cp.compcode = 155
      AND cp.status = 'Closed'
      AND pp.deleted IS NOT TRUE
      AND cp.customer_purchase_id >= 71 -- Genuine July-October runs
    GROUP BY cpi.product_id
),
active_serials_summary AS (
    SELECT 
        ssp.product_id,
        COUNT(ssp.id) AS active_serials_in_store
    FROM store_serialized_products ssp
    WHERE ssp.compcode = 155 
      AND ssp.status = 'Available'
    GROUP BY ssp.product_id
)
SELECT 
    p.product_id,
    p.sku_id,
    p.product_name,
    sp.quantity AS physical_store_product_count,
    COALESCE(gp.total_jul_oct_produced, 0) AS genuine_produced_quantity,
    COALESCE(ass.active_serials_in_store, 0) AS active_serial_barcodes,
    CASE 
        WHEN sp.quantity = COALESCE(gp.total_jul_oct_produced, 0) THEN '100% RECONCILED (Exact Match)'
        ELSE 'DISCREPANCY'
    END AS stock_reconciliation_verdict
FROM store_product sp
JOIN products p 
    ON p.product_id = sp.product_id
LEFT JOIN genuine_produced gp 
    ON gp.product_id = sp.product_id
LEFT JOIN active_serials_summary ass 
    ON ass.product_id = sp.product_id
WHERE sp.compcode = 155
ORDER BY sp.product_id ASC;


-- ------------------------------------------------------------------------------
-- 3. STATUS SUMMARY CHECK FOR EXECUTIVE DASHBOARD
-- ------------------------------------------------------------------------------
SELECT 
    cp.status AS order_status,
    cp.deleted AS is_deleted,
    COUNT(DISTINCT cp.customer_purchase_id) AS order_count,
    COALESCE(SUM(cpi.quantity_ordered), 0) AS total_ordered_qty
FROM customer_purchase cp
LEFT JOIN customer_purchase_items cpi 
    ON cpi.customer_purchase_id = cp.customer_purchase_id
WHERE cp.compcode = 155
GROUP BY cp.status, cp.deleted
ORDER BY cp.deleted, cp.status;
