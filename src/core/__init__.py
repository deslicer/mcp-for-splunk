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
    from .context import SplunkContext as SplunkContextAlt
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
]
