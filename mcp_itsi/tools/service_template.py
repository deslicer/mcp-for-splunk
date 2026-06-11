"""Tools for managing ITSI service templates (`base_service_template`)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.tools import _itoa_ops as ops

_OBJECT_TYPE = "base_service_template"


class ListServiceTemplates(BaseITSITool):
    """List service templates."""

    METADATA = ToolMetadata(
        name="itsi_list_service_templates",
        description=(
            "List ITSI service templates (base_service_template). Service "
            "templates carry shared KPIs and entity rules that propagate to "
            "linked services. Use this to find an existing template before "
            "creating a new service."
        ),
        category="service-insights",
        tags=("itsi", "service-template", "list"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        filter_query: dict[str, Any] | str | None = None,
        fields: str | None = "title,_key,description,sync_status,total_linked_services",
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        templates = await ops.list_objects(
            ctx,
            _OBJECT_TYPE,
            filter_query=filter_query,
            fields=fields,
            limit=limit,
            offset=offset,
        )
        return success_response(count=len(templates), templates=templates)


class GetServiceTemplate(BaseITSITool):
    """Retrieve a service template by key."""

    METADATA = ToolMetadata(
        name="itsi_get_service_template",
        description=(
            "Fetch the full document for an ITSI service template, including "
            "its KPI definitions, entity rules and the list of linked services."
        ),
        category="service-insights",
        tags=("itsi", "service-template", "get"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        tpl = await ops.get_object(ctx, _OBJECT_TYPE, key)
        if tpl is None:
            return error_response("service_template not found", key=key)
        return success_response(template=tpl)


class TemplatizeService(BaseITSITool):
    """Generate a template payload from an existing service."""

    METADATA = ToolMetadata(
        name="itsi_templatize_service",
        description=(
            "Generate a service-template-shaped payload from an existing ITSI "
            "service. Useful when you want to reproduce a service definition "
            "across many services or environments. Only `service` and "
            "`kpi_base_search` objects support templatize."
        ),
        category="service-insights",
        tags=("itsi", "service-template", "templatize"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        result = await ops.templatize_object(ctx, "service", key)
        return success_response(template=result)


class CreateServiceTemplate(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_create_service_template",
        description=(
            "Create an ITSI service template. `payload` requires `title` AND "
            "`service_id` (the `_key` of an existing service the template is "
            "derived from). Optional: `description`, `kpis[]`, "
            "`entity_rules[]`. Use `itsi_templatize_service` to generate a "
            "ready-to-use payload from an existing service. Templates can "
            "only belong to `default_itsi_security_group`."
        ),
        category="service-insights",
        tags=("itsi", "service-template", "create"),
    )

    async def execute(
        self, mcp_ctx: Context, ctx: ITSICallContext, payload: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return error_response("`payload` must be a JSON object")
        result = await ops.create_object(ctx, _OBJECT_TYPE, payload)
        return success_response(template=result)


class UpdateServiceTemplate(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_update_service_template",
        description=(
            "Update an existing ITSI service template by `_key`. Defaults to "
            "a partial update; set `is_partial=False` for full replacement."
        ),
        category="service-insights",
        tags=("itsi", "service-template", "update"),
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
        return success_response(template=result)


class DeleteServiceTemplate(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_delete_service_template",
        description="Delete an ITSI service template by `_key`.",
        category="service-insights",
        tags=("itsi", "service-template", "delete"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        result = await ops.delete_object(ctx, _OBJECT_TYPE, key)
        return success_response(deleted_key=key, **result)
