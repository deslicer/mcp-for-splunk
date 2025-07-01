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
    """Loads and registers resources with the FastMCP server using ResourceRegistry."""

    def __init__(self, mcp_server: FastMCP):
        self.mcp_server = mcp_server
        self.logger = logging.getLogger(f"{__name__}.ResourceLoader")
        self._registered_resources = {}  # URI -> resource_type mapping

    def load_resources(self) -> int:
        """Load all discovered resources into the MCP server."""
        from .discovery import discover_resources
        from .registry import resource_registry

        loaded_count = 0

        # Discover resources if not already done
        resource_metadata_list = resource_registry.list_resources()
        if not resource_metadata_list:
            discover_resources()
            resource_metadata_list = resource_registry.list_resources()

        # Also load our Splunk-specific resources
        loaded_count += self._load_splunk_resources()

        # Load resources from registry
        for metadata in resource_metadata_list:
            try:
                loaded_count += self._load_single_resource(metadata)
            except Exception as e:
                self.logger.error(f"Failed to load resource {metadata.uri}: {e}")

        # Note: FastMCP automatically handles resource listing when resources are registered
        # with @mcp.resource() decorators, so no explicit list handler registration is needed

        self.logger.info(f"Successfully loaded {loaded_count} resources")
        return loaded_count

    def _load_splunk_resources(self) -> int:
        """Load Splunk-specific resources into the registry and FastMCP"""
        try:
            from .base import ResourceMetadata
            from .registry import resource_registry
            from .resources.splunk_config import (
                SplunkAppsResource,
                SplunkConfigResource,
                SplunkHealthResource,
                SplunkIndexesResource,
                SplunkSavedSearchesResource,
                SplunkSearchResultsResource,
            )

            loaded_count = 0

            # Define resource configurations
            resource_configs = [
                {
                    "class": SplunkConfigResource,
                    "template": True,
                    "pattern": "splunk://config/{config_file}",
                    "uris": []  # Template resources don't need predefined URIs
                },
                {
                    "class": SplunkHealthResource,
                    "uris": [
                        "splunk://health/status",
                        # "splunk://health/indexer",
                        # "splunk://health/search",
                        # "splunk://health/forwarder"
                    ]
                },
                {
                    "class": SplunkAppsResource,
                    "uris": [
                        "splunk://apps/installed",
                        # "splunk://apps/enabled",
                        # "splunk://apps/disabled"
                    ]
                },
                {
                    "class": SplunkIndexesResource,
                    "uris": [
                        "splunk://indexes/list"
                    ]
                },
                {
                    "class": SplunkSavedSearchesResource,
                    "uris": [
                        "splunk://savedsearches/list"
                    ]
                },
                {
                    "class": SplunkSearchResultsResource,
                    "uris": [
                        "splunk://search/results/recent",
                        "splunk://search/results/completed"
                    ]
                }
            ]

            # Load each resource type
            for config in resource_configs:
                resource_class = config["class"]
                is_template = config.get("template", False)
                uris = config["uris"]

                if is_template:
                    # Handle template resources
                    try:
                        pattern = config.get("pattern", resource_class.METADATA.uri)

                        # Register template with ResourceRegistry using the pattern
                        resource_registry.register(resource_class, resource_class.METADATA)

                        # Register template with FastMCP server
                        self._register_template_resource(resource_class, pattern)

                        self._registered_resources[pattern] = f"{resource_class.__name__} (template)"
                        loaded_count += 1
                        self.logger.debug(f"Loaded Splunk template resource: {pattern}")

                    except Exception as e:
                        self.logger.error(f"Failed to load Splunk template resource {pattern}: {e}")
                else:
                    # Handle regular resources with specific URIs
                    for uri in uris:
                        try:
                            # Create metadata for this specific URI
                            base_metadata = resource_class.METADATA
                            metadata = ResourceMetadata(
                                uri=uri,
                                name=f"{base_metadata.name} - {self._get_resource_name_from_uri(uri)}",
                                description=f"{base_metadata.description} ({uri})",
                                mime_type=base_metadata.mime_type,
                                category=base_metadata.category,
                                tags=base_metadata.tags
                            )

                            # Register with ResourceRegistry
                            resource_registry.register(resource_class, metadata)

                            # Register with FastMCP server
                            self._register_with_fastmcp(resource_class, uri)

                            self._registered_resources[uri] = resource_class.__name__
                            loaded_count += 1
                            self.logger.debug(f"Loaded Splunk resource: {uri}")

                        except Exception as e:
                            self.logger.error(f"Failed to load Splunk resource {uri}: {e}")

            return loaded_count

        except ImportError as e:
            self.logger.warning(f"Could not import Splunk resources: {e}")
            return 0

    def _load_single_resource(self, metadata) -> int:
        """Load a single resource from registry into FastMCP"""
        try:
            from .registry import resource_registry

            # Skip if already loaded as Splunk resource
            if metadata.uri in self._registered_resources:
                return 0

            # Get resource class from registry
            resource_class = resource_registry._resources.get(metadata.uri)
            if not resource_class:
                self.logger.warning(f"No resource class found for URI: {metadata.uri}")
                return 0

            # Register with FastMCP
            self._register_with_fastmcp(resource_class, metadata.uri)
            self._registered_resources[metadata.uri] = resource_class.__name__

            self.logger.debug(f"Loaded registry resource: {metadata.uri}")
            return 1

        except Exception as e:
            self.logger.error(f"Failed to load resource {metadata.uri}: {e}")
            return 0

    def _register_template_resource(self, resource_class, pattern: str):
        """Register template resource with FastMCP that handles dynamic URIs"""
        # For config template, register a catch-all pattern
        if "config" in pattern:
            @self.mcp_server.resource("splunk://config/{config_file}", name="get_config_resource")
            async def get_config_template(config_file: str) -> str:
                """Get Splunk configuration resource (template)"""
                try:
                    from .registry import resource_registry
                    ctx = get_context()

                    # Create the actual URI from the template
                    uri = f"splunk://config/{config_file}"

                    # Get resource instance from registry using the pattern
                    resource = resource_registry.get_resource(pattern)
                    if not resource:
                        # Create instance directly if not in registry
                        resource = resource_class(
                            uri=pattern,
                            name=resource_class.METADATA.name,
                            description=resource_class.METADATA.description,
                            mime_type=resource_class.METADATA.mime_type
                        )

                    # Call with the specific URI
                    return await resource.get_content(ctx, uri)
                except Exception as e:
                    self.logger.error(f"Error reading config template {config_file}: {e}")
                    raise RuntimeError(f"Failed to read config: {str(e)}")
        else:
            # Fallback for other template types
            self._register_generic_resource(resource_class, pattern)

    def _register_with_fastmcp(self, resource_class, uri: str):
        """Register resource with FastMCP using appropriate pattern matching"""
        # Extract the pattern from URI for FastMCP registration
        if "config" in uri:
            self._register_config_resource(resource_class, uri)
        elif "health" in uri:
            self._register_health_resource(resource_class, uri)
        elif "apps" in uri:
            self._register_apps_resource(resource_class, uri)
        elif "indexes" in uri:
            self._register_indexes_resource(resource_class, uri)
        elif "savedsearches" in uri:
            self._register_saved_searches_resource(resource_class, uri)
        elif "search" in uri:
            self._register_search_resource(resource_class, uri)
        else:
            # Generic resource registration
            self._register_generic_resource(resource_class, uri)

    def _register_config_resource(self, resource_class, uri: str):
        """Register configuration resource with FastMCP"""
        config_file = self._extract_config_file_from_uri(uri)
        # Create unique resource URI to avoid conflicts
        unique_uri = f"splunk://config/{config_file}/{hash(uri) % 10000}"

        name = "get_config_"+config_file.replace("/", "_")
        @self.mcp_server.resource(unique_uri, name=name)
        async def get_config_resource() -> str:
            """Get Splunk configuration resource"""
            try:
                from .registry import resource_registry
                ctx = get_context()
                resource = resource_registry.get_resource(uri)
                if not resource:
                    raise ValueError(f"Resource not found: {uri}")
                return await resource.get_content(ctx)
            except Exception as e:
                self.logger.error(f"Error reading config resource {uri}: {e}")
                raise RuntimeError(f"Failed to read config: {str(e)}")

    def _register_health_resource(self, resource_class, uri: str):
        """Register health resource with FastMCP"""
        component = self._extract_component_from_uri(uri)
        # Create unique resource URI to avoid conflicts
        unique_uri = f"splunk://health/{component}/{hash(uri) % 10000}"

        name = "get_health_"+component.replace("/", "_")
        @self.mcp_server.resource(unique_uri, name=name)
        async def get_health_resource() -> str:
            """Get Splunk health resource"""
            try:
                from .registry import resource_registry
                ctx = get_context()
                resource = resource_registry.get_resource(uri)
                if not resource:
                    raise ValueError(f"Resource not found: {uri}")
                return await resource.get_content(ctx)
            except Exception as e:
                self.logger.error(f"Error reading health resource {uri}: {e}")
                raise RuntimeError(f"Failed to read health: {str(e)}")

    def _register_apps_resource(self, resource_class, uri: str):
        """Register apps resource with FastMCP"""
        app_type = self._extract_app_type_from_uri(uri)
        # Create unique resource URI to avoid conflicts
        unique_uri = f"splunk://apps/{app_type}/{hash(uri) % 10000}"
        name = "get_apps_"+app_type.replace("/", "_")
        @self.mcp_server.resource(unique_uri, name=name)
        async def get_apps_resource() -> str:
            """Get Splunk apps resource"""
            try:
                from .registry import resource_registry
                ctx = get_context()
                resource = resource_registry.get_resource(uri)
                if not resource:
                    raise ValueError(f"Resource not found: {uri}")
                return await resource.get_content(ctx)
            except Exception as e:
                self.logger.error(f"Error reading apps resource {uri}: {e}")
                raise RuntimeError(f"Failed to read apps: {str(e)}")

    def _register_search_resource(self, resource_class, uri: str):
        """Register search resource with FastMCP"""
        search_type = self._extract_search_type_from_uri(uri)
        # Create unique resource URI to avoid conflicts
        unique_uri = f"splunk://search/{search_type}/{hash(uri) % 10000}"
        name = "get_search_"+search_type.replace("/", "_")
        @self.mcp_server.resource(unique_uri, name=name)
        async def get_search_resource() -> str:
            """Get Splunk search resource"""
            try:
                from .registry import resource_registry
                ctx = get_context()
                resource = resource_registry.get_resource(uri)
                if not resource:
                    raise ValueError(f"Resource not found: {uri}")
                return await resource.get_content(ctx)
            except Exception as e:
                self.logger.error(f"Error reading search resource {uri}: {e}")
                raise RuntimeError(f"Failed to read search: {str(e)}")

    def _register_generic_resource(self, resource_class, uri: str):
        """Register generic resource with FastMCP"""
        @self.mcp_server.resource(uri)
        async def get_generic_resource() -> str:
            """Get generic resource"""
            try:
                from .registry import resource_registry
                ctx = get_context()
                resource = resource_registry.get_resource(uri)
                if not resource:
                    raise ValueError(f"Resource not found: {uri}")
                return await resource.get_content(ctx)
            except Exception as e:
                self.logger.error(f"Error reading resource {uri}: {e}")
                raise RuntimeError(f"Failed to read resource: {str(e)}")



    def _get_resource_name_from_uri(self, uri: str) -> str:
        """Extract a human-readable name from URI"""
        parts = uri.split('/')
        if len(parts) > 0:
            return parts[-1].replace('.conf', '').replace('_', ' ').title()
        return "Unknown"

    def _extract_config_file_from_uri(self, uri: str) -> str:
        """Extract config file name from URI"""
        parts = uri.split('/')
        return parts[-1] if parts else "unknown.conf"

    def _extract_component_from_uri(self, uri: str) -> str:
        """Extract component name from health URI"""
        parts = uri.split('/')
        return parts[-1] if parts else "status"

    def _extract_app_type_from_uri(self, uri: str) -> str:
        """Extract app type from apps URI"""
        parts = uri.split('/')
        return parts[-1] if parts else "installed"

    def _extract_search_type_from_uri(self, uri: str) -> str:
        """Extract search type from search URI"""
        parts = uri.split('/')
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"  # e.g., "results/recent"
        return parts[-1] if parts else "recent"

    def _register_indexes_resource(self, resource_class, uri: str):
        """Register indexes resource with FastMCP"""
        # Create unique resource URI to avoid conflicts
        unique_uri = f"splunk://indexes/list/{hash(uri) % 10000}"
        name = "get_indexes_list"
        @self.mcp_server.resource(unique_uri, name=name)
        async def get_indexes_resource() -> str:
            """Get Splunk indexes resource"""
            try:
                from .registry import resource_registry
                ctx = get_context()
                resource = resource_registry.get_resource(uri)
                if not resource:
                    raise ValueError(f"Resource not found: {uri}")
                return await resource.get_content(ctx)
            except Exception as e:
                self.logger.error(f"Error reading indexes resource {uri}: {e}")
                raise RuntimeError(f"Failed to read indexes: {str(e)}")

    def _register_saved_searches_resource(self, resource_class, uri: str):
        """Register saved searches resource with FastMCP"""
        # Create unique resource URI to avoid conflicts
        unique_uri = f"splunk://savedsearches/list/{hash(uri) % 10000}"
        name = "get_saved_searches_list"
        @self.mcp_server.resource(unique_uri, name=name)
        async def get_saved_searches_resource() -> str:
            """Get Splunk saved searches resource"""
            try:
                from .registry import resource_registry
                ctx = get_context()
                resource = resource_registry.get_resource(uri)
                if not resource:
                    raise ValueError(f"Resource not found: {uri}")
                return await resource.get_content(ctx)
            except Exception as e:
                self.logger.error(f"Error reading saved searches resource {uri}: {e}")
                raise RuntimeError(f"Failed to read saved searches: {str(e)}")


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
