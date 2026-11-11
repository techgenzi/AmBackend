# DevOps Release Instructions - Stock Cost Report Fields Addition
**Date:** 2026-07-27

## Overview
This release adds `unit_cost`, `last_grn_rate`, and `total_valuation` fields to the `/am-invregistry/stocklist/` endpoint to support inventory pricing, purchase rates, and valuation reports on the frontend.

## Database Dependencies
* **Table:** `products` (Column: `cost` - Numeric)
* **Table:** `grnlineitems` (Column: `rate_per_item` - Numeric)
* **Note:** This release relies entirely on the existing columns and tables. No database migrations/schema updates are required.

## Backend Changes Applied
1. **API Schema (`invregistry/app/api_doc.py`)**:
   * Added `unit_cost` (`fields.Float`), `last_grn_rate` (`fields.Float`), and `total_valuation` (`fields.Float`) to the `stock_list` model mapping.
2. **SQL Query (`invregistry/app/api/invregistry.py`)**:
   * Left-joined `grnlineitems` (using `DISTINCT ON` to extract the most recent `rate_per_item` as `last_grn_rate` for each product).
   * Updated the selected query fields:
     * `coalesce(p.cost, 0) as unit_cost`
     * `coalesce(grn_rate.last_grn_rate, 0) as last_grn_rate`
     * `coalesce(sp.product_count * coalesce(nullif(p.cost, 0), grn_rate.last_grn_rate, 0), 0) as total_valuation`
   * Updated `GROUP BY` statement to include `p.cost` and `grn_rate.last_grn_rate`.

## Deploy / Verify Steps
1. Deploy the updated backend code (`AmNonOvens`).
2. Restart the backend service.
3. Verify that the `/am-invregistry/stocklist/` endpoint outputs the new fields:
   ```json
   {
     "results": [
       {
         "product_id": 123,
         "sku_id": "SKU-001",
         "product_code": "PROD001",
         "product_name": "Raw Material A",
         "product_count": 100,
         "unit_cost": 0.00,
         "last_grn_rate": 25.50,
         "total_valuation": 2550.00
       }
     ]
   }
   ```
