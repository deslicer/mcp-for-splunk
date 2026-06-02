"""Tools that expose ITSI object schemas and validate payloads.

These make CRUD on deeply nested ITOA objects reliable: agents can fetch the
schema for any object type, get annotated example payloads, and dry-run
validate a payload before calling a create/update tool.
"""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import Context

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext, build_call_context
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.knowledge.schema import PayloadValidator, registry
from mcp_itsi.knowledge.schema.examples import examples_for
from mcp_itsi.tools import _itoa_ops as ops

logger = logging.getLogger(__name__)


class ListObjectSchemas(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_list_object_schemas",
        description=(
            "List every ITSI object type that has a documented schema (ITSI "
            "4.21). Returns the object_type id, title, REST endpoint, attribute "
            "count and subordinate (nested) objects. Call this first to discover "
            "which type to inspect with itsi_get_object_schema."
        ),
        category="schema",
        tags=("itsi", "schema", "discovery"),
        requires_connection=False,
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext) -> dict[str, Any]:
        entries = [
            {
                "object_type": s.object_type,
                "title": s.title,
                "endpoint": s.endpoint,
                "description": s.description,
                "attribute_count": len(s.attributes),
                "required_fields": s.required_fields,
                "subordinate_objects": list(s.subordinate_objects),
            }
            for s in registry.list_object_types()
        ]
        return success_response(count=len(entries), object_types=entries)


class GetObjectSchema(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_get_object_schema",
        description=(
            "Return the full schema for an ITSI object type (e.g. 'service', "
            "'kpi_base_search', 'entity'). Includes every documented field with "
            "type/description, inlined schemas for subordinate (nested) objects "
            "like service KPIs and entity rules, a derived JSON Schema, and "
            "minimal/full/curated example payloads. Set include_live_example=True "
            "to also fetch one real object from the connected ITSI instance. Use "
            "this before creating or updating an object."
        ),
        category="schema",
        tags=("itsi", "schema", "get"),
        requires_connection=False,
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        object_type: str,
        include_examples: bool = True,
        include_json_schema: bool = True,
        include_live_example: bool = False,
    ) -> dict[str, Any]:
        if not object_type:
            return error_response("`object_type` is required")
        schema = registry.get(object_type)
        if schema is None:
            return error_response(
                f"No schema for object type '{object_type}'.",
                hint="Call itsi_list_object_schemas to see supported types.",
            )

        subordinates = {
            slug: sub.to_dict()
            for slug in schema.subordinate_objects
            if (sub := registry.get(slug)) is not None
        }

        response: dict[str, Any] = {
            "object_type": schema.object_type,
            "title": schema.title,
            "endpoint": schema.endpoint,
            "schema": schema.to_dict(),
            "subordinate_schemas": subordinates,
        }
        if include_json_schema:
            response["json_schema"] = schema.to_json_schema()
        if include_examples:
            response["examples"] = examples_for(schema)
        if include_live_example:
            response["live_example"] = await self._live_example(mcp_ctx, schema.object_type)

        return success_response(**response)

    async def _live_example(self, mcp_ctx: Context, object_type: str | None) -> Any:
        if not object_type:
            return {"available": False, "reason": "Not a top-level REST object type."}
        try:
            call_ctx = build_call_context(mcp_ctx)
        except ValueError as exc:
            return {"available": False, "reason": f"No ITSI connection: {exc}"}
        try:
            items = await ops.list_objects(call_ctx, object_type, limit=1)
        except Exception as exc:  # noqa: BLE001 - best-effort enrichment
            logger.warning("Live example fetch failed for %s: %s", object_type, exc)
            return {"available": False, "reason": str(exc)}
        if not items:
            return {"available": False, "reason": "No objects of this type exist yet."}
        return {"available": True, "object": items[0]}


class ValidateObjectPayload(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_validate_object_payload",
        description=(
            "Dry-run validate a payload against an ITSI object schema WITHOUT "
            "writing anything. Returns ok plus structured errors (unknown/"
            "misspelled fields, wrong types, missing required fields) and "
            "warnings (read-only or undocumented fields). Recurses into nested "
            "objects such as service KPIs and entity rules. Set is_partial=True "
            "to skip required-field checks (for partial updates). Call this "
            "before itsi_create_* / itsi_update_*."
        ),
        category="schema",
        tags=("itsi", "schema", "validate"),
        requires_connection=False,
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        object_type: str,
        payload: dict[str, Any],
        is_partial: bool = False,
    ) -> dict[str, Any]:
        if not object_type:
            return error_response("`object_type` is required")
        if not isinstance(payload, dict):
            return error_response("`payload` must be a JSON object")
        result = PayloadValidator().validate(object_type, payload, is_partial=is_partial)
        return success_response(object_type=object_type, **result.to_dict())
