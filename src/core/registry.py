"""
Registry system for managing tools, resources, and prompts.

Provides centralized registration and discovery of MCP components.
"""

import logging
from typing import Any, Dict, List, Optional, Type

from .base import BaseTool, BaseResource, BasePrompt, ToolMetadata, ResourceMetadata, PromptMetadata

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing MCP tools"""
    
    def __init__(self):
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._instances: Dict[str, BaseTool] = {}
    
    def register(self, tool_class: Type[BaseTool], metadata: ToolMetadata) -> None:
        """
        Register a tool class with metadata.
        
        Args:
            tool_class: Tool class to register
            metadata: Tool metadata
        """
        name = metadata.name
        
        if name in self._tools:
            logger.warning(f"Tool '{name}' is already registered, overwriting")
        
        self._tools[name] = tool_class
        self._metadata[name] = metadata
        
        logger.info(f"Registered tool: {name} (category: {metadata.category})")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool instance by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        if name not in self._tools:
            return None
        
        # Create singleton instance
        if name not in self._instances:
            tool_class = self._tools[name]
            metadata = self._metadata[name]
            self._instances[name] = tool_class(metadata.name, metadata.description)
        
        return self._instances[name]
    
    def list_tools(self, category: Optional[str] = None) -> List[ToolMetadata]:
        """
        List all registered tools, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of tool metadata
        """
        if category:
            return [meta for meta in self._metadata.values() if meta.category == category]
        return list(self._metadata.values())
    
    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """
        Get tool metadata by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool metadata or None if not found
        """
        return self._metadata.get(name)
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.
        
        Args:
            name: Tool name
            
        Returns:
            True if tool was unregistered, False if not found
        """
        if name not in self._tools:
            return False
        
        del self._tools[name]
        del self._metadata[name]
        if name in self._instances:
            del self._instances[name]
        
        logger.info(f"Unregistered tool: {name}")
        return True


class ResourceRegistry:
    """Registry for managing MCP resources"""
    
    def __init__(self):
        self._resources: Dict[str, Type[BaseResource]] = {}
        self._metadata: Dict[str, ResourceMetadata] = {}
        self._instances: Dict[str, BaseResource] = {}
    
    def register(self, resource_class: Type[BaseResource], metadata: ResourceMetadata) -> None:
        """
        Register a resource class with metadata.
        
        Args:
            resource_class: Resource class to register
            metadata: Resource metadata
        """
        uri = metadata.uri
        
        if uri in self._resources:
            logger.warning(f"Resource '{uri}' is already registered, overwriting")
        
        self._resources[uri] = resource_class
        self._metadata[uri] = metadata
        
        logger.info(f"Registered resource: {uri} (category: {metadata.category})")
    
    def get_resource(self, uri: str) -> Optional[BaseResource]:
        """
        Get a resource instance by URI.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource instance or None if not found
        """
        if uri not in self._resources:
            return None
        
        # Create singleton instance
        if uri not in self._instances:
            resource_class = self._resources[uri]
            metadata = self._metadata[uri]
            self._instances[uri] = resource_class(
                metadata.uri, 
                metadata.name, 
                metadata.description, 
                metadata.mime_type
            )
        
        return self._instances[uri]
    
    def list_resources(self, category: Optional[str] = None) -> List[ResourceMetadata]:
        """
        List all registered resources, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of resource metadata
        """
        if category:
            return [meta for meta in self._metadata.values() if meta.category == category]
        return list(self._metadata.values())
    
    def get_metadata(self, uri: str) -> Optional[ResourceMetadata]:
        """
        Get resource metadata by URI.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource metadata or None if not found
        """
        return self._metadata.get(uri)


class PromptRegistry:
    """Registry for managing MCP prompts"""
    
    def __init__(self):
        self._prompts: Dict[str, Type[BasePrompt]] = {}
        self._metadata: Dict[str, PromptMetadata] = {}
        self._instances: Dict[str, BasePrompt] = {}
    
    def register(self, prompt_class: Type[BasePrompt], metadata: PromptMetadata) -> None:
        """
        Register a prompt class with metadata.
        
        Args:
            prompt_class: Prompt class to register
            metadata: Prompt metadata
        """
        name = metadata.name
        
        if name in self._prompts:
            logger.warning(f"Prompt '{name}' is already registered, overwriting")
        
        self._prompts[name] = prompt_class
        self._metadata[name] = metadata
        
        logger.info(f"Registered prompt: {name} (category: {metadata.category})")
    
    def get_prompt(self, name: str) -> Optional[BasePrompt]:
        """
        Get a prompt instance by name.
        
        Args:
            name: Prompt name
            
        Returns:
            Prompt instance or None if not found
        """
        if name not in self._prompts:
            return None
        
        # Create singleton instance
        if name not in self._instances:
            prompt_class = self._prompts[name]
            metadata = self._metadata[name]
            self._instances[name] = prompt_class(metadata.name, metadata.description)
        
        return self._instances[name]
    
    def list_prompts(self, category: Optional[str] = None) -> List[PromptMetadata]:
        """
        List all registered prompts, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of prompt metadata
        """
        if category:
            return [meta for meta in self._metadata.values() if meta.category == category]
        return list(self._metadata.values())
    
    def get_metadata(self, name: str) -> Optional[PromptMetadata]:
        """
        Get prompt metadata by name.
        
        Args:
            name: Prompt name
            
        Returns:
            Prompt metadata or None if not found
        """
        return self._metadata.get(name)


# Global registry instances
tool_registry = ToolRegistry()
resource_registry = ResourceRegistry()
prompt_registry = PromptRegistry() 