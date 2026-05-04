"""ITSI knowledge bundle.

This package ships curated, distilled markdown summaries of the official
Splunk ITSI documentation. Each entry is exposed twice:

* As an MCP **resource** (URI ``itsi://docs/<slug>``) for clients that browse
  resources directly.
* As tool input via :func:`get_doc` so AI agents can ``call`` ``read_doc``
  and ``search_docs`` without round-tripping to the resource API.
"""

from mcp_itsi.knowledge.catalog import KnowledgeEntry, get_doc, list_docs, search

__all__ = ["KnowledgeEntry", "get_doc", "list_docs", "search"]
