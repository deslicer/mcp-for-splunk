"""
Context management utilities for Splunk MCP server.

Provides context management for Splunk connections and shared state.
"""

import logging
from dataclasses import dataclass
from typing import Any

from splunklib import client

logger = logging.getLogger(__name__)


@dataclass
class SplunkContext:
    """Context for Splunk operations"""

    service: client.Service | None
    is_connected: bool

    def __post_init__(self):
        """Post-initialization logging"""
        if self.is_connected and self.service:
            logger.info("Splunk context initialized with active connection")
        else:
            logger.warning("Splunk context initialized without connection")


def validate_splunk_connection(ctx: Any) -> tuple[bool, client.Service | None, str]:
    """
    Validate Splunk connection from MCP context.

    Args:
        ctx: MCP context containing lifespan context

    Returns:
        Tuple of (is_available, service, error_message)
    """
    try:
        splunk_ctx = ctx.request_context.lifespan_context

        if not splunk_ctx.is_connected or not splunk_ctx.service:
            return (
                False,
                None,
                "Splunk service is not available. MCP server is running in degraded mode.",
            )

        return True, splunk_ctx.service, ""

    except AttributeError as e:
        logger.error(f"Invalid context structure: {e}")
        return False, None, "Invalid context structure"
    except Exception as e:
        logger.error(f"Unexpected error validating Splunk connection: {e}")
        return False, None, f"Connection validation error: {str(e)}"
