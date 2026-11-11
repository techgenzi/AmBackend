# Fabrico360 / AmNonOvens MCP Server Connection Guide

## Server Overview
* **Server Name:** `Fabrico360-Manufacturing-MCP`
* **Transport:** Server-Sent Events (SSE) + HTTP POST JSON-RPC
* **Base URL:** `https://ipssapi.techgenzi.com`
* **SSE Stream Endpoint:** `https://ipssapi.techgenzi.com/mcp/sse`
* **Messages Endpoint (POST):** `https://ipssapi.techgenzi.com/mcp/messages/?session_id=<SESSION_ID>`
* **Authentication:** HTTP Basic Authentication
  * **Username:** `rajkumar`
  * **Password:** `techgenzi password 2026`
  * **Authorization Header:** `Authorization: Basic cmFqa3VtYXI6dGVjaGdlbnppIHBhc3N3b3JkIDIwMjY=`

---

## 1. Claude Desktop Configuration

Edit your Claude Desktop configuration file:
* **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
* **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add the `ipssapi-dev` entry under `mcpServers`:

```json
{
  "mcpServers": {
    "ipssapi-dev": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://ipssapi.techgenzi.com/mcp/sse",
        "--header",
        "Authorization: Basic cmFqa3VtYXI6dGVjaGdlbnppIHBhc3N3b3JkIDIwMjY="
      ]
    }
  }
}
```

> **Note on Native SSE in Claude Desktop:**
> If using a client that supports remote SSE URLs directly without `mcp-remote`:
> ```json
> {
>   "mcpServers": {
>     "ipssapi-dev": {
>       "url": "https://ipssapi.techgenzi.com/mcp/sse",
>       "headers": {
>         "Authorization": "Basic cmFqa3VtYXI6dGVjaGdlbnppIHBhc3N3b3JkIDIwMjY="
>       }
>     }
>   }
> }
> ```

---

## 2. Cursor IDE Configuration

In `~/.cursor/mcp.json` or **Cursor Settings > Features > MCP > Add New Server**:
* **Name:** `ipssapi-dev`
* **Type:** `sse`
* **URL:** `https://ipssapi.techgenzi.com/mcp/sse`
* **Headers:**
  ```json
  {
    "Authorization": "Basic cmFqa3VtYXI6dGVjaGdlbnppIHBhc3N3b3JkIDIwMjY="
  }
  ```

---

## 3. Interactive Web Testing via MCP Inspector

To inspect, discover schemas, and trigger tools in a browser GUI:

```bash
npx @modelcontextprotocol/inspector
```
1. Set **Transport Type** to `SSE`.
2. Set **URL** to: `https://ipssapi.techgenzi.com/mcp/sse`
3. Add **Custom Header**:
   * Header: `Authorization`
   * Value: `Basic cmFqa3VtYXI6dGVjaGdlbnppIHBhc3N3b3JkIDIwMjY=`
4. Click **Connect**.

---

## 4. Testing via cURL (Terminal)

### Step 1: Open the SSE listener in Terminal 1
```bash
curl -N -i -u "rajkumar:techgenzi password 2026" "https://ipssapi.techgenzi.com/mcp/sse"
```
The server will return:
```http
event: endpoint
data: /mcp/messages/?session_id=<SESSION_ID>
```

### Step 2: Send JSON-RPC requests in Terminal 2

**Initialize:**
```bash
curl -X POST "https://ipssapi.techgenzi.com/mcp/messages/?session_id=<SESSION_ID>" \
  -u "rajkumar:techgenzi password 2026" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "curl-client", "version": "1.0"}
    }
  }'
```

**List Available Tools:**
```bash
curl -X POST "https://ipssapi.techgenzi.com/mcp/messages/?session_id=<SESSION_ID>" \
  -u "rajkumar:techgenzi password 2026" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'
```

**Call a Tool (`get_companies_and_compcodes`):**
```bash
curl -X POST "https://ipssapi.techgenzi.com/mcp/messages/?session_id=<SESSION_ID>" \
  -u "rajkumar:techgenzi password 2026" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "get_companies_and_compcodes",
      "arguments": {}
    }
  }'
```

