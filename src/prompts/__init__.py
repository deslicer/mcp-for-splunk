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
        # Import available prompt modules (optional)
        try:
            from . import mcp_usage  # noqa: F401
        except Exception as e:
            logger.debug(f"Optional prompt module not available: {e}")

        # Discover additional prompts
        discover_prompts()

        prompt_count = len(prompt_registry.list_prompts())
        logger.info(f"Successfully registered {prompt_count} prompts")

    except Exception as e:
        logger.error(f"Failed to register prompts: {e}", exc_info=True)


# Auto-register prompts when module is imported
register_all_prompts()
