#!/usr/bin/env python3
"""
Quick setup test script for MCP Server for Splunk
This replaces the curl-based "First Success Test" with a cleaner FastMCP client test.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys

from dotenv import load_dotenv

try:
    from fastmcp import Client
except ImportError:
    print("❌ FastMCP is not installed. The server setup script should have installed it.")
    print("   Try running: uv pip install fastmcp")
    sys.exit(1)

# Load environment variables from a .env file if present
load_dotenv()


def _build_server_url_from_env() -> str:
    """Build MCP server URL from environment variables.

    Uses MCP_SERVER_HOST and MCP_SERVER_PORT with sensible defaults.
    """
    host = os.getenv("MCP_SERVER_HOST", "localhost").strip()
    port = str(os.getenv("MCP_SERVER_PORT", "8001")).strip()
    return f"http://{host}:{port}/mcp/"


async def test_server_connection(url: str = "", detailed: bool = False):
    """Test the MCP server connection and basic functionality."""

    # Quiet down all logging for cohesive output (re-enable at end)
    logging.disable(logging.CRITICAL)

    resolved_url = url or _build_server_url_from_env()

    print("== MCP Server Check ==")
    print(f"URL: {resolved_url}")

    try:
        client = Client(resolved_url)

        async with client:
            # Server connectivity
            print("• MCP Server: OK ✅")

            # Tools/resources counts (minimal by default)
            tools = await client.list_tools()
            resources = await client.list_resources()
            print(f"• Tools: {len(tools)} | Resources: {len(resources)}")

            # Detailed listing
            if detailed:
                if tools:
                    print("\n📋 Tools (first 5):")
                    for i, tool in enumerate(tools[:5], 1):
                        desc = (tool.description or "").strip()
                        print(f"  {i}. {tool.name}{' - ' + desc if desc else ''}")
                    if len(tools) > 5:
                        print(f"  ... and {len(tools) - 5} more tools")
                if resources:
                    print("\n📚 Resources (first 5):")
                    for i, resource in enumerate(resources[:5], 1):
                        name = getattr(resource, "name", "") or ""
                        print(f"  {i}. {resource.uri}{' - ' + name if name else ''}")
                    if len(resources) > 5:
                        print(f"  ... and {len(resources) - 5} more resources")

            # Try to call get_splunk_health (preferred) or the first health-ish tool
            health_tool = next((t for t in tools if t.name == "get_splunk_health"), None)
            if not health_tool:
                health_tool = next((t for t in tools if "health" in t.name.lower()), None)

            if health_tool:
                try:
                    result = await client.call_tool(health_tool.name, {})
                    # Normalize structured output
                    status_info = None
                    if hasattr(result, "structured_content") and isinstance(
                        result.structured_content, dict
                    ):
                        status_info = result.structured_content
                    elif hasattr(result, "data") and isinstance(result.data, dict):
                        status_info = result.data
                    else:
                        # Fallback: parse first text content as JSON if present
                        try:
                            texts = []
                            if hasattr(result, "content") and result.content:
                                for item in result.content:
                                    text_val = getattr(item, "text", None)
                                    if text_val:
                                        texts.append(text_val)
                            if texts:
                                status_info = json.loads(texts[0])
                        except (ValueError, TypeError, json.JSONDecodeError):
                            status_info = None

                    print()
                    print("-- Splunk Health --")
                    if isinstance(status_info, dict):
                        status = (status_info.get("status") or "unknown").lower()
                        server_name = (
                            status_info.get("server_name") or status_info.get("server") or "unknown"
                        )
                        version = status_info.get("version") or "unknown"
                        source = status_info.get("connection_source") or ""

                        is_connected = status == "connected"
                        print(f"• Status: {'Connected ✅' if is_connected else 'Not connected ❌'}")
                        if is_connected or detailed:
                            print(f"• Server: {server_name}")
                            print(f"• Version: {version}")
                            if source:
                                print(f"• Source: {source}")
                        if not is_connected:
                            print()
                            print("Troubleshooting:")
                            print("1) Verify Splunk settings in .env:")
                            print(
                                "   SPLUNK_HOST, SPLUNK_PORT, SPLUNK_USERNAME, SPLUNK_PASSWORD, SPLUNK_SCHEME, SPLUNK_VERIFY_SSL"
                            )
                            print("2) Restart MCP Server:")
                            print("   mcp-server --stop")
                            print("   mcp-server --local")
                    else:
                        print("• Unable to parse health response")

                    if detailed:
                        print("\nRaw health result (truncated):")
                        preview = (
                            json.dumps(status_info, indent=2)[:800]
                            if isinstance(status_info, dict)
                            else str(status_info)[:800]
                        )
                        print(preview)
                except (RuntimeError, ValueError, TypeError) as e:
                    print(f"🔧 Splunk Health: error calling '{health_tool.name}': {e}")
            else:
                print("-- Splunk Health --")
                print("• Health tool not available")

    except ConnectionError:
        print(f"❌ Could not connect to MCP Server at {resolved_url}")
        print("   Make sure the server is running with:")
        print("   mcp-server --local")
        sys.exit(1)
    except (RuntimeError, ValueError, TypeError) as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        logging.disable(logging.NOTSET)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="test-mcp-server", description="Quick MCP server verification"
    )
    parser.add_argument(
        "--url", help="Override server URL (e.g., http://localhost:8003/mcp/)", default=""
    )
    parser.add_argument(
        "--detailed", action="store_true", help="Show detailed tool/resource and health output"
    )
    args = parser.parse_args()

    asyncio.run(test_server_connection(args.url, args.detailed))


if __name__ == "__main__":
    main()
