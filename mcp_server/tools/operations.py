from mcp.server.fastmcp import FastMCP as MCPServer
from typing import Optional, Dict, Any
from utils.http_client import fetch_get, FABRICO_BE_URL

def register_operations_tools(mcp: MCPServer):
    """
    Registers Core Operational & Inventory Tools from Fabrico360-BE and AmNonOvens.
    """

    @mcp.tool()
    async def get_inventory_stock(
        sku_id: Optional[str] = None,
        product_id: Optional[int] = None,
        product_name: Optional[str] = None,
        results_per_page: int = 15
    ) -> Dict[str, Any]:
        """
        Queries live available stock balances, current quantities, ROQL, and warehouse locations.
        """
        params = {"results_per_page": results_per_page}
        if sku_id: params["sku_id"] = sku_id
        if product_id: params["product_id"] = product_id
        if product_name: params["product_name"] = product_name
        return await fetch_get(f"{FABRICO_BE_URL}/fabrico/baseConfig/products/", params=params)

    @mcp.tool()
    async def get_customer_purchase_orders(
        order_no: Optional[str] = None,
        order_id: Optional[int] = None,
        customer_name: Optional[str] = None,
        results_per_page: int = 15
    ) -> Dict[str, Any]:
        """
        Retrieves customer purchase orders (CPO), shipping deadlines, buyer accounts, and order volume.
        """
        params = {"results_per_page": results_per_page, "order_type": "Customer"}
        if order_no: params["order_no"] = order_no
        if order_id: params["order_id"] = order_id
        if customer_name: params["customer_name"] = customer_name
        return await fetch_get(f"{FABRICO_BE_URL}/fabrico-customer-purchase-order/", params=params)

    @mcp.tool()
    async def get_job_orders(
        job_order_no: Optional[str] = None,
        plan_id: Optional[int] = None,
        results_per_page: int = 15
    ) -> Dict[str, Any]:
        """
        Queries production job orders, line assignments, planned quantities, and execution stages.
        """
        params = {"results_per_page": results_per_page, "type": "job_order"}
        if job_order_no: params["job_order_no"] = job_order_no
        if plan_id: params["plan_id"] = plan_id
        return await fetch_get(f"{FABRICO_BE_URL}/am-job_order/", params=params)

    @mcp.tool()
    async def get_bill_of_materials(
        bom_id: Optional[int] = None,
        product_id: Optional[int] = None,
        sku_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetches BOM recipes, component ratios, and consumption standards for styles.
        """
        params = {}
        if bom_id: params["bom_id"] = bom_id
        if product_id: params["product_id"] = product_id
        if sku_id: params["sku_id"] = sku_id
        return await fetch_get(f"{FABRICO_BE_URL}/fabrico-bom/", params=params)

    @mcp.tool()
    async def get_workforce_muster(date: Optional[str] = None, results_per_page: int = 50) -> Dict[str, Any]:
        """
        Fetches daily biometric attendance muster from PeopleChamp HRMS to correlate with line operator starvation.
        """
        # Enforce safe pagination ceiling (max 100) to protect backend memory
        safe_limit = max(1, min(int(results_per_page or 50), 100))
        params = {"results_per_page": safe_limit}
        if date:
            params["date"] = date
        return await fetch_get(f"{FABRICO_BE_URL}/line/employee_line_report", params=params)

    @mcp.tool()
    async def get_consolidated_dashboard(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetches consolidated plant-wide manufacturing dashboard, high-level KPIs (total present, allocated vs unallocated operators, produced qty, WIP), floor blocks (B1-B5), direct labour cost, and departmental overheads (Stores, Medline, etc.).
        """
        params = {}
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        return await fetch_get(f"{FABRICO_BE_URL}/am-dashboard/consolidated_dashboard", params=params)
