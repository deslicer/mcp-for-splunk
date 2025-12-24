"""
Core framework for MCP Server for Splunk

This module provides the foundational classes and utilities for building
modular tools, resources, and prompts for the MCP server.
"""

# Import base classes (these should always be available)
from .base import BasePrompt, BaseResource, BaseTool, SplunkContext
from .utils import format_error_response, validate_splunk_connection

# Import other modules with error handling for development
try:
    from .context import SplunkContext as SplunkContextAlt  # noqa: F401
    from .discovery import discover_prompts, discover_resources, discover_tools
    from .loader import ComponentLoader, PromptLoader, ResourceLoader, ToolLoader
    from .registry import (
        PromptRegistry,
        ResourceRegistry,
        ToolRegistry,
        prompt_registry,
        resource_registry,
        tool_registry,
    )
except ImportError as e:
    # During development, some modules might not be fully implemented
    import logging

    logging.getLogger(__name__).warning(f"Some core modules not available: {e}")

    # Provide fallback imports for essential components
    def discover_tools(*args):
        return 0

    def discover_resources(*args):
        return 0

    def discover_prompts(*args):
        return 0

    ToolLoader = None
    ResourceLoader = None
    PromptLoader = None
    ComponentLoader = None
    ToolRegistry = None
    ResourceRegistry = None
    PromptRegistry = None
    tool_registry = None
    resource_registry = None
    prompt_registry = None

# Sentry integration (optional - only loaded if Sentry is configured)
try:
    from .sentry import (  # noqa: F401
        SentryHTTPMiddleware,
        SentryMCPMiddleware,
        _sentry_sdk_available,
        add_breadcrumb,
        capture_mcp_error,
        create_sentry_middlewares,
        init_sentry,
        is_sentry_enabled,
        mcp_span,
        set_mcp_context,
        trace_mcp_resource,
        trace_mcp_tool,
        trace_splunk_operation,
    )

    _sentry_exports = [
        "_sentry_sdk_available",
        "init_sentry",
        "is_sentry_enabled",
        "mcp_span",
        "trace_mcp_tool",
        "trace_mcp_resource",
        "trace_splunk_operation",
        "set_mcp_context",
        "capture_mcp_error",
        "add_breadcrumb",
        "SentryHTTPMiddleware",
        "SentryMCPMiddleware",
        "create_sentry_middlewares",
    ]
except ImportError:
    _sentry_sdk_available = False
    _sentry_exports = ["_sentry_sdk_available"]

__all__ = [
    "BaseTool",
    "BaseResource",
    "BasePrompt",
    "SplunkContext",
    "discover_tools",
    "discover_resources",
    "discover_prompts",
    "ToolLoader",
    "ResourceLoader",
    "PromptLoader",
    "ComponentLoader",
    "ToolRegistry",
    "ResourceRegistry",
    "PromptRegistry",
    "tool_registry",
    "resource_registry",
    "prompt_registry",
    "validate_splunk_connection",
    "format_error_response",
    *_sentry_exports,
]
