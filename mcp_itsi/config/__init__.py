"""Configuration helpers for the ITSI MCP server.

Each module in this package has a single responsibility:

* :mod:`mcp_itsi.config.settings` -- Process-wide server configuration loaded
  from environment variables (server host/port, default Splunk target, etc).
* :mod:`mcp_itsi.config.headers` -- Per-request configuration extracted from
  HTTP headers sent by the MCP client.
"""

from mcp_itsi.config.headers import (
    HEADER_PREFIX_ITSI,
    HEADER_PREFIX_SPLUNK,
    ITSIRequestConfig,
    extract_request_config,
)
from mcp_itsi.config.settings import ITSIServerSettings, load_settings

__all__ = [
    "HEADER_PREFIX_ITSI",
    "HEADER_PREFIX_SPLUNK",
    "ITSIRequestConfig",
    "ITSIServerSettings",
    "extract_request_config",
    "load_settings",
]
