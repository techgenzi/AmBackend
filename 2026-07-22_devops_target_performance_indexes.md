# Database Migration: Create Indexes for Production Plans, Targets, and Hourly Targets

**Date**: 2026-07-22  
**Target Tables**: `plan_targets`, `plan_details`, `production_plan`, `hourly_target`  
**Objective**: Create database indexes to resolve performance bottlenecks when loading, setting, or updating stage and daily targets.

---

## 1. Migration Execution SQL

Run the following SQL script to create the necessary indexes:

```sql
-- Indexes for plan_targets table
CREATE INDEX IF NOT EXISTS idx_plan_targets_production_plan_id ON plan_targets(production_plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_targets_compcode_deleted ON plan_targets(compcode, deleted);
CREATE INDEX IF NOT EXISTS idx_plan_targets_stage_id ON plan_targets(stage_id);

-- Indexes for plan_details table
CREATE INDEX IF NOT EXISTS idx_plan_details_production_plan_id ON plan_details(production_plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_details_compcode_deleted ON plan_details(compcode, deleted);

-- Indexes for production_plan table
CREATE INDEX IF NOT EXISTS idx_production_plan_compcode_deleted ON production_plan(compcode, deleted);

-- Indexes for hourly_target table
CREATE INDEX IF NOT EXISTS idx_hourly_target_plan_id ON hourly_target(plan_id);
CREATE INDEX IF NOT EXISTS idx_hourly_target_compcode_deleted ON hourly_target(compcode, deleted);
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
    tablename IN ('plan_targets', 'plan_details', 'production_plan', 'hourly_target')
ORDER BY 
    tablename, 
    indexname;
```
