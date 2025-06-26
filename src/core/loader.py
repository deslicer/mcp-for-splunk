"""
Component loader for the MCP server.

This module handles loading and registering tools, resources, and prompts
with the FastMCP server instance.
"""

import inspect
import logging
from typing import Any, Dict, List, Optional, Type

from fastmcp import FastMCP, Context

from .base import BaseTool, BaseResource, BasePrompt
from .discovery import discover_tools, discover_resources, discover_prompts
from .registry import tool_registry, resource_registry, prompt_registry

logger = logging.getLogger(__name__)


class ToolLoader:
    """Loads and registers tools with the FastMCP server."""
    
    def __init__(self, mcp_server: FastMCP):
        self.mcp_server = mcp_server
        self.logger = logging.getLogger(f"{__name__}.ToolLoader")
    
    def _create_tool_wrapper(self, tool_class: Type[BaseTool], tool_name: str):
        """Create a wrapper function for the tool that FastMCP can register."""
        
        # Get the execute method signature
        execute_method = getattr(tool_class, 'execute')
        sig = inspect.signature(execute_method)
        
        logger.debug(f"Tool {tool_name} - Original signature: {sig}")
        
        # Build parameter list - include Context as first parameter (FastMCP dependency injection)
        params = []
        
        # Add Context parameter first (FastMCP will inject this automatically)
        ctx_param = inspect.Parameter(
            'ctx',
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=Context
        )
        params.append(ctx_param)
        
        # Process all parameters from the original signature (except 'self' and 'ctx')
        for param_name, param in sig.parameters.items():
            if param_name in ('self', 'ctx'):
                continue
            
            logger.debug(f"Tool {tool_name} - Processing param: {param_name} = {param}")
            
            # For other parameters, preserve their signatures but ensure proper annotations
            # Handle union types like str | None properly
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else Any
            
            logger.debug(f"Tool {tool_name} - Param {param_name}: annotation={annotation}, default={param.default}")
            
            # Preserve the parameter with its original default value and annotation
            new_param = inspect.Parameter(
                param_name,
                param.kind,
                default=param.default,
                annotation=annotation
            )
            params.append(new_param)
        
        # Create new signature for the wrapper (with ctx parameter for FastMCP injection)
        new_sig = inspect.Signature(params)
        logger.debug(f"Tool {tool_name} - New signature: {new_sig}")
        
        async def tool_wrapper(ctx: Context, **kwargs):
            """Wrapper function that creates tool instance and calls execute."""
            try:
                # Create tool instance
                tool_instance = tool_class(tool_name, "modular")
                
                # Call the tool's execute method with ctx and other parameters
                result = await tool_instance.execute(ctx, **kwargs)
                return result
                
            except Exception as e:
                logger.error(f"Tool {tool_name} execution failed: {e}")
                return {
                    "status": "error",
                    "error": str(e)
                }
        
        # Apply the signature to the wrapper
        tool_wrapper.__signature__ = new_sig
        tool_wrapper.__name__ = tool_name
        tool_wrapper.__doc__ = tool_class.METADATA.description
        
        logger.debug(f"Tool {tool_name} - Final wrapper signature: {tool_wrapper.__signature__}")
        
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
    
    def load_all_components(self) -> Dict[str, int]:
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