"""
Component loader for the MCP server.

This module handles loading and registering tools, resources, and prompts
with the FastMCP server instance.
"""

import inspect
import logging
import os
import sys
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
        self._loaded_tools = {}  # Track loaded tools for reload functionality

    def reload_tools(self) -> int:
        """
        Reload all tools by clearing cache and rediscovering.
        Useful for development hot reload.
        """
        self.logger.info("Hot reloading tools...")

        # Clear the tool registry to force rediscovery
        tool_registry._tools.clear()
        tool_registry._metadata.clear()
        tool_registry._instances.clear()

        # Clear our tracking
        self._loaded_tools.clear()

        # Reload tool modules if in development mode
        if os.environ.get("MCP_RELOAD_MODULES", "false").lower() == "true":
            self._reload_tool_modules()

        # Rediscover and load tools
        return self.load_tools()

    def _reload_tool_modules(self):
        """Reload Python modules containing tools to pick up changes."""
        import importlib

        # Get list of modules that might contain tools
        tool_modules = [
            "src.tools.admin.tool_enhancer",
            "src.tools.admin.apps",
            "src.tools.admin.config",
            "src.tools.admin.users",
            "src.tools.admin.me",
            "src.tools.admin.app_management",
            "src.tools.health.status",
            "src.tools.kvstore.collections",
            "src.tools.kvstore.data",
            "src.tools.metadata.indexes",
            "src.tools.metadata.sources",
            "src.tools.metadata.sourcetypes",
            "src.tools.search.oneshot_search",
            "src.tools.search.job_search",
            "src.tools.search.saved_search_tools",
            "src.tools.workflows.workflow_requirements",
            "src.tools.workflows.workflow_builder",
            "src.tools.workflows.list_workflows",
            "src.tools.workflows.workflow_runner",
        ]

        reloaded_count = 0
        for module_name in tool_modules:
            try:
                if module_name in sys.modules:
                    self.logger.debug(f"Reloading module: {module_name}")
                    importlib.reload(sys.modules[module_name])
                    reloaded_count += 1
            except Exception as e:
                self.logger.warning(f"Failed to reload module {module_name}: {e}")

        self.logger.info(f"Reloaded {reloaded_count} tool modules")

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
                    ) from e

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
            from .base import ResourceMetadata  # noqa: F401
            from .registry import resource_registry  # noqa: F401

            # First, register documentation resources
            self._register_documentation_resources()

            # Core Splunk config resources are now registered automatically
            # through the resources __init__.py registration system
            pass

        except ImportError as e:
            self.logger.warning(f"Could not import Splunk resources: {e}")

    def _register_documentation_resources(self) -> None:
        """Register Splunk documentation resources with the discovery registry"""
        try:
            # Import and register documentation resources
            from ..resources import register_all_resources

            register_all_resources()
            self.logger.info("Registered Splunk documentation resources")

            # Register dynamic documentation handlers
            self._register_dynamic_documentation_handlers()

        except ImportError as e:
            self.logger.debug(f"Documentation resources not available: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to register documentation resources: {e}")

    def _register_dynamic_documentation_handlers(self) -> None:
        """Register dynamic documentation resource handlers with FastMCP"""
        try:
            self.logger.info("Starting registration of dynamic documentation handlers...")

            # Register troubleshooting documentation handler
            self.logger.info("Registering troubleshooting documentation handler...")

            @self.mcp_server.resource(
                "splunk-docs://{version}/troubleshooting/{topic}", name="get_troubleshooting_docs"
            )
            async def get_troubleshooting_docs(version: str, topic: str) -> str:
                """Get Splunk troubleshooting documentation for specific version and topic"""
                try:
                    from ..resources.splunk_docs import create_troubleshooting_resource

                    ctx = get_context()

                    resource = create_troubleshooting_resource(version, topic)
                    content = await resource.get_content(ctx)
                    return content
                except Exception as e:
                    self.logger.error(f"Error getting troubleshooting docs for {topic}: {e}")
                    return f"""# Error: Troubleshooting Documentation

Failed to retrieve troubleshooting documentation for `{topic}` (version {version}).

**Error**: {str(e)}

Please check:
- Topic name spelling
- Version availability
- Network connectivity

Try using the discovery resource: `splunk-docs://discovery`
"""

            self.logger.info("✅ Troubleshooting handler registered successfully")

            # Register SPL command documentation handler
            self.logger.info("Registering SPL command documentation handler...")

            @self.mcp_server.resource(
                "splunk-docs://{version}/spl-reference/{command}", name="get_spl_command_docs"
            )
            async def get_spl_command_docs(version: str, command: str) -> str:
                """Get SPL command documentation for specific version and command"""
                try:
                    from ..resources.splunk_docs import create_spl_command_resource

                    ctx = get_context()

                    resource = create_spl_command_resource(version, command)
                    content = await resource.get_content(ctx)
                    return content
                except Exception as e:
                    self.logger.error(f"Error getting SPL command docs for {command}: {e}")
                    return f"""# Error: SPL Command Documentation

Failed to retrieve documentation for `{command}` (version {version}).

**Error**: {str(e)}

Please check:
- Command name spelling
- Version availability
- Network connectivity

Try using the discovery resource: `splunk-docs://discovery`
"""

            self.logger.info("✅ SPL command handler registered successfully")

            # Register admin guide documentation handler
            self.logger.info("Registering admin guide documentation handler...")

            @self.mcp_server.resource(
                "splunk-docs://{version}/admin/{topic}", name="get_admin_guide_docs"
            )
            async def get_admin_guide_docs(version: str, topic: str) -> str:
                """Get Splunk administration documentation for specific version and topic"""
                try:
                    from ..resources.splunk_docs import create_admin_guide_resource

                    ctx = get_context()

                    resource = create_admin_guide_resource(version, topic)
                    content = await resource.get_content(ctx)
                    return content
                except Exception as e:
                    self.logger.error(f"Error getting admin docs for {topic}: {e}")
                    return f"""# Error: Administration Documentation

Failed to retrieve administration documentation for `{topic}` (version {version}).

**Error**: {str(e)}

Please check:
- Topic name
- Version availability
- Network connectivity

Try using the discovery resource: `splunk-docs://discovery`
"""

            self.logger.info("✅ Admin guide handler registered successfully")

            self.logger.info(
                "Successfully registered 3 dynamic documentation handlers (troubleshooting, spl-commands, admin)"
            )

        except Exception as e:
            self.logger.error(f"Failed to register dynamic documentation handlers: {e}")
            # Re-raise to see the full traceback
            raise

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
                # Skip template resources that are already handled by dynamic handlers
                if any(
                    pattern in metadata.uri
                    for pattern in [
                        "splunk-docs://{version}/troubleshooting/{topic}",
                        "splunk-docs://{version}/spl-reference/{command}",
                        "splunk-docs://{version}/admin/{topic}",
                    ]
                ):
                    self.logger.debug(
                        f"Skipping template resource {metadata.uri} - already handled by dynamic handlers"
                    )
                    return 0

                # Handle other template resources (like config templates)
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
                    raise RuntimeError(f"Failed to read config: {str(e)}") from e

        else:
            # Fallback for other template types
            self._register_generic_resource(resource_class, pattern, resource_class.METADATA)

    def _register_with_fastmcp(self, resource_class, uri: str, metadata):
        """Register resource with FastMCP using appropriate pattern matching"""
        # Extract the pattern from URI for FastMCP registration
        if "splunk-docs://" in uri:
            self._register_documentation_resource(resource_class, uri, metadata)
        elif "config" in uri:
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
                raise RuntimeError(f"Failed to read config: {str(e)}") from e

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
                raise RuntimeError(f"Failed to read health: {str(e)}") from e

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
                raise RuntimeError(f"Failed to read apps: {str(e)}") from e

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
                raise RuntimeError(f"Failed to read search: {str(e)}") from e

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
                raise RuntimeError(f"Failed to read resource: {str(e)}") from e

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
                raise RuntimeError(f"Failed to read indexes: {str(e)}") from e

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
                raise RuntimeError(f"Failed to read saved searches: {str(e)}") from e

    def _register_documentation_resource(self, resource_class, uri: str, metadata):
        """Register documentation resource with FastMCP"""
        # Use metadata for proper naming and description
        resource_name = metadata.name
        resource_description = metadata.description

        # Create a closure to capture the URI - static resources have no function parameters
        @self.mcp_server.resource(uri, name=resource_name, description=resource_description)
        async def get_documentation_resource() -> str:
            """Get Splunk documentation resource"""
            try:
                from .registry import resource_registry

                ctx = get_context()
                resource = resource_registry.get_resource(uri)
                if not resource:
                    raise ValueError(f"Resource not found: {uri}")
                return await resource.get_content(ctx)
            except Exception as e:
                self.logger.error(f"Error reading documentation resource {uri}: {e}")
                raise RuntimeError(f"Failed to read documentation: {str(e)}") from e


