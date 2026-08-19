"""List alert actions installed on the connected Splunk instance."""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution
from src.tools.alerts.alert_action_catalog import AlertActionCatalog
from src.tools.alerts.alert_tool_context import AlertContextMixin


class ListAlertActions(AlertContextMixin, BaseTool):
    """Discover built-in and custom Splunk alert actions and their param keys."""

    METADATA = ToolMetadata(
        name="list_alert_actions",
        description=(
            "List alert actions installed on the connected Splunk instance, including custom "
            "actions. Returns name, label, description, is_custom, app, and param_keys. Call this "
            "before create_alert or update_alert when using a custom action so you pass the correct "
            "action name and param keys.\n\n"
            "Outputs: 'alert_actions' array and 'count'.\n"
            "Security: results are constrained by the authenticated user's permissions."
        ),
        category="alerts",
        tags=["alerts", "alert-actions", "discovery", "custom"],
        requires_connection=True,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        log_tool_execution("list_alert_actions")
        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            return await self.fail(ctx, error_msg)

        try:
            await ctx.info("Retrieving installed Splunk alert actions")
            await self.notify_progress(ctx, 0, 100, "Listing alert actions")
            actions = AlertActionCatalog().list_actions(service)
            await ctx.info(f"Found {len(actions)} alert actions")
            await self.notify_progress(ctx, 100, 100, f"Found {len(actions)} alert actions")
            return self.format_success_response(
                {"alert_actions": actions, "count": len(actions)}
            )
        except Exception as exc:
            self.logger.error("Failed to list alert actions: %s", exc)
            return await self.fail(ctx, f"Failed to list alert actions: {exc}")
