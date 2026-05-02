"""Discovery / introspection tools for the ITSI REST API."""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.client.endpoints import ITOA_INTERFACE
from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import success_response


class GetSupportedObjectTypes(BaseITSITool):
    """Return the list of supported ITOA object types for the connected ITSI."""

    METADATA = ToolMetadata(
        name="itsi_get_supported_object_types",
        description=(
            "Lists every ITOA object type the connected ITSI instance exposes "
            "(team, entity, service, base_service_template, kpi_base_search, "
            "deep_dive, glass_table, home_view, kpi_template, kpi_threshold_template, "
            "event_management_state, entity_filter_rule, entity_type)."
        ),
        category="meta",
        tags=("itsi", "discovery"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext) -> dict[str, Any]:
        async with ctx.client() as client:
            result = await client.get_json(f"{ITOA_INTERFACE}/get_supported_object_types")
        types = result if isinstance(result, list) else []
        return success_response(count=len(types), object_types=types)


class GetAliasList(BaseITSITool):
    """List entity alias and informational field names defined in the deployment."""

    METADATA = ToolMetadata(
        name="itsi_get_alias_list",
        description=(
            "Returns the union of identifier and informational alias field names "
            "across every ITSI entity in the environment. Use this when modelling "
            "entity rules or building KPI base searches that need to align with "
            "existing alias conventions."
        ),
        category="meta",
        tags=("itsi", "entities", "discovery"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext) -> dict[str, Any]:
        async with ctx.client() as client:
            result = await client.get_json(f"{ITOA_INTERFACE}/get_alias_list")
        if not isinstance(result, dict):
            result = {}
        return success_response(
            identifier=result.get("identifier", []),
            informational=result.get("informational", []),
        )
