# Database Migration: Create Indexes for Bill of Materials (BOM) Query Optimization

**Date**: 2026-08-24  
**Target Tables**: `bom`  
**Objective**: Create database indexes to optimize the recursive Bill of Materials query that partitions by `product_id` and orders by `bom_id DESC`.

---

## 1. Migration Execution SQL

Run the following SQL script to create the optimized index:

```sql
-- Create index to speed up the partition and ordering of BOM queries
CREATE INDEX IF NOT EXISTS idx_bom_product_id_bom_id_active 
ON bom (product_id, bom_id DESC) 
WHERE deleted IS NOT TRUE;
```

---

## 2. Verification Query

Verify that the index is created correctly in PostgreSQL:

```sql
SELECT 
    tablename, 
    indexname, 
    indexdef 
FROM 
    pg_indexes 
WHERE 
    tablename = 'bom'
ORDER BY 
    indexname;
```
