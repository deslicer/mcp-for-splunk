"""Tools for inspecting KPI base searches (`kpi_base_search`)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.tools import _itoa_ops as ops

_OBJECT_TYPE = "kpi_base_search"


class ListKpiBaseSearches(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_list_kpi_base_searches",
        description=(
            "List KPI base searches. A KPI base search is a reusable saved "
            "search that powers multiple KPIs across services and templates."
        ),
        category="kpi",
        tags=("itsi", "kpi", "base-search", "list"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        filter_query: dict[str, Any] | str | None = None,
        fields: str | None = "title,_key,description,base_search,metrics",
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
        return success_response(count=len(items), kpi_base_searches=items)


class GetKpiBaseSearch(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_get_kpi_base_search",
        description="Retrieve the full document for a single KPI base search.",
        category="kpi",
        tags=("itsi", "kpi", "base-search", "get"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        item = await ops.get_object(ctx, _OBJECT_TYPE, key)
        if item is None:
            return error_response("kpi_base_search not found", key=key)
        return success_response(kpi_base_search=item)
