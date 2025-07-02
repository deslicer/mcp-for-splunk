"""
Resources package for MCP server.

Provides read-only resources including Splunk documentation and other data sources.
"""

try:
    from .splunk_docs import register_documentation_resources

    __all__ = ["register_documentation_resources"]

    def register_all_resources():
        """Register all available resources with the registry."""
        register_documentation_resources()

except ImportError as e:
    # Handle missing dependencies gracefully
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import documentation resources: {e}")

    __all__ = []

    def register_all_resources():
        """Register all available resources with the registry."""
        pass
