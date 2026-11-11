# Database Migration: Create Indexes for Production Planning Targets Optimization

**Date**: 2026-08-12  
**Target Tables**: `invregistry`, `dispatch`, `plan_details`, `order_items_extract`  
**Objective**: Create database indexes to resolve performance bottlenecks when loading, setting, or updating stage and daily targets in production planning list view.

---

## 1. Migration Execution SQL

Run the following SQL script to create the necessary indexes:

```sql
-- Indexes for invregistry table
CREATE INDEX IF NOT EXISTS idx_invregistry_prod_plan_id ON invregistry(prod_plan_id);

-- Indexes for dispatch table
CREATE INDEX IF NOT EXISTS idx_dispatch_releseid ON dispatch(releseid);

-- Indexes for plan_details table
CREATE INDEX IF NOT EXISTS idx_plan_details_order_extract_id ON plan_details(order_extract_id);

-- Indexes for order_items_extract table
CREATE INDEX IF NOT EXISTS idx_order_items_extract_order_items_id ON order_items_extract(order_items_id);
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
    tablename IN ('invregistry', 'dispatch', 'plan_details', 'order_items_extract')
ORDER BY 
    tablename, 
    indexname;
```
