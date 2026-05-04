"""Server factory for the ITSI MCP server.

This module owns:

* :func:`build_server` — construct a :class:`fastmcp.FastMCP` instance and
  register every ITSI tool / resource / prompt on it.
* :func:`run_standalone` — run the server as a process (used by ``__main__``
  and the ``mcp-itsi-server`` console script).

The plugin entrypoint for the parent ``mcp-for-splunk`` server lives in
:mod:`mcp_itsi.plugin` so that import is cheap when this server is mounted
into another process.
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from mcp_itsi._version import __version__
from mcp_itsi.config.settings import ITSIServerSettings, load_settings
from mcp_itsi.core.registration import (
    register_prompts,
    register_resources,
    register_tools,
)
from mcp_itsi.prompts import all_prompts
from mcp_itsi.resources import all_resources
from mcp_itsi.tools import all_tools

logger = logging.getLogger(__name__)


def build_server(
    *,
    name: str = "ITSI MCP Server",
    settings: ITSIServerSettings | None = None,
) -> tuple[FastMCP, ITSIServerSettings]:
    """Construct and configure the FastMCP server.

    Returns the constructed server and the resolved settings so callers can
    decide which transport to use without re-loading settings.
    """
    settings = settings or load_settings()
    _configure_logging(settings.log_level)

    mcp = FastMCP(name=name, version=__version__)

    register_tools(mcp, all_tools())
    register_resources(mcp, all_resources())
    register_prompts(mcp, all_prompts())

    logger.info(
        "ITSI MCP server ready (version=%s, transport=%s)",
        __version__,
        settings.transport,
    )
    return mcp, settings


def run_standalone(settings: ITSIServerSettings | None = None) -> None:
    """Run the server in standalone mode using the configured transport."""
    mcp, settings = build_server(settings=settings)

    transport = (settings.transport or "http").lower()
    if transport in {"http", "streamable-http"}:
        mcp.run(
            transport="http",
            host=settings.server_host,
            port=settings.server_port,
            stateless_http=settings.stateless_http,
            json_response=settings.json_response,
        )
    elif transport == "stdio":
        mcp.run(transport="stdio")
    else:
        raise ValueError(f"Unsupported MCP_ITSI_TRANSPORT={transport!r}")


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    logging.getLogger("mcp_itsi").setLevel(level)
