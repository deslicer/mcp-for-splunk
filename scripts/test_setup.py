#!/usr/bin/env python3
"""
Quick setup test script for MCP Server for Splunk
This replaces the curl-based "First Success Test" with a cleaner FastMCP client test.
"""

import asyncio
import os
import json
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


async def test_server_connection(url: str = ""):
    """Test the MCP server connection and basic functionality."""

    resolved_url = url or _build_server_url_from_env()

    print(f"🔍 Testing MCP Server at {resolved_url}")
    print("-" * 50)

    try:
        # Create client
        client = Client(resolved_url)

        async with client:
            # Test 1: Server connectivity
            print("✓ Connected to MCP Server")

            # Test 2: List tools
            print("\n📋 Available Tools:")
            tools = await client.list_tools()
            if tools:
                for i, tool in enumerate(tools[:5], 1):  # Show first 5 tools
                    print(f"  {i}. {tool.name}")
                    if tool.description:
                        print(f"     {tool.description[:60]}...")
                if len(tools) > 5:
                    print(f"  ... and {len(tools) - 5} more tools")
            else:
                print("  ❌ No tools found")

            # Test 3: List resources
            print("\n📚 Available Resources:")
            resources = await client.list_resources()
            if resources:
                for i, resource in enumerate(resources[:5], 1):  # Show first 5 resources
                    print(f"  {i}. {resource.uri}")
                    if resource.name:
                        print(f"     {resource.name}")
                if len(resources) > 5:
                    print(f"  ... and {len(resources) - 5} more resources")
            else:
                print("  ❌ No resources found")

            # Test 4: Read server info resource
            print("\n📖 Reading Server Info:")
            try:
                server_info = await client.read_resource("info://server")
                if server_info and server_info[0].text:
                    print(f"  {server_info[0].text}")
                else:
                    print("  ❌ Could not read server info")
            except Exception as e:
                print(f"  ❌ Error reading server info: {e}")

            # Test 5: Try to call a simple tool (if available)
            print("\n🔧 Testing Tool Execution:")
            if tools:
                # Look for a simple tool like get_splunk_health
                health_tool = next((t for t in tools if "health" in t.name.lower()), None)
                if health_tool:
                    try:
                        result = await client.call_tool(health_tool.name, {})
                        print(f"  ✓ Called '{health_tool.name}' successfully")

                        # Try to extract structured info from the result
                        status_info = None
                        if hasattr(result, "structured_content") and isinstance(result.structured_content, dict):
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
                            except Exception:
                                status_info = None

                        if isinstance(status_info, dict):
                            status = status_info.get("status", "unknown")
                            version = status_info.get("version", "unknown")
                            server_name = status_info.get("server_name", status_info.get("server", "unknown"))
                            source = status_info.get("connection_source", "")
                            print(f"  Connection Status: {status}")
                            print(f"  Server: {server_name}")
                            print(f"  Version: {version}")
                            if source:
                                print(f"  Source: {source}")
                        else:
                            # If we cannot parse, show raw result as fallback
                            print(f"  Result: {result}")
                    except Exception as e:
                        print(f"  ⚠️  Could not call '{health_tool.name}': {e}")
                        print("  This might be normal if Splunk is not configured yet.")
                else:
                    print("  ℹ️  No health check tool found to test")

            print("\n✅ MCP Server is running and responding correctly!")
            print("\n🎉 Setup verification complete! Your MCP server is ready to use.")

            # Provide next steps
            print("\n📋 Next Steps:")
            print("1. Configure your .env file with Splunk credentials")
            print("2. Open MCP Inspector at http://localhost:6274")
            print("3. Connect your AI client (Claude, Cursor, etc.)")
            print("4. Start using the available tools and resources!")

    except ConnectionError:
        print(f"❌ Could not connect to MCP Server at {resolved_url}")
        print("   Make sure the server is running with:")
        print("   ./scripts/build_and_run.sh (macOS/Linux)")
        print("   .\\scripts\\build_and_run.ps1 (Windows)")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    # Check if a custom URL was provided
    url = sys.argv[1] if len(sys.argv) > 1 else ""

    # Run the async test
    asyncio.run(test_server_connection(url))


if __name__ == "__main__":
    main()
