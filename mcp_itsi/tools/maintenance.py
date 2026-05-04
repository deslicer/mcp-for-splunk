"""Tools for ITSI maintenance windows."""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.client.endpoints import MAINTENANCE_INTERFACE
from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response


class ListMaintenanceWindows(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_list_maintenance_windows",
        description=(
            "List ITSI maintenance windows. During maintenance, KPI severity is "
            "suppressed and the impacted services display a special status."
        ),
        category="maintenance",
        tags=("itsi", "maintenance-window", "list"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        filter_query: dict[str, Any] | str | None = None,
        fields: str | None = "title,_key,start_time,end_time,objects,status",
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if filter_query is not None:
            params["filter"] = filter_query
        if fields:
            params["fields"] = fields
        async with ctx.client() as client:
            result = await client.get_json(
                f"{MAINTENANCE_INTERFACE}/maintenance_calendar", params=params
            )
        items = result if isinstance(result, list) else []
        return success_response(count=len(items), maintenance_windows=items)


class GetMaintenanceWindow(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_get_maintenance_window",
        description="Fetch a single ITSI maintenance window document by `_key`.",
        category="maintenance",
        tags=("itsi", "maintenance-window", "get"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        async with ctx.client() as client:
            result = await client.get_json(f"{MAINTENANCE_INTERFACE}/maintenance_calendar/{key}")
        if isinstance(result, list):
            result = result[0] if result else None
        if result is None:
            return error_response("maintenance_window not found", key=key)
        return success_response(maintenance_window=result)
