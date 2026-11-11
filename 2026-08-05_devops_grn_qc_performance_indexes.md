# Database Migration: Create Performance Indexes for GRN, Quality Control, and Inventory Ledger

**Date**: 2026-08-05  
**Target Tables**: `grnotes`, `grnlineitems`, `invregistry`, `joline_items`  
**Objective**: Create database indexes to resolve performance bottlenecks during Goods Received Note (GRN) operations, Quality Control (QC), stock moves, and inventory audits/stock list generation.

---

## 1. Migration Execution SQL

Run the following SQL script to create the necessary indexes on the PostgreSQL database:

```sql
-- Indexes for grnlineitems table
CREATE INDEX IF NOT EXISTS idx_grnlineitems_product_id ON grnlineitems(product_id);
CREATE INDEX IF NOT EXISTS idx_grnlineitems_grnotesid ON grnlineitems(grnotesid);

-- Indexes for grnotes table
CREATE INDEX IF NOT EXISTS idx_grnotes_compcode ON grnotes(compcode);
CREATE INDEX IF NOT EXISTS idx_grnotes_joborderid ON grnotes(joborderid);

-- Indexes for invregistry table
CREATE INDEX IF NOT EXISTS idx_invregistry_product_id ON invregistry(product_id);
CREATE INDEX IF NOT EXISTS idx_invregistry_compcode ON invregistry(compcode);
CREATE INDEX IF NOT EXISTS idx_invregistry_ref_id ON invregistry(ref_id);

-- Indexes for joline_items table
CREATE INDEX IF NOT EXISTS idx_joline_items_jo_id ON joline_items(jo_id);
CREATE INDEX IF NOT EXISTS idx_joline_items_compcode ON joline_items(compcode);
```

---

## 2. Verification Query

Verify that the indexes are created correctly in PostgreSQL:

```sql
SELECT 
    tablename, 
    indexname, 
    indexdef 
FROM 
    pg_indexes 
WHERE 
    tablename IN ('grnotes', 'grnlineitems', 'invregistry', 'joline_items')
ORDER BY 
    tablename, 
    indexname;
```
