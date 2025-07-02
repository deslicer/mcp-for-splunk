"""
Discovery system for automatically finding and loading tools, resources, and prompts.

Provides automatic discovery of MCP components from the file system.
"""

import importlib
import logging
import pkgutil

from .base import BasePrompt, BaseResource, BaseTool
from .registry import prompt_registry, resource_registry, tool_registry

logger = logging.getLogger(__name__)


def discover_tools(search_paths: list[str] | None = None) -> int:
    """
    Discover and register tools from specified paths.

    Args:
        search_paths: Paths to search for tools (defaults to core and contrib tools)

    Returns:
        Number of tools discovered and registered
    """
    if search_paths is None:
        search_paths = [
            "src.tools",  # Core tools
            "contrib.tools",  # Community tools
        ]

    discovered_count = 0

    for search_path in search_paths:
        try:
            discovered_count += _discover_modules_in_package(
                search_path, BaseTool, _register_tool_class
            )
        except ImportError as e:
            logger.debug(f"Could not import {search_path}: {e}")
        except Exception as e:
            logger.error(f"Error discovering tools in {search_path}: {e}")

    logger.info(f"Discovered and registered {discovered_count} tools")
    return discovered_count


def discover_resources(search_paths: list[str] | None = None) -> int:
    """
    Discover and register resources from specified paths.

    Args:
        search_paths: Paths to search for resources (defaults to core and contrib resources)

    Returns:
        Number of resources discovered and registered
    """
    if search_paths is None:
        search_paths = [
            "src.core.resources",  # Core resources (actual location)
            "src.resources",  # New resources directory (Splunk docs, etc.)
            "contrib.resources",  # Community resources
        ]

    discovered_count = 0

    for search_path in search_paths:
        try:
            discovered_count += _discover_modules_in_package(
                search_path, BaseResource, _register_resource_class
            )
        except ImportError as e:
            logger.debug(f"Could not import {search_path}: {e}")
        except Exception as e:
            logger.error(f"Error discovering resources in {search_path}: {e}")

    logger.info(f"Discovered and registered {discovered_count} resources")
    return discovered_count


def discover_prompts(search_paths: list[str] | None = None) -> int:
    """
    Discover and register prompts from specified paths.

    Args:
        search_paths: Paths to search for prompts (defaults to core and contrib prompts)

    Returns:
        Number of prompts discovered and registered
    """
    if search_paths is None:
        search_paths = [
            "src.prompts",  # Core prompts
            "contrib.prompts",  # Community prompts
        ]

    discovered_count = 0

    for search_path in search_paths:
        try:
            discovered_count += _discover_modules_in_package(
                search_path, BasePrompt, _register_prompt_class
            )
        except ImportError as e:
            logger.debug(f"Could not import {search_path}: {e}")
        except Exception as e:
            logger.error(f"Error discovering prompts in {search_path}: {e}")

    logger.info(f"Discovered and registered {discovered_count} prompts")
    return discovered_count


def _discover_modules_in_package(package_name: str, base_class: type, register_func) -> int:
    """
    Discover modules in a package and register classes that inherit from base_class.

    Args:
        package_name: Package to search
        base_class: Base class to look for
        register_func: Function to call for registration

    Returns:
        Number of classes discovered and registered
    """
    try:
        package = importlib.import_module(package_name)
    except ImportError:
        logger.debug(f"Package {package_name} not found or not importable")
        return 0

    discovered_count = 0

    # Walk through all modules in the package
    if hasattr(package, "__path__"):
        for _importer, modname, _ispkg in pkgutil.walk_packages(
            package.__path__, package.__name__ + "."
        ):
            try:
                module = importlib.import_module(modname)
                discovered_count += _process_module(module, base_class, register_func)
            except Exception as e:
                logger.error(f"Error importing module {modname}: {e}")
    else:
        # Single module package
        discovered_count += _process_module(package, base_class, register_func)

    return discovered_count


def _process_module(module, base_class: type, register_func) -> int:
    """
    Process a module to find and register classes.

    Args:
        module: Module to process
        base_class: Base class to look for
        register_func: Function to call for registration

    Returns:
        Number of classes processed
    """
    discovered_count = 0

    for name in dir(module):
        obj = getattr(module, name)

        # Check if it's a class that inherits from base_class but isn't base_class itself
        if (
            isinstance(obj, type)
            and issubclass(obj, base_class)
            and obj is not base_class
            and not name.startswith("_")
        ):
            try:
                register_func(obj, module)
                discovered_count += 1
                logger.debug(f"Discovered {base_class.__name__}: {name}")
            except Exception as e:
                logger.error(f"Error registering {name}: {e}")

    return discovered_count


def _register_tool_class(tool_class: type[BaseTool], module) -> None:
    """Register a discovered tool class"""
    # Look for metadata in the module or class
    metadata = _get_tool_metadata(tool_class, module)
    if metadata:
        tool_registry.register(tool_class, metadata)


def _register_resource_class(resource_class: type[BaseResource], module) -> None:
    """Register a discovered resource class"""
    # Look for metadata in the module or class
    metadata = _get_resource_metadata(resource_class, module)
    if metadata:
        resource_registry.register(resource_class, metadata)


def _register_prompt_class(prompt_class: type[BasePrompt], module) -> None:
    """Register a discovered prompt class"""
    # Look for metadata in the module or class
    metadata = _get_prompt_metadata(prompt_class, module)
    if metadata:
        prompt_registry.register(prompt_class, metadata)


def _get_tool_metadata(tool_class: type[BaseTool], module):
    """Extract tool metadata from class or module"""
    from .base import ToolMetadata

    # Look for METADATA attribute in class
    if hasattr(tool_class, "METADATA"):
        return tool_class.METADATA

    # Look for metadata in module
    if hasattr(module, "TOOL_METADATA"):
        return module.TOOL_METADATA

    # Create default metadata
    class_name = tool_class.__name__
    return ToolMetadata(
        name=_camel_to_snake(class_name),
        description=tool_class.__doc__ or f"Tool: {class_name}",
        category="general",
    )


def _get_resource_metadata(resource_class: type[BaseResource], module):
    """Extract resource metadata from class or module"""
    from .base import ResourceMetadata

    # Look for METADATA attribute in class
    if hasattr(resource_class, "METADATA"):
        return resource_class.METADATA

    # Look for metadata in module
    if hasattr(module, "RESOURCE_METADATA"):
        return module.RESOURCE_METADATA

    # Create default metadata
    class_name = resource_class.__name__
    uri = f"resource://{_camel_to_snake(class_name)}"
    return ResourceMetadata(
        uri=uri,
        name=class_name,
        description=resource_class.__doc__ or f"Resource: {class_name}",
        category="general",
    )


def _get_prompt_metadata(prompt_class: type[BasePrompt], module):
    """Extract prompt metadata from class or module"""
    from .base import PromptMetadata

    # Look for METADATA attribute in class
    if hasattr(prompt_class, "METADATA"):
        return prompt_class.METADATA

    # Look for metadata in module
    if hasattr(module, "PROMPT_METADATA"):
        return module.PROMPT_METADATA

    # Create default metadata
    class_name = prompt_class.__name__
    return PromptMetadata(
        name=_camel_to_snake(class_name),
        description=prompt_class.__doc__ or f"Prompt: {class_name}",
        category="general",
    )


def _camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case"""
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
