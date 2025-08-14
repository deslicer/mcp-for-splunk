"""
Core tools for MCP Server for Splunk.

This module contains the core tools maintained by the project team.
"""

# Import all core tools to make them discoverable  # noqa: F401,F403
from .admin import *  # noqa: F401,F403
from .alerts import *  # noqa: F401,F403
from .health import *  # noqa: F401,F403
from .kvstore import *  # noqa: F401,F403
from .metadata import *  # noqa: F401,F403
from .search import *  # noqa: F401,F403
from .workflows import *  # noqa: F401,F403

__all__ = [
    # Search tools
    "OneshotSearch",
    "JobSearch",
    "ListSavedSearches",
    "ExecuteSavedSearch",
    "CreateSavedSearch",
    "UpdateSavedSearch",
    "DeleteSavedSearch",
    "GetSavedSearchDetails",
    # Metadata tools
    "ListIndexes",
    "ListSourcetypes",
    "ListSources",
    # Health tools
    "GetSplunkHealth",
    # Admin tools
    "ListApps",
    "ListUsers",
    "Me",
    "GetConfigurations",
    "ToolDescriptionEnhancer",
    # Alerts tools
    "ListTriggeredAlerts",
    # KV Store tools
    "ListKvstoreCollections",
    "GetKvstoreData",
    "CreateKvstoreCollection",
    # Workflow tools
    "WorkflowRunnerTool",
    "ListWorkflowsTool",
    "WorkflowBuilderTool",
    "WorkflowRequirementsTool",
    "create_summarization_tool",
    "SummarizationTool",
]
