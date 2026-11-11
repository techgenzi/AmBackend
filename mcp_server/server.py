"""
Fabrico360 & AmNonOvens Manufacturing MCP Server
Exposes deterministic tool definitions and analytical resources for tiramai BizInsights.
"""
import os
import sys
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP as MCPServer

load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.reports import register_reporting_tools
from tools.operations import register_operations_tools
from tools.user_roles import register_user_role_tools
from tools.master_data import register_master_data_tools
from resources.analytics import register_analytics_resources

# Initialize MCPServer (MCP 2.x standard)
mcp = MCPServer(
    name="Fabrico360-Manufacturing-MCP"
)

# Register Tools & Resources
register_reporting_tools(mcp)
register_operations_tools(mcp)
register_user_role_tools(mcp)
register_master_data_tools(mcp)
register_analytics_resources(mcp)

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    if transport == "sse":
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))
        mount_path = os.getenv("MCP_MOUNT_PATH", "/mcp")
        print(f"Starting Fabrico360 MCP Server on SSE transport at http://{host}:{port}/sse (mount: {mount_path})")
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run(transport="sse", mount_path=mount_path)
    else:
        mcp.run()
