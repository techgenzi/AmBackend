# DevOps Migration Guide: Store Sub-Location Support

This guide outlines the database migration steps required to support optional text-based sub-locations (Aisle, Rack, Shelf, Bin) for store inventory tracking.

---

## 1. Database Schema Migration

Execute the following SQL DDL query on the PostgreSQL database:

```sql
-- 1. Add sub_location column to store_product and invregistry tables (if not already added)
ALTER TABLE store_product ADD COLUMN IF NOT EXISTS sub_location VARCHAR(255);
ALTER TABLE invregistry ADD COLUMN IF NOT EXISTS sub_location VARCHAR(255);

-- 2. Drop the old unique constraint on store_product (if any)
-- Adjust the constraint name if it differs on the target environment.
ALTER TABLE store_product DROP CONSTRAINT IF EXISTS store_product_product_id_store_id_key;
ALTER TABLE store_product DROP CONSTRAINT IF EXISTS unique_product_store;

-- 3. Create a unique index on store_product that groups by product, store, and sub-location (if not already created)
-- Note: COALESCE is used so that multiple NULLs/empty strings are treated as a single "default" store location.
CREATE UNIQUE INDEX IF NOT EXISTS store_product_uniq_idx 
ON store_product (product_id, store_id, COALESCE(sub_location, ''));
```

---

## 2. Verification / Validation Queries

After running the migrations, verify that the columns have been added and constraints are in place:

### Query 1: Validate Table Columns
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name IN ('store_product', 'invregistry') 
  AND column_name = 'sub_location';
```
*Expected Result:* Returns rows for both tables showing `sub_location` with data type `character varying`.

### Query 2: Validate Unique Index
```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'store_product' 
  AND indexname = 'store_product_uniq_idx';
```
*Expected Result:* Returns the definition of the new `store_product_uniq_idx` index.
