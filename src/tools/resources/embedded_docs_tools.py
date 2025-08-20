"""
Tools for accessing embedded Splunk documentation resources.

Provides tools to list, retrieve, and search embedded documentation
including cheat sheets, SPL reference, troubleshooting guides, and admin guides.
"""

import logging
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool
from src.resources.embedded_splunk_docs import (
    embedded_splunk_docs_registry,
    get_embedded_splunk_doc,
    list_embedded_splunk_docs,
)

logger = logging.getLogger(__name__)


class ListEmbeddedDocsTool(BaseTool):
    """Tool to list all available embedded Splunk documentation."""

    def __init__(self):
        super().__init__(
            name="list_embedded_docs",
            description="List all available embedded Splunk documentation resources"
        )

    async def execute(self, ctx: Context, **kwargs) -> dict[str, Any]:
        """Execute the tool to list embedded documentation."""
        try:
            include_content = kwargs.get("include_content", False)
            docs = list_embedded_splunk_docs()

            if include_content:
                # Add content preview for each doc
                for doc in docs:
                    resource = get_embedded_splunk_doc(doc["uri"])
                    if resource:
                        # Get first 500 characters as preview
                        content = resource.embedded_content
                        if isinstance(content, str):
                            doc["content_preview"] = content[:500] + "..." if len(content) > 500 else content
                        else:
                            doc["content_preview"] = str(content)[:500] + "..."

            return {
                "success": True,
                "count": len(docs),
                "documentation": docs,
                "message": f"Found {len(docs)} embedded documentation resources"
            }

        except Exception as e:
            logger.error(f"Error listing embedded docs: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to list embedded documentation"
            }


class GetEmbeddedDocTool(BaseTool):
    """Tool to get specific embedded Splunk documentation."""

    def __init__(self):
        super().__init__(
            name="get_embedded_doc",
            description="Get specific embedded Splunk documentation by name or URI"
        )

    async def execute(self, ctx: Context, **kwargs) -> dict[str, Any]:
        """Execute the tool to get embedded documentation."""
        try:
            name = kwargs.get("name")
            uri = kwargs.get("uri")
            include_metadata = kwargs.get("include_metadata", True)

            # Find the resource
            resource = None
            if name and name in embedded_splunk_docs_registry:
                resource = embedded_splunk_docs_registry[name]
            elif uri:
                resource = get_embedded_splunk_doc(uri)
            else:
                return {
                    "success": False,
                    "error": "Either 'name' or 'uri' must be provided",
                    "message": "Please specify either the documentation name or URI"
                }

            if not resource:
                return {
                    "success": False,
                    "error": "Documentation not found",
                    "message": f"Could not find documentation for name={name}, uri={uri}"
                }

            # Get content
            content = await resource.get_content(ctx)

            result = {
                "success": True,
                "content": content,
                "message": f"Successfully retrieved {resource.name}"
            }

            if include_metadata:
                result["metadata"] = {
                    "name": resource.name,
                    "uri": resource.uri,
                    "description": resource.description,
                    "mime_type": resource.mime_type,
                    "cache_ttl": resource.cache_ttl
                }

            return result

        except Exception as e:
            logger.error(f"Error getting embedded doc: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get embedded documentation"
            }


