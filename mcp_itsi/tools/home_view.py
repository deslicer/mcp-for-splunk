"""Tools for ITSI Service Analyzer (`home_view`)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.tools import _itoa_ops as ops

_OBJECT_TYPE = "home_view"


class ListHomeViews(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_list_home_views",
        description=(
            "List Service Analyzer home views. Home views are custom layouts "
            "of services and KPIs used as the entry point in the ITSI UI."
        ),
        category="visualization",
        tags=("itsi", "home-view", "service-analyzer", "list"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        filter_query: dict[str, Any] | str | None = None,
        fields: str | None = "title,_key,description,acl",
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
        return success_response(count=len(items), home_views=items)


class GetHomeView(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_get_home_view",
        description="Fetch a single Service Analyzer home view document.",
        category="visualization",
        tags=("itsi", "home-view", "service-analyzer", "get"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        item = await ops.get_object(ctx, _OBJECT_TYPE, key)
        if item is None:
            return error_response("home_view not found", key=key)
        return success_response(home_view=item)
