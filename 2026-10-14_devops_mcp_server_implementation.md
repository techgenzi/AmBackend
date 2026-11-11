# DevOps Deployment & Operations Guide: Manufacturing Model Context Protocol (MCP) Server

**Date:** 2026-10-14  
**Module:** AI Integration / Model Context Protocol (MCP) Server for tiramai BizInsights  
**Repository:** `Work/AmNonOvens`  
**Target Environment:** Containerized Microservices (`amdev/deployment` & Production Cluster)  
**Assigned Service Port:** Internal `5047` | External Gateway Path `/mcp/`  

---

## 1. Executive Overview

To enable **tiramai BizInsights**, executive assistants, and LLM autonomous agents to query live Fabrico360 shop-floor execution, production metrics, and inventory data, the **Manufacturing MCP Server** has been consolidated into the core `AmNonOvens` service suite.

### Key Advantages of In-Tree Consolidation
1. **Existing Automated CI/CD Pipeline**: Leverages existing GitHub Actions (`.github/workflows/dev.yml` and `prod.yml`) for automated Docker container packaging, tagging, and deployment.
2. **Co-located Domain Services**: Eliminates redundant network hops and maintains direct alignment with reporting and execution schemas (`invregistry`, `order_reports`, `production_plans`).
3. **Dual Transport Support**: Exposes real-time Server-Sent Events (SSE) for web-based copilots and supports standard I/O (stdio) for local CLI / IDE inspection.

---

## 2. Architecture & Service Topology

```
                       ┌────────────────────────────────────────────────────────┐
                       │                   Ingress / Gateway                    │
                       │           (omniplus-api.techgenzi.com)                 │
                       └──────────────────────────┬─────────────────────────────┘
                                                  │
                                                  ▼
                       ┌────────────────────────────────────────────────────────┐
                       │                 Nginx Reverse Proxy                    │
                       │               (/amdev_deployment/nginx-conf)           │
                       └───────────┬────────────────────────────────┬───────────┘
                                   │                                │
                     /am-invregistry, etc.                         /mcp/
                                   │                                │
                                   ▼                                ▼
                       ┌───────────────────────┐        ┌───────────────────────┐
                       │  Existing Backend     │        │  Manufacturing MCP    │
                       │  Microservices        │        │  Server (port 5047)   │
                       │  (ports 5002-5046)    │        │  (SSE Transport)      │
                       └───────────────────────┘        └───────────────────────┘
```

---

## 3. Files Added & Modified

| File | Change Type | Purpose |
| :--- | :---: | :--- |
| `mcp_server/` | **NEW** | Complete MCP service directory containing `server.py`, `tools/`, `resources/`, and `utils/`. |
| `mcp_server/server.py` | **NEW** | Main MCP entrypoint initializing `MCPServer` and registering reporting & operations tools. |
| `mcp_server/tools/reports.py` | **NEW** | 9 Manufacturing & Executive reporting tools (stock movement, order lifecycle, dispatch, efficiency, rejections, material costs). |
| `mcp_server/tools/operations.py` | **NEW** | 5 Core operational tools (inventory stock, customer purchase orders, job orders, BOM, biometric muster). |
| `mcp_server/resources/analytics.py` | **NEW** | Fast aggregated factory fact resource (`fabrico://analytics/daily-factory-fact`). |
| `mcp_server/utils/http_client.py` | **NEW** | Async HTTP client configured for internal / gateway communication with bearer token pass-through. |
| `Dockerfile.amdev_deployment` | **MODIFIED** | Added `COPY mcp_server mcp_server` to ensure the package is included in the production image. |
| `amdev_deployment/requirements.txt`| **MODIFIED** | Added dependencies: `mcp>=1.0.0`, `httpx>=0.25.0`, `python-dotenv>=1.0.0`. |
| `amdev_deployment/supervisord.conf` | **MODIFIED** | Added `[program:mcp_server]` process definition running on port `5047` in SSE mode. |
| `amdev_deployment/nginx-conf` | **MODIFIED** | Added `/mcp/` reverse proxy configuration routing to `http://127.0.0.1:5047/` with streaming timeouts. |

---

## 4. Configuration & Environment Variables

The MCP server respects standard environment variables defined in container environments:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `MCP_TRANSPORT` | `sse` | Transport mode (`sse` for server deployment, `stdio` for local inspection). |
| `MCP_HOST` | `127.0.0.1` | Host interface binding for the internal MCP service. |
| `MCP_PORT` | `5047` | Internal listening port monitored by Supervisord. |
| `FABRICO_BE_URL` | `https://omniplus-api.techgenzi.com` | Backend REST gateway URL for data fetchers. |
| `FABRICO_SERVICE_TOKEN` | *Optional* | System service JWT token used for non-delegated background agent tasks. |

