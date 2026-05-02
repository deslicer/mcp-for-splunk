"""Tools for inspecting KPI threshold templates."""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.tools import _itoa_ops as ops

_OBJECT_TYPE = "kpi_threshold_template"


class ListKpiThresholdTemplates(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_list_kpi_threshold_templates",
        description=(
            "List KPI threshold templates. Threshold templates encapsulate the "
            "severity levels (info / normal / low / medium / high / critical) "
            "and adaptive thresholding configuration that can be reused across "
            "many KPIs."
        ),
        category="kpi",
        tags=("itsi", "kpi", "threshold-template", "list"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        filter_query: dict[str, Any] | str | None = None,
        fields: str | None = "title,_key,description,adaptive_thresholds_is_enabled",
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
        return success_response(count=len(items), threshold_templates=items)


class GetKpiThresholdTemplate(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_get_kpi_threshold_template",
        description="Fetch a single KPI threshold template document.",
        category="kpi",
        tags=("itsi", "kpi", "threshold-template", "get"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        item = await ops.get_object(ctx, _OBJECT_TYPE, key)
        if item is None:
            return error_response("kpi_threshold_template not found", key=key)
        return success_response(threshold_template=item)


class CreateKpiThresholdTemplate(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_create_kpi_threshold_template",
        description=(
            "Create a KPI threshold template. `payload` should follow the "
            "ITSI `kpi_threshold_template` schema (title, description, "
            "`time_variate_thresholds`, `time_variate_thresholds_specification`, "
            "adaptive thresholding settings)."
        ),
        category="kpi",
        tags=("itsi", "kpi", "threshold-template", "create"),
    )

    async def execute(
        self, mcp_ctx: Context, ctx: ITSICallContext, payload: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(payload, dict) or not payload.get("title"):
            return error_response("payload.title is required to create a threshold template")
        result = await ops.create_object(ctx, _OBJECT_TYPE, payload)
        return success_response(threshold_template=result)


class UpdateKpiThresholdTemplate(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_update_kpi_threshold_template",
        description=(
            "Update an existing KPI threshold template by `_key`. Defaults to "
            "a partial update; set `is_partial=False` for a full overwrite."
        ),
        category="kpi",
        tags=("itsi", "kpi", "threshold-template", "update"),
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
        return success_response(threshold_template=result)


class DeleteKpiThresholdTemplate(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_delete_kpi_threshold_template",
        description="Delete a KPI threshold template by `_key`.",
        category="kpi",
        tags=("itsi", "kpi", "threshold-template", "delete"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        result = await ops.delete_object(ctx, _OBJECT_TYPE, key)
        return success_response(deleted_key=key, **result)
