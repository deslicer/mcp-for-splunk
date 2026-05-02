"""Tools for managing ITSI services (the central object in Service Insights)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.tools import _itoa_ops as ops

_OBJECT_TYPE = "service"


class ListServices(BaseITSITool):
    """List ITSI services with optional MongoDB-style filtering."""

    METADATA = ToolMetadata(
        name="itsi_list_services",
        description=(
            "Returns ITSI services with optional MongoDB-style filtering, "
            "sorting and pagination. Pass `filter_query` as a JSON string or "
            "object (e.g. {'title': {'$regex': '.*Web.*'}}). Use `fields` to "
            "limit response size when listing many services."
        ),
        category="service-insights",
        tags=("itsi", "service", "list"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        filter_query: dict[str, Any] | str | None = None,
        fields: str | None = "title,_key,description,enabled,sec_grp",
        sort_key: str | None = "title",
        sort_dir: int = 1,
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        services = await ops.list_objects(
            ctx,
            _OBJECT_TYPE,
            filter_query=filter_query,
            fields=fields,
            sort_key=sort_key,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )
        return success_response(count=len(services), services=services)


class GetService(BaseITSITool):
    """Retrieve a single ITSI service by `_key`."""

    METADATA = ToolMetadata(
        name="itsi_get_service",
        description=(
            "Fetch the full document for a single ITSI service, including "
            "KPIs, entity rules, dependencies and security group."
        ),
        category="service-insights",
        tags=("itsi", "service", "get"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        service = await ops.get_object(ctx, _OBJECT_TYPE, key)
        if service is None:
            return error_response("service not found", key=key)
        return success_response(service=service)


class CountServices(BaseITSITool):
    """Return the count of services matching an optional filter."""

    METADATA = ToolMetadata(
        name="itsi_count_services",
        description=(
            "Return how many ITSI services match a MongoDB-style filter, "
            "or the total count if no filter is supplied."
        ),
        category="service-insights",
        tags=("itsi", "service", "count"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        filter_query: dict[str, Any] | str | None = None,
    ) -> dict[str, Any]:
        count = await ops.count_objects(ctx, _OBJECT_TYPE, filter_query)
        return success_response(count=count)


class CreateService(BaseITSITool):
    """Create a new ITSI service from a payload."""

    METADATA = ToolMetadata(
        name="itsi_create_service",
        description=(
            "Create a new ITSI service. `payload` must follow the ITSI REST API "
            "schema for service objects (title, description, kpis, entity_rules, "
            "services_depends_on, sec_grp, enabled, ...). See the embedded "
            "knowledge resource itsi://docs/api/schema for the full schema."
        ),
        category="service-insights",
        tags=("itsi", "service", "create"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(payload, dict) or not payload.get("title"):
            return error_response("payload.title is required to create a service")
        result = await ops.create_object(ctx, _OBJECT_TYPE, payload)
        return success_response(service=result)


class UpdateService(BaseITSITool):
    """Update an existing ITSI service (partial by default)."""

    METADATA = ToolMetadata(
        name="itsi_update_service",
        description=(
            "Update an existing ITSI service identified by `key`. Defaults to a "
            "partial update (only the fields you send are changed). Set "
            "`is_partial=False` for a full replacement of the service document."
        ),
        category="service-insights",
        tags=("itsi", "service", "update"),
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
        return success_response(service=result)


class DeleteService(BaseITSITool):
    """Delete a service by key."""

    METADATA = ToolMetadata(
        name="itsi_delete_service",
        description=(
            "Permanently delete an ITSI service by `_key`. This operation cannot "
            "be undone; consumers should confirm intent with the user before "
            "calling."
        ),
        category="service-insights",
        tags=("itsi", "service", "delete"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        result = await ops.delete_object(ctx, _OBJECT_TYPE, key)
        return success_response(deleted_key=key, **result)
