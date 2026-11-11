# Technical Findings & Root Cause Analysis: Production Cost Report Discrepancies

**Date:** 2026-09-30  
**Endpoints Investigated:** 
- `/am-customer-purchase-order/plan_cost` (Customer Purchase / Production Cost Report)
- `/reports/productioncostreport` (Frontend UI & Excel Export)

---

## 1. Executive Summary

During single-day and date-range queries on the Production Cost Report (e.g. `2026-09-28`), reporting values displayed severe discrepancies:
1. **Actual Material Costs doubled / tripled** across orders containing multi-product production plans (e.g. Order `CO-000085` showed `₹37,236.00` instead of `₹18,618.00`).
2. **Estimated Material Costs exploded** into tens of crores (e.g. `₹31,89,23,539.37` and `₹5,10,65,365.68` for individual order line items totaling over `₹61.9 Crores`).

Detailed investigation isolated two distinct root causes:
- An **aggregation & allocation defect** across plans containing multiple product lines.
- A **Unit of Measure (UOM) / Packaging conversion omission** in estimated material cost calculation.

---

## 2. Issue 1: Actual Material Cost Multiplication

### Root Cause
Production plans can have multiple product lines (e.g. child cutting parts alongside the finished good SKU).
In `customer_purchase/app/api/helper.py`:
- `get_material_cost_bulk(production_plan_ids)` computes the total material consumption cost **per plan ID**, returning:
  ```python
  { 1781: 18618.0 } # Keyed solely by production_plan_id
  ```

In `customer_purchase/app/api/customer_purchase.py` (`PlanCost`):
```python
for product in product_data:
    plans = product.get('data', [])
    for plan in plans:
        plan_id = plan.get('production_plan_id')
        if not plan.get('is_done'):
            # The entire plan's material cost was assigned to EVERY product under the plan:
            plan['total_material_cost'] = float(actual_material_bulk.get(plan_id, 0))
    # Product sum accumulated the plan cost:
    product['sum_total_material_cost'] = sum(float(p.get('total_material_cost') or 0) for p in plans)
```

In the frontend (`Report.js` and `ExcelDownload.js`):
- Both the UI cards and the order summary rows iterated through every product and summed `p.sum_total_material_cost`.
- Because plan `1781` appeared under both Product 1 and Product 2, `₹18,618.00` was added twice (`₹37,236.00`), artificially doubling the order-level and grand total actual material cost.

### Fix Implemented
1. **Frontend (`AmNonOvens-AM-FE` - Commit `95082101`):**
   - In [`Report.js`](file:///Users/rajkumarmuthuramalingam/Work/AmNonOvens-AM-FE/Reports/src/components/ProductionCostReport/Report.js) and [`ExcelDownload.js`](file:///Users/rajkumarmuthuramalingam/Work/AmNonOvens-AM-FE/Reports/src/components/ProductionCostReport/ExcelDownload.js):
     - Maintained a `Set` of visited `production_plan_id`s per order.
     - Summed `actual_material_cost` and `actual_labour_cost` across **unique plans**, preventing duplicate multiplication in order headers, badges, and grand totals.
2. **Backend (`AmNonOvens` - `customer_purchase/app/api/customer_purchase.py`):**
   - Updated the response builder to track `seen_actual_material_plans`.
   - The actual material cost is assigned once per unique `production_plan_id` per order, while secondary product lines receive `0.0`.

---

## 3. Issue 2: Estimated Material Cost UOM & Packaging Mismatch

### Root Cause
In `customer_purchase/app/api/helper.py`:
```sql
SELECT pp.production_plan_id, 
       COALESCE(pp.product_id, ppp.product_id) AS product_id, 
       COALESCE(SUM(COALESCE(pp.planed_quantity, ppp.planned_quantity) 
                    * COALESCE(bc.quantity::numeric, 0) 
                    * COALESCE(mc.cost, 0)), 0) AS estimated_cost
FROM production_plan pp
LEFT JOIN production_plan_products ppp ON ppp.production_plan_id = pp.production_plan_id AND ppp.deleted IS NOT TRUE
LEFT JOIN bom b ON b.product_id = COALESCE(pp.product_id, ppp.product_id) AND b.compcode = :compcode AND b.deleted IS NOT TRUE
LEFT JOIN bom_component bc ON bc.bom_id = b.bom_id AND bc.deleted IS NOT TRUE
LEFT JOIN material_cost mc ON mc.product_id = bc.product_id
WHERE pp.production_plan_id IN :production_plan_ids
GROUP BY pp.production_plan_id, COALESCE(pp.product_id, ppp.product_id);
```

#### Why it produced astronomical values (e.g. ₹31.89 Crores):
- **Planned Quantity Unit vs. BOM Unit:**
  - Orders and production plans for items like `SKU-000283` were planned in units of **Carton Box** (e.g. 312 carton boxes).
  - The Bill of Materials (`bom_component`) specifies component raw materials either per base piece or per pre-pack batch.
  - When the SQL multiplied `312 * bc.quantity * mc.cost` directly, it ignored packaging relationships and unit conversions.

---

## 4. Location of UOM & Conversion Information in the Database

The system maintains UOM and pack-conversion information across three primary locations:

| Source | Table & Columns | Purpose & How It Is Used in Code |
| :--- | :--- | :--- |
| **Packaging / Kits** | `package_items`<br>• `pakage_id`<br>• `product_id`<br>• `needded_count` | Defines child product multipliers inside a packaged SKU.<br>Used in `customer_purchase/app/api/helper.py` (`data_extract_from_package`) and `bill_of_material/app/api/bom.py` (`ProductGetField`):<br>`(COALESCE(pc.needded_count, 1)::numeric * quantity_ordered)` |
| **Product Master** | `products`<br>• `product_id`<br>• `uom_id`<br>• `base_uom`<br>• `product_count` | `product_count` stores the pack size multiplier (e.g. number of pieces per carton box). Used in `store_product`, `invregistry`, and `production_plans/app/api/post_module.py`. |
| **BOM Definition** | `bom`<br>• `uom`<br>`bom_component`<br>• `quantity`<br>• `uom` | Defines the reference unit for the BOM and the component consumption per unit of that BOM. |

---

## 5. Architectural Recommendations & Next Steps

1. **Deployment of Applied Fixes:**
   - **Frontend:** Commit `95082101` on branch `brahadeesh-am` contains deduplication for table rows, badges, and Excel export.
   - **Backend:** Code updated in `customer_purchase/app/api/customer_purchase.py` to prevent redundant plan material cost assignment across products.
2. **Estimated Cost Query Normalization (`helper.py`):**
   - Update `get_estimated_material_cost_bulk` to join `package_items` or evaluate `products.product_count` when calculating BOM requirements for packaged SKUs, matching the calculation pattern used in `bill_of_material/app/api/bom.py`.
3. **Database Performance Indexing:**
   - Await completion of the DevOps index migrations (`2026-09-28_devops_cost_reports_performance_indexes.sql`) before pushing heavy backend migrations to staging.
