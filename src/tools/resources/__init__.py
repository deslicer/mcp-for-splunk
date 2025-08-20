"""
Resource tools for MCP Server.

Provides tools for accessing embedded resources and documentation.
"""

from .embedded_docs_tools import (
    GetAdminGuideTool,
    GetEmbeddedDocTool,
    GetSPLReferenceTool,
    GetSplunkCheatSheetTool,
    GetTroubleshootingGuideTool,
    ListEmbeddedDocsTool,
    SearchEmbeddedDocsTool,
    get_embedded_docs_tools,
)

__all__ = [
    "ListEmbeddedDocsTool",
    "GetEmbeddedDocTool",
    "SearchEmbeddedDocsTool",
    "GetSplunkCheatSheetTool",
    "GetSPLReferenceTool",
    "GetTroubleshootingGuideTool",
    "GetAdminGuideTool",
    "get_embedded_docs_tools",
]