---

## 5. Deployment Instructions

### 5.1 Automated Pipeline (Standard)
1. Commit the changes on branch `amdev/deployment`:
   ```bash
   git add mcp_server/ Dockerfile.amdev_deployment amdev_deployment/ 2026-10-14_devops_mcp_server_implementation.md
   git commit -m "feat(mcp): integrate manufacturing mcp server into amdev deployment pipeline"
   git push origin amdev/deployment
   ```
2. GitHub Actions workflow (`.github/workflows/dev.yml`) will automatically trigger:
   - Build container image.
   - Install `mcp`, `httpx`, and `python-dotenv`.
   - Publish tagged image to container registry.
   - Deploy container onto target Kubernetes / droplet cluster.

### 5.2 Manual Docker Verification (Optional Local Build)
```bash
# Build the deployment image locally
docker build -f Dockerfile.amdev_deployment -t fabrico-amdev:latest .

# Run the container
docker run -p 8080:80 -e MCP_TRANSPORT=sse fabrico-amdev:latest
```

---

## 6. Verification & Health Checks

Once deployed, verify the MCP service using `curl` or browser:

### 1. Nginx Routing & Health Check
```bash
curl -I https://omniplus-api.techgenzi.com/mcp/sse
```
*Expected Response:* `HTTP/1.1 200 OK` (Content-Type: `text/event-stream`).

### 2. Supervisord Process Status
On the running container or host shell:
```bash
supervisorctl status mcp_server
```
*Expected Output:* `mcp_server RUNNING pid 1234, uptime 0:05:00`.

### 3. Log Inspection
- Process stdout: `/var/log/mcp_server.log`
- Process stderr: `/var/log/mcp_server_error.log`

---

## 7. Rollback Plan

If any container build issue arises:
1. Revert `Dockerfile.amdev_deployment`, `amdev_deployment/requirements.txt`, `amdev_deployment/supervisord.conf`, and `amdev_deployment/nginx-conf` using Git:
   ```bash
   git checkout HEAD~1 -- Dockerfile.amdev_deployment amdev_deployment/
   git commit -m "revert: rollback mcp server deployment config"
   git push origin amdev/deployment
   ```
2. The CI pipeline will rebuild and deploy the prior stable release without the MCP process.

---

## 8. Authentication Architecture & Token Delegation

The MCP Server implements a **Delegated Multi-Tenant Bearer Token Model** with an optional system service fallback (`mcp_server/utils/http_client.py`):

```
┌────────────────────────────────────────────────────────┐
│   tiramai BizInsights / Agent Client (Logged in)       │
│       JWT Bearer Token with Claims:                    │
│       • sub: username                                  │
│       • compcode: 'Demo' | 'AURA'                      │
│       • tenant_id: 1                                   │
│       • user_role / permissions                        │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ 1. Forwarded via Request Context / Tool Calls
                           ▼
┌────────────────────────────────────────────────────────┐
│             Manufacturing MCP Server                   │
│        (mcp_server/utils/http_client.py)               │
│                                                        │
│   Headers constructed:                                 │
│   • Authorization: Bearer <user_token || service_token>│
│   • X-Company-Code: <compcode>                         │
│   • X-Tenant-Id: <tenant_id>                           │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ 2. Authenticated REST Call
                           ▼
┌────────────────────────────────────────────────────────┐
│       Fabrico360 / AmNonOvens Backend APIs             │
│   (Enforces @login_required, tenant & role isolation)  │
└────────────────────────────────────────────────────────┘
```

1. **User Context Delegation (Primary)**: The client forwards the presenter's or user's active session token (`ipss_access_token`). All native permission decorators (`@login_required(permissions=...)`), company isolation (`compcode`), and tenant segregation (`tenant_id`) remain 100% enforced by the backend API.
2. **Service Token Fallback (`DEFAULT_TOKEN`)**: For unauthenticated background agent jobs or crons, falls back to `FABRICO_SERVICE_TOKEN`.
3. **Multi-Tenant Context Headers**: Automatically propagates `X-Company-Code` and `X-Tenant-Id` to guarantee query isolation.

---

## 9. Comprehensive Post-Deployment Testing Guide

DevOps and QA can verify the MCP server post-deployment using the following 5 verification stages:

### Stage 1: Basic Endpoint & Transport Handshake (cURL)
Verify the Server-Sent Events (SSE) stream over HTTPS:
```bash
curl -i -N https://omniplus-api.techgenzi.com/mcp/sse
```
*Expected Output:*
```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

event: endpoint
data: /mcp/messages?session_id=...
```

### Stage 2: MCP Protocol Discovery & Tool Listing (JSON-RPC)
Using the `session_id` returned from Stage 1:

