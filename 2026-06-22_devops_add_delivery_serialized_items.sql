-- Migration: Create table delivery_serialized_items
-- Date: 2026-06-22

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
