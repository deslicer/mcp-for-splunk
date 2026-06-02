"""Expose each ITSI object schema as a read-only resource.

Resources are addressable at ``itsi://schema/<object_type>`` and return the
structured schema (plus example payloads) as JSON. This mirrors the doc
resources in :mod:`mcp_itsi.resources.docs_resource`.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

from fastmcp import Context

from mcp_itsi.core.base import BaseITSIResource, ResourceMetadata
from mcp_itsi.knowledge.schema import ObjectSchema, registry
from mcp_itsi.knowledge.schema.examples import examples_for


def _make_class(schema: ObjectSchema) -> type[BaseITSIResource]:
    metadata = ResourceMetadata(
        uri=f"itsi://schema/{schema.object_type}",
        name=f"ITSI schema: {schema.title}",
        description=f"Structured schema and examples for the ITSI '{schema.object_type}' object.",
        mime_type="application/json",
        category="schema",
        tags=("itsi", "schema", schema.object_type or "object"),
    )

    class _SchemaResource(BaseITSIResource):
        METADATA = metadata
        _schema: ObjectSchema = schema

        async def read(self, mcp_ctx: Context) -> str:
            payload = {
                "schema": self._schema.to_dict(),
                "json_schema": self._schema.to_json_schema(),
                "examples": examples_for(self._schema),
            }
            return json.dumps(payload, indent=2, ensure_ascii=False)

    _SchemaResource.__name__ = f"SchemaResource_{schema.object_type}"
    _SchemaResource.__qualname__ = _SchemaResource.__name__
    return _SchemaResource


def build_schema_resources() -> Iterable[type[BaseITSIResource]]:
    return [_make_class(s) for s in registry.list_object_types()]
