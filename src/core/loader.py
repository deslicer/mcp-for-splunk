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
        
        # Build parameter list excluding 'self' (keep ctx for FastMCP)
        params = []
        
        # First add the ctx parameter with proper typing
        ctx_param = inspect.Parameter('ctx', inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Context)
        params.append(ctx_param)
        
        # Then add all other parameters (excluding 'self' and 'ctx' from original)
        for param_name, param in sig.parameters.items():
            if param_name in ('self', 'ctx'):
                continue
            params.append(param.replace(annotation=param.annotation if param.annotation != inspect.Parameter.empty else Any))
        
        # Create new signature for the wrapper
        new_sig = inspect.Signature(params)
        
        async def tool_wrapper(ctx: Context, **kwargs):
            """Wrapper function that creates tool instance and calls execute."""
            try:
                # Create tool instance
                tool_instance = tool_class(tool_name, "modular")
                
                # Call the tool's execute method directly with kwargs
                # FastMCP will validate parameters based on our signature
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
        loaded_count = 0
        
        # Discover resources if not already done
        resource_metadata_list = resource_registry.list_resources()
        if not resource_metadata_list:
            discover_resources()
            resource_metadata_list = resource_registry.list_resources()
        
        # Use registry's private access for resource classes (this is internal framework use)
        for resource_metadata in resource_metadata_list:
            resource_uri = resource_metadata.uri
            resource_class = resource_registry._resources.get(resource_uri)
            
            if not resource_class:
                self.logger.error(f"Resource class not found for {resource_uri}")
                continue
                
            try:
                # Create resource instance
                resource_instance = resource_class(resource_uri, "modular", "modular resource")
                
                # Create wrapper function
                async def resource_wrapper(uri: str) -> str:
                    return await resource_instance.read(uri)
                
                # Register with FastMCP
                self.mcp_server.resource(resource_instance.get_uri_pattern())(resource_wrapper)
                
                loaded_count += 1
                self.logger.info(f"Loaded resource: {resource_uri}")
                
            except Exception as e:
                self.logger.error(f"Failed to register resource '{resource_uri}': {e}")
        
        self.logger.info(f"Loaded {loaded_count} resources into MCP server")
        return loaded_count


class PromptLoader:
    """Loads and registers prompts with the FastMCP server."""
    
    def __init__(self, mcp_server: FastMCP):
        self.mcp_server = mcp_server
        self.logger = logging.getLogger(f"{__name__}.PromptLoader")
    
    def load_prompts(self) -> int:
        """Load all discovered prompts into the MCP server."""
        loaded_count = 0
        
        # Discover prompts if not already done
        prompt_metadata_list = prompt_registry.list_prompts()
        if not prompt_metadata_list:
            discover_prompts()
            prompt_metadata_list = prompt_registry.list_prompts()
        
        # Use registry's private access for prompt classes (this is internal framework use)
        for prompt_metadata in prompt_metadata_list:
            prompt_name = prompt_metadata.name
            prompt_class = prompt_registry._prompts.get(prompt_name)
            
            if not prompt_class:
                self.logger.error(f"Prompt class not found for {prompt_name}")
                continue
                
            try:
                # Create prompt instance
                prompt_instance = prompt_class(prompt_name, "modular")
                
                # Create wrapper function
                async def prompt_wrapper(arguments: Dict[str, Any]) -> str:
                    return await prompt_instance.render(arguments)
                
                # Register with FastMCP
                self.mcp_server.prompt(prompt_name)(prompt_wrapper)
                
                loaded_count += 1
                self.logger.info(f"Loaded prompt: {prompt_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to register prompt '{prompt_name}': {e}")
        
        self.logger.info(f"Loaded {loaded_count} prompts into MCP server")
        return loaded_count


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