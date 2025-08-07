"""
Health dashboard routes for MCP Server for Splunk

This module provides health check endpoints for monitoring server status,
component loading, and Splunk connectivity.
"""

import logging
import os
import time

import tomllib
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from .templates import load_css, load_template, render_template

logger = logging.getLogger(__name__)


def get_version() -> str:
    """Get version from pyproject.toml"""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        pyproject_path = os.path.join(project_root, "pyproject.toml")
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
            return pyproject_data.get("project", {}).get("version", "unknown")
    except Exception as e:
        logger.debug(f"Could not read version from pyproject.toml: {e}")
        return "unknown"  # fallback


def get_component_counts(mcp_server: FastMCP) -> tuple[int, int, int]:
    """Get component counts from stored results"""
    tools_count = 0
    resources_count = 0
    prompts_count = 0

    try:
        # Access the stored component loading results from the server instance
        if hasattr(mcp_server, '_component_loading_results') and mcp_server._component_loading_results:
            results = mcp_server._component_loading_results
            tools_count = results.get('tools', 0)
            resources_count = results.get('resources', 0)
            prompts_count = results.get('prompts', 0)
            logger.debug(f"Using stored component counts: tools={tools_count}, resources={resources_count}, prompts={prompts_count}")
        else:
            logger.debug("No stored component loading results found - server may still be starting up")
    except Exception as e:
        logger.debug(f"Could not get component counts: {e}")

    return tools_count, resources_count, prompts_count


def get_splunk_status(mcp_server: FastMCP) -> tuple[str, str, str]:
    """Get Splunk connection status and server info from stored context"""
    splunk_status = "Disconnected"
    splunk_server_name = "Unknown"
    splunk_version = "Unknown"

    try:
        # Access the stored Splunk context from the server instance
        if hasattr(mcp_server, '_splunk_context') and mcp_server._splunk_context:
            splunk_ctx = mcp_server._splunk_context
            if splunk_ctx.is_connected and splunk_ctx.service:
                # Try a simple API call to verify the connection works
                try:
                    info = splunk_ctx.service.info
                    if info:
                        splunk_version = info.get('version', 'unknown')
                        splunk_server_name = info.get('serverName', 'Unknown')
                        splunk_status = f"Connected (v{splunk_version})"
                    else:
                        splunk_status = "Unknown"
                except:
                    splunk_status = "Unknown"
            else:
                logger.debug("Splunk context shows disconnected state")
        else:
            logger.debug("No stored Splunk context found - server may still be starting up")
    except Exception as e:
        logger.debug(f"Could not check Splunk connection: {e}")

    return splunk_status, splunk_server_name, splunk_version


