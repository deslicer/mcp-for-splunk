"""Tools that expose the bundled ITSI knowledge bundle as callable tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.knowledge import catalog


class ListDocs(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_list_docs",
        description=(
            "List every bundled ITSI knowledge document. Returns slug, title, "
            "category and source URL so an agent can decide which doc to read."
        ),
        category="docs",
        tags=("itsi", "docs", "list"),
        requires_connection=False,
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext) -> dict[str, Any]:
        entries = [
            {
                "slug": e.slug,
                "uri": e.uri,
                "title": e.title,
                "description": e.description,
                "category": e.category,
                "tags": list(e.tags),
                "source": e.source,
            }
            for e in catalog.list_docs()
        ]
        return success_response(count=len(entries), docs=entries)


class ReadDoc(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_read_doc",
        description=(
            "Read the full markdown contents of a bundled ITSI knowledge doc. "
            "`slug` is the short identifier returned by `itsi_list_docs` "
            "(e.g. `service-insights`, `api/schema`)."
        ),
        category="docs",
        tags=("itsi", "docs", "read"),
        requires_connection=False,
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, slug: str) -> dict[str, Any]:
        if not slug:
            return error_response("`slug` is required")
        entry = catalog.get_doc(slug)
        if entry is None:
            return error_response("doc not found", slug=slug)
        return success_response(
            slug=entry.slug,
            uri=entry.uri,
            title=entry.title,
            source=entry.source,
            content=entry.read(),
        )


class SearchDocs(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_search_docs",
        description=(
            "Search the bundled ITSI knowledge corpus by free-text query. "
            "Returns matching docs ranked by relevance. Useful for "
            "agents that want to find guidance before calling a mutating tool."
        ),
        category="docs",
        tags=("itsi", "docs", "search"),
        requires_connection=False,
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        query: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        if not query:
            return error_response("`query` is required")
        hits = [
            {
                "slug": e.slug,
                "uri": e.uri,
                "title": e.title,
                "description": e.description,
                "score": score,
            }
            for e, score in catalog.search(query, limit=limit)
        ]
        return success_response(count=len(hits), query=query, hits=hits)
