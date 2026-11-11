# Technical Alignment & Reconciliation Review: Consolidated Dashboard vs. WIP Labour Cost Report vs. Customer Excel

**Document Date:** October 8, 2026  
**Reference Dataset:** Production Date: `2026-10-05` (5th Oct 2026)  
**Primary Files Analyzed:**
- `5th Oct (1).xlsx` (Customer Excel Workings & Final Comparison)
- `/am-labour/labour_cost_employee_wise` (WIP Labour Cost Report API)
- `/am-dashboard/consolidated_dashboard` / `mv_daily_manufacturing_fact` (Consolidated Dashboard)

---

## Executive Summary

The customer confirmed that the **WIP Labour Cost Report** (`/am-labour/labour_cost_employee_wise`) matches their manual Excel calculation for October 5th, 2026 at **₹1,29,070.59**. However, discrepancies were raised when comparing this with the **Consolidated Dashboard**.

| System / Report | Total Actual Labour Cost (₹) | Total Estimated Labour Cost (₹) | Variance (Est - Act) (₹) |
|---|---|---|---|
| **Customer Excel (`5th Oct (1).xlsx`)** | **₹1,29,070.59** | ₹1,42,430.28 | +₹13,359.69 |
| **WIP Labour Cost Report API** | **₹1,29,070.59** | *(Not calculated at summary)* | — |
| **Consolidated Dashboard (Current MV)** | **₹1,34,262.98** | **₹1,32,111.97** | -₹2,151.01 |
| **Reconciliation Gap** | **+₹5,192.39** | -₹10,318.31 | — |

---

## 1. Actual Labour Cost Alignment (The ₹5,192.39 Gap)

### 1.1 Root Cause Analysis
- **WIP Labour Cost Report & Customer Excel (Wage-Apportionment Method):**
  Treats employee daily CTC/salary as the true actual expenditure. For an employee on daily wages of ₹320:
  $$\text{Hourly Wage} = \frac{\text{Daily Wage}}{8} = ₹40.00/\text{hr}$$
  $$\text{Hour Cost} = \frac{\text{Hourly Wage}}{\text{Logs in that hour}}$$
  The employee's total actual cost for the day is capped at **₹320.00**.

- **Consolidated Dashboard (Current `execution_log.labour_cost` Method):**
  Currently computes `SUM(el.labour_cost)`. In several production logs, `el.labour_cost` was populated as **Piece-Rate Rate $\times$ Outward Quantity**:
  $$\text{Cost} = 747 \text{ pcs} \times ₹0.6667 = ₹498.00 \text{ (in a single hour)}$$
  For high-output workers (e.g., Emp `37265`), total recorded `labour_cost` reached **₹3,376.67**, when their true daily salary is only **₹320.00**.

### 1.2 Top 5 Distorted Employees
| Employee ID | Name | Actual Daily Wage (CTC) | Total Logged in `execution_log` | Excess Distorting Dashboard |
|---|---|---|---|---|
| **37265** | Alagumeena A | ₹320.00 | ₹3,376.67 | **+₹3,056.67** |
| **40857** | K. Priya | ₹315.04 | ₹3,350.81 | **+₹3,035.77** |
| **40726** | Pandiselvi M | ₹315.04 | ₹3,348.83 | **+₹3,033.79** |
| **37156** | Shanmuga Priya | ₹346.00 | ₹2,018.31 | **+₹1,672.31** |
| **41419** | R. Pandeeswari | ₹341.04 | ₹1,989.19 | **+₹1,648.15** |

### 1.3 Alignment Required
Update the Consolidated Dashboard Materialized View (`mv_daily_manufacturing_fact`) to use the **Wage-Apportionment formula** from the WIP report instead of raw `el.labour_cost`. This immediately brings the Consolidated Dashboard company-wide actual cost down to **₹1,29,070.59**, matching Excel to the exact rupee.

---

## 2. Block / Floor Attribution Alignment & Customer Claim Review

### 2.1 The Customer's Claim
> *"Employees would not be shifted to any other block in the same day."*

### 2.2 Concrete Findings from the Customer's Own Data (`5th Oct (1).xlsx`)
In the customer's own **`Working`** sheet, **11 employees** have outward quantities logged across **both Block B5 and Block B1** on October 5th, 2026:

