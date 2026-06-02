"""Tools for managing ITSI entities."""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.tools import _itoa_ops as ops

_OBJECT_TYPE = "entity"


class ListEntities(BaseITSITool):
    """List entities, optionally filtered."""

    METADATA = ToolMetadata(
        name="itsi_list_entities",
        description=(
            "List ITSI entities. Entities represent IT components (hosts, "
            "containers, network devices, applications) that can be associated "
            "with services via entity rules. Supports MongoDB-style filters."
        ),
        category="entity-integrations",
        tags=("itsi", "entity", "list"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        filter_query: dict[str, Any] | str | None = None,
        fields: str | None = "title,_key,description,entity_type_ids",
        sort_key: str | None = "title",
        sort_dir: int = 1,
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        entities = await ops.list_objects(
            ctx,
            _OBJECT_TYPE,
            filter_query=filter_query,
            fields=fields,
            sort_key=sort_key,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )
        return success_response(count=len(entities), entities=entities)


class GetEntity(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_get_entity",
        description="Retrieve a single ITSI entity by `_key`.",
        category="entity-integrations",
        tags=("itsi", "entity", "get"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        entity = await ops.get_object(ctx, _OBJECT_TYPE, key)
        if entity is None:
            return error_response("entity not found", key=key)
        return success_response(entity=entity)


class CreateEntity(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_create_entity",
        description=(
            "Create a new ITSI entity. `payload` must include `title`, "
            "`identifier` (alias `fields`/`values` that uniquely identify "
            "events for the entity) and optionally `informational` and "
            "`entity_type_ids`. IMPORTANT: every alias field listed in "
            "`identifier.fields` must also exist as a top-level array on "
            "the payload (e.g. if `identifier.fields=['host']`, include "
            "`host: ['my-host']`). Entities can only belong to "
            "`default_itsi_security_group`. Returns the new `_key`."
        ),
        category="entity-integrations",
        tags=("itsi", "entity", "create"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return error_response("`payload` must be a JSON object")
        if "identifier" not in payload:
            return error_response("payload.identifier is required to create an entity")
        result = await ops.create_object(ctx, _OBJECT_TYPE, payload)
        return success_response(entity=result)


class UpdateEntity(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_update_entity",
        description=(
            "Update an existing ITSI entity. Defaults to a partial update; "
            "set `is_partial=False` for a full overwrite."
        ),
        category="entity-integrations",
        tags=("itsi", "entity", "update"),
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
        return success_response(entity=result)


class DeleteEntity(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_delete_entity",
        description="Delete an ITSI entity by `_key`.",
        category="entity-integrations",
        tags=("itsi", "entity", "delete"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        result = await ops.delete_object(ctx, _OBJECT_TYPE, key)
        return success_response(deleted_key=key, **result)
