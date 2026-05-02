"""Process-wide settings for the ITSI MCP server.

These settings are read from environment variables and frozen at startup.
Per-request configuration (the values that may differ between MCP clients on
a single shared server) belongs in :mod:`mcp_itsi.config.headers`.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning("Invalid integer value %r; using default %d", value, default)
        return default


@dataclass(frozen=True)
class ITSIServerSettings:
    """Top-level server settings.

    All fields have safe defaults so the server can start in a degraded mode
    even when the environment is not yet fully configured.
    """

    server_host: str = "0.0.0.0"
    server_port: int = 8004
    transport: str = "http"

    stateless_http: bool = True
    json_response: bool = True

    log_level: str = "INFO"

    default_splunk_host: str | None = None
    default_splunk_port: int = 8089
    default_splunk_scheme: str = "https"
    default_splunk_username: str | None = None
    default_splunk_password: str | None = None
    default_splunk_token: str | None = None
    default_splunk_verify_ssl: bool = False

    default_itsi_app: str = "SA-ITOA"
    default_itsi_user_ns: str = "nobody"
    default_itsi_version: str = "vLatest"

    request_timeout_seconds: float = 30.0


def load_settings() -> ITSIServerSettings:
    """Load settings from environment variables.

    Environment variables follow the same naming convention as the parent
    ``mcp-for-splunk`` project to keep operator experience consistent. ITSI
    specific overrides start with ``MCP_ITSI_``.
    """

    return ITSIServerSettings(
        server_host=os.getenv("MCP_ITSI_SERVER_HOST", os.getenv("MCP_SERVER_HOST", "0.0.0.0")),
        server_port=_int(
            os.getenv("MCP_ITSI_SERVER_PORT") or os.getenv("MCP_ITSI_PORT"),
            8004,
        ),
        transport=os.getenv("MCP_ITSI_TRANSPORT", os.getenv("MCP_TRANSPORT", "http")),
        stateless_http=_bool(os.getenv("MCP_STATELESS_HTTP"), True),
        json_response=_bool(os.getenv("MCP_JSON_RESPONSE"), True),
        log_level=os.getenv("MCP_ITSI_LOG_LEVEL", os.getenv("MCP_LOG_LEVEL", "INFO")).upper(),
        default_splunk_host=os.getenv("SPLUNK_HOST") or None,
        default_splunk_port=_int(os.getenv("SPLUNK_PORT"), 8089),
        default_splunk_scheme=os.getenv("SPLUNK_SCHEME", "https"),
        default_splunk_username=os.getenv("SPLUNK_USERNAME") or None,
        default_splunk_password=os.getenv("SPLUNK_PASSWORD") or None,
        default_splunk_token=os.getenv("SPLUNK_TOKEN") or None,
        default_splunk_verify_ssl=_bool(os.getenv("SPLUNK_VERIFY_SSL"), False),
        default_itsi_app=os.getenv("ITSI_APP", "SA-ITOA"),
        default_itsi_user_ns=os.getenv("ITSI_USER_NS", "nobody"),
        default_itsi_version=os.getenv("ITSI_API_VERSION", "vLatest"),
        request_timeout_seconds=float(os.getenv("ITSI_REQUEST_TIMEOUT", "30")),
    )