#### 1. Initialize Handshake
```bash
curl -s -X POST "https://omniplus-api.techgenzi.com/mcp/messages?session_id=<SESSION_ID>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": { "name": "DevOps-Verification", "version": "1.0.0" }
    }
  }'
```

#### 2. Query Available Tools (`tools/list`)
```bash
curl -s -X POST "https://omniplus-api.techgenzi.com/mcp/messages?session_id=<SESSION_ID>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
  }' | jq '.result.tools[].name'
```
*Expected Output (14 Registered Tools):*
- `get_stock_movement_report`
- `get_order_lifecycle_report`
- `get_dispatch_delivery_report`
- `get_production_efficiency_report`
- `get_qc_rejection_report`
- `get_material_cost_report`
- `get_employee_efficiency_report`
- `get_grn_inward_report`
- `get_plan_to_outward_report`
- `get_inventory_stock`
- `get_customer_purchase_orders`
- `get_job_orders`
- `get_bill_of_materials`
- `get_workforce_muster`

### Stage 3: Live Tool Execution Test (`tools/call`)
Verify execution of a live operational tool:
```bash
curl -s -X POST "https://omniplus-api.techgenzi.com/mcp/messages?session_id=<SESSION_ID>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "get_customer_purchase_orders",
      "arguments": {
        "results_per_page": 5
      }
    }
  }' | jq .
```
*Expected Output:* Returns live Customer Purchase Orders from `/fabrico-customer-purchase-order/`.

### Stage 4: Automated End-to-End Test Script (Python SDK)
Create and run a programmatic verification script:
```python
# test_mcp_client.py
import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

MCP_SERVER_URL = "https://omniplus-api.techgenzi.com/mcp/sse"

async def test_mcp():
    print(f"Connecting to remote MCP server at {MCP_SERVER_URL}...")
    async with sse_client(MCP_SERVER_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # 1. Initialize Handshake
            await session.initialize()
            print("✓ MCP Session initialized successfully!")

            # 2. List tools
            tools = await session.list_tools()
            print(f"✓ Discovered {len(tools.tools)} registered tools:")
            for t in tools.tools[:5]:
                print(f"   - {t.name}: {t.description[:60]}...")

            # 3. Call a report tool
            print("\nExecuting 'get_production_efficiency_report'...")
            result = await session.call_tool("get_production_efficiency_report", arguments={"results_per_page": 3})
            print("✓ Tool Result:", str(result.content)[:200], "...")

            # 4. Read analytical resource
            print("\nReading resource 'fabrico://analytics/daily-factory-fact'...")
            resource = await session.read_resource("fabrico://analytics/daily-factory-fact")
            print("✓ Factory Fact:", resource.contents[0].text)

if __name__ == "__main__":
    asyncio.run(test_mcp())
```

### Stage 5: Target Host & Container Process Inspection
On the host or container terminal:
```bash
# Verify process status under supervisord
supervisorctl status mcp_server
# Expected: mcp_server RUNNING pid 1234, uptime 0:10:00

# Inspect live stdout / stderr logs
tail -n 50 /var/log/mcp_server.log
tail -n 50 /var/log/mcp_server_error.log
```

---

## 10. Username / Password Authentication Workflow for Testing & Integration

When testing the MCP server or integrating external agent clients (e.g. tiramai BizInsights, LangChain, AutoGen, custom scripts) that do not yet have an active frontend browser session, use the **standard Username/Password Login Exchange** to obtain a JWT Bearer token before connecting to the MCP Server.

### 10.1 Architecture: From Credentials to MCP Execution

```
┌─────────────────────────────────┐
│     Client / Tester / Agent     │
│   username: "rajkumar"          │
│   password: "Password@123"      │
└────────────────┬────────────────┘
                 │
                 │ 1. POST /users/login
                 ▼
┌────────────────────────────────────────────────────────┐
│             UserRole Authentication Gateway            │
│         (https://ipssapi.techgenzi.com/users/login)    │
└────────────────┬───────────────────────────────────────┘
                 │
                 │ 2. Returns JSON with access_token
                 ▼
┌────────────────────────────────────────────────────────┐
│     JWT Bearer Token with Embedded Claims:             │
│     • compcode: "Demo" | "AURA"                        │
│     • tenant_id: 1                                     │
│     • userid: 1582536975861                            │
│     • user_role: "Super Admin"                         │
└────────────────┬───────────────────────────────────────┘
                 │
                 │ 3. Pass in Authorization Header or Tool Context
                 ▼
┌────────────────────────────────────────────────────────┐
│             Manufacturing MCP Server (/mcp/sse)        │
│       Executes tools with authenticated user context   │
└────────────────────────────────────────────────────────┘
```

---

### 10.2 Step-by-Step cURL Instructions

