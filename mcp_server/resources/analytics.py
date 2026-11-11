from mcp.server.fastmcp import FastMCP as MCPServer
from typing import Dict, Any
import json
from utils.http_client import fetch_get, FABRICO_BE_URL

def register_analytics_resources(mcp: MCPServer):
    """
    Registers fast analytical snapshot resources for tiramai BizInsights.
    """

    @mcp.resource("fabrico://analytics/daily-factory-fact")
    async def get_daily_factory_fact() -> str:
        """
        Returns real-time aggregated factory KPIs (overall efficiency, line count, scrap %, delay alerts).
        """
        data = await fetch_get(f"{FABRICO_BE_URL}/am-production/efficiency-report/?results_per_page=1")
        return json.dumps(data, indent=2)

    @mcp.resource("fabrico://schema/order-lifecycle")
    def get_order_lifecycle_schema() -> str:
        """
        Returns the canonical 8-step OmniPlus manufacturing workflow schema.
        """
        lifecycle = {
            "stages": [
                {"step": 1, "name": "Customer PO Creation", "route": "/customerpurchaseorder/"},
                {"step": 2, "name": "Production Planning", "route": "/productionplanning/"},
                {"step": 3, "name": "BOM & Stock Allocation", "route": "/am-invregistry/allocation"},
                {"step": 4, "name": "Management Plan Approval", "route": "/productionplanning/approval"},
                {"step": 5, "name": "Material Store Request", "route": "/materialrequest/"},
                {"step": 6, "name": "Store Issue & Floor Dispatch", "route": "/dispatch/store"},
                {"step": 7, "name": "Shop Floor Execution & Serialization", "route": "/productionexecution/"},
                {"step": 8, "name": "Move FG to Store & Delivery Challan", "route": "/deliverychallan/"}
            ],
            "description": "Canonical 8-step lifecycle reference for unscripted queries."
        }
        return json.dumps(lifecycle, indent=2)
