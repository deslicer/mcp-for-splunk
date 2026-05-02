"""Tools for ITSI glass tables."""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.tools import _itoa_ops as ops

_OBJECT_TYPE = "glass_table"


class ListGlassTables(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_list_glass_tables",
        description=(
            "List ITSI glass tables. Glass tables are custom canvases used to "
            "visualise the topology of services with KPIs, health scores and "
            "imagery."
        ),
        category="visualization",
        tags=("itsi", "glass-table", "list"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        filter_query: dict[str, Any] | str | None = None,
        fields: str | None = "title,_key,description",
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        items = await ops.list_objects(
            ctx,
            _OBJECT_TYPE,
            filter_query=filter_query,
            fields=fields,
            limit=limit,
            offset=offset,
        )
        return success_response(count=len(items), glass_tables=items)


class GetGlassTable(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_get_glass_table",
        description="Fetch a single ITSI glass table document.",
        category="visualization",
        tags=("itsi", "glass-table", "get"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        item = await ops.get_object(ctx, _OBJECT_TYPE, key)
        if item is None:
            return error_response("glass_table not found", key=key)
        return success_response(glass_table=item)
