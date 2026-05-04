"""Plugin entrypoint for the parent ``mcp-for-splunk`` server.

The parent server discovers plugins via Python ``entry_points`` in the
``mcp_splunk.plugins`` group. To enable ITSI capabilities inside the
shared MCP server, install this package and register the entry point in
``pyproject.toml``::

    [project.entry-points."mcp_splunk.plugins"]
    itsi = "mcp_itsi.plugin:setup"

The parent server calls ``setup(mcp, root_app=...)`` with the existing
:class:`fastmcp.FastMCP` instance; we register every ITSI tool, resource
and prompt on it. The ITSI capabilities then become available alongside
the parent project's tools, sharing the same HTTP transport, session
handling and X-Splunk-* headers.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp_itsi.core.registration import register_prompts, register_resources, register_tools
from mcp_itsi.prompts import all_prompts
from mcp_itsi.resources import all_resources
from mcp_itsi.tools import all_tools

logger = logging.getLogger(__name__)


def setup(mcp: Any, root_app: Any | None = None) -> None:
    """Register ITSI capabilities on a parent FastMCP server."""
    logger.info("Loading ITSI plugin into parent MCP server")
    register_tools(mcp, all_tools())
    register_resources(mcp, all_resources())
    register_prompts(mcp, all_prompts())
    logger.info("ITSI plugin loaded")
