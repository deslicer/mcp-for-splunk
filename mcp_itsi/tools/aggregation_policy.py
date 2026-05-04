"""CRUD tools for ITSI notable event aggregation policies.

Aggregation policies live under the Event Management Interface and group
notable events into episodes. We keep CRUD here (separate from
``event_management.py`` which focuses on notable events themselves) so
each module remains tightly scoped.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.tools import _event_ops as ops

_OBJECT_TYPE = "notable_event_aggregation_policy"


class GetAggregationPolicy(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_get_aggregation_policy",
        description=("Fetch a single notable event aggregation policy by `_key`."),
        category="event-analytics",
        tags=("itsi", "aggregation-policy", "get"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        item = await ops.get_object(ctx, _OBJECT_TYPE, key)
        if item is None:
            return error_response("aggregation_policy not found", key=key)
        return success_response(aggregation_policy=item)


class CreateAggregationPolicy(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_create_aggregation_policy",
        description=(
            "Create a notable event aggregation policy. Required fields: "
            "`title`. Common fields: `description`, `disabled` (0/1), "
            "`priority`, `filter_criteria`, `breaking_criteria`, "
            "`group_title`, `group_severity`, `group_status`, `rules`, "
            "`split_by_field`, `service_topology_enabled`."
        ),
        category="event-analytics",
        tags=("itsi", "aggregation-policy", "create"),
    )

    async def execute(
        self, mcp_ctx: Context, ctx: ITSICallContext, payload: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(payload, dict) or not payload.get("title"):
            return error_response("payload.title is required to create an aggregation policy")
        result = await ops.create_object(ctx, _OBJECT_TYPE, payload)
        return success_response(aggregation_policy=result)


class UpdateAggregationPolicy(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_update_aggregation_policy",
        description=(
            "Update an aggregation policy by `_key`. ITSI validates the "
            "full schema even when `is_partial=True`, so the recommended "
            "pattern is: call `itsi_get_aggregation_policy`, merge your "
            "changes into the returned document, then submit it back with "
            "`is_partial=False`."
        ),
        category="event-analytics",
        tags=("itsi", "aggregation-policy", "update"),
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
        return success_response(aggregation_policy=result)


class DeleteAggregationPolicy(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_delete_aggregation_policy",
        description="Delete a notable event aggregation policy by `_key`.",
        category="event-analytics",
        tags=("itsi", "aggregation-policy", "delete"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        result = await ops.delete_object(ctx, _OBJECT_TYPE, key)
        return success_response(deleted_key=key, **result)
