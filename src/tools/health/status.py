"""
Tool for checking Splunk connection health.
"""

from typing import Any, Dict

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class GetSplunkHealth(BaseTool):
    """
    Get Splunk connection health status.
    """
    
    METADATA = ToolMetadata(
        name="get_splunk_health",
        description="Get Splunk connection health status and version information",
        category="health",
        tags=["health", "status", "monitoring"],
        requires_connection=False  # This tool should work even when connection is down
    )
    
    async def execute(self, ctx: Context) -> Dict[str, Any]:
        """
        Check Splunk health status.
        
        Returns:
            Dict containing Splunk connection status and version information
        """
        log_tool_execution("get_splunk_health")
        
        self.logger.info("Checking Splunk health status...")
        ctx.info("Checking Splunk health status...")
        
        # Get the Splunk context from lifespan
        splunk_ctx = ctx.request_context.lifespan_context

        if not splunk_ctx.is_connected or not splunk_ctx.service:
            ctx.error("Splunk service is not available. MCP server is running in degraded mode.")
            return {
                "status": "disconnected",
                "error": "Splunk service is not available",
                "message": "MCP server is running in degraded mode"
            }

        try:
            service = splunk_ctx.service
            info = {
                "status": "connected",
                "version": service.info["version"],
                "server_name": service.info.get("host", "unknown")
            }
            ctx.info(f"Health check successful: {info}")
            self.logger.info(f"Health check successful: {info}")
            return info
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            ctx.error(f"Health check failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            } 