"""
Tool for checking Splunk connection health.
"""

import asyncio
from typing import Any

from fastmcp import Context

from mcp_server_for_splunk.client.splunk_client import get_splunk_service
from mcp_server_for_splunk.core.base import BaseTool, ToolMetadata
from mcp_server_for_splunk.core.utils import log_tool_execution


class GetSplunkHealth(BaseTool):
    """
    Get Splunk connection health status.

    Supports both server-configured and client-provided Splunk connections.
    """

    METADATA = ToolMetadata(
        name="get_splunk_health",
        description=(
            "Check Splunk server connectivity and return comprehensive health status information "
            "including server version, connection status, and system information. Supports both "
            "server-configured connections and custom connection parameters for testing different "
            "Splunk instances. Essential for connectivity troubleshooting and server validation.\\n\\n"
            "Args:\\n"
            "    splunk_host (str, optional): Splunk server hostname or IP address "
            "(e.g., 'localhost', 'splunk.example.com', '10.1.1.100')\\n"
            "    splunk_port (int, optional): Splunk management port, typically 8089 "
            "(e.g., 8089, 8000, 9997)\\n"
            "    splunk_username (str, optional): Splunk username for authentication "
            "(e.g., 'admin', 'splunk', 'analyst')\\n"
            "    splunk_password (str, optional): Splunk password for authentication\\n"
            "    splunk_scheme (str, optional): Connection scheme - 'http' or 'https'\\n"
            "    splunk_verify_ssl (bool, optional): Whether to verify SSL certificates\\n\\n"
            "Note: If connection parameters are not provided, uses the server's configured connection.\\n\\n"
            "Response Format:\\n"
            "Returns 'status', 'version', 'server_name' (Splunk serverName), 'hostname' (OS host), 'instance_guid', and 'connection_source'. "
            "Status can be 'connected' or 'error'."
        ),
        category="health",
        tags=["health", "status", "monitoring", "connectivity"],
        requires_connection=False,  # This tool should work even when connection is down
    )

    async def execute(
        self,
        ctx: Context,
        splunk_host: str | None = None,
        splunk_port: int | None = None,
        splunk_username: str | None = None,
        splunk_password: str | None = None,
        splunk_scheme: str | None = None,
        splunk_verify_ssl: bool | None = None,
    ) -> dict[str, Any]:
        """
        Check Splunk server connectivity and health status.

        Args:
            splunk_host (str, optional): Splunk server hostname or IP address. If not provided,
                                       uses the server's configured connection.
            splunk_port (int, optional): Splunk management port (typically 8089). Defaults to
                                       server configuration.
            splunk_username (str, optional): Splunk username for authentication. Uses server
                                           configuration if not provided.
            splunk_password (str, optional): Splunk password for authentication. Uses server
                                           configuration if not provided.
            splunk_scheme (str, optional): Connection scheme ('http' or 'https'). Defaults to
                                         server configuration.
            splunk_verify_ssl (bool, optional): Whether to verify SSL certificates. Defaults to
                                              server configuration.

        Returns:
            Dict containing connection status, Splunk version, server name, and connection source
        """
        log_tool_execution("get_splunk_health")

        self.logger.info("Checking Splunk health status...")
        await ctx.info("Checking Splunk health status...")

        # Extract client configuration from parameters
        kwargs = locals().copy()
        kwargs.pop("self")
        kwargs.pop("ctx")
        client_config = self.extract_client_config(kwargs) or await self.get_client_config_from_context(ctx)

        try:
            # Try to get Splunk service with client config or fallback to server default
            # A health probe must never identify a different default server when
            # the explicitly selected client connection fails.
            service = (
                await asyncio.to_thread(get_splunk_service, client_config)
                if client_config
                else await self.get_splunk_service(ctx)
            )

            # If we got here, we have a working connection
            server_info = await asyncio.to_thread(lambda: service.info)
            info = {
                "status": "connected",
                "version": server_info["version"],
                "server_name": server_info.get("serverName") or server_info.get("host", "unknown"),
                "hostname": server_info.get("host"),
                "instance_guid": server_info.get("guid"),
                "connection_source": "client_config" if client_config else "server_config",
            }

            await ctx.info(f"Health check successful: {info}")
            self.logger.info("Health check successful: %s", info)
            return info

        except Exception as e:
            # Report failure for the selected connection; do not change targets.
            self.logger.error("Health check failed: %s", str(e))
            await ctx.error(f"Health check failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "connection_source": "client_config" if client_config else "server_config",
            }
