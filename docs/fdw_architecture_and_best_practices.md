# Foreign Data Wrapper (FDW) Architecture & Best Practices Guide

## 1. Executive Summary

This repository relies on PostgreSQL Foreign Data Wrapper (`postgres_fdw`) to link manufacturing and production planning databases with the centralized Human Resources Management (HRM) system.

Because foreign tables live on an external server across the network, queries that do not strictly isolate foreign scans can experience severe latency degradation—often causing **504 Gateway Time-out** errors (>60s) under standard web application traffic.

---

## 2. Foreign Server Infrastructure

All foreign tables in the database are routed to a single remote foreign server:

| Attribute | Details |
| :--- | :--- |
| **Server Name** | `hrm_live` |
| **FDW Extension** | `postgres_fdw` |
| **Remote Host** | `143.110.245.242` |
| **Remote Port** | `5432` |
| **Remote Database** | `ipss` |
| **Local Schema** | `public` |

---

## 3. Complete Inventory of Foreign Tables

The following **13 foreign tables** are linked from `hrm_live`:

| # | Foreign Table Name | Row Count (Live) | Description / Primary Usage | Risk Level |
| :---: | :--- | :---: | :--- | :---: |
| 1 | **`att`** | **`2,400,215`** | **Biometric Attendance Logs** (raw punches, `raw_attdate`, device logs). Used in cadre and attendance overhead calculations. | **CRITICAL** |
| 2 | **`hremploymast`** | **`8,707`** | **Employee Master** (idcard, full names, `daily_wages`, `ctc_amount`, department, designation). Core table for direct & indirect labour costing. | **HIGH** |
| 3 | **`employee_config_map`** | **`7,439`** | Employee skill and machine line assignments. | MEDIUM |
| 4 | **`globalparametercontrol`** | **`2,345`** | Global HRM configuration and parameter definitions. | LOW |
| 5 | **`euser`** | **`1,127`** | HRM user credentials and permissions. | LOW |
| 6 | **`designation_mast`** | **`379`** | Designation master lookup (`desgmastid`, `desg_name`). | LOW |
| 7 | **`user_companies`** | **`272`** | User to company access matrix. | LOW |
| 8 | **`config_master`** | **`90`** | Machine and process line master configuration. | LOW |
| 9 | **`department_mast`** | **`89`** | Department lookup (`deptmastid`, `dept_name`). | LOW |
| 10 | **`ot_config`** | **`45`** | Overtime threshold and eligibility rules. | LOW |
| 11 | **`config_map`** | **`40`** | Configuration mapping records. | LOW |
| 12 | **`ot_pay_config`** | **`3`** | Overtime payout rates. | LOW |
| 13 | **`mail_configure`** | **`1`** | HRM SMTP notification settings. | LOW |

---

## 4. Root Cause of 504 Time-outs: PostgreSQL 12+ CTE Inlining

### The Problem
In PostgreSQL 12 and later, Common Table Expressions (`WITH cte AS (...)`) are **inlined by default** unless explicitly prevented.

When joining local manufacturing tables (e.g., `execution_log`, `production_plan`, or `mv_daily_manufacturing_fact`) with foreign tables like `hremploymast`:
1. The planner lacks foreign table indexes and exact statistics.
2. The optimizer frequently selects a **Nested Loop Join**.
3. Under a nested loop, PostgreSQL executes a **`Foreign Scan` on the remote server once per outer row**.
4. Example benchmark:
   - 446 active workers on a single day resulted in **446 remote queries** fetching 8,707 rows each.
   - Total network wait time: **69.72 seconds**, triggering an Nginx `504 Gateway Time-out`.

### The Solution: CTE Materialization
By declaring `WITH ... AS MATERIALIZED (...)`:
```sql
WITH distinct_emps AS (
    SELECT DISTINCT emp_id FROM base_logs
),
hourly_wage AS MATERIALIZED (
    SELECT 
        h.hremploymastid as emp_id,
        h.idcardno as emp_code,
        trim(concat(h.fname, ' ', coalesce(h.mname, ''), ' ', coalesce(h.lname, ''))) as emp_name,
        CASE
            WHEN h.daily_wages = TRUE THEN round((NULLIF(trim(h.ctc_amount), '')::numeric / 8), 2)
            ELSE round((NULLIF(trim(h.ctc_amount), '')::numeric / (30 * 8)), 2)
        END as hourly_rate,
        ...
    FROM distinct_emps de
    JOIN hremploymast h ON h.hremploymastid = de.emp_id
)
```
- PostgreSQL creates an optimization barrier.
- It queries the remote server **exactly once**, populates an in-memory temporary cache, and joins locally.
- Runtime dropped from **69.72 seconds to 0.71 seconds (99% reduction)**.

---

## 5. Mandatory Engineering Rules for FDW Queries

When querying any of the 13 foreign tables (especially `hremploymast` and `att`), always adhere to the following rules:

### Rule 1: Always Pre-filter IDs Locally
Never join a foreign table directly against an unconstrained or wide local table. Always collect the exact required IDs first:
```sql
-- GOOD:
WITH target_emps AS (
    SELECT DISTINCT emp_id FROM local_fact_or_log WHERE ...
),
emp_data AS MATERIALIZED (
    SELECT h.* FROM target_emps te JOIN hremploymast h ON h.hremploymastid = te.emp_id
)
```

### Rule 2: Always Use `AS MATERIALIZED`
Always enforce `AS MATERIALIZED` on any CTE that reads from a foreign table to prevent the planner from pushing it into an inner loop of a nested loop.

### Rule 3: Narrow Timestamp Filters for `att` (2.4M rows)
Never query `att` without precise, index-friendly boundaries on `raw_attdate`:
```sql
-- GOOD:
WHERE a.raw_attdate >= cast(:start_date as timestamp)
  AND a.raw_attdate < cast(:start_date as timestamp) + interval '1 day'
```

### Rule 4: Apply Pagination Before Foreign Joins
In paginated listing endpoints, always apply `LIMIT` and `OFFSET` to the local IDs *before* performing joins with `hremploymast` or other FDW tables.
