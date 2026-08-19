"""Delete a Splunk alert (the underlying saved search)."""

import time
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution
from src.tools.alerts.alert_saved_search import (
    apply_saved_search_namespace,
    find_alert_saved_search,
)
from src.tools.alerts.alert_tool_context import AlertContextMixin
from src.tools.search.saved_search_acl import get_saved_search_acl


class DeleteAlert(AlertContextMixin, BaseTool):
    """Delete a Splunk alert after explicit confirmation."""

    METADATA = ToolMetadata(
        name="delete_alert",
        description=(
            "Delete a Splunk alert. Alerts are saved searches, so this removes that saved search. "
            "Requires confirm=true. Use app and owner when the name exists in more than one "
            "namespace.\n\n"
            "Args:\n"
            "    name (str): Alert name (required)\n"
            "    confirm (bool): Must be true to delete (default: false)\n"
            "    app (str, optional): App context for lookup\n"
            "    owner (str, optional): Owner context for lookup\n"
        ),
        category="alerts",
        tags=["alerts", "delete", "saved_searches"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        name: str,
        confirm: bool = False,
        app: str | None = None,
        owner: str | None = None,
    ) -> dict[str, Any]:
        log_tool_execution("delete_alert", name=name, confirm=confirm)
        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            return await self.fail(ctx, error_msg, name=name, deleted=False)

        try:
            if not confirm:
                return await self.fail(
                    ctx,
                    "Deletion requires explicit confirmation. Set confirm=true to proceed.",
                    name=name,
                    deleted=False,
                )
            saved_search = find_alert_saved_search(service, name, app, owner)
            if not saved_search:
                return await self.fail(
                    ctx, f"Alert '{name}' not found", name=name, deleted=False
                )
            acl = get_saved_search_acl(saved_search)
            await ctx.info(f"Deleting alert '{name}'")
            await self.notify_progress(ctx, 50, 100, f"Deleting alert '{name}'")
            original_namespace = apply_saved_search_namespace(service, saved_search)
            try:
                saved_search = service.saved_searches[saved_search.name]
                saved_search.delete()
            finally:
                service.namespace = original_namespace
            await self.notify_progress(ctx, 100, 100, f"Deleted alert '{name}'")
            return self.format_success_response(
                {
                    "name": name,
                    "deleted": True,
                    "app": acl.get("app", ""),
                    "owner": acl.get("owner", ""),
                    "deleted_at": time.time(),
                }
            )
        except Exception as exc:
            self.logger.error("Failed to delete alert '%s': %s", name, exc)
            return await self.fail(
                ctx, f"Failed to delete alert '{name}': {exc}", name=name, deleted=False
            )
