# Fabrico360 & AmNonOvens Manufacturing MCP Server

Standard Model Context Protocol (MCP) server exposing ERP data, shop-floor execution, and reporting APIs to **tiramai BizInsights** and external AI agents.

## Supported Tools (16)

### Reporting Suite
- `get_stock_movement_report`: Stock ledger, inward receipts, and dispatches.
- `get_order_lifecycle_report`: PO -> Cutting -> Sewing -> Finishing -> Dispatch.
- `get_dispatch_delivery_report`: Delivery Challans (DC) and invoice balances.
- `get_production_efficiency_report`: Line hourly outputs and SAM efficiency %.
- `get_qc_rejection_report`: Defect rates, scrap %, and failure classifications.
- `get_material_cost_report`: Actual vs standard BOM costs.
- `get_employee_efficiency_report`: Operator output, targets, piece-rates.
- `get_grn_inward_report`: Fabric inward lots and vendor OTIF.
- `get_plan_to_outward_report`: Planned target pieces vs packed cartons.
- `get_labour_cost_report`: Plan-wise and stage-wise actual vs estimated labour costs and variances.

### Operations & Planning
- `get_inventory_stock`: Warehouse balances and ROQL.
- `get_customer_purchase_orders`: CPOs and order status.
- `get_job_orders`: Job orders and line stage progress.
- `get_bill_of_materials`: Style BOMs and component ratios.
- `get_workforce_muster`: Line employee biometric attendance and workstation allocations.
- `get_consolidated_dashboard`: Plant-wide executive dashboard, KPIs, floor outputs, WIP, direct labour and overhead costs.

## Running Locally

```bash
# stdio mode (for Claude Desktop / Cursor)
python3 server.py

# SSE mode (for tiramai BizInsights remote web client)
MCP_TRANSPORT=sse MCP_PORT=8000 python3 server.py
```