#### Step 1: Authenticate and Acquire JWT Access Token
Submit user credentials to the authentication gateway:
```bash
# 1. Login to get access_token
LOGIN_RESPONSE=$(curl -s -X POST "https://ipssapi.techgenzi.com/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "rajkumar",
    "password": "Password@123"
  }')

# 2. Extract access_token
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

echo "Acquired JWT Token:"
echo "${ACCESS_TOKEN:0:50}..."
```

*(Optional)* If you wish to switch the active company code (e.g., from `Demo` to `AURA`) for your session before executing MCP tools:
```bash
curl -s -X POST "https://ipssapi.techgenzi.com/company/properties" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "finyr": "2024-2025",
    "compcode": "AURA"
  }'
```

#### Step 2: Connect to MCP Stream with Bearer Token
Initiate the Server-Sent Events stream passing your acquired bearer token:
```bash
curl -i -N https://omniplus-api.techgenzi.com/mcp/sse \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
*Expected Response:*
```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

event: endpoint
data: /mcp/messages?session_id=abc-123-xyz
```

#### Step 3: Execute MCP Tools with Delegated User Context
Use the `session_id` returned in Step 2 to call operational or reporting tools:
```bash
curl -s -X POST "https://omniplus-api.techgenzi.com/mcp/messages?session_id=<SESSION_ID>" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_customer_purchase_orders",
      "arguments": {
        "results_per_page": 5
      }
    }
  }' | jq .
```

---

### 10.3 Complete Python Automated Integration Script

Save this script as `test_mcp_login_auth.py` for automated integration tests:

```python
import asyncio
import requests
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

# Gateway Endpoints
LOGIN_URL = "https://ipssapi.techgenzi.com/users/login"
SWITCH_COMPANY_URL = "https://ipssapi.techgenzi.com/company/properties"
MCP_SSE_URL = "https://omniplus-api.techgenzi.com/mcp/sse"

# Test Credentials
USERNAME = "rajkumar"
PASSWORD = "Password@123"
TARGET_COMPCODE = "AURA"  # or "Demo"

def login_and_get_token(username, password, compcode=None):
    """Step 1: Authenticate with username and password to get JWT token."""
    print(f"Authenticating user '{username}' at {LOGIN_URL}...")
    resp = requests.post(LOGIN_URL, json={"username": username, "password": password})
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed ({resp.status_code}): {resp.text}")
    
    data = resp.json()
    if not data.get("success") or not data.get("access_token"):
        raise RuntimeError(f"Login unsuccessful: {data.get('message')}")
    
    token = data["access_token"]
    print("✓ Login successful! Acquired JWT Bearer token.")

    # Optional: Switch active company context
    if compcode:
        print(f"Switching active company context to '{compcode}'...")
        switch_resp = requests.post(
            SWITCH_COMPANY_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"finyr": "2024-2025", "compcode": compcode}
        )
        if switch_resp.status_code == 200:
            print(f"✓ Active session company set to '{compcode}'.")
        else:
            print(f"⚠️ Company switch note: {switch_resp.text}")

    return token

async def run_mcp_test(token):
    """Step 2: Connect to MCP Server via SSE using Bearer token."""
    headers = {"Authorization": f"Bearer {token}"}
    print(f"\nConnecting to MCP Server at {MCP_SSE_URL} with Bearer token...")
    
    async with sse_client(MCP_SSE_URL, headers=headers) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize MCP handshake
            await session.initialize()
            print("✓ MCP Session initialized with authenticated user context!")

            # Discover available tools
            tools = await session.list_tools()
            print(f"✓ Discovered {len(tools.tools)} tools.")

            # Test Tool 1: Order Lifecycle Report
            print("\nExecuting Tool: get_order_lifecycle_report...")
            order_report = await session.call_tool("get_order_lifecycle_report", arguments={"results_per_page": 2})
            print("✓ Tool Output:", str(order_report.content)[:250], "...\n")

            # Test Tool 2: Inventory Stock
            print("Executing Tool: get_inventory_stock...")
            stock_report = await session.call_tool("get_inventory_stock", arguments={"results_per_page": 2})
            print("✓ Tool Output:", str(stock_report.content)[:250], "...\n")

if __name__ == "__main__":
    jwt_token = login_and_get_token(USERNAME, PASSWORD, TARGET_COMPCODE)
    asyncio.run(run_mcp_test(jwt_token))
```

### 10.4 Running the Integration Test
```bash
python3 test_mcp_login_auth.py
```
*Expected Result:*
- Automatically logs in via `POST /users/login`.
- Switches context to `AURA` (or `Demo`).
- Connects to MCP SSE server passing the token.
- Discovers 14 registered tools and executes `get_order_lifecycle_report` and `get_inventory_stock`.
