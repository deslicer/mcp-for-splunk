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


class CreateDeepDive(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_create_deep_dive",
        description=(
            "Create a new ITSI deep dive. The schema requires `title` and "
            "`focus_id`/`focus_type` (or `lane_settings_collection`). When "
            "updating, ITSI requires `owner`, `_owner` and `_user` to be "
            "present in the payload."
        ),
        category="investigation",
        tags=("itsi", "deep-dive", "create"),
    )

    async def execute(
        self, mcp_ctx: Context, ctx: ITSICallContext, payload: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return error_response("`payload` must be a JSON object")
        result = await ops.create_object(ctx, _OBJECT_TYPE, payload)
        return success_response(deep_dive=result)


class UpdateDeepDive(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_update_deep_dive",
        description=(
            "Update an existing deep dive by `_key`. NOTE: ITSI requires "
            "`owner`, `_owner` and `_user` to be present in the payload."
        ),
        category="investigation",
        tags=("itsi", "deep-dive", "update"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        key: str,
        payload: dict[str, Any],
        is_partial: bool = True,
    ) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        result = await ops.update_object(ctx, _OBJECT_TYPE, key, payload, is_partial=is_partial)
        return success_response(deep_dive=result)


class DeleteDeepDive(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_delete_deep_dive",
        description="Delete a deep dive by `_key`.",
        category="investigation",
        tags=("itsi", "deep-dive", "delete"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        result = await ops.delete_object(ctx, _OBJECT_TYPE, key)
        return success_response(deleted_key=key, **result)
