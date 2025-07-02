"""
Registry system for managing tools, resources, and prompts.

Provides centralized registration and discovery of MCP components.
"""

import logging

from .base import BasePrompt, BaseResource, BaseTool, PromptMetadata, ResourceMetadata, ToolMetadata

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing MCP tools"""

    def __init__(self):
        self._tools: dict[str, type[BaseTool]] = {}
        self._metadata: dict[str, ToolMetadata] = {}
        self._instances: dict[str, BaseTool] = {}

    def register(self, tool_class: type[BaseTool], metadata: ToolMetadata) -> None:
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

    def get_tool(self, name: str) -> BaseTool | None:
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

    def list_tools(self, category: str | None = None) -> list[ToolMetadata]:
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

    def get_metadata(self, name: str) -> ToolMetadata | None:
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
        self._resources: dict[str, type[BaseResource]] = {}
        self._metadata: dict[str, ResourceMetadata] = {}
        self._instances: dict[str, BaseResource] = {}

    def register(self, resource_class: type[BaseResource], metadata: ResourceMetadata) -> None:
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

    def get_resource(self, uri: str) -> BaseResource | None:
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
                metadata.uri, metadata.name, metadata.description, metadata.mime_type
            )

        return self._instances[uri]

    def list_resources(self, category: str | None = None) -> list[ResourceMetadata]:
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

    def get_metadata(self, uri: str) -> ResourceMetadata | None:
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
        self._prompts: dict[str, type[BasePrompt]] = {}
        self._metadata: dict[str, PromptMetadata] = {}
        self._instances: dict[str, BasePrompt] = {}

    def register(self, prompt_class: type[BasePrompt], metadata: PromptMetadata) -> None:
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

    def get_prompt(self, name: str) -> BasePrompt | None:
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

    def list_prompts(self, category: str | None = None) -> list[PromptMetadata]:
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

    def get_metadata(self, name: str) -> PromptMetadata | None:
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
