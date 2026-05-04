"""Build :class:`BaseITSIResource` subclasses for every bundled doc.

Each ``KnowledgeEntry`` becomes its own resource class so FastMCP can
register them with their canonical URI and metadata.
"""

from __future__ import annotations

from collections.abc import Iterable

from fastmcp import Context

from mcp_itsi.core.base import BaseITSIResource, ResourceMetadata
from mcp_itsi.knowledge import catalog
from mcp_itsi.knowledge.catalog import KnowledgeEntry


def _make_class(entry: KnowledgeEntry) -> type[BaseITSIResource]:
    metadata = ResourceMetadata(
        uri=entry.uri,
        name=entry.title,
        description=entry.description,
        mime_type="text/markdown",
        category=entry.category,
        tags=entry.tags,
    )

    class _DocResource(BaseITSIResource):
        METADATA = metadata
        _entry: KnowledgeEntry = entry

        async def read(self, mcp_ctx: Context) -> str:
            return self._entry.read()

    _DocResource.__name__ = f"DocResource_{entry.slug.replace('/', '_')}"
    _DocResource.__qualname__ = _DocResource.__name__
    return _DocResource


def build_doc_resources() -> Iterable[type[BaseITSIResource]]:
    return [_make_class(entry) for entry in catalog.list_docs()]
