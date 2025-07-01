"""
Core tools for MCP Server for Splunk.

This module contains the core tools maintained by the project team.
"""

# Import all core tools to make them discoverable
from .admin import *
from .health import *
from .kvstore import *
from .metadata import *
from .search import *

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
    "GetConfigurations",

    # KV Store tools
    "ListKvstoreCollections",
    "GetKvstoreData",
    "CreateKvstoreCollection",
]
