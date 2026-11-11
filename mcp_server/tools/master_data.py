from mcp.server.fastmcp import FastMCP as MCPServer
from typing import Optional, Dict, Any
from utils.http_client import fetch_get, FABRICO_BE_URL

def register_master_data_tools(mcp: MCPServer):
    """
    Registers Master Data, Catalog, Planning, QC, and Costing Tools into MCPServer.
    """

    @mcp.tool()
    async def get_uom_list(
        uom_name: Optional[str] = None,
        results_per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Fetch configured Units of Measure (UOM) master records (Roll, CM, Meters, Pieces, Box, Kgs, Nos, etc.).
        """
        params = {"results_per_page": min(max(int(results_per_page or 50), 1), 100)}
        if uom_name:
            params["uom_name"] = uom_name
        return await fetch_get(f"{FABRICO_BE_URL}/baseConfig/uom/", params=params)

    @mcp.tool()
    async def get_store_locations(
        location_name: Optional[str] = None,
        results_per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Fetch warehouse store locations, sub-locations, racks, and storage rooms.
        """
        params = {"results_per_page": min(max(int(results_per_page or 50), 1), 100)}
        if location_name:
            params["location_name"] = location_name
        return await fetch_get(f"{FABRICO_BE_URL}/baseConfig/products/", params=params)

    @mcp.tool()
    async def get_products(
        product_name: Optional[str] = None,
        product_group_id: Optional[int] = None,
        results_per_page: int = 25
    ) -> Dict[str, Any]:
        """
        Retrieve registered products, catalog specifications, categories, and units of measure (UOM).
        """
        params = {"results_per_page": min(max(int(results_per_page or 25), 1), 100)}
        if product_name:
            params["product_name"] = product_name
        if product_group_id:
            params["product_group_id"] = product_group_id
        return await fetch_get(f"{FABRICO_BE_URL}/baseConfig/products/", params=params)

    @mcp.tool()
    async def get_product_variants(
        product_id: Optional[int] = None,
        results_per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Retrieve product variants, style configurations, and dynamic variant attributes (Dimensions, GSM, Width, Color, Size).
        """
        params = {"results_per_page": min(max(int(results_per_page or 50), 1), 100)}
        if product_id:
            params["product_id"] = product_id
        return await fetch_get(f"{FABRICO_BE_URL}/baseConfig/product_variant/", params=params)

    @mcp.tool()
    async def get_product_groups(
        group_name: Optional[str] = None,
        results_per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Retrieve list of product groups, material categories, and classifications.
        """
        params = {"results_per_page": min(max(int(results_per_page or 50), 1), 100)}
        if group_name:
            params["group_name"] = group_name
        return await fetch_get(f"{FABRICO_BE_URL}/baseConfig/product_group/", params=params)

    @mcp.tool()
    async def get_cost_estimations(
        product_id: Optional[int] = None,
        estimate_no: Optional[str] = None,
        results_per_page: int = 25
    ) -> Dict[str, Any]:
        """
        Fetch cost estimations, raw material costs, operational expenses, and calculated product costs.
        """
        params = {"results_per_page": min(max(int(results_per_page or 25), 1), 100)}
        if product_id:
            params["product_id"] = product_id
        if estimate_no:
            params["estimate_no"] = estimate_no
        return await fetch_get(f"{FABRICO_BE_URL}/am-cost_estimation/", params=params)

    @mcp.tool()
    async def get_sales_pipeline(
        stage: Optional[str] = None,
        customer_name: Optional[str] = None,
        results_per_page: int = 25
    ) -> Dict[str, Any]:
        """
        Fetch sales pipeline leads, prospective deals, deal values, and stage progression.
        """
        params = {"results_per_page": min(max(int(results_per_page or 25), 1), 100)}
        if stage:
            params["stage"] = stage
        if customer_name:
            params["customer_name"] = customer_name
        return await fetch_get(f"{FABRICO_BE_URL}/am-vendors/pipeline/", params=params)

    @mcp.tool()
    async def get_vendors(
        vendor_name: Optional[str] = None,
        city: Optional[str] = None,
        results_per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Fetch registered suppliers, vendor directory, contact details, and supplier codes.
        """
        params = {
            "types": "VENDOR",
            "results_per_page": min(max(int(results_per_page or 50), 1), 100)
        }
        if vendor_name:
            params["vendor_name"] = vendor_name
        if city:
            params["city"] = city
        return await fetch_get(f"{FABRICO_BE_URL}/am-vendors/", params=params)

    @mcp.tool()
    async def get_production_plans(
        plan_date: Optional[str] = None,
        line_id: Optional[int] = None,
        results_per_page: int = 25
    ) -> Dict[str, Any]:
        """
        Retrieve daily/weekly production plans, target assembly lines, schedules, and planned production quantities.
        """
        params = {"results_per_page": min(max(int(results_per_page or 25), 1), 100)}
        if plan_date:
            params["plan_date"] = plan_date
        if line_id:
            params["line_id"] = line_id
        return await fetch_get(f"{FABRICO_BE_URL}/am-prod_plans/", params=params)

    @mcp.tool()
    async def get_production_execution_logs(
        date: Optional[str] = None,
        job_order_id: Optional[int] = None,
        results_per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Retrieve real-time hourly and daily production logs, machine output quantities, and defect counts.
        """
        params = {"results_per_page": min(max(int(results_per_page or 50), 1), 100)}
        if date:
            params["date"] = date
        if job_order_id:
            params["job_order_id"] = job_order_id
        return await fetch_get(f"{FABRICO_BE_URL}/am-prod_exe/", params=params)

    @mcp.tool()
    async def get_grn_qc_records(
        grn_number: Optional[str] = None,
        qc_status: Optional[str] = None,
        results_per_page: int = 25
    ) -> Dict[str, Any]:
        """
        Fetch Goods Receipt Notes (GRN), inbound raw material inspection reports, and Quality Check (QC) status.
        """
        params = {"results_per_page": min(max(int(results_per_page or 25), 1), 100)}
        if grn_number:
            params["grn_number"] = grn_number
        if qc_status:
            params["qc_status"] = qc_status
        return await fetch_get(f"{FABRICO_BE_URL}/am-grnotes/", params=params)

    @mcp.tool()
    async def get_dispatch_records(
        dc_number: Optional[str] = None,
        customer_name: Optional[str] = None,
        results_per_page: int = 25
    ) -> Dict[str, Any]:
        """
        Retrieve goods dispatch entries, delivery challans (DC), dispatched product quantities, and vehicles.
        """
        params = {"results_per_page": min(max(int(results_per_page or 25), 1), 100)}
        if dc_number:
            params["dc_number"] = dc_number
        if customer_name:
            params["customer_name"] = customer_name
        return await fetch_get(f"{FABRICO_BE_URL}/am-dispatch-module/", params=params)

    @mcp.tool()
    async def get_production_summary(
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch top-level aggregated production KPIs, completed vs delivered quantities, and factory output numbers.
        """
        params = {}
        if date:
            params["date"] = date
        return await fetch_get(f"{FABRICO_BE_URL}/am-dashboard/", params=params)

    @mcp.tool()
    async def get_pending_summary() -> Dict[str, Any]:
        """
        Fetch executive summary of pending production plans, delayed items, and floor backlogs.
        """
        return await fetch_get(f"{FABRICO_BE_URL}/am-dashboard/pending")

    @mcp.tool()
    async def get_labour_costing(
        style: Optional[str] = None,
        results_per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Fetch style labour costing, SMV (Standard Minute Value), hourly targets, and piece rates.
        """
        params = {"results_per_page": min(max(int(results_per_page or 50), 1), 100)}
        if style:
            params["style"] = style
        return await fetch_get(f"{FABRICO_BE_URL}/am-labour/", params=params)
