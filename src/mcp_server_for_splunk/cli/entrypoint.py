"""Launch installed servers directly; preserve the checkout development helper."""

import argparse
import asyncio
from importlib import import_module

from .paths import source_checkout


def main(argv: list[str] | None = None) -> int:
    if source_checkout() is not None:
        return int(import_module(".build_and_run", __package__).main(argv))

    parser = argparse.ArgumentParser(description="Run the installed MCP Server for Splunk")
    parser.add_argument("--local", action="store_true", help="Run locally (the default)")
    parser.add_argument("--transport", choices=("http", "stdio"), default="http")
    parser.add_argument("--host", help="HTTP bind host (otherwise MCP_SERVER_HOST or 0.0.0.0)")
    parser.add_argument("--port", type=int, help="HTTP port (otherwise MCP_SERVER_PORT or 8001)")
    args = parser.parse_args(argv)
    # Import after argument parsing so --help does not initialize a server.
    server = import_module("mcp_server_for_splunk.server")
    if args.transport == "stdio":
        server.mcp.run(transport="stdio")
    else:
        asyncio.run(server.main(host=args.host, port=args.port))
    return 0
