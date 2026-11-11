# DevOps Deployment Instructions: Delivery Serialized Items Integration
**Date:** 2026-06-22

This document details the database migration required to deploy the serialized finished goods delivery integration.

## 1. Database Migration (PostgreSQL)

Run the SQL migration script [2026-06-22_devops_add_delivery_serialized_items.sql](file:///Users/rajkumarmuthuramalingam/Work/AmNonOvens/2026-06-22_devops_add_delivery_serialized_items.sql) on the production database (`ipss_db`):

```sql
CREATE TABLE IF NOT EXISTS delivery_serialized_items (
    id BIGSERIAL PRIMARY KEY,
    deliveryid BIGINT NOT NULL,
    delivery_line_item_id BIGINT NOT NULL,
    serial_number VARCHAR(255) NOT NULL,
    compcode BIGINT NOT NULL,
    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dsi_deliveryid ON delivery_serialized_items(deliveryid);
CREATE INDEX IF NOT EXISTS idx_dsi_serial ON delivery_serialized_items(serial_number);
```

## 2. Backend Service Redeployment

The **`delivery`** microservice has configuration and code updates.
Please rebuild and redeploy the `delivery` container / service once the schema updates are complete.
