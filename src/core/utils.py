"""
Common utilities for the MCP Splunk server core framework.

Provides shared utility functions used across tools, resources, and prompts.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_splunk_connection(ctx: Any) -> tuple[bool, Any, str]:
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
            return False, None, "Splunk service is not available. MCP server is running in degraded mode."

        return True, splunk_ctx.service, ""

    except AttributeError as e:
        logger.error(f"Invalid context structure: {e}")
        return False, None, "Invalid context structure"
    except Exception as e:
        logger.error(f"Unexpected error validating Splunk connection: {e}")
        return False, None, f"Connection validation error: {str(e)}"


def format_error_response(error: str, **kwargs) -> dict[str, Any]:
    """
    Format a consistent error response.

    Args:
        error: Error message
        **kwargs: Additional error context

    Returns:
        Formatted error response dictionary
    """
    return {
        "status": "error",
        "error": error,
        **kwargs
    }


def format_success_response(data: dict[str, Any]) -> dict[str, Any]:
    """
    Format a consistent success response.

    Args:
        data: Response data

    Returns:
        Formatted success response dictionary
    """
    return {
        "status": "success",
        **data
    }


def sanitize_search_query(query: str) -> str:
    """
    Sanitize and prepare a Splunk search query.

    Args:
        query: Raw search query

    Returns:
        Sanitized search query with 'search' command added if needed
    """
    query = query.strip()

    # Add 'search' command if not present and query doesn't start with a pipe
    if not query.lower().startswith(('search ', '| ')):
        query = f"search {query}"

    return query


def validate_time_range(earliest_time: str, latest_time: str) -> tuple[bool, str]:
    """
    Validate time range parameters.

    Args:
        earliest_time: Start time for search
        latest_time: End time for search

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Basic validation - could be expanded with more sophisticated checks
    if not earliest_time or not latest_time:
        return False, "Both earliest_time and latest_time must be provided"

    # Check for obviously invalid formats
    invalid_chars = ['<', '>', ';', '&', '|', '`']
    for char in invalid_chars:
        if char in earliest_time or char in latest_time:
            return False, f"Invalid character '{char}' in time range"

    return True, ""


def log_tool_execution(tool_name: str, **kwargs):
    """
    Log tool execution for monitoring and debugging.

    Args:
        tool_name: Name of the tool being executed
        **kwargs: Additional context to log
    """
    logger.info(f"Executing tool: {tool_name}")
    if kwargs:
        logger.debug(f"Tool parameters: {kwargs}")


def truncate_large_response(data: Any, max_items: int = 1000) -> tuple[Any, bool]:
    """
    Truncate large responses to prevent overwhelming the client.

    Args:
        data: Response data to potentially truncate
        max_items: Maximum number of items to include

    Returns:
        Tuple of (truncated_data, was_truncated)
    """
    if isinstance(data, list) and len(data) > max_items:
        return data[:max_items], True

    if isinstance(data, dict) and 'results' in data and isinstance(data['results'], list):
        if len(data['results']) > max_items:
            truncated_data = data.copy()
            truncated_data['results'] = data['results'][:max_items]
            truncated_data['truncated'] = True
            truncated_data['original_count'] = len(data['results'])
            return truncated_data, True

    return data, False