| Employee ID | Name | Row in `Working` | Plan ID | Line Name | Logged Block | Qty |
|---|---|---|---|---|---|---|
| **1004** | Mariyammal Duraipandi | Row 4<br>Row 5<br>Row 6 | PLN-001364<br>PLN-001365<br>PLN-001358 | Medline Cutting Line 1<br>Medline Cutting Line 1<br>Medline Cutting Line 1 | **B5**<br>**B5**<br>**B1** | 2,084<br>1,781<br>531 |
| **1208** | Jeyachitra | Row 64<br>Row 65<br>Row 66 | PLN-001364<br>PLN-001365<br>PLN-001358 | Medline Cutting Line 1<br>Medline Cutting Line 1<br>Medline Cutting Line 1 | **B5**<br>**B5**<br>**B1** | 2,084<br>1,781<br>531 |
| **1389** | Kasthuri Prakash | Rows 91–93 | PLN-001364 / 1365 / 1358 | Medline Cutting Line 1 | **B5 & B1** | Multi-plan |
| **1560** | P. Jeeva | Rows 145–147 | PLN-001364 / 1365 / 1358 | Medline Cutting Line 1 | **B5 & B1** | Multi-plan |
| **1920** | M Selvi | Rows 201–203 | PLN-001364 / 1365 / 1358 | Medline Cutting Line 1 | **B5 & B1** | Multi-plan |
| **2230** | Alagu Panneer Selvam | Rows 245–247 | PLN-001364 / 1365 / 1358 | Medline Cutting Line 1 | **B5 & B1** | Multi-plan |
| **2242** | Maheswari M | Rows 251–253 | PLN-001364 / 1365 / 1358 | Medline Cutting Line 1 | **B5 & B1** | Multi-plan |
| **3357** | Gobinath | Rows 395–397 | PLN-001364 / 1365 / 1358 | Medline Cutting Line 1 | **B5 & B1** | Multi-plan |
| **3983** | Janaki P | Rows 451–453 | PLN-001364 / 1365 / 1358 | Medline Cutting Line 1 | **B5 & B1** | Multi-plan |
| **4567** | Sangeeta N | Rows 511–513 | PLN-001364 / 1365 / 1358 | Medline Cutting Line 1 | **B5 & B1** | Multi-plan |
| **6638** | Kasthoori P | Rows 681–683 | PLN-001364 / 1365 / 1358 | Medline Cutting Line 1 | **B5 & B1** | Multi-plan |

### 2.3 Why the Customer Believed No Shifting Occurred
In the customer's sheet `Labour Cost Report`, Column E assigns each worker to a block using:
```excel
=XLOOKUP(A2, Working!C:C, Working!K:K, 0, 0, 1)
```
- Because `XLOOKUP` stops at the **first occurrence**, Employee `1004` matched Row 4 (`B5`) and had **100% of her salary credited to B5**.
- Her output on Plan `PLN-001358` under `B1` (Row 6) was omitted from cost assignment in their spreadsheet.
- **Operational Reality:** The workers remained physically at `Medline Cutting Line 1`, but the line processed jobs booked to **two different cost centers (B1 and B5)** in the same shift.

---

## 3. Estimated Labour Cost Alignment (The ₹10,318.31 Gap)

### 3.1 Comparison of Estimation Formulas
- **Customer's Excel Formula (`Working` Sheet, Column X):**
  $$= W2 \times U2 = \text{Stage Rate} \times \text{Total Day Qty}$$
  The customer extracted whether an operation is the final process of a stage into Column V (`Final Process`), but **failed to apply Column V in their Column X formula**. Consequently, multi-process stages multiplied the entire stage rate multiple times across separate sub-operations.
- **Consolidated Dashboard (Materialized View):**
  Enforces `WHERE el.process_id = slp.last_process_id`. Standard stage labour cost is credited **only once per physical piece produced at the end of each stage**.

> **Conclusion on Estimates:** The Consolidated Dashboard formula ($₹1,32,111.97$) is statistically and operationally superior to the customer's Excel Col X ($₹1,42,430.28$) because it prevents double-crediting multi-operation stages.

---

## 4. Alignment Strategy & Decision Options

### Option 1: True Operational Apportionment (Recommended)
- **Actuals:** Use the WIP wage apportionment CTE in `mv_daily_manufacturing_fact`. Wages are prorated to the exact plan/floor where work was performed.
- **Total:** Reconciles 100% to **₹1,29,070.59**.
- **Floor Breakdown:** Floors receive true cost matching the output produced without cross-subsidization.

### Option 2: Primary-Floor Assignment (Strict Alignment with Customer Excel)
- **Actuals:** If the customer mandates that an employee's cost cannot be split between floors, assign 100% of the employee's wage to their **primary floor** (the floor where they logged the most hours/output on that day).
- **Floor Breakdown:** Will replicate the customer's Excel Block totals (`B1: ₹60,300.29`, `B5: ₹63,369.90`, `3M: ₹5,400.40`).

---

## 5. Next Steps for Implementation
1. Review this document with stakeholders / customer.
2. Confirm preference between **Option 1 (Prorated by Plan)** vs **Option 2 (Primary Floor Only)**.
3. Apply the updated CTE into [`2026-10-05_devops_daily_manufacturing_fact_mv.sql`](file:///Users/rajkumarmuthuramalingam/Work/AmNonOvens/2026-10-05_devops_daily_manufacturing_fact_mv.sql) and refresh `mv_daily_manufacturing_fact`.
