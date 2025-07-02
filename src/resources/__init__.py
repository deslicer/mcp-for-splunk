"""
Resources package for MCP server.

Provides read-only resources including Splunk documentation and core configuration resources.
"""

import logging

logger = logging.getLogger(__name__)

__all__ = ["register_all_resources"]


def register_all_resources():
    """Register all available resources with the registry."""
    try:
        # Register documentation resources
        from .splunk_docs import register_all_resources as register_documentation_resources
        register_documentation_resources()
        logger.debug("Registered documentation resources")
    except ImportError as e:
        logger.warning(f"Could not import documentation resources: {e}")

    try:
        # Register core Splunk configuration resources
        from ..core.registry import resource_registry
        from ..core.base import ResourceMetadata
        from .splunk_config import (
            SplunkAppsResource,
            SplunkConfigResource,
            SplunkHealthResource,
            SplunkIndexesResource,
            SplunkSavedSearchesResource,
            SplunkSearchResultsResource,
        )

        # Manually register these resources with the discovery registry
        splunk_resources = [
            (SplunkConfigResource, "splunk://config/{config_file}"),  # Template
            (SplunkHealthResource, "splunk://health/status"),
            (SplunkAppsResource, "splunk://apps/installed"),
            (SplunkIndexesResource, "splunk://indexes/list"),
            (SplunkSavedSearchesResource, "splunk://savedsearches/list"),
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
                    logger.debug(f"Registered {resource_class.__name__} ({uri}) with discovery registry")
                except Exception as e:
                    logger.warning(f"Could not register {resource_class.__name__} with discovery: {e}")

        logger.info(f"Pre-registered {len(splunk_resources)} core Splunk resources with discovery system")
        
    except ImportError as e:
        logger.warning(f"Could not import core Splunk configuration resources: {e}")
    except Exception as e:
        logger.error(f"Error registering core Splunk resources: {e}")
