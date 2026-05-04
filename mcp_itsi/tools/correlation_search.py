"""CRUD tools for ITSI correlation searches.

Correlation searches are saved searches that emit notable events. Unlike
ITOA objects they are addressed by saved-search ``name`` (the URL-safe
title), not by ``_key``.

Schema reference:
    https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-reference/itsi-rest-api-reference
"""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.tools import _event_ops as ops

_OBJECT_TYPE = "correlation_search"


class GetCorrelationSearch(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_get_correlation_search",
        description=(
            "Fetch a single ITSI correlation search by its saved-search "
            "`name`. Returns scheduling, search SPL, alert configuration "
            "and notable-event-generator parameters."
        ),
        category="event-analytics",
        tags=("itsi", "correlation-search", "get"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, name: str) -> dict[str, Any]:
        if not name:
            return error_response("`name` is required")
        item = await ops.get_object(ctx, _OBJECT_TYPE, name)
        if item is None:
            return error_response("correlation_search not found", name=name)
        return success_response(correlation_search=item)


class CreateCorrelationSearch(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_create_correlation_search",
        description=(
            "Create an ITSI correlation search. Required: `name` (the saved "
            "search title) and `search` (SPL). Common: `description`, "
            "`cron_schedule`, `dispatch.earliest_time`, `dispatch.latest_time`, "
            "`alert.severity`, `disabled` (`0`/`1`), and the "
            "`action.itsi_event_generator.param.*` set that controls how "
            "notable events are produced."
        ),
        category="event-analytics",
        tags=("itsi", "correlation-search", "create"),
    )

    async def execute(
        self, mcp_ctx: Context, ctx: ITSICallContext, payload: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(payload, dict) or not payload.get("name"):
            return error_response("payload.name is required to create a correlation search")
        if not payload.get("search"):
            return error_response("payload.search (SPL) is required")
        result = await ops.create_object(ctx, _OBJECT_TYPE, payload)
        return success_response(correlation_search=result)


class UpdateCorrelationSearch(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_update_correlation_search",
        description=(
            "Update an existing correlation search by its `name`. NOTE: "
            "ITSI's update handler requires the `name` field to also be "
            "present in the payload (otherwise the server returns a 500 "
            "with a 'name' KeyError). Defaults to a partial update; set "
            "`is_partial=False` for a full overwrite."
        ),
        category="event-analytics",
        tags=("itsi", "correlation-search", "update"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        name: str,
        payload: dict[str, Any],
        is_partial: bool = True,
    ) -> dict[str, Any]:
        if not name:
            return error_response("`name` is required")
        result = await ops.update_object(ctx, _OBJECT_TYPE, name, payload, is_partial=is_partial)
        return success_response(correlation_search=result)


class DeleteCorrelationSearch(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_delete_correlation_search",
        description="Delete a correlation search by its saved-search `name`.",
        category="event-analytics",
        tags=("itsi", "correlation-search", "delete"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, name: str) -> dict[str, Any]:
        if not name:
            return error_response("`name` is required")
        result = await ops.delete_object(ctx, _OBJECT_TYPE, name)
        return success_response(deleted_name=name, **result)
