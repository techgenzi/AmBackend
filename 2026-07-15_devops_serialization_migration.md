# DevOps Migration Guide: Serialization for Inwarded Finished Goods (GRN/GRNQC)

This guide outlines the database migration steps required to support serializing imported finished goods during GRN/GRNQC and tracking them at a serial-number level in the stores.

---

## 1. Database Schema Migrations

Execute the following DDL queries on the database to update the product catalog and create the new tracking tables for serialized items:

```sql
-- Step 1: Add serialization capability fields to Products table
ALTER TABLE public.products 
ADD COLUMN IF NOT EXISTS is_serializable BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS serialization_params JSONB;

-- Step 2: Create the GRN Item Serials table to track serials scanned during inwarding
CREATE TABLE IF NOT EXISTS public.grn_item_serials (
    id BIGSERIAL PRIMARY KEY,
    grnotesid BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    serial_number VARCHAR(255) NOT NULL,
    qc_readings JSONB, -- Stores numeric/boolean parameter readings for this specific serial
    compcode BIGINT NOT NULL, -- Tenant code
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT false,
    
    CONSTRAINT uq_grn_serial UNIQUE (grnotesid, product_id, serial_number)
);

-- Step 3: Create Store Serialized Products table to track inventory at a serial level
CREATE TABLE IF NOT EXISTS public.store_serialized_products (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    store_id BIGINT NOT NULL,
    sub_location VARCHAR(255), -- Rack/Bin/Sub-Location details
    serial_number VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'Available', -- 'Available', 'Dispatched', 'Damaged', 'Reserved'
    grnotesid BIGINT, -- Linked origin GRN if imported
    compcode BIGINT NOT NULL, -- Tenant code
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT false,
    unit_data JSONB, -- Stores product-specific attributes (specification, passwords, etc)
    
    CONSTRAINT uq_store_product_serial UNIQUE (compcode, product_id, serial_number)
);
```

---

## 2. Backward Compatibility Verification Query
Use this query to verify that existing products that do not use serialization are still correctly represented, and to list all products now utilizing product-level serialization config:

```sql
SELECT product_id, product_code, product_name, is_serializable, compcode 
FROM public.products 
WHERE deleted IS NOT TRUE;
```

---

## 3. Service Deployment & Configuration

The following backend services have been updated to support the new unified serialization and must be rebuilt/redeployed:

1. **`Base_Config`** (adds support for uploading and managing serial numbers in `store_serialized_products`)
2. **`qualityCheck`** (adds support for validating and persisting serial numbers during GRN QC)
3. **`delivery`** (adds support for validating scanned serial numbers from either `item_serial_registry` or `store_serialized_products` and dispatching them accordingly)

