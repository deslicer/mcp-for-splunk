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
        description="Get Splunk connection health status and version information",
        category="health",
        tags=["health", "status", "monitoring"],
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
        Check Splunk health status.

        Args:
            splunk_host: Optional Splunk host (overrides server config)
            splunk_port: Optional Splunk port (overrides server config)
            splunk_username: Optional Splunk username (overrides server config)
            splunk_password: Optional Splunk password (overrides server config)
            splunk_scheme: Optional Splunk scheme (overrides server config)
            splunk_verify_ssl: Optional SSL verification setting (overrides server config)

        Returns:
            Dict containing Splunk connection status and version information
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
