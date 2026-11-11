# Backend API Implementation Plan: Distinct Lot/Batch Architecture

**Date**: 2026-09-02  
**Target Services**: `grnotes`, `qualityCheck`, `invregistry`, `production_execution`, `delivery`  
**Database Script**: `2026-09-02_devops_backend_lot_architecture_migration.sql`

---

## 1. Summary of Database Schema Alignments

Based on the actual SQLAlchemy models in `AmNonOvens`, the following table columns are mapped:

| Service / Domain | SQLAlchemy Model & Table | Added Column | Purpose |
| :--- | :--- | :--- | :--- |
| **Inward / Procurement** | `GRNLineItems` (`grnlineitems`) | `supplier_lot_no` (VARCHAR 100, NULL) | Inward vendor lot captured from fabric roll / tag. |
| **Store & Inventory** | `InvRegistry` (`invregistry`) | `lot_no` (VARCHAR 100, NULL) | Stock movement lot (Supplier lot for RM, Production lot for FG). |
| **Plan Allocation** | `planAllocation` (`plan_allocation`) | `supplier_lot_no` (VARCHAR 100, NULL) | Soft reservation of lot quantities for a specific production plan. |
| **Store Balances** | `LocationProduct` (`store_product`) | `lot_no` (VARCHAR 100, NULL) | Available balance grouped by `(store_id, product_id, lot_no)`. |
| **Shop-Floor Execution** | `ProdExecution` (`prod_execution`) | `supplier_lot_no` & `production_lot_no` | Binds consumed RM lots to generated FG lots. |
| **Dispatch / Delivery** | `DeliveryLineItems` (`delivery_line_items`) | `production_lot_no` (VARCHAR 100, NULL) | Records the FG lot dispatched on the Delivery Challan (DC). |

---

## 2. Service-by-Service API Modifications

### 1. `grnotes` & `qualityCheck` Service
* **Model**: Add `supplier_lot_no = Column(VARCHAR(100), nullable=True)` to `GRNLineItems` in `grnotes/app/models/grnotes.py` and `qualityCheck/app/models/qc.py`.
* **API Inward (`POST /goods_note/`)**:
  * Extract `supplier_lot_no` from request payload line items and save to `grnlineitems`.
* **Stock Inward (`POST /goods_note/move-to-inventory/`)**:
  * Pass `supplier_lot_no` as `lot_no` when writing inward entries into `invregistry` and updating `store_product`.

---

### 2. `invregistry` Service
* **Model**: Add `lot_no` to `InvRegistry` and `LocationProduct`, and `supplier_lot_no` to `planAllocation`.
* **API (`GET /invregistry/available-stock/`)**:
  * Support optional breakdown by `lot_no`.
* **API Allocation (`POST /invregistry/plan-allocation/`)**:
  * Allow soft-reserving specific `supplier_lot_no` quantities for a `prod_plan_id`.
  * Calculate available balance as `Total in Store Product - SUM(Allocated in plan_allocation)`.

---

### 3. `production_execution` Service
* **Model**: Add `supplier_lot_no` and `production_lot_no` to `ProdExecution` in `production_execution/app/models/execution.py`.
* **API (`POST /am-production-execution/`)**:
  * Record input `supplier_lot_no` consumed during stage processing.
* **API ("Move FG to Store")**:
  * Accept `production_lot_no` in the payload and pass it to `invregistry` when recording finished goods into the store.

---

### 4. `delivery` Service
* **Model**: Add `production_lot_no` to `DeliveryLineItems` in `delivery/app/models/dc.py`.
* **API (`POST /am-delivery/`)**:
  * Accept `production_lot_no` per line item during DC creation.
  * Reduce inventory from `store_product` where `product_id = X` and `lot_no = production_lot_no`.

---

## 3. Backward Compatibility Safeguards

1. **All parameters are optional**: If a client does not send `supplier_lot_no` or `production_lot_no`, the APIs default them to `None` / `NULL`.
2. **Serializers remain stable**: Existing API response structures are preserved, adding the new lot fields cleanly without breaking current frontend components.