---

## 5. Python Client (MCP SDK)

```python
import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

AUTH_HEADER = "Basic cmFqa3VtYXI6dGVjaGdlbnppIHBhc3N3b3JkIDIwMjY="

async def main():
    headers = {"Authorization": AUTH_HEADER}
    async with sse_client("https://ipssapi.techgenzi.com/mcp/sse", headers=headers) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            # List tools
            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])
            
            # Call tool
            result = await session.call_tool("get_companies_and_compcodes", arguments={})
            print("Result:", result)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Complete Tools Catalog (19 Tools)

### Organization, Users & Accounts (UserRole)
| Tool Name | Key Parameters | Description | Answers Prompts Such As |
| :--- | :--- | :--- | :--- |
| `get_companies_and_compcodes` | None | Lists all company codes (compcode), organization names, and IDs in the system. | *"list the compcodes"*, *"what is the company name?"* |
| `get_customer_accounts` | `results_per_page`, `page` | Queries master vendor, supplier, and partner accounts with names, contact numbers, and emails. | *"list the accounts"*, *"who are our vendors?"* |
| `get_system_users` | `search`, `results_per_page`, `page` | Lists system user accounts, emails, roles, and assigned company entities with fuzzy search. | *"find user rajkumar"*, *"list all admins"* |
| `get_user_roles` | `results_per_page`, `page` | Queries security roles, privilege bundles, and permission profiles. | *"what roles exist in the system?"* |
| `get_system_navigation_menu` | None | Returns the full ERP module hierarchy and menu layout. | *"what modules are available?"* |

### Orders & Logistics
| Tool Name | Key Parameters | Description |
| :--- | :--- | :--- |
| `get_customer_purchase_orders` | `order_no`, `order_id`, `customer_name`, `results_per_page` | CPO orders, status, deadlines, items count |
| `get_order_lifecycle_report` | `order_id`, `results_per_page` | PO -> Planning -> Cutting -> Sewing -> Finishing -> Dispatch |
| `get_dispatch_delivery_report` | `order_no`, `start_date`, `end_date`, `results_per_page` | Delivery challans (DC), invoices, pending balances |
| `get_plan_to_outward_report` | `plan_id`, `results_per_page` | Planned targets vs packed output ready for dispatch |

### Inventory, Stock & Procurement
| Tool Name | Key Parameters | Description |
| :--- | :--- | :--- |
| `get_inventory_stock` | `sku_id`, `product_id`, `product_name`, `results_per_page` | Stock balance, quantities on hand, warehouse locations |
| `get_stock_movement_report` | `product_id`, `start_date`, `end_date`, `results_per_page` | Stock ledger movement, receipts, floor dispatches, balances |
| `get_grn_inward_report` | `vendor_id`, `start_date`, `end_date`, `results_per_page` | Goods receipt notes (GRN), raw fabric deliveries, OTIF |
| `get_bill_of_materials` | `bom_id`, `product_id`, `sku_id` | BOM recipes, component ratios, consumption standards |
| `get_material_cost_report` | `order_id`, `results_per_page` | Actual fabric/trim consumption vs standard BOM budgeted cost |

### Production, Quality & Workforce
| Tool Name | Key Parameters | Description |
| :--- | :--- | :--- |
| `get_job_orders` | `job_order_no`, `plan_id`, `results_per_page` | Production job orders, line assignments, planned quantities |
| `get_production_efficiency_report`| `line_id`, `date`, `results_per_page` | Hourly output, SAM/SMV line efficiency %, bottleneck stations |
| `get_qc_rejection_report` | `style_id`, `stage_id`, `results_per_page` | Quality inspection defects, rework %, scrap %, causes |
| `get_employee_efficiency_report` | `emp_id`, `date`, `results_per_page` | Operator hourly output, target achievement, piece rates |
| `get_workforce_muster` | `date`, `results_per_page` | Daily biometric attendance muster from PeopleChamp HRMS |
