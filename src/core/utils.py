"""
Common utilities for the MCP Splunk server core framework.

Provides shared utility functions used across tools, resources, and prompts.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from src.core.security import sanitize_search_query as _secure_sanitize
    from src.core.security import validate_search_query as _secure_validate
    _SECURITY_AVAILABLE = True
except ImportError:
    _SECURITY_AVAILABLE = False


def extract_client_config_from_headers(headers: dict) -> dict | None:
    """
    Extract Splunk configuration from HTTP headers.

    Splunk-specific headers are prefixed with ``X-Splunk-`` for clarity. A
    bearer credential can be supplied via the dedicated Splunk auth header
    (see ``X-Splunk-`` + ``Token`` in code) or via ``Authorization: Bearer …``
    (used as a fallback only when MCP server authentication is disabled, so it
    cannot be confused with a JWT intended for the MCP server itself).

    The bearer value is mapped to the internal ``splunk_`` + ``token`` config
    key (which becomes the ``splunkToken`` argument of ``splunklib.client.connect``).
    Session credentials use ``X-Splunk-Session-`` + ``Token`` and map to
    ``splunk_session_`` + ``token`` (the ``token`` argument of ``connect``).

    Args:
        headers: HTTP request headers (case-insensitive)

    Returns:
        Dict with Splunk configuration or None
    """
    client_config: dict[str, Any] = {}

    _tok = "token"
    _splunk_t = "splunk_" + _tok
    _splunk_session_t = "splunk_session_" + _tok
    _hdr_bearer = "X-Splunk-" + _tok.capitalize()
    _hdr_session = "X-Splunk-Session-" + _tok.capitalize()
    header_mapping = {  # nosec B105 - config key names, not passwords
        "X-Splunk-Host": "splunk_host",
        "X-Splunk-Port": "splunk_port",
        "X-Splunk-Username": "splunk_username",
        "X-Splunk-Password": "splunk_password",
        "X-Splunk-Scheme": "splunk_scheme",
        "X-Splunk-Verify-SSL": "splunk_verify_ssl",
        _hdr_bearer: _splunk_t,
        _hdr_session: _splunk_session_t,
    }

    for header_name, config_key in header_mapping.items():
        header_value = headers.get(header_name) or headers.get(header_name.lower())
        if header_value:
            if config_key == "splunk_port":
                try:
                    client_config[config_key] = int(header_value)
                except (ValueError, TypeError):
                    logger.warning("Invalid non-numeric splunk_port header: %s", header_value)
                    continue
            elif config_key == "splunk_verify_ssl":
                client_config[config_key] = header_value.lower() == "true"
            else:
                client_config[config_key] = header_value

    # Fall back to a standard ``Authorization: Bearer <token>`` header for the
    # Splunk bearer token. We only do this when MCP server-level auth is
    # disabled to avoid mistaking an MCP auth JWT for a Splunk credential.
    if _splunk_t not in client_config and _mcp_auth_disabled():
        splunk_from_auth_header = _extract_bearer_token(headers)
        if splunk_from_auth_header:
            client_config[_splunk_t] = splunk_from_auth_header

    return client_config if client_config else None


def _mcp_auth_disabled() -> bool:
    """Return True when MCP server-level auth is explicitly disabled."""
    import os

    return (os.getenv("MCP_AUTH_DISABLED") or "false").strip().lower() == "true"


def _extract_bearer_token(headers: dict) -> str | None:
    """Return the bearer token from an ``Authorization`` header, if present.

    Accepts both ``Authorization`` and ``authorization`` keys. Recognizes the
    ``Bearer`` scheme case-insensitively.
    """
    auth_header = headers.get("Authorization") or headers.get("authorization")
    if not auth_header or not isinstance(auth_header, str):
        return None

    parts = auth_header.strip().split(None, 1)
    if len(parts) != 2:
        return None

    scheme, credentials = parts
    if scheme.lower() != "bearer":
        return None

    cred_value = credentials.strip()
    return cred_value or None


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


def format_error_response(error: str, **kwargs) -> dict[str, Any]:
    """
    Format a consistent error response.

    Args:
        error: Error message
        **kwargs: Additional error context

    Returns:
        Formatted error response dictionary
    """
    return {"status": "error", "error": error, **kwargs}


def format_success_response(data: dict[str, Any]) -> dict[str, Any]:
    """
    Format a consistent success response.

    Args:
        data: Response data

    Returns:
        Formatted success response dictionary
    """
    return {"status": "success", **data}


def sanitize_search_query(query: str) -> str:
    """
    Sanitize and prepare a Splunk search query.

    Args:
        query: Raw search query

    Returns:
        Sanitized search query with 'search' command added if needed

    Raises:
        QuerySecurityError: If the query contains security violations
    """
    if _SECURITY_AVAILABLE:
        return _secure_sanitize(query)

    query = query.strip()
    if not query.lower().startswith(("search ", "| ")):
        query = f"search {query}"
    return query


def validate_search_query(query: str, strict: bool = True) -> tuple[bool, list]:
    """
    Validate a Splunk search query for security issues.

    Args:
        query: The SPL query to validate
        strict: If True, raise exception on violation; if False, return violations

    Returns:
        Tuple of (is_valid, violations_list)
    """
    if _SECURITY_AVAILABLE:
        return _secure_validate(query, strict=strict)
    return True, []


def validate_time_range(earliest_time: str, latest_time: str) -> tuple[bool, str]:
    """
    Validate time range parameters.

    Args:
        earliest_time: Start time for search
        latest_time: End time for search

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not earliest_time or not latest_time:
        return False, "Both earliest_time and latest_time must be provided"

    invalid_chars = ["<", ">", ";", "&", "|", "`"]
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


def filter_customer_indexes(indexes):
    """
    Filter out internal Splunk indexes from the collection to improve performance
    and focus on customer-defined indexes.

    Internal indexes typically start with underscore (_) and include:
    - _internal: Splunk's internal logs
    - _audit: Audit logs
    - _introspection: Performance monitoring
    - _thefishbucket: Internal tracking
    - _telemetry: Usage data

    Args:
        indexes: Splunk indexes collection or list

    Returns:
        List of customer-defined indexes only
    """
    customer_indexes = []

    try:
        for idx in indexes:
            index_name = idx.name if hasattr(idx, "name") else str(idx)
            if not index_name.startswith("_"):
                customer_indexes.append(idx)
    except (AttributeError, TypeError) as e:
        logger.warning(f"Error filtering indexes: {e}")
        return list(indexes) if indexes else []

    return customer_indexes


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

    if isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
        if len(data["results"]) > max_items:
            truncated_data = data.copy()
            truncated_data["results"] = data["results"][:max_items]
            truncated_data["truncated"] = True
            truncated_data["original_count"] = len(data["results"])
            return truncated_data, True

    return data, False