class SearchEmbeddedDocsTool(BaseTool):
    """Tool to search within embedded Splunk documentation."""

    def __init__(self):
        super().__init__(
            name="search_embedded_docs",
            description="Search within embedded Splunk documentation content"
        )

    async def execute(self, ctx: Context, **kwargs) -> dict[str, Any]:
        """Execute the tool to search embedded documentation."""
        try:
            query = kwargs.get("query", "").strip()
            docs_to_search = kwargs.get("docs", [])
            case_sensitive = kwargs.get("case_sensitive", False)
            max_results = kwargs.get("max_results", 10)

            if not query:
                return {
                    "success": False,
                    "error": "Search query is required",
                    "message": "Please provide a search query"
                }

            # Determine which docs to search
            if docs_to_search:
                search_docs = {name: embedded_splunk_docs_registry[name]
                              for name in docs_to_search
                              if name in embedded_splunk_docs_registry}
            else:
                search_docs = embedded_splunk_docs_registry

            results = []
            search_query = query if case_sensitive else query.lower()

            for name, resource in search_docs.items():
                try:
                    content = await resource.get_content(ctx)
                    search_content = content if case_sensitive else content.lower()

                    # Simple text search
                    if search_query in search_content:
                        # Find context around the match
                        lines = content.split('\n')
                        matching_lines = []

                        for i, line in enumerate(lines):
                            line_to_search = line if case_sensitive else line.lower()
                            if search_query in line_to_search:
                                # Get context (previous and next lines)
                                start = max(0, i - 2)
                                end = min(len(lines), i + 3)
                                context = '\n'.join(lines[start:end])
                                matching_lines.append({
                                    "line_number": i + 1,
                                    "line": line.strip(),
                                    "context": context
                                })

                        if matching_lines:
                            results.append({
                                "doc_name": name,
                                "doc_title": resource.name,
                                "doc_uri": resource.uri,
                                "matches": matching_lines[:max_results // len(search_docs)]
                            })

                except Exception as e:
                    logger.warning(f"Error searching in {name}: {e}")
                    continue

            return {
                "success": True,
                "query": query,
                "results": results,
                "total_docs_searched": len(search_docs),
                "total_matches": sum(len(r["matches"]) for r in results),
                "message": f"Found {sum(len(r['matches']) for r in results)} matches across {len(results)} documents"
            }

        except Exception as e:
            logger.error(f"Error searching embedded docs: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to search embedded documentation"
            }


class GetSplunkCheatSheetTool(BaseTool):
    """Tool to get the Splunk cheat sheet specifically."""

    def __init__(self):
        super().__init__(
            name="get_splunk_cheat_sheet",
            description="Get the comprehensive Splunk cheat sheet with search commands, SPL syntax, and common patterns"
        )

    async def execute(self, ctx: Context, **kwargs) -> dict[str, Any]:
        """Execute the tool to get the Splunk cheat sheet."""
        try:
            include_metadata = kwargs.get("include_metadata", True)

            if "cheat_sheet" not in embedded_splunk_docs_registry:
                return {
                    "success": False,
                    "error": "Cheat sheet not available",
                    "message": "Splunk cheat sheet is not available"
                }

            resource = embedded_splunk_docs_registry["cheat_sheet"]
            content = await resource.get_content(ctx)

            result = {
                "success": True,
                "content": content,
                "message": "Successfully retrieved Splunk cheat sheet"
            }

            if include_metadata:
                result["metadata"] = {
                    "name": resource.name,
                    "uri": resource.uri,
                    "description": resource.description,
                    "mime_type": resource.mime_type
                }

            return result

        except Exception as e:
            logger.error(f"Error getting Splunk cheat sheet: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get Splunk cheat sheet"
            }


class GetSPLReferenceTool(BaseTool):
    """Tool to get the SPL reference specifically."""

    def __init__(self):
        super().__init__(
            name="get_spl_reference",
            description="Get the comprehensive SPL (Search Processing Language) reference with syntax and examples"
        )

    async def execute(self, ctx: Context, **kwargs) -> dict[str, Any]:
        """Execute the tool to get the SPL reference."""
        try:
            include_metadata = kwargs.get("include_metadata", True)

            if "spl_reference" not in embedded_splunk_docs_registry:
                return {
                    "success": False,
                    "error": "SPL reference not available",
                    "message": "SPL reference is not available"
                }

            resource = embedded_splunk_docs_registry["spl_reference"]
            content = await resource.get_content(ctx)

            result = {
                "success": True,
                "content": content,
                "message": "Successfully retrieved SPL reference"
            }

            if include_metadata:
                result["metadata"] = {
                    "name": resource.name,
                    "uri": resource.uri,
                    "description": resource.description,
                    "mime_type": resource.mime_type
                }

            return result

        except Exception as e:
            logger.error(f"Error getting SPL reference: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get SPL reference"
            }


class GetTroubleshootingGuideTool(BaseTool):
    """Tool to get the Splunk troubleshooting guide specifically."""

    def __init__(self):
        super().__init__(
            name="get_troubleshooting_guide",
            description="Get the comprehensive Splunk troubleshooting guide for common issues and solutions"
        )

    async def execute(self, ctx: Context, **kwargs) -> dict[str, Any]:
        """Execute the tool to get the troubleshooting guide."""
        try:
            include_metadata = kwargs.get("include_metadata", True)

            if "troubleshooting" not in embedded_splunk_docs_registry:
                return {
                    "success": False,
                    "error": "Troubleshooting guide not available",
                    "message": "Splunk troubleshooting guide is not available"
                }

            resource = embedded_splunk_docs_registry["troubleshooting"]
            content = await resource.get_content(ctx)

            result = {
                "success": True,
                "content": content,
                "message": "Successfully retrieved Splunk troubleshooting guide"
            }

            if include_metadata:
                result["metadata"] = {
                    "name": resource.name,
                    "uri": resource.uri,
                    "description": resource.description,
                    "mime_type": resource.mime_type
                }

            return result

        except Exception as e:
            logger.error(f"Error getting troubleshooting guide: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get troubleshooting guide"
            }


class GetAdminGuideTool(BaseTool):
    """Tool to get the Splunk administration guide specifically."""

    def __init__(self):
        super().__init__(
            name="get_admin_guide",
            description="Get the comprehensive Splunk administration guide for deployment and management"
        )

    async def execute(self, ctx: Context, **kwargs) -> dict[str, Any]:
        """Execute the tool to get the administration guide."""
        try:
            include_metadata = kwargs.get("include_metadata", True)

            if "admin_guide" not in embedded_splunk_docs_registry:
                return {
                    "success": False,
                    "error": "Admin guide not available",
                    "message": "Splunk administration guide is not available"
                }

            resource = embedded_splunk_docs_registry["admin_guide"]
            content = await resource.get_content(ctx)

            result = {
                "success": True,
                "content": content,
                "message": "Successfully retrieved Splunk administration guide"
            }

            if include_metadata:
                result["metadata"] = {
                    "name": resource.name,
                    "uri": resource.uri,
                    "description": resource.description,
                    "mime_type": resource.mime_type
                }

            return result

        except Exception as e:
            logger.error(f"Error getting admin guide: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get administration guide"
            }


# Tool instances
list_embedded_docs_tool = ListEmbeddedDocsTool()
get_embedded_doc_tool = GetEmbeddedDocTool()
search_embedded_docs_tool = SearchEmbeddedDocsTool()
get_splunk_cheat_sheet_tool = GetSplunkCheatSheetTool()
get_spl_reference_tool = GetSPLReferenceTool()
get_troubleshooting_guide_tool = GetTroubleshootingGuideTool()
get_admin_guide_tool = GetAdminGuideTool()


def get_embedded_docs_tools() -> list[BaseTool]:
    """Get all embedded documentation tools."""
    return [
        list_embedded_docs_tool,
        get_embedded_doc_tool,
        search_embedded_docs_tool,
        get_splunk_cheat_sheet_tool,
        get_spl_reference_tool,
        get_troubleshooting_guide_tool,
        get_admin_guide_tool,
    ]
