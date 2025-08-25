"""
Documentation tools for agentic frameworks.

These tools wrap existing resources and return embedded resources with actual content,
making them compatible with agentic frameworks that don't support MCP resources natively.
"""

from .splunk_docs_tools import (
    DiscoverSplunkDocs,
    GetAdminGuide,
    GetSPLReference,
    GetSplunkCheatSheet,
    # Documentation tools
    GetSplunkDocumentation,
    GetTroubleshootingGuide,
    ListAdminTopics,
    # Discovery tools
    ListAvailableTopics,
    ListSPLCommands,
    ListTroubleshootingTopics,
)

__all__ = [
    # Discovery tools for topic/command awareness
    "ListAvailableTopics",
    "ListTroubleshootingTopics",
    "ListAdminTopics",
    "ListSPLCommands",
    # Documentation access tools
    "GetSplunkDocumentation",
    "GetSplunkCheatSheet",
    "DiscoverSplunkDocs",
    "GetSPLReference",
    "GetTroubleshootingGuide",
    "GetAdminGuide",
]
