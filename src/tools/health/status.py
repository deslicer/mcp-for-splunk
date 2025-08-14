"""
Tool for checking Splunk connection health.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


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
            "Returns dictionary with 'status', 'version', 'server_name', and 'connection_source' fields. "
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
        ctx.info("Checking Splunk health status...")

        # Extract client configuration from parameters
        kwargs = locals().copy()
        kwargs.pop("self")
        kwargs.pop("ctx")
        client_config = self.extract_client_config(kwargs)

        try:
            # Try to get Splunk service with client config or fallback to server default
            service = await self.get_splunk_service(ctx, client_config)

            # If we got here, we have a working connection
            info = {
                "status": "connected",
                "version": service.info["version"],
                "server_name": service.info.get("host", "unknown"),
                "connection_source": "client_config" if client_config else "server_config",
            }

            host_wide = await service.get("/services/server/status/resource-usage/hostwide")
            self.logger.info(f"Host wide: {host_wide}")

            ctx.info(f"Health check successful: {info}")
            self.logger.info(f"Health check successful: {info}")
            return info

        except Exception as e:
            # If client config fails, also try server default if we haven't already
            if client_config:
                self.logger.info("Client config failed, trying server default...")
                try:
                    # Check server default connection
                    splunk_ctx = ctx.request_context.lifespan_context
                    if splunk_ctx.is_connected and splunk_ctx.service:
                        service = splunk_ctx.service
                        info = {
                            "status": "connected",
                            "version": service.info["version"],
                            "server_name": service.info.get("host", "unknown"),
                            "connection_source": "server_config",
                            "note": "Client config failed, using server default",
                        }
                        ctx.info(f"Health check successful with server config: {info}")
                        self.logger.info(f"Health check successful with server config: {info}")
                        return info
                except Exception as fallback_error:
                    self.logger.error(f"Both client and server configs failed: {fallback_error}")

            # Both attempts failed
            self.logger.error(f"Health check failed: {str(e)}")
            ctx.error(f"Health check failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "connection_source": "client_config" if client_config else "server_config",
            }
