"""
Component loader for the MCP server.

This module handles loading and registering tools, resources, and prompts
with the FastMCP server instance.
"""

import inspect
import logging
from typing import Any, get_type_hints

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context

from .base import BaseTool
from .discovery import discover_tools
from .registry import tool_registry

logger = logging.getLogger(__name__)


class ToolLoader:
    """Loads and registers tools with the FastMCP server."""

    def __init__(self, mcp_server: FastMCP):
        self.mcp_server = mcp_server
        self.logger = logging.getLogger(f"{__name__}.ToolLoader")

    def _create_tool_wrapper(self, tool_class: type[BaseTool], tool_name: str):
        """Create a wrapper function for the tool that FastMCP can register."""

        # Get the execute method and its type hints
        execute_method = tool_class.execute
        sig = inspect.signature(execute_method)

        # Get the proper type hints using get_type_hints which resolves forward references
        try:
            type_hints = get_type_hints(execute_method)
        except (NameError, AttributeError) as e:
            self.logger.warning(f"Could not get type hints for {tool_name}: {e}")
            type_hints = {}

        self.logger.debug(f"Tool {tool_name} - Original signature: {sig}")
        self.logger.debug(f"Tool {tool_name} - Type hints: {type_hints}")

        # Create parameters excluding 'self' and 'ctx'
        filtered_params = []
        for name, param in sig.parameters.items():
            if name not in ('self', 'ctx'):
                # Use the type hint if available, otherwise fall back to annotation
                param_annotation = type_hints.get(name, param.annotation)
                if param_annotation == inspect.Parameter.empty:
                    param_annotation = Any

                # Create new parameter with proper type annotation
                new_param = inspect.Parameter(
                    name=name,
                    kind=param.kind,
                    default=param.default,
                    annotation=param_annotation
                )
                filtered_params.append(new_param)

        # Create the new signature
        wrapper_sig = inspect.Signature(filtered_params)

        # Create the wrapper function
        async def tool_wrapper(*args, **kwargs):
            """Wrapper that delegates to the tool's execute method"""
            try:
                # Create tool instance
                tool_instance = tool_class(tool_name, "modular")

                # Get the current context using FastMCP's dependency function
                try:
                    ctx = get_context()
                except Exception as e:
                    self.logger.error(f"Could not get current context for {tool_name}: {e}")
                    raise RuntimeError(f"Tool {tool_name} can only be called within an MCP request context")

                # Bind the arguments to ensure proper parameter mapping
                bound_args = wrapper_sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                # Call the tool's execute method
                result = await tool_instance.execute(ctx, **bound_args.arguments)
                return result

            except Exception as e:
                self.logger.error(f"Tool {tool_name} execution failed: {e}")
                self.logger.exception("Full traceback:")
                return {
                    "status": "error",
                    "error": str(e)
                }

        # Set function metadata
        tool_wrapper.__name__ = tool_name
        tool_wrapper.__doc__ = tool_class.METADATA.description
        tool_wrapper.__signature__ = wrapper_sig

        # Set type annotations using the resolved type hints
        tool_wrapper.__annotations__ = {}
        for param in filtered_params:
            if param.annotation != inspect.Parameter.empty:
                tool_wrapper.__annotations__[param.name] = param.annotation

        # Set return annotation if present
        return_annotation = type_hints.get('return', sig.return_annotation)
        if return_annotation != inspect.Parameter.empty:
            tool_wrapper.__annotations__['return'] = return_annotation

        # Ensure the function has the __module__ attribute for Pydantic
        tool_wrapper.__module__ = execute_method.__module__

        self.logger.debug(f"Tool {tool_name} - Wrapper signature: {wrapper_sig}")
        self.logger.debug(f"Tool {tool_name} - Wrapper annotations: {tool_wrapper.__annotations__}")

        return tool_wrapper

    def load_tools(self) -> int:
        """Load all discovered tools into the MCP server."""
        loaded_count = 0

        # Discover tools if not already done
        tool_metadata_list = tool_registry.list_tools()
        if not tool_metadata_list:
            discover_tools()
            tool_metadata_list = tool_registry.list_tools()

        # Use registry's private access for tool classes (this is internal framework use)
        for tool_metadata in tool_metadata_list:
            tool_name = tool_metadata.name
            tool_class = tool_registry._tools.get(tool_name)

            if not tool_class:
                self.logger.error(f"Tool class not found for {tool_name}")
                continue

            try:
                # Create wrapper function for FastMCP
                tool_wrapper = self._create_tool_wrapper(tool_class, tool_name)

                # Register with FastMCP using the tool decorator
                self.mcp_server.tool(name=tool_name)(tool_wrapper)

                loaded_count += 1
                self.logger.info(f"Loaded tool: {tool_name}")

            except Exception as e:
                self.logger.error(f"Failed to register tool '{tool_name}': {e}")
                self.logger.exception("Full registration error:")

        self.logger.info(f"Loaded {loaded_count} tools into MCP server")
        return loaded_count


class ResourceLoader:
    """Loads and registers resources with the FastMCP server."""

    def __init__(self, mcp_server: FastMCP):
        self.mcp_server = mcp_server
        self.logger = logging.getLogger(f"{__name__}.ResourceLoader")

    def load_resources(self) -> int:
        """Load all discovered resources into the MCP server."""
        self.logger.info("Resource loading is currently not implemented")
        self.logger.info("The BaseResource interface is incompatible with FastMCP's @mcp.resource decorator system")
        self.logger.info("Resources should be implemented using @mcp.resource decorators directly in FastMCP")

        # For now, return 0 until resource loading is properly implemented
        # TODO: Implement proper resource loading compatible with FastMCP's resource system
        return 0


class PromptLoader:
    """Loads and registers prompts with the FastMCP server."""

    def __init__(self, mcp_server: FastMCP):
        self.mcp_server = mcp_server
        self.logger = logging.getLogger(f"{__name__}.PromptLoader")

    def load_prompts(self) -> int:
        """Load all discovered prompts into the MCP server."""
        self.logger.info("Prompt loading is currently not implemented")
        self.logger.info("The BasePrompt interface is incompatible with FastMCP's @mcp.prompt decorator system")
        self.logger.info("Prompts should be implemented using @mcp.prompt decorators directly in FastMCP")

        # For now, return 0 until prompt loading is properly implemented
        # TODO: Implement proper prompt loading compatible with FastMCP's prompt system
        return 0


class ComponentLoader:
    """Main component loader that coordinates loading of all component types."""

    def __init__(self, mcp_server: FastMCP):
        self.mcp_server = mcp_server
        self.tool_loader = ToolLoader(mcp_server)
        self.resource_loader = ResourceLoader(mcp_server)
        self.prompt_loader = PromptLoader(mcp_server)
        self.logger = logging.getLogger(f"{__name__}.ComponentLoader")

    def load_all_components(self) -> dict[str, int]:
        """
        Load all components (tools, resources, prompts) into the MCP server.

        Returns:
            Dict containing counts of loaded components by type
        """
        self.logger.info("Starting component loading...")

        # Load all component types
        tools_loaded = self.tool_loader.load_tools()
        resources_loaded = self.resource_loader.load_resources()
        prompts_loaded = self.prompt_loader.load_prompts()

        results = {
            "tools": tools_loaded,
            "resources": resources_loaded,
            "prompts": prompts_loaded
        }

        total_loaded = sum(results.values())
        self.logger.info(f"Loaded {total_loaded} total components: {results}")

        return results