class PromptLoader:
    """Loads and registers prompts with the FastMCP server."""

    def __init__(self, mcp_server: FastMCP):
        self.mcp_server = mcp_server
        self.logger = logging.getLogger(f"{__name__}.PromptLoader")
        self._registered_prompts = {}  # name -> prompt_class mapping

    def load_prompts(self) -> int:
        """Load all discovered prompts into the MCP server."""
        from .discovery import discover_prompts
        from .registry import prompt_registry

        loaded_count = 0

        # Check if prompts are already loaded to prevent duplicates
        if len(self._registered_prompts) > 0:
            self.logger.info(
                f"Prompts already loaded ({len(self._registered_prompts)} prompts), skipping reload"
            )
            return len(self._registered_prompts)

        # First, pre-register our Splunk prompts to ensure they're available
        self._load_manual_splunk_prompts()

        # Discover additional prompts if needed
        prompt_metadata_list = prompt_registry.list_prompts()
        if not prompt_metadata_list:
            discover_prompts()
            prompt_metadata_list = prompt_registry.list_prompts()

        # Load all prompts from registry
        for metadata in prompt_metadata_list:
            try:
                loaded_count += self._load_single_prompt(metadata)
            except Exception as e:
                self.logger.error(f"Failed to load prompt {metadata.name}: {e}")

        self.logger.info(f"Successfully loaded {loaded_count} prompts")
        return loaded_count

    def _load_manual_splunk_prompts(self) -> None:
        """Pre-register Splunk-specific prompts with the discovery registry"""
        try:
            # Import and register prompts
            from ..prompts import register_all_prompts

            register_all_prompts()
            self.logger.info("Registered Splunk prompts")

        except ImportError as e:
            self.logger.debug(f"Splunk prompts not available: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to register Splunk prompts: {e}")

    def _load_single_prompt(self, metadata) -> int:
        """Load a single prompt from registry into FastMCP"""
        try:
            from .registry import prompt_registry

            # Skip if already loaded
            if metadata.name in self._registered_prompts:
                return 0

            # Get prompt class from registry
            prompt_class = prompt_registry._prompts.get(metadata.name)
            if not prompt_class:
                self.logger.warning(f"No prompt class found for name: {metadata.name}")
                return 0

            # Register with FastMCP using the prompt decorator
            self._register_prompt_with_fastmcp(prompt_class, metadata)
            self._registered_prompts[metadata.name] = prompt_class.__name__
            self.logger.debug(f"Loaded prompt: {metadata.name}")

            return 1

        except Exception as e:
            self.logger.error(f"Failed to load prompt {metadata.name}: {e}")
            return 0

    def _register_prompt_with_fastmcp(self, prompt_class, metadata):
        """Register prompt with FastMCP using the @mcp.prompt decorator"""
        prompt_name = metadata.name
        prompt_description = metadata.description

        # Handle specific prompts with their unique signatures
        if prompt_name == "troubleshoot_inputs":
            # Create a wrapper function with the specific signature for this prompt
            async def prompt_wrapper(
                earliest_time: str = "-24h",
                latest_time: str = "now",
                focus_index: str | None = None,
                focus_host: str | None = None,
            ) -> list[dict[str, Any]]:
                """Guided workflow for troubleshooting Splunk data input issues using metrics.log analysis"""
                try:
                    # Create prompt instance
                    prompt_instance = prompt_class(metadata.name, metadata.description)

                    # Get the current context using FastMCP's dependency function
                    try:
                        ctx = get_context()
                    except Exception as e:
                        self.logger.error(
                            f"Could not get current context for prompt {prompt_name}: {e}"
                        )
                        raise RuntimeError(
                            f"Prompt {prompt_name} can only be called within an MCP request context"
                        ) from e

                    # Call the prompt's get_prompt method with parameters
                    result = await prompt_instance.get_prompt(
                        ctx,
                        earliest_time=earliest_time,
                        latest_time=latest_time,
                        focus_index=focus_index,
                        focus_host=focus_host,
                    )

                    # Convert to FastMCP prompt format
                    if isinstance(result, dict) and "content" in result:
                        return result["content"]
                    else:
                        # Fallback format
                        return [{"type": "text", "text": str(result)}]

                except Exception as e:
                    self.logger.error(f"Prompt {prompt_name} execution failed: {e}")
                    self.logger.exception("Full traceback:")
                    return [{"type": "text", "text": f"Error: {str(e)}"}]

        elif prompt_name == "troubleshoot_indexing_performance":
            # Create a wrapper function with the specific signature for this prompt
            async def prompt_wrapper(
                earliest_time: str = "-24h",
                latest_time: str = "now",
                focus_index: str | None = None,
                focus_host: str | None = None,
                analysis_depth: str = "standard",
                include_delay_analysis: bool = True,
                include_platform_instrumentation: bool = True,
            ) -> list[dict[str, Any]]:
                """Comprehensive workflow for identifying and triaging Splunk indexing performance issues"""
                try:
                    # Create prompt instance
                    prompt_instance = prompt_class(metadata.name, metadata.description)

                    # Get the current context using FastMCP's dependency function
                    try:
                        ctx = get_context()
                    except Exception as e:
                        self.logger.error(
                            f"Could not get current context for prompt {prompt_name}: {e}"
                        )
                        raise RuntimeError(
                            f"Prompt {prompt_name} can only be called within an MCP request context"
                        ) from e

                    # Call the prompt's get_prompt method with parameters
                    result = await prompt_instance.get_prompt(
                        ctx,
                        earliest_time=earliest_time,
                        latest_time=latest_time,
                        focus_index=focus_index,
                        focus_host=focus_host,
                        analysis_depth=analysis_depth,
                        include_delay_analysis=include_delay_analysis,
                        include_platform_instrumentation=include_platform_instrumentation,
                    )

                    # Convert to FastMCP prompt format
                    if isinstance(result, dict) and "content" in result:
                        return result["content"]
                    else:
                        # Fallback format
                        return [{"type": "text", "text": str(result)}]

                except Exception as e:
                    self.logger.error(f"Prompt {prompt_name} execution failed: {e}")
                    self.logger.exception("Full traceback:")
                    return [{"type": "text", "text": f"Error: {str(e)}"}]

        elif prompt_name == "troubleshoot_inputs_multi_agent":
            # Create a wrapper function with the specific signature for this prompt
            async def prompt_wrapper(
                earliest_time: str = "-24h",
                latest_time: str = "now",
                focus_index: str | None = None,
                focus_host: str | None = None,
                complexity_level: str = "moderate",
                include_performance_analysis: bool = True,
                enable_cross_validation: bool = True,
                analysis_mode: str = "diagnostic",
            ) -> list[dict[str, Any]]:
                """Advanced multi-agent troubleshooting workflow for Splunk data input issues"""
                try:
                    # Create prompt instance
                    prompt_instance = prompt_class(metadata.name, metadata.description)

                    # Get the current context using FastMCP's dependency function
                    try:
                        ctx = get_context()
                    except Exception as e:
                        self.logger.error(
                            f"Could not get current context for prompt {prompt_name}: {e}"
                        )
                        raise RuntimeError(
                            f"Prompt {prompt_name} can only be called within an MCP request context"
                        ) from e

                    # Call the prompt's get_prompt method with parameters
                    result = await prompt_instance.get_prompt(
                        ctx,
                        earliest_time=earliest_time,
                        latest_time=latest_time,
                        focus_index=focus_index,
                        focus_host=focus_host,
                        complexity_level=complexity_level,
                        include_performance_analysis=include_performance_analysis,
                        enable_cross_validation=enable_cross_validation,
                        analysis_mode=analysis_mode,
                    )

                    # Convert to FastMCP prompt format
                    if isinstance(result, dict) and "content" in result:
                        return result["content"]
                    else:
                        # Fallback format
                        return [{"type": "text", "text": str(result)}]

                except Exception as e:
                    self.logger.error(f"Prompt {prompt_name} execution failed: {e}")
                    self.logger.exception("Full traceback:")
                    return [{"type": "text", "text": f"Error: {str(e)}"}]

        elif prompt_name == "troubleshoot_performance":
            # Create a wrapper function with the specific signature for this prompt
            async def prompt_wrapper(
                earliest_time: str = "-7d",
                latest_time: str = "now",
                analysis_type: str = "comprehensive",
            ) -> list[dict[str, Any]]:
                """Specialized prompt for Splunk performance analysis and optimization"""
                try:
                    # Create prompt instance
                    prompt_instance = prompt_class(metadata.name, metadata.description)

                    # Get the current context using FastMCP's dependency function
                    try:
                        ctx = get_context()
                    except Exception as e:
                        self.logger.error(
                            f"Could not get current context for prompt {prompt_name}: {e}"
                        )
                        raise RuntimeError(
                            f"Prompt {prompt_name} can only be called within an MCP request context"
                        ) from e

                    # Call the prompt's get_prompt method with parameters
                    result = await prompt_instance.get_prompt(
                        ctx,
                        earliest_time=earliest_time,
                        latest_time=latest_time,
                        analysis_type=analysis_type,
                    )

                    # Convert to FastMCP prompt format
                    if isinstance(result, dict) and "content" in result:
                        return result["content"]
                    else:
                        # Fallback format
                        return [{"type": "text", "text": str(result)}]

                except Exception as e:
                    self.logger.error(f"Prompt {prompt_name} execution failed: {e}")
                    self.logger.exception("Full traceback:")
                    return [{"type": "text", "text": f"Error: {str(e)}"}]

        else:
            # Intelligent wrapper for prompts with parameters - dynamically generate signature from metadata
            async def prompt_wrapper(**kwargs) -> list[dict[str, Any]]:
                """Intelligent prompt wrapper that handles parameters dynamically"""
                try:
                    # Create prompt instance
                    prompt_instance = prompt_class(metadata.name, metadata.description)

                    # Get the current context using FastMCP's dependency function
                    try:
                        ctx = get_context()
                    except Exception as e:
                        self.logger.error(
                            f"Could not get current context for prompt {prompt_name}: {e}"
                        )
                        raise RuntimeError(
                            f"Prompt {prompt_name} can only be called within an MCP request context"
                        ) from e

                    # Call the prompt's get_prompt method with all provided parameters
                    result = await prompt_instance.get_prompt(ctx, **kwargs)

                    # Convert to FastMCP prompt format
                    if isinstance(result, dict) and "content" in result:
                        return result["content"]
                    else:
                        # Fallback format
                        return [{"type": "text", "text": str(result)}]

                except Exception as e:
                    self.logger.error(f"Prompt {prompt_name} execution failed: {e}")
                    self.logger.exception("Full traceback:")
                    return [{"type": "text", "text": f"Error: {str(e)}"}]

            # Dynamically set the function signature based on prompt metadata
            if hasattr(metadata, 'arguments') and metadata.arguments:
                # Import inspect for signature manipulation
                import inspect

                # Create parameter objects for the function signature
                params = []
                for arg in metadata.arguments:
                    # Determine parameter type annotation
                    if arg.get("type") == "string":
                        annotation = str
                    elif arg.get("type") == "boolean":
                        annotation = bool
                    elif arg.get("type") == "number":
                        annotation = (int, float)
                    else:
                        annotation = Any

                    # Create parameter with proper defaults
                    if arg.get("required", False):
                        # Required parameter
                        param = inspect.Parameter(
                            name=arg["name"],
                            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=annotation
                        )
                    else:
                        # Optional parameter with default
                        default_value = None
                        if arg.get("type") == "boolean":
                            default_value = False
                        elif arg.get("type") == "string":
                            default_value = ""
                        elif arg.get("type") == "number":
                            default_value = 0

                        param = inspect.Parameter(
                            name=arg["name"],
                            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            default=default_value,
                            annotation=annotation
                        )

                    params.append(param)

                # Create new signature
                new_sig = inspect.Signature(params, return_annotation=list[dict[str, Any]])
                prompt_wrapper.__signature__ = new_sig

                # Set type annotations
                prompt_wrapper.__annotations__ = {}
                for param in params:
                    if param.annotation != inspect.Parameter.empty:
                        prompt_wrapper.__annotations__[param.name] = param.annotation
                prompt_wrapper.__annotations__["return"] = list[dict[str, Any]]

                self.logger.debug(f"Generated parameterized signature for {prompt_name}: {new_sig}")
            else:
                # No parameters - use simple signature
                prompt_wrapper.__signature__ = inspect.signature(lambda: None)
                prompt_wrapper.__annotations__ = {"return": list[dict[str, Any]]}

        # Set function metadata
        prompt_wrapper.__name__ = prompt_name
        prompt_wrapper.__doc__ = prompt_description

        # Register with FastMCP
        self.mcp_server.prompt(name=prompt_name, description=prompt_description)(prompt_wrapper)

        self.logger.info(f"Registered prompt: {prompt_name}")


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

    def reload_all_components(self) -> dict[str, int]:
        """
        Hot reload all components for development.

        Returns:
            Dict containing counts of reloaded components by type
        """
        self.logger.info("Hot reloading all components...")

        # Reload all component types
        tools_reloaded = self.tool_loader.reload_tools()
        # Resources and prompts don't change descriptions as often, but we could add reload for them too
        resources_loaded = self.resource_loader.load_resources()
        prompts_loaded = self.prompt_loader.load_prompts()

        results = {
            "tools": tools_reloaded,
            "resources": resources_loaded,
            "prompts": prompts_loaded,
        }

        total_reloaded = sum(results.values())
        self.logger.info(f"Reloaded {total_reloaded} total components: {results}")

        return results
