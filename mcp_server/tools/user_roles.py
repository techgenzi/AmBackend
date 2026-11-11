from mcp.server.fastmcp import FastMCP as MCPServer
from typing import Optional, Dict, Any, List
from utils.http_client import fetch_get, FABRICO_BE_URL

def register_user_role_tools(mcp: MCPServer):
    """
    Registers User, Roles, Compcode, and Organization Hierarchy Tools (from UserRole).
    """

    @mcp.tool()
    async def get_companies_and_compcodes() -> Dict[str, Any]:
        """
        Retrieves all company codes (compcode), company IDs, and organization names in the system.
        Use this tool when asked:
        - 'list the compcodes'
        - 'what is the company name'
        - 'list companies / accounts'
        """
        data = await fetch_get(f"{FABRICO_BE_URL}/users/?results_per_page=100")
        if not isinstance(data, dict) or "results" not in data:
            return {"success": False, "error": "Unable to fetch organization companies", "details": data}

        companies_map = {}
        for user in data.get("results", []):
            for comp in (user.get("user_companies") or []):
                cid = comp.get("company_id")
                code = comp.get("compcode")
                if cid and code and cid not in companies_map:
                    companies_map[cid] = {
                        "company_id": cid,
                        "compcode": code
                    }

        return {
            "success": True,
            "total_companies": len(companies_map),
            "companies": sorted(list(companies_map.values()), key=lambda x: str(x.get("compcode")))
        }

    @mcp.tool()
    async def get_system_users(
        search: Optional[str] = None,
        results_per_page: int = 25,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Lists registered users, email addresses, usernames, and their assigned companies and roles.
        Supports fuzzy name or email searching.
        """
        safe_limit = min(max(int(results_per_page or 25), 1), 100)
        params = {
            "results_per_page": safe_limit,
            "paged": max(int(page or 1), 1)
        }
        if search:
            params["search"] = search
        return await fetch_get(f"{FABRICO_BE_URL}/users/", params=params)

    @mcp.tool()
    async def get_user_roles(
        results_per_page: int = 25,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Lists security roles and permission levels configured in the system.
        """
        safe_limit = min(max(int(results_per_page or 25), 1), 100)
        params = {
            "results_per_page": safe_limit,
            "paged": max(int(page or 1), 1)
        }
        return await fetch_get(f"{FABRICO_BE_URL}/users/user-roles/", params=params)

    @mcp.tool()
    async def get_system_navigation_menu() -> Dict[str, Any]:
        """
        Retrieves the ERP navigation hierarchy, available modules, and feature groupings.
        """
        return await fetch_get(f"{FABRICO_BE_URL}/users/user-configurations/menu.json")

    @mcp.tool()
    async def get_customer_accounts(
        results_per_page: int = 50,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Lists registered business partners, vendors, suppliers, and customer accounts with contact details.
        Use this tool when asked:
        - 'list the accounts'
        - 'find account details for customer X'
        """
        safe_limit = min(max(int(results_per_page or 50), 1), 100)
        params = {
            "results_per_page": safe_limit,
            "paged": max(int(page or 1), 1)
        }
        return await fetch_get(f"{FABRICO_BE_URL}/am-vendors/", params=params)
