"""
Tool for managing Splunk applications - enable, disable, install, restart.

This tool provides app management actions, while app information/listing
is provided via the apps resource for LLM context.
"""

from typing import Any, Literal

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
        description=(
            "Manage Splunk application lifecycle operations including enable, disable, restart, "
            "and reload actions. Use this tool when you need to change the state of a Splunk app, "
            "such as enabling a disabled app, restarting for configuration changes, or troubleshooting issues. "
            "This tool provides essential app management capabilities for "
            "maintaining Splunk environments, troubleshooting app issues, and controlling app "
            "availability. Operations affect app state and may require Splunk restart for "
            "some changes to take effect.\n\n"
            "Args:\n"
            "    action (str): Management action to perform. Valid options:\n"
            "        - 'enable': Activate the application\n"
            "        - 'disable': Deactivate the application\n"
            "        - 'restart': Disable then enable the application\n"
            "        - 'reload': Refresh application configuration\n"
            "    app_name (str): Name of the Splunk application to manage. Examples:\n"
            "        - 'search': Core Splunk Search app\n"
            "        - 'splunk_monitoring_console': Monitoring Console\n"
            "        - 'my_custom_app': Custom business applications\n\n"
            "Response Format:\n"
            "Returns a dictionary with 'status' field and 'data' containing:\n"
            "- action: The performed action\n"
            "- app_name: The target application name\n"
            "- result: Action-specific status and configuration details"
        ),
        category="admin",
        tags=["apps", "administration", "management", "actions"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        action: Literal["enable", "disable", "restart", "reload"],
        app_name: str,
    ) -> dict[str, Any]:
        """
        Manage Splunk application state.

        Args:
            action: Action to perform ('enable', 'disable', 'restart', 'reload')
            app_name: Name of the app to manage

        Returns:
            Dict containing operation result
        """
        log_tool_execution(f"manage_apps_{action}")

        # Check Splunk availability using context
        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        # action is validated by Literal type in the schema

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
