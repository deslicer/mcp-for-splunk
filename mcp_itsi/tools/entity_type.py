"""Tools for inspecting ITSI entity types."""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.tools import _itoa_ops as ops

_OBJECT_TYPE = "entity_type"


class ListEntityTypes(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_list_entity_types",
        description=(
            "List ITSI entity types. An entity type classifies a data source "
            "(Linux, Windows, VMware, Kubernetes, ...) and can carry data "
            "drilldowns, dashboard drilldowns, and vital metrics."
        ),
        category="entity-integrations",
        tags=("itsi", "entity-type", "list"),
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
        types = await ops.list_objects(
            ctx,
            _OBJECT_TYPE,
            filter_query=filter_query,
            fields=fields,
            limit=limit,
            offset=offset,
        )
        return success_response(count=len(types), entity_types=types)


class GetEntityType(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_get_entity_type",
        description="Fetch a single entity type document including drilldowns and vital metrics.",
        category="entity-integrations",
        tags=("itsi", "entity-type", "get"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        et = await ops.get_object(ctx, _OBJECT_TYPE, key)
        if et is None:
            return error_response("entity_type not found", key=key)
        return success_response(entity_type=et)
