# Labour Module SQL Optimization Documentation

**Target File:** [`labour/app/api/labour.py`](file:///Users/rajkumarmuthuramalingam/Work/AmNonOvens/labour/app/api/labour.py)  
**Target Endpoints:**
1. `/am-labour/labour_cost` (`LabourCost.get`)
2. `/am-labour/labour_cost_employee_wise` (`EmployeeWiseLabourCost.get`)

---

## 1. Overview of Bottlenecks

Both endpoints in `labour.py` aggregate production floor execution logs, hourly employee wages from an external HRM system (via PostgreSQL Foreign Data Wrapper `postgres_fdw`), incentive slabs, and bill of materials / product cost configurations.

Under production workloads or wide date ranges, both queries experience significant latency and time-outs (504 Gateway Time-out) due to four distinct architectural issues:

| Issue | Root Cause | Impact |
| :--- | :--- | :--- |
| **FDW Inlining & Re-scanning** | Common Table Expressions querying foreign table `hremploymast` (`143.110.245.242`) are inlined by PostgreSQL 12+, causing multiple remote network round-trips. | **30s – 60s+ latency (Time-outs)** |
| **Repeated Lateral JSON Extraction** | `est_cost` expands the JSON array `labour_cost.add_attribute` via `CROSS JOIN LATERAL json_array_elements(...)` inside an unmaterialized CTE, repeating JSON parsing on every row join. | **15s+ overhead** |
| **Correlated Scalar Subquery** | `order_unique` string aggregation executes an unindexed correlated subquery per result row (up to 3,450 times for a single day). | **2s – 4s overhead** |
| **Massive Nested JSON Serialization** | Large pagination requests (`results_per_page=435`) construct 3 levels of nested `jsonb_build_object` / `json_agg` trees (2.88 MB payload) inside PostgreSQL. | **~14s serialization & buffer overhead** |

---

## 2. Optimization Details for `/am-labour/labour_cost`

### Context
`LabourCost.get` calculates labour cost aggregated by date, shift hour, employee, and process/stage.

### Changes Applied
1. **Target Employee Filtering:**
   Extracts `DISTINCT emp_id` into a compact CTE first so downstream FDW lookups only fetch necessary employee records.
2. **`MATERIALIZED` FDW CTE (`emp_wages`):**
   Forces PostgreSQL to evaluate the foreign table `hremploymast` exactly once into a temporary memory buffer.

### Optimized Query Structure
```sql
WITH active_logs AS (
    SELECT 
        el.emp_id,
        el.target_id,
        el.stage_id,
        el.process_id,
        el.outward_qty,
        date(el.opertaion_start_date) as work_date,
        hc.time_value as work_hour,
        count(*) over(partition by el.emp_id, date(el.opertaion_start_date), hc.record_id) as logs_in_hour
    FROM execution_log el
    LEFT JOIN hour_config hc ON hc.record_id = el.hour_config_id
    WHERE el.deleted is not true and el.compcode = :compcode AND coalesce(el.outward_qty, 0) > 0 
      AND el.opertaion_start_date >= cast(:start_date as timestamp) 
      AND el.opertaion_start_date < cast(:end_date as timestamp) + interval '1 day'
),
target_emps AS MATERIALIZED (
    SELECT DISTINCT emp_id FROM active_logs
),
emp_wages AS MATERIALIZED (
    SELECT 
        hremploymastid as emp_id,
        COALESCE(
            CASE
                WHEN daily_wages = TRUE THEN round((NULLIF(trim(ctc_amount), '')::numeric / 8), 2)
                ELSE round((NULLIF(trim(ctc_amount), '')::numeric / (30 * 8)), 2)
            END,
            0
        ) as hourly_rate
    FROM hremploymast
    WHERE hremploymastid IN (SELECT emp_id FROM target_emps)
)
...
```

---

## 3. Optimization Details for `/am-labour/labour_cost_employee_wise`

### Context
`EmployeeWiseLabourCost.get` aggregates individual worker performance and cost across all 8 hours of a shift, outputting a nested JSON structure with per-hour breakdowns and production plans worked.

### Bottlenecks & Fixes

#### A. Materialize FDW Hourly Wage CTE (`hourly_wage AS MATERIALIZED`)
- **Before:** Without `MATERIALIZED`, `hourly_wage` is re-evaluated when joined against both `employee_cost` (outer aggregation) and `sub2` (nested shift plans).
- **Fix:**
  ```sql
  hourly_wage AS MATERIALIZED (
      SELECT 
          hremploymastid as emp_id,
          COALESCE(
              CASE
                  WHEN daily_wages = TRUE THEN round((NULLIF(trim(ctc_amount), '')::numeric / 8), 2)
                  ELSE round((NULLIF(trim(ctc_amount), '')::numeric / (30 * 8)), 2)
              END,
              0
          ) as hourly_rate,
          fname, lname, idcardno
      FROM hremploymast
      WHERE hremploymastid IN (SELECT DISTINCT emp_id FROM active_logs)
  )
  ```

#### B. Materialize JSON Parsing CTE (`est_cost AS MATERIALIZED`)
- **Before:** `est_cost` expands `json_array_elements(COALESCE(lc.add_attribute::json, '[]'::json))` dynamically for every join iteration with `sub2`.
- **Benchmark:** Evaluating this unmaterialized took **15.20s**; materializing it dropped evaluation to **1.39s** (10.9x speedup).
- **Fix:**
  ```sql
  est_cost AS MATERIALIZED (
      SELECT 
          lc.product_id,
          (elem->>'stage_id')::int AS stage_id,
          sum((elem->>'rate')::numeric) AS rate
      FROM labour_cost lc
      JOIN (
          SELECT DISTINCT COALESCE(pt.product_id, pp.product_id) as product_id
          FROM apportioned_logs al
          JOIN paginated_employees pe ON pe.emp_id = al.emp_id
          JOIN plan_targets pt ON pt.plan_target_id = al.target_id
          JOIN production_plan pp ON pp.production_plan_id = pt.production_plan_id
          WHERE COALESCE(pt.product_id, pp.product_id) IS NOT NULL
      ) ep ON ep.product_id = lc.product_id
      CROSS JOIN LATERAL json_array_elements(COALESCE(lc.add_attribute::json, '[]'::json)) AS elem
      WHERE lc.compcode = :compcode and lc.deleted is not true
      GROUP BY lc.product_id, stage_id
  )
  ```

#### C. Pre-aggregate Customer Orders into CTE (`plan_orders AS MATERIALIZED`)
- **Before:** Correlated scalar subquery executed inside `sub2` for each employee-hour-plan row:
  ```sql
  COALESCE((
      SELECT string_agg(DISTINCT cp.order_unique, ', ')
      FROM plan_details pd
      JOIN order_items_extract oie ON oie.extract_id = pd.order_extract_id
      JOIN customer_purchase_items cpi ON cpi.items_id = oie.order_items_id
      JOIN customer_purchase cp ON cp.customer_purchase_id = cpi.customer_purchase_id
      WHERE pd.production_plan_id = pp.production_plan_id AND pd.deleted IS NOT TRUE
  ), '-') as order_unique
  ```
- **Fix:** Pre-aggregate unique order strings once for only the active production plans on that day:
  ```sql
  plan_orders AS MATERIALIZED (
      SELECT 
          pd.production_plan_id,
          string_agg(DISTINCT cp.order_unique, ', ') as order_unique
      FROM plan_details pd
      JOIN order_items_extract oie ON oie.extract_id = pd.order_extract_id
      JOIN customer_purchase_items cpi ON cpi.items_id = oie.order_items_id
      JOIN customer_purchase cp ON cp.customer_purchase_id = cpi.customer_purchase_id
      WHERE pd.deleted IS NOT TRUE 
        AND pd.production_plan_id IN (
            SELECT DISTINCT pt.production_plan_id 
            FROM apportioned_logs al
            JOIN plan_targets pt ON pt.plan_target_id = al.target_id
        )
      GROUP BY pd.production_plan_id
  )
  ```
  Then join via `LEFT JOIN plan_orders po ON po.production_plan_id = pp.production_plan_id` and select `COALESCE(po.order_unique, '-') as order_unique`.

---

## 4. Benchmark Summary (Live Staging Database)

| Scenario / Configuration | Original Runtime | Optimized Runtime | Speedup |
| :--- | :---: | :---: | :---: |
| `/am-labour/labour_cost` (30 days date range) | **>60.0s (504 Time-out)** | **0.82s** | **~73x** |
| `/am-labour/labour_cost_employee_wise` (Page size = 20) | 3.40s | **0.66s** | **5.1x** |
| `/am-labour/labour_cost_employee_wise` (Page size = 100) | 8.90s | **1.78s** | **5.0x** |
| `/am-labour/labour_cost_employee_wise` (Page size = 435, full day) | 18.42s | **16.74s** * | **1.1x** * |

> **Note on Page Size 435:**
> In the 435 employee request, actual database calculation and relational scanning takes only **~2.2 seconds**. The remaining **~14.5 seconds** is consumed exclusively by PostgreSQL building 3,450 nested JSON structures and returning a **2.88 MB** raw JSON payload. Client-side pagination (defaulting to 20–50 items) is strongly recommended for standard page loads.
