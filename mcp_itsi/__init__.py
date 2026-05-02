"""MCP server for Splunk IT Service Intelligence (ITSI).

This package exposes ITSI REST API capabilities to MCP-compatible AI clients.
It can be run in three modes:

* As a **standalone FastMCP HTTP server** (``python -m mcp_itsi``).
* As a **stdio FastMCP server** for direct integration in IDEs / agents.
* As a **plugin** mounted onto the existing ``mcp-for-splunk`` server via the
  ``mcp_itsi.plugin:setup`` entrypoint declared in ``pyproject.toml``.

All tools accept the same X-Splunk-* HTTP headers used by ``mcp-for-splunk``
(plus optional ``X-ITSI-*`` overrides). See ``mcp_itsi.config`` for the
authoritative list.
"""

from mcp_itsi._version import __version__

__all__ = ["__version__"]
