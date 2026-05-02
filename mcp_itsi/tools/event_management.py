"""Tools for the ITSI Event Management Interface (Event Analytics)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.client.endpoints import event_collection, event_item
from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response


def _common_params(
    filter_query: dict[str, Any] | str | None,
    fields: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if filter_query is not None:
        params["filter"] = filter_query
    if fields:
        params["fields"] = fields
    return params


class ListNotableEvents(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_list_notable_events",
        description=(
            "List notable events from the ITSI Event Management Interface. "
            "Notable events are produced by correlation searches and can be "
            "grouped into episodes by aggregation policies. Filter using the "
            'MongoDB-style syntax (e.g. {"severity": {"$gte": 4}}).'
        ),
        category="event-analytics",
        tags=("itsi", "notable-event", "list"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        filter_query: dict[str, Any] | str | None = None,
        fields: str | None = "title,description,severity,owner,status,event_id,service_ids",
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        params = _common_params(filter_query, fields, limit, offset)
        async with ctx.client() as client:
            result = await client.get_json(event_collection("notable_event"), params=params)
        events = result if isinstance(result, list) else []
        return success_response(count=len(events), notable_events=events)


class GetNotableEvent(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_get_notable_event",
        description=(
            "Fetch a single notable event by `event_id`. Includes severity, "
            "owner, status, drilldown context and any episode association."
        ),
        category="event-analytics",
        tags=("itsi", "notable-event", "get"),
    )

    async def execute(
        self, mcp_ctx: Context, ctx: ITSICallContext, event_id: str
    ) -> dict[str, Any]:
        if not event_id:
            return error_response("`event_id` is required")
        async with ctx.client() as client:
            result = await client.get_json(event_item("notable_event", event_id))
        if isinstance(result, list):
            result = result[0] if result else None
        if result is None:
            return error_response("notable_event not found", event_id=event_id)
        return success_response(notable_event=result)


class AcknowledgeNotableEvent(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_acknowledge_notable_event",
        description=(
            "Acknowledge a notable event by setting its status to 'In progress' "
            "(status code 2) and assigning an owner. The owner field defaults "
            "to the authenticating Splunk user."
        ),
        category="event-analytics",
        tags=("itsi", "notable-event", "ack"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        event_id: str,
        owner: str | None = None,
    ) -> dict[str, Any]:
        if not event_id:
            return error_response("`event_id` is required")
        body: dict[str, Any] = {"status": "2"}
        if owner:
            body["owner"] = owner
        async with ctx.client() as client:
            result = await client.post_json(event_item("notable_event", event_id), body=body)
        return success_response(notable_event=result)


class CloseNotableEvent(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_close_notable_event",
        description=(
            "Close a notable event (set status code 5). Optionally provide a "
            "`comment` that will be appended to the event's notes."
        ),
        category="event-analytics",
        tags=("itsi", "notable-event", "close"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        event_id: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        if not event_id:
            return error_response("`event_id` is required")
        body: dict[str, Any] = {"status": "5"}
        async with ctx.client() as client:
            result = await client.post_json(event_item("notable_event", event_id), body=body)
            if comment:
                await client.post_json(
                    event_collection("notable_event_comment"),
                    body={"event_id": event_id, "comment": comment},
                )
        return success_response(notable_event=result)


class ListAggregationPolicies(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_list_aggregation_policies",
        description=(
            "List notable event aggregation policies. Aggregation policies "
            "group notable events into episodes based on a set of rules."
        ),
        category="event-analytics",
        tags=("itsi", "aggregation-policy", "list"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        filter_query: dict[str, Any] | str | None = None,
        fields: str | None = "title,_key,description,disabled,priority",
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        params = _common_params(filter_query, fields, limit, offset)
        async with ctx.client() as client:
            result = await client.get_json(
                event_collection("notable_event_aggregation_policy"), params=params
            )
        items = result if isinstance(result, list) else []
        return success_response(count=len(items), aggregation_policies=items)


class ListCorrelationSearches(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_list_correlation_searches",
        description=(
            "List correlation searches. Correlation searches are saved searches "
            "that emit notable events when conditions are met."
        ),
        category="event-analytics",
        tags=("itsi", "correlation-search", "list"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        filter_query: dict[str, Any] | str | None = None,
        fields: str | None = "name,description,is_scheduled,disabled,security_domain",
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        params = _common_params(filter_query, fields, limit, offset)
        async with ctx.client() as client:
            result = await client.get_json(event_collection("correlation_search"), params=params)
        items = result if isinstance(result, list) else []
        return success_response(count=len(items), correlation_searches=items)
