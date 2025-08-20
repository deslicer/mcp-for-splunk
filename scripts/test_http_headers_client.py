#!/usr/bin/env python3
"""
HTTP headers integration test using FastMCP Client (script form).

This script assumes your MCP server is running at http://localhost:8001/mcp/
via docker-compose-dev.yml (Traefik). It:
- Sends X-Splunk-* headers to /mcp/health (HTTP transport) to trigger header capture
- Connects via FastMCP Client over HTTP and calls list_indexes
- Prints whether discovery worked and reminds you to check logs

Configure headers via environment variables (recommended):
  SPLUNK_HOST, SPLUNK_PORT, SPLUNK_USERNAME, SPLUNK_PASSWORD,
  SPLUNK_SCHEME (http|https), SPLUNK_VERIFY_SSL (true|false)
"""

import asyncio
import logging
import os
import sys

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


async def main() -> int:

    # Bump logging to DEBUG so we can see attachment/use messages
    logging.getLogger().setLevel(logging.DEBUG)

    # Prepare headers from environment (do not hardcode secrets)
    splunk_1_headers = {
        "X-Splunk-Host": "orange-ab.splunkcloud.com",
        "X-Splunk-Port": "8089",
        "X-Splunk-Username": "daniel.young@orangecyberdefense.com",
        "X-Splunk-Password": "7kG5iT&Py6T6^CdM",
        "X-Splunk-Scheme": "https",
        "X-Splunk-Verify-SSL": "true",
        "X-Session-ID": os.environ.get("MCP_SESSION_ID", "splunk-mcp-test-session-1"),
    }
    splunk_2_headers = {
        "X-Splunk-Host": "so1",
        "X-Splunk-Port": "8089",
        "X-Splunk-Username": "admin",
        "X-Splunk-Password": "changeme",
        "X-Splunk-Scheme": "http",
        "X-Splunk-Verify-SSL": "false",
        "X-Session-ID": "splunk-mcp-test-session-2"
      }


    transport = StreamableHttpTransport("http://localhost:8001/mcp/", headers=splunk_1_headers)
    async with Client(transport) as client:
        try:
            tools = await client.list_tools()
            tool_names = [t.name for t in tools]
            print(f"🧰 Discovered {len(tool_names)} tools")

            if "list_indexes" not in tool_names:
                print("⚠️  'list_indexes' not found; continuing anyway")
            else:
                _ = await client.call_tool("list_indexes")
                print("✅ Invoked list_indexes successfully")

        except RuntimeError as e:
            print(f"❌ HTTP tool invocation failed: {e}")

        print(
            "\nNow check server logs for these lines (DEBUG/INFO):\n"
            " - Attached client_config to request.state for downstream access\n"
            " - Using client config from HTTP headers\n"
        )


    transport = StreamableHttpTransport("http://localhost:8001/mcp/", headers=splunk_2_headers)
    async with Client(transport) as client:
        try:
            tools = await client.list_tools()
            tool_names = [t.name for t in tools]
            print(f"🧰 Discovered {len(tool_names)} tools")

            if "list_indexes" not in tool_names:
                print("⚠️  'list_indexes' not found; continuing anyway")
            else:
                _ = await client.call_tool("list_indexes")
                print("✅ Invoked list_indexes successfully")

        except RuntimeError as e:
            print(f"❌ HTTP tool invocation failed: {e}")

        print(
            "\nNow check server logs for these lines (DEBUG/INFO):\n"
            " - Attached client_config to request.state for downstream access\n"
            " - Using client config from HTTP headers\n"
        )
        return True


if __name__ == "__main__":
    try:
        rc = asyncio.run(main())
    except KeyboardInterrupt:
        rc = 130
    sys.exit(rc)