def setup_health_routes(mcp: FastMCP):
    """Setup health routes for the MCP server"""

    @mcp.custom_route("/", methods=["GET"])
    async def health_page(request: Request) -> HTMLResponse:
        """Server health page at root URL with real server data"""
        try:
            # Get real version from pyproject.toml
            version = get_version()

            # Get component counts from stored results
            tools_count, resources_count, prompts_count = get_component_counts(mcp)

            server_info_data = {
                "name": "MCP Server for Splunk",
                "version": version,
                "transport": "http",
                "capabilities": [],
                "description": "Modular MCP Server providing Splunk integration",
                "status": "unknown",
                "tools_count": tools_count,
                "resources_count": resources_count,
                "prompts_count": prompts_count,
            }

            # Get Splunk connection status
            splunk_status, splunk_server_name, splunk_version = get_splunk_status(mcp)

            # Determine real capabilities based on loaded components
            capabilities = []
            if tools_count > 0:
                capabilities.append(f"tools ({tools_count})")
            if resources_count > 0:
                capabilities.append(f"resources ({resources_count})")
            if prompts_count > 0:
                capabilities.append(f"prompts ({prompts_count})")

            server_info_data["capabilities"] = capabilities
            # Determine status: running if we have components OR if Splunk is connected (server is operational)
            has_components = len(capabilities) > 0
            splunk_connected = "Connected" in splunk_status
            server_info_data["status"] = "running" if (has_components or splunk_connected) else "degraded"

            # Load template and CSS
            template_content = load_template("health.html")
            css_content = load_css("health.css")

            # Prepare template variables
            server_status_class = "running" if server_info_data["status"] == "running" else "degraded"
            splunk_status_class = "connected" if "Connected" in splunk_status else "disconnected"

            capabilities_tags = ''.join([
                f'<span class="capability-tag">{cap}</span>' for cap in capabilities
            ])

            # Render template with data
            html_content = render_template(
                template_content,
                css_content=css_content,
                server_name=server_info_data["name"],
                server_status=server_info_data["status"].title(),
                server_status_class=server_status_class,
                server_version=server_info_data["version"],
                server_transport=server_info_data["transport"].upper(),
                splunk_status=splunk_status,
                splunk_status_class=splunk_status_class,
                splunk_server=splunk_server_name,
                tools_count=tools_count,
                resources_count=resources_count,
                prompts_count=prompts_count,
                capabilities_tags=capabilities_tags,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
            )

            return HTMLResponse(content=html_content)
        except Exception as e:
            logger.error(f"Error in health_page: {e}")
            return HTMLResponse(content=f"<h1>Server Health</h1><p>Error: {str(e)}</p>", status_code=500)

    @mcp.custom_route("/health", methods=["GET"])
    async def health_api(request: Request) -> JSONResponse:
        """API endpoint for health checks with real data"""
        try:
            # Get real version from pyproject.toml
            version = get_version()

            # Get component counts from stored results
            tools_count, resources_count, prompts_count = get_component_counts(mcp)

            capabilities = []
            if tools_count > 0:
                capabilities.append(f"tools ({tools_count})")
            if resources_count > 0:
                capabilities.append(f"resources ({resources_count})")
            if prompts_count > 0:
                capabilities.append(f"prompts ({prompts_count})")

            # Determine status: running if we have components OR if Splunk is connected (server is operational)
            has_components = len(capabilities) > 0

            server_info_data = {
                "name": "MCP Server for Splunk",
                "version": version,
                "transport": "http",
                "capabilities": capabilities,
                "description": "Modular MCP Server providing Splunk integration",
                "status": "unknown",  # Will be set after Splunk check
                "tools_count": tools_count,
                "resources_count": resources_count,
                "prompts_count": prompts_count,
            }

            # Check real Splunk connection status from stored context
            splunk_status = "disconnected"
            splunk_info = {}
            try:
                # Access the stored Splunk context from the server instance
                if hasattr(mcp, '_splunk_context') and mcp._splunk_context:
                    splunk_ctx = mcp._splunk_context
                    if splunk_ctx.is_connected and splunk_ctx.service:
                        splunk_status = "connected"
                        try:
                            info = splunk_ctx.service.info
                            if info:
                                splunk_info = {
                                    "version": info.get('version', 'unknown'),
                                    "serverName": info.get('serverName', 'Unknown')
                                }
                        except:
                            pass
                    else:
                        logger.debug("Splunk context shows disconnected state")
                else:
                    logger.debug("No stored Splunk context found - server may still be starting up")
            except Exception as e:
                logger.debug(f"Could not check Splunk connection: {e}")

            # Update server status based on components and Splunk connection
            splunk_connected = splunk_status == "connected"
            server_info_data["status"] = "running" if (has_components or splunk_connected) else "degraded"

            return JSONResponse({
                "status": "healthy",
                "server": server_info_data,
                "splunk_connection": splunk_status,
                "splunk_info": splunk_info,
                "timestamp": time.time()
            })
        except Exception as e:
            logger.error(f"Error in health_api: {e}")
            return JSONResponse({
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }, status_code=500)
