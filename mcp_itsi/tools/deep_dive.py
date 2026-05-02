"""Tools for ITSI deep dives."""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.tools import _itoa_ops as ops

_OBJECT_TYPE = "deep_dive"


class ListDeepDives(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_list_deep_dives",
        description=(
            "List ITSI deep dives. A deep dive is an investigative tool that "
            "shows KPIs and service health scores side-by-side over time to "
            "help correlate root cause."
        ),
        category="investigation",
        tags=("itsi", "deep-dive", "list"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        filter_query: dict[str, Any] | str | None = None,
        fields: str | None = "title,_key,description,owner",
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
        return success_response(count=len(items), deep_dives=items)


class GetDeepDive(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_get_deep_dive",
        description="Fetch a single ITSI deep dive document.",
        category="investigation",
        tags=("itsi", "deep-dive", "get"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        item = await ops.get_object(ctx, _OBJECT_TYPE, key)
        if item is None:
            return error_response("deep_dive not found", key=key)
        return success_response(deep_dive=item)
