# Release Notes: Stage-Level Serialization & Tracking (Final Alignment)

This document outlines the required changes for deploying the Stage-Level Serialization feature. It includes database migrations, API changes, and deployment instructions.

## 1. Overview
The serialization feature allows production stages to be flagged for unit-level data capture. Individual units (identified by serial numbers) can now have their own parameter data (e.g., Voltage, Watts) persisted in a centralized registry.

---

## 2. Database Migration Scripts (PostgreSQL)

Execute these scripts in your production database to ensure the schema matches the updated backend models.

### Step 2.1: Update Existing Tables
Run these to add the new flags and JSON persistence columns.
```sql
-- 1. In 'production_config' database:
ALTER TABLE stage 
ADD COLUMN IF NOT EXISTS is_serialization BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS serialization_params JSONB;

-- 2. In 'production_stages' database:
ALTER TABLE production_stages 
ADD COLUMN IF NOT EXISTS is_serialization BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS serialization_params JSONB;

-- 3. In 'execution_log' database:
ALTER TABLE execution_log 
ADD COLUMN IF NOT EXISTS serialized_units JSONB;
```

### Step 2.2: Create / Update Tracking Table
Run this in the **execution_log** database to support unit-level tracking.
```sql
-- Create the registry table if it doesn't exist
CREATE TABLE IF NOT EXISTS item_serial_registry (
    id BIGSERIAL PRIMARY KEY,
    execution_log_id BIGINT,
    production_plan_id BIGINT,
    product_id BIGINT,
    serial_number VARCHAR(255),
    current_stage BIGINT,
    status VARCHAR(100) DEFAULT 'In Store',
    unit_data JSONB,
    compcode BIGINT,
    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_by VARCHAR(250),
    deleted_at TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);

-- IMPORTANT: If the table already existed, ensure the 'unit_data' column is present
ALTER TABLE item_serial_registry ADD COLUMN IF NOT EXISTS unit_data JSONB;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_item_serial_number ON item_serial_registry(serial_number);
CREATE INDEX IF NOT EXISTS idx_item_execution_log ON item_serial_registry(execution_log_id);
```

---

## 3. Backend Deployment Instructions

The following services have had their Python models and API definitions updated. They **MUST** be redeployed to production:

1.  **`production_config`**: Updated `Stage` model and API decorators.
2.  **`production_stages`**: Updated `ProdStages` model and detail view.
3.  **`execution_log`**: Updated `ExecutionLog` model and `bulkpost` logic to handle `serialized_units`.

---

## 4. API Reference

### Bulk Execution API
**`POST` /execution_log/rawmaterials/bulkpost-execution_rawmaterials**
The `serialized_units` array is now supported. All keys within the unit objects (e.g., "Voltage", "Serial No") are saved in the `unit_data` registry.

### Stage Parameter Configuration
**`GET` /production_config/stage/StageParams**
Includes `serialization_params` which triggers the dynamic data capture popup in the frontend.
