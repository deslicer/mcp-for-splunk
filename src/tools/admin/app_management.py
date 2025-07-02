"""
Tool for managing Splunk applications - enable, disable, install, restart.

This tool provides app management actions, while app information/listing
is provided via the apps resource for LLM context.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class ManageApps(BaseTool):
    """
    Manage Splunk applications - enable, disable, restart operations.

    Note: App listing and information is provided via the apps resource.
    This tool focuses on state-changing management actions.
    """

    METADATA = ToolMetadata(
        name="manage_apps",
        description="Enable, disable, or restart Splunk applications",
        category="admin",
        tags=["apps", "administration", "management", "actions"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        action: str,
        app_name: str,
        splunk_host: str | None = None,
        splunk_port: int | None = None,
        splunk_username: str | None = None,
        splunk_password: str | None = None,
        splunk_scheme: str | None = None,
        splunk_verify_ssl: bool | None = None,
    ) -> dict[str, Any]:
        """
        Manage Splunk application state.

        Args:
            action: Action to perform ('enable', 'disable', 'restart', 'reload')
            app_name: Name of the app to manage
            splunk_host: Optional Splunk host (overrides server config)
            splunk_port: Optional Splunk port (overrides server config)
            splunk_username: Optional Splunk username (overrides server config)
            splunk_password: Optional Splunk password (overrides server config)
            splunk_scheme: Optional Splunk scheme (overrides server config)
            splunk_verify_ssl: Optional SSL verification setting (overrides server config)

        Returns:
            Dict containing operation result
        """
        log_tool_execution(f"manage_apps_{action}")

        # Extract client configuration from parameters
        kwargs = locals().copy()
        kwargs.pop("self")
        kwargs.pop("ctx")
        kwargs.pop("action")
        kwargs.pop("app_name")
        client_config = self.extract_client_config(kwargs)

        # Get Splunk service connection (client-specific or server default)
        try:
            service = await self.get_splunk_service(ctx, client_config)
        except Exception as e:
            return self.format_error_response(f"Failed to connect to Splunk: {str(e)}")

        # Validate action
        valid_actions = ["enable", "disable", "restart", "reload"]
        if action not in valid_actions:
            return self.format_error_response(
                f"Invalid action '{action}'. Valid actions: {', '.join(valid_actions)}"
            )

        self.logger.info(f"Managing app '{app_name}': {action}")
        ctx.info(f"Managing app '{app_name}': {action}")

        try:
            # Get the app
            app = service.apps[app_name]

            # Initialize result
            result = {}

            if action == "enable":
                result = self._enable_app(app)
            elif action == "disable":
                result = self._disable_app(app)
            elif action == "restart":
                result = self._restart_app(app)
            elif action == "reload":
                result = self._reload_app(app)
            else:
                # This should never happen due to validation above, but for safety
                raise ValueError(f"Unhandled action: {action}")

            ctx.info(f"Successfully {action}d app '{app_name}'")
            return self.format_success_response(
                {
                    "action": action,
                    "app_name": app_name,
                    "result": result,
                    "connection_source": "client_config" if client_config else "server_config",
                }
            )

        except KeyError:
            error_msg = f"App '{app_name}' not found"
            self.logger.error(error_msg)
            ctx.error(error_msg)
            return self.format_error_response(error_msg)
        except Exception as e:
            error_msg = f"Failed to {action} app '{app_name}': {str(e)}"
            self.logger.error(error_msg)
            ctx.error(error_msg)
            return self.format_error_response(error_msg)

    def _enable_app(self, app) -> dict[str, Any]:
        """Enable a Splunk app"""
        try:
            app.enable()
            app.refresh()

            return {
                "status": "enabled",
                "disabled": app.content.get("disabled", False),
                "configured": app.content.get("configured", False),
                "restart_required": app.content.get("state_change_requires_restart", False),
            }
        except Exception as e:
            raise Exception(f"Failed to enable app: {str(e)}") from e

    def _disable_app(self, app) -> dict[str, Any]:
        """Disable a Splunk app"""
        try:
            app.disable()
            app.refresh()

            return {
                "status": "disabled",
                "disabled": app.content.get("disabled", True),
                "configured": app.content.get("configured", False),
                "restart_required": app.content.get("state_change_requires_restart", False),
            }
        except Exception as e:
            raise Exception(f"Failed to disable app: {str(e)}") from e

    def _restart_app(self, app) -> dict[str, Any]:
        """Restart a Splunk app"""
        try:
            # Disable then enable the app
            app.disable()
            app.refresh()
            app.enable()
            app.refresh()

            return {
                "status": "restarted",
                "disabled": app.content.get("disabled", False),
                "configured": app.content.get("configured", False),
                "restart_completed": True,
            }
        except Exception as e:
            raise Exception(f"Failed to restart app: {str(e)}") from e

    def _reload_app(self, app) -> dict[str, Any]:
        """Reload a Splunk app configuration"""
        try:
            # Refresh the app to reload its configuration
            app.refresh()

            return {
                "status": "reloaded",
                "disabled": app.content.get("disabled", False),
                "configured": app.content.get("configured", False),
                "last_reload": "now",
            }
        except Exception as e:
            raise Exception(f"Failed to reload app: {str(e)}") from e
