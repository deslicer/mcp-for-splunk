"""FastMCP Context helpers for alert tools.

FastMCP 4 sends client notifications via ``ctx.info`` / ``ctx.error`` /
``ctx.warning`` / ``ctx.report_progress``. This mixin keeps those calls on
every failure path while still returning the repo's structured error dicts
(the tool loader already converts uncaught exceptions into the same shape).
"""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from src.tools.alerts.alert_action_catalog import AlertActionCatalog


class AlertContextMixin:
    """Mixin for BaseTool subclasses that talk to the MCP client Context."""

    async def fail(self, ctx: Context, message: str, **extra: Any) -> dict[str, Any]:
        await ctx.error(message)
        return self.format_error_response(message, **extra)  # type: ignore[attr-defined]

    async def notify_progress(
        self, ctx: Context, progress: float, total: float, message: str
    ) -> None:
        await ctx.report_progress(progress=progress, total=total, message=message)

    async def unknown_actions_message(
        self,
        ctx: Context,
        service: Any,
        parsed_actions: list[dict[str, Any]] | None,
    ) -> str | None:
        requested = [item["name"] for item in (parsed_actions or [])]
        if not requested:
            return None
        catalog = AlertActionCatalog()
        try:
            missing = catalog.unknown_actions(service, requested)
        except Exception as exc:
            await ctx.warning(f"Skipping alert-action catalog validation: {exc}")
            return None
        if not missing:
            return None
        available = ", ".join(sorted(catalog.names(service)))
        return (
            f"Unknown alert action(s): {', '.join(missing)}. "
            f"Call list_alert_actions. Available: {available}"
        )
