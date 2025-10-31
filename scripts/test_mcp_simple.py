#!/usr/bin/env python3
"""
Simple test script for MCP Server using FastMCP Client.

This demonstrates the proper way to test MCP tools with HTTP headers.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_with_fastmcp_client():
    """Test using the FastMCP Client (proper way)"""
    print("\n" + "=" * 60)
    print("Testing MCP Server with FastMCP Client")
    print("=" * 60 + "\n")

    try:
        from fastmcp import Client
    except ImportError:
        print("❌ FastMCP not installed. Run: pip install fastmcp")
        return False

    # Splunk configuration as HTTP headers
    headers = {
        "X-Splunk-Host": os.getenv("SPLUNK_HOST", "localhost"),
        "X-Splunk-Port": os.getenv("SPLUNK_PORT", "8089"),
        "X-Splunk-Username": os.getenv("SPLUNK_USERNAME", "admin"),
        "X-Splunk-Password": os.getenv("SPLUNK_PASSWORD", "changeme"),
        "X-Splunk-Scheme": os.getenv("SPLUNK_SCHEME", "https"),
        "X-Splunk-Verify-SSL": os.getenv("SPLUNK_VERIFY_SSL", "false"),
        "X-Session-ID": "test-session-simple",
    }

    print("📋 Splunk Configuration:")
    for key, value in headers.items():
        if "Password" in key:
            print(f"  {key}: {'*' * len(value)}")
        else:
            print(f"  {key}: {value}")
    print()

    try:
        # Connect to MCP server with custom headers
        # Note: FastMCP Client doesn't support custom headers directly
        # We need to use httpx with custom headers
        print("🔌 Connecting to MCP server at http://localhost:8003/mcp...")

        import httpx

        # Create custom httpx client with headers
        http_client = httpx.AsyncClient(headers=headers, timeout=60.0, follow_redirects=True)

        async with Client(
            transport="http://localhost:8003/mcp",
            http_client=http_client,  # Pass custom httpx client with headers
        ) as client:
            print("✅ Connected successfully!\n")

            # Test 1: List available tools
            print("📚 Test 1: Listing available tools...")
            tools = await client.list_tools()
            print(f"✅ Found {len(tools)} tools")
            print(f"   Sample tools: {', '.join([t.name for t in tools[:5]])}\n")

            # Test 2: Call user_agent_info (simple tool)
            print("🔧 Test 2: Calling user_agent_info...")
            result = await client.call_tool("user_agent_info", {})
            if result and hasattr(result, "content") and len(result.content) > 0:
                print("✅ user_agent_info executed successfully\n")
            else:
                print("❌ user_agent_info returned unexpected result\n")
                return False

            # Test 3: Call list_indexes (requires session)
            print("🔧 Test 3: Calling list_indexes (requires proper session)...")
            try:
                result = await client.call_tool("list_indexes", {})
                if result and hasattr(result, "content") and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, "text"):
                        import json

                        data = json.loads(content.text)
                        indexes = data.get("indexes", [])
                        print("✅ list_indexes executed successfully!")
                        print(f"   Found {len(indexes)} indexes")
                        if indexes:
                            print(f"   Sample: {', '.join(indexes[:5])}\n")
                    return True
                else:
                    print("❌ list_indexes returned unexpected result\n")
                    return False
            except Exception as e:
                print(f"❌ list_indexes failed: {e}\n")
                return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run the test"""
    print("\n" + "=" * 60)
    print("MCP Server for Splunk - Simple Test with FastMCP Client")
    print("=" * 60)

    # Check if server is running
    print("\n⚠️  Make sure the MCP server is running:")
    print("   uv run mcp-server --local -d\n")

    success = await test_with_fastmcp_client()

    if success:
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60 + "\n")
        return True
    else:
        print("\n" + "=" * 60)
        print("❌ TESTS FAILED")
        print("=" * 60 + "\n")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
