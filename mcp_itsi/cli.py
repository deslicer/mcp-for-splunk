"""Console-script entry point for ``mcp-itsi-server``."""

from __future__ import annotations

import argparse
import logging

from mcp_itsi._version import __version__
from mcp_itsi.config.settings import load_settings
from mcp_itsi.server import run_standalone

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="mcp-itsi-server",
        description="Run the ITSI MCP server as a standalone process.",
    )
    parser.add_argument(
        "--transport",
        choices=("http", "stdio", "streamable-http"),
        default=None,
        help="Override MCP_ITSI_TRANSPORT for this invocation.",
    )
    parser.add_argument("--host", default=None, help="Override MCP_ITSI_SERVER_HOST.")
    parser.add_argument("--port", type=int, default=None, help="Override MCP_ITSI_SERVER_PORT.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    settings = load_settings()
    overrides: dict = {}
    if args.transport is not None:
        overrides["transport"] = args.transport
    if args.host is not None:
        overrides["server_host"] = args.host
    if args.port is not None:
        overrides["server_port"] = args.port
    if overrides:
        from dataclasses import replace

        settings = replace(settings, **overrides)

    run_standalone(settings)


if __name__ == "__main__":
    main()
