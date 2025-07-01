"""
Component loader for the MCP server.

This module handles loading and registering tools, resources, and prompts
with the FastMCP server instance.
"""

import inspect
import logging
import uuid
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
            if name not in ("self", "ctx"):
                # Use the type hint if available, otherwise fall back to annotation
                param_annotation = type_hints.get(name, param.annotation)
                if param_annotation == inspect.Parameter.empty:
                    param_annotation = Any

                # Create new parameter with proper type annotation
                new_param = inspect.Parameter(
                    name=name, kind=param.kind, default=param.default, annotation=param_annotation
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
                    raise RuntimeError(
                        f"Tool {tool_name} can only be called within an MCP request context"
                    )

                # Bind the arguments to ensure proper parameter mapping
                bound_args = wrapper_sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                # Call the tool's execute method
                result = await tool_instance.execute(ctx, **bound_args.arguments)
                return result

            except Exception as e:
                self.logger.error(f"Tool {tool_name} execution failed: {e}")
                self.logger.exception("Full traceback:")
                return {"status": "error", "error": str(e)}

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
        return_annotation = type_hints.get("return", sig.return_annotation)
        if return_annotation != inspect.Parameter.empty:
            tool_wrapper.__annotations__["return"] = return_annotation

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

    def clear_resources(self):
        """Clear all registered resources to allow fresh reload."""
        self.logger.info("Clearing all registered resources")
        self._registered_resources.clear()

    def force_reload_resources(self) -> int:
        """Force reload all resources by clearing cache first."""
        self.clear_resources()
        return self.load_resources()

    def load_resources(self) -> int:
        """Load all discovered resources into the MCP server."""
        from .discovery import discover_resources
        from .registry import resource_registry

        loaded_count = 0

        # Check if resources are already loaded to prevent duplicates
        if len(self._registered_resources) > 0:
            self.logger.info(
                f"Resources already loaded ({len(self._registered_resources)} resources), skipping reload"
            )
            return len(self._registered_resources)

        # First, pre-register our Splunk resources to ensure they're available
        self._load_manual_splunk_resources()

        # Discover additional resources if needed
        resource_metadata_list = resource_registry.list_resources()
        if not resource_metadata_list:
            discover_resources()
            resource_metadata_list = resource_registry.list_resources()

        # Load all resources from registry (both manual and discovered)
        for metadata in resource_metadata_list:
            try:
                loaded_count += self._load_single_resource(metadata)
            except Exception as e:
                self.logger.error(f"Failed to load resource {metadata.uri}: {e}")

        # Note: FastMCP automatically handles resource listing when resources are registered
        # with @mcp.resource() decorators, so no explicit list handler registration is needed

        self.logger.info(f"Successfully loaded {loaded_count} resources")
        return loaded_count

    def _load_manual_splunk_resources(self) -> None:
        """Pre-register Splunk-specific resources with the discovery registry"""
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

            # Manually register these resources with the discovery registry
            # This ensures they're available for the normal discovery and loading process
            splunk_resources = [
                (SplunkConfigResource, "splunk://config/{config_file}"),  # Template
                (SplunkHealthResource, "splunk://health/status"),
                (SplunkAppsResource, "splunk://apps/installed"),
                (SplunkIndexesResource, "splunk://indexes/list"),
                (SplunkSavedSearchesResource, "splunk://savedsearches/list"),
                # (SplunkSearchResultsResource, "splunk://search/results/recent"),
                (SplunkSearchResultsResource, "splunk://search/results/completed"),
            ]

            for resource_class, uri in splunk_resources:
                if hasattr(resource_class, "METADATA"):
                    # Create specific metadata for this URI
                    base_metadata = resource_class.METADATA
                    metadata = ResourceMetadata(
                        uri=uri,
                        name=base_metadata.name,
                        description=base_metadata.description,
                        mime_type=base_metadata.mime_type,
                        category=base_metadata.category,
                        tags=base_metadata.tags or [],
                    )

                    # Register with the discovery registry
                    try:
                        resource_registry.register(resource_class, metadata)
                        self.logger.debug(
                            f"Registered {resource_class.__name__} ({uri}) with discovery registry"
                        )
                    except Exception as e:
                        self.logger.warning(
                            f"Could not register {resource_class.__name__} with discovery: {e}"
                        )

            self.logger.info(
                f"Pre-registered {len(splunk_resources)} Splunk resources with discovery system"
            )

        except ImportError as e:
            self.logger.warning(f"Could not import Splunk resources: {e}")

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

            # Check if this is a template resource
            if "{" in metadata.uri and "}" in metadata.uri:
                # Template resource - register with special handling
                self._register_template_resource(resource_class, metadata.uri)
                self._registered_resources[metadata.uri] = f"{resource_class.__name__} (template)"
                self.logger.debug(f"Loaded template resource: {metadata.uri}")
            else:
                # Regular resource - register with FastMCP
                self._register_with_fastmcp(resource_class, metadata.uri, metadata)
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
            async def get_config_template(
                config_file: str,
                captured_pattern: str = pattern,
                captured_resource_class=resource_class,
            ) -> str:  # Fix closure bug with default parameters
                """Get Splunk configuration resource (template)"""
                try:
                    from .registry import resource_registry

                    ctx = get_context()

                    # Create the actual URI from the template
                    uri = f"splunk://config/{config_file}"

                    # Get resource instance from registry using the pattern
                    resource = resource_registry.get_resource(captured_pattern)
                    if not resource:
                        # Create instance directly if not in registry
                        resource = captured_resource_class(
                            uri=captured_pattern,
                            name=captured_resource_class.METADATA.name,
                            description=captured_resource_class.METADATA.description,
                            mime_type=captured_resource_class.METADATA.mime_type,
                        )

                    # Call with the specific URI
                    return await resource.get_content(ctx, uri)
                except Exception as e:
                    self.logger.error(f"Error reading config template {config_file}: {e}")
                    raise RuntimeError(f"Failed to read config: {str(e)}")
        else:
            # Fallback for other template types
            self._register_generic_resource(resource_class, pattern, resource_class.METADATA)

    def _register_with_fastmcp(self, resource_class, uri: str, metadata):
        """Register resource with FastMCP using appropriate pattern matching"""
        # Extract the pattern from URI for FastMCP registration
        if "config" in uri:
            self._register_config_resource(resource_class, uri, metadata)
        elif "health" in uri:
            self._register_health_resource(resource_class, uri, metadata)
        elif "apps" in uri:
            self._register_apps_resource(resource_class, uri, metadata)
        elif "indexes" in uri:
            self._register_indexes_resource(resource_class, uri, metadata)
        elif "savedsearches" in uri:
            self._register_saved_searches_resource(resource_class, uri, metadata)
        elif "search" in uri:
            self._register_search_resource(resource_class, uri, metadata)
        else:
            # Generic resource registration
            self._register_generic_resource(resource_class, uri, metadata)

    def _register_config_resource(self, resource_class, uri: str, metadata):
        """Register configuration resource with FastMCP"""
        # Use metadata for proper naming and description
        resource_name = metadata.name
        resource_description = metadata.description

        # Create a closure to capture the URI - static resources have no function parameters
        @self.mcp_server.resource(uri, name=resource_name, description=resource_description)
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

    def _register_health_resource(self, resource_class, uri: str, metadata):
        """Register health resource with FastMCP"""
        # Use metadata for proper naming and description
        resource_name = metadata.name
        resource_description = metadata.description

        # Create a closure to capture the URI - static resources have no function parameters
        @self.mcp_server.resource(uri, name=resource_name, description=resource_description)
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

    def _register_apps_resource(self, resource_class, uri: str, metadata):
        """Register apps resource with FastMCP"""
        # Use metadata for proper naming and description
        resource_name = metadata.name
        resource_description = metadata.description

        # Create a closure to capture the URI - static resources have no function parameters
        @self.mcp_server.resource(uri, name=resource_name, description=resource_description)
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

    def _register_search_resource(self, resource_class, uri: str, metadata):
        """Register search resource with FastMCP"""
        # Use metadata for proper naming and description
        resource_name = metadata.name
        resource_description = metadata.description

        # Create a closure to capture the URI - static resources have no function parameters
        @self.mcp_server.resource(uri, name=resource_name, description=resource_description)
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

    def _register_generic_resource(self, resource_class, uri: str, metadata):
        """Register generic resource with FastMCP"""
        # Use metadata for proper naming and description
        resource_name = metadata.name
        resource_description = metadata.description

        # Create a closure to capture the URI - static resources have no function parameters
        @self.mcp_server.resource(uri, name=resource_name, description=resource_description)
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
        parts = uri.split("/")
        if len(parts) > 0:
            return parts[-1].replace(".conf", "").replace("_", " ").title()
        return "Unknown"

    def _register_indexes_resource(self, resource_class, uri: str, metadata):
        """Register indexes resource with FastMCP"""
        # Use metadata for proper naming and description
        resource_name = metadata.name
        resource_description = metadata.description

        # Create a closure to capture the URI - static resources have no function parameters
        @self.mcp_server.resource(uri, name=resource_name, description=resource_description)
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

    def _register_saved_searches_resource(self, resource_class, uri: str, metadata):
        """Register saved searches resource with FastMCP"""
        # Use metadata for proper naming and description
        resource_name = metadata.name
        resource_description = metadata.description

        # Create a closure to capture the URI - static resources have no function parameters
        @self.mcp_server.resource(uri, name=resource_name, description=resource_description)
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
        self.logger.info(
            "The BasePrompt interface is incompatible with FastMCP's @mcp.prompt decorator system"
        )
        self.logger.info(
            "Prompts should be implemented using @mcp.prompt decorators directly in FastMCP"
        )

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

        results = {"tools": tools_loaded, "resources": resources_loaded, "prompts": prompts_loaded}

        total_loaded = sum(results.values())
        self.logger.info(f"Loaded {total_loaded} total components: {results}")

        return results
