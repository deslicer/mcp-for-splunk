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
