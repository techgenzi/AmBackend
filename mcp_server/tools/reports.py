from mcp.server.fastmcp import FastMCP as MCPServer
from typing import Optional, Dict, Any
from utils.http_client import fetch_get, FABRICO_BE_URL

def register_reporting_tools(mcp: MCPServer):
    """
    Registers all Manufacturing & Executive Reporting APIs into MCPServer
    consumed by tiramai BizInsights.
    """

    @mcp.tool()
    async def get_stock_movement_report(
        product_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        results_per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Retrieves the stock ledger movement report showing inward receipts, floor dispatches, and balance quantities.
        """
        params = {"results_per_page": results_per_page}
        if product_id: params["product_id"] = product_id
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        return await fetch_get(f"{FABRICO_BE_URL}/am-invregistry/stocklist/movement-report/", params=params)

    @mcp.tool()
    async def get_dispatch_delivery_report(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        order_no: Optional[str] = None,
        results_per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Retrieves goods delivery and dispatch records including delivery challan (DC), customer invoice numbers, and pending balances.
        """
        params = {"results_per_page": results_per_page}
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        if order_no: params["order_no"] = order_no
        return await fetch_get(f"{FABRICO_BE_URL}/am-order-reports/Delivery-report", params=params)

    @mcp.tool()
    async def get_production_efficiency_report(
        line_id: Optional[int] = None,
        date: Optional[str] = None,
        results_per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Retrieves line-wise planned vs actual hourly output, SAM/SMV efficiency percentage, and bottleneck stations.
        """
        params = {"results_per_page": results_per_page}
        if line_id: params["line_id"] = line_id
        if date: params["date"] = date
        return await fetch_get(f"{FABRICO_BE_URL}/am-production/efficiency-report/", params=params)

    @mcp.tool()
    async def get_qc_rejection_report(
        style_id: Optional[int] = None,
        stage_id: Optional[int] = None,
        results_per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Retrieves quality inspection defect logs, rework rates, fabric scrap %, and quality failure causes across lines.
        """
        params = {"results_per_page": results_per_page}
        if style_id: params["style_id"] = style_id
        if stage_id: params["stage_id"] = stage_id
        return await fetch_get(f"{FABRICO_BE_URL}/am-qualitycheck/rejection-report/", params=params)

    @mcp.tool()
    async def get_material_cost_report(order_id: Optional[str] = None, results_per_page: int = 50) -> Dict[str, Any]:
        """
        Retrieves actual fabric & trim consumption cost vs standard BOM budgeted cost to isolate margin leakage.
        """
        params = {"results_per_page": results_per_page}
        if order_id: params["order_id"] = order_id
        return await fetch_get(f"{FABRICO_BE_URL}/am-costing/material-report/", params=params)

    @mcp.tool()
    async def get_employee_efficiency_report(
        emp_id: Optional[str] = None,
        date: Optional[str] = None,
        results_per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Retrieves individual operator hourly output, target achievement %, and stage piece-rate earnings.
        """
        params = {"results_per_page": results_per_page}
        if emp_id: params["emp_id"] = emp_id
        if date: params["date"] = date
        return await fetch_get(f"{FABRICO_BE_URL}/am-production/employee-efficiency/", params=params)

    @mcp.tool()
    async def get_grn_inward_report(
        vendor_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        results_per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Retrieves goods receipt notes (GRN), raw fabric deliveries, inward lot inspections, and supplier OTIF compliance.
        """
        params = {"results_per_page": results_per_page}
        if vendor_id: params["vendor_id"] = vendor_id
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        return await fetch_get(f"{FABRICO_BE_URL}/am-grnotes/report/", params=params)

    @mcp.tool()
    async def get_plan_to_outward_report(plan_id: Optional[int] = None, results_per_page: int = 50) -> Dict[str, Any]:
        """
        Retrieves planned target quantities vs serialized packed output ready for shipment dispatch.
        """
        params = {"results_per_page": results_per_page}
        if plan_id: params["plan_id"] = plan_id
        return await fetch_get(f"{FABRICO_BE_URL}/am-production/plan-to-outward/", params=params)

    @mcp.tool()
    async def get_labour_cost_report(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        results_per_page: int = 10
    ) -> Dict[str, Any]:
        """
        Retrieves plan-wise and stage-wise actual vs estimated labour costs, completed output, and stage variance across Cutting, Stitching, Pouch Packing, and Box Packing to isolate margin leaks and cost overruns.
        """
        safe_limit = max(1, min(int(results_per_page or 10), 20))
        params = {"results_per_page": safe_limit}
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        return await fetch_get(f"{FABRICO_BE_URL}/am-labour/labour_cost", params=params)
