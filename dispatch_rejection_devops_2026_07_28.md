# DevOps and Backend Guide: Dispatch Rejection Integration (2026-07-28)

This document outlines the required backend modifications and database migration steps to support rejection inputs during the dispatch step (`/am-delivery/`).

---

## 1. Database Schema Migration

The delivery items table (specifically `delivery_line_items` in the backend database) needs to be updated with four new columns to store rejection metrics per line item.

### SQL Migration Script (Alembic / Raw SQL)
```sql
-- Migration script generated on 2026-07-28
ALTER TABLE delivery_line_items 
ADD COLUMN rejected_quantity NUMERIC(10, 4) DEFAULT 0.0 NOT NULL,
ADD COLUMN is_rejected BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN rejection_action VARCHAR(50) DEFAULT NULL,
ADD COLUMN rejection_store_id INTEGER REFERENCES store_location(store_id) DEFAULT NULL;

-- Index to optimize querying of rejected items
CREATE INDEX IF NOT EXISTS idx_delivery_line_items_rejection ON delivery_line_items(is_rejected, rejection_store_id);
```

---

## 2. Backend API Changes

### A. Request Payload Validation Schema
Update the validation model for `POST /am-delivery/` items (located in the `delivery` service). The new fields must be **optional/nullable** to preserve backward compatibility.

**Python (Pydantic / Marshmallow Schema Example):**
```python
from typing import Optional, List
from pydantic import BaseModel

class DeliveryItemSchema(BaseModel):
    workOrderLineId: int
    quantity: float  # Good quality dispatch quantity
    serial_numbers: Optional[List[str]] = []
    store_id: Optional[int] = None
    
    # New Rejection Fields (Backward Compatible Defaults)
    rejected_quantity: Optional[float] = 0.0
    is_rejected: Optional[bool] = False
    rejection_action: Optional[str] = None
    rejection_store_id: Optional[int] = None
```

### B. Controller / Service Layer Logic
Within the `delivery` service logic:
1. **Save Delivery Details:** Persist `rejected_quantity`, `is_rejected`, `rejection_action`, and `rejection_store_id` into the `delivery_line_items` record.
2. **Inventory Registry Integration (Stock Deductions/Transfers):**
   - For `quantity` (Good Stock): Deduct from the source store.
   - For `rejected_quantity` where `is_rejected` is `True`:
     - If `rejection_action == "Return to Store"`: Retain or move the stock back to the designated `rejection_store_id`.
     - If `rejection_action == "Write Off"`: Deduct the quantity and log a write-off transaction.
     - If `rejection_action == "Rework"`: Move the quantity into the rework store designated by `rejection_store_id`.
