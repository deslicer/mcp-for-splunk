"""
Core framework for MCP Server for Splunk

This module provides the foundational classes and utilities for building
modular tools, resources, and prompts for the MCP server.
"""

# Import base classes (these should always be available)
from .base import BaseTool, BaseResource, BasePrompt, SplunkContext
from .utils import validate_splunk_connection, format_error_response

# Import other modules with error handling for development
try:
    from .context import SplunkContext as SplunkContextAlt
    from .discovery import discover_tools, discover_resources, discover_prompts
    from .loader import ToolLoader, ResourceLoader, PromptLoader, ComponentLoader
    from .registry import ToolRegistry, ResourceRegistry, PromptRegistry, tool_registry, resource_registry, prompt_registry
except ImportError as e:
    # During development, some modules might not be fully implemented
    import logging
    logging.getLogger(__name__).warning(f"Some core modules not available: {e}")
    
    # Provide fallback imports for essential components
    discover_tools = lambda *args: 0
    discover_resources = lambda *args: 0  
    discover_prompts = lambda *args: 0
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