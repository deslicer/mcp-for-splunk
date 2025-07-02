"""
Splunk MCP prompts package.

Provides structured prompts for common Splunk operations and troubleshooting workflows.
"""

import logging

from ..core.discovery import discover_prompts
from ..core.registry import prompt_registry

logger = logging.getLogger(__name__)


def register_all_prompts():
    """Register all prompts with the prompt registry."""
    try:
        # Import all prompt modules to ensure they register themselves
        from . import troubleshooting  # noqa: F401

        # Discover additional prompts
        discover_prompts()

        prompt_count = len(prompt_registry.list_prompts())
        logger.info(f"Successfully registered {prompt_count} prompts")

    except Exception as e:
        logger.error(f"Failed to register prompts: {e}")


# Auto-register prompts when module is imported
register_all_prompts()
