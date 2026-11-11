-- ============================================================================
-- BACKEND DATABASE MIGRATION SCRIPT: Distinct Lot / Batch Architecture
-- Date: 2026-09-02
-- Scope: grnlineitems, invregistry, plan_allocation, prod_execution, delivery_line_items
-- Compatibility: All columns are NULL DEFAULT NULL (100% backward compatible)
-- ============================================================================

-- 1. GRN Line Items (Raw Material Supplier Lot capture)
ALTER TABLE grnlineitems 
ADD COLUMN IF NOT EXISTS supplier_lot_no VARCHAR(100) NULL DEFAULT NULL;
COMMENT ON COLUMN grnlineitems.supplier_lot_no IS 'Vendor/Supplier lot number from raw material tag/COA';

-- 2. Inventory Registry (Stock Inward/Outward/Movement Lot Number)
ALTER TABLE invregistry 
ADD COLUMN IF NOT EXISTS lot_no VARCHAR(100) NULL DEFAULT NULL;
CREATE INDEX IF NOT EXISTS idx_invregistry_lot_no ON invregistry(lot_no);
COMMENT ON COLUMN invregistry.lot_no IS 'Lot number (supplier lot for RM, production lot for FG)';

-- 3. Plan Allocation (Material Reservation per Production Plan & Lot)
ALTER TABLE plan_allocation 
ADD COLUMN IF NOT EXISTS supplier_lot_no VARCHAR(100) NULL DEFAULT NULL;
COMMENT ON COLUMN plan_allocation.supplier_lot_no IS 'Supplier lot number reserved for production plan';

-- 4. Store Product (Aggregated Store Balance per Product & Lot)
ALTER TABLE store_product 
ADD COLUMN IF NOT EXISTS lot_no VARCHAR(100) NULL DEFAULT NULL;
CREATE INDEX IF NOT EXISTS idx_store_product_lot_no ON store_product(product_id, store_id, lot_no);

-- 5. Production Execution (Material Issue & Multi-Lot Output Mapping)
ALTER TABLE prod_execution 
ADD COLUMN IF NOT EXISTS supplier_lot_no VARCHAR(100) NULL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS production_lot_no VARCHAR(100) NULL DEFAULT NULL;
COMMENT ON COLUMN prod_execution.supplier_lot_no IS 'Raw material supplier lot consumed in this stage';
COMMENT ON COLUMN prod_execution.production_lot_no IS 'Finished/Semi-finished product lot generated in this stage';

-- 6. Delivery Line Items (Finished Goods Dispatched Lot Number)
ALTER TABLE delivery_line_items 
ADD COLUMN IF NOT EXISTS production_lot_no VARCHAR(100) NULL DEFAULT NULL;
COMMENT ON COLUMN delivery_line_items.production_lot_no IS 'Production lot number dispatched to customer';
