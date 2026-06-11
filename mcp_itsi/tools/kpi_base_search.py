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


class CreateKpiBaseSearch(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_create_kpi_base_search",
        description=(
            "Create a new KPI base search. `payload` must follow the ITSI "
            "`kpi_base_search` schema (`title`, `base_search`, `metrics`, "
            "`entity_id_fields`, `entity_alias_filtering_fields`, "
            "`alert_period`, ...). Call itsi_get_object_schema('kpi_base_search') "
            "for the full schema + examples and itsi_validate_object_payload to "
            "check it first. The payload is validated before submission. Returns "
            "the new `_key`."
        ),
        category="kpi",
        tags=("itsi", "kpi", "base-search", "create"),
    )

    async def execute(
        self, mcp_ctx: Context, ctx: ITSICallContext, payload: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return error_response("`payload` must be a JSON object")
        result = await ops.create_object(ctx, _OBJECT_TYPE, payload)
        return success_response(kpi_base_search=result)


class UpdateKpiBaseSearch(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_update_kpi_base_search",
        description=(
            "Update an existing KPI base search by `_key`. Defaults to a "
            "partial update; set `is_partial=False` for a full overwrite. The "
            "payload is validated against the kpi_base_search schema before "
            "submission."
        ),
        category="kpi",
        tags=("itsi", "kpi", "base-search", "update"),
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
        return success_response(kpi_base_search=result)


class DeleteKpiBaseSearch(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_delete_kpi_base_search",
        description="Delete a KPI base search by `_key`.",
        category="kpi",
        tags=("itsi", "kpi", "base-search", "delete"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        result = await ops.delete_object(ctx, _OBJECT_TYPE, key)
        return success_response(deleted_key=key, **result)
