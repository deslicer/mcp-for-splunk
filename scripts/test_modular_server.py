#!/usr/bin/env python3
"""
Test script for the modular MCP server.

This script validates that the modular server works correctly by:
1. Testing tool discovery and loading
2. Verifying all expected tools are present
3. Testing basic tool functionality
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastmcp import Client

from src.server import mcp

# Expected tools in the modular server
EXPECTED_TOOLS = [
    # Search tools
    "run_oneshot_search",
    "run_splunk_search",
    # Metadata tools
    "list_indexes",
    "list_sourcetypes",
    "list_sources",
    # Health tools
    "get_splunk_health",
    # Admin tools
    "list_apps",
    "list_users",
    "get_configurations",
    # KV Store tools
    "list_kvstore_collections",
    "get_kvstore_data",
    "create_kvstore_collection",
    # Example tools from contrib may be added here as they are created
]


async def test_tool_discovery():
    """Test that all expected tools are discovered and registered."""
    print("🔍 Testing tool discovery...")

    async with Client(mcp) as client:
        try:
            # List all available tools
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]

            print(f"✅ Discovered {len(tool_names)} tools:")
            for tool_name in sorted(tool_names):
                print(f"   - {tool_name}")

            # Check if all expected tools are present
            missing_tools = set(EXPECTED_TOOLS) - set(tool_names)
            unexpected_tools = set(tool_names) - set(EXPECTED_TOOLS)

            if missing_tools:
                print(f"❌ Missing tools: {missing_tools}")
                return False

            if unexpected_tools:
                print(f"ℹ️  Unexpected tools (may be from contributions): {unexpected_tools}")

            print("✅ All expected tools discovered successfully!")
            return True

        except Exception as e:
            print(f"❌ Tool discovery failed: {e}")
            return False


async def test_health_tool():
    """Test the Splunk health tool."""
    print("\n🏥 Testing Splunk health tool...")

    async with Client(mcp) as client:
        try:
            # Test health tool (should work even without Splunk connection)
            result = await client.call_tool("get_splunk_health", {})

            if result:
                print("✅ Health tool executed successfully!")
                print(f"   Status: {result}")
                return True
            else:
                print("❌ Health tool returned no result")
                return False

        except Exception as e:
            print(f"❌ Health tool test failed: {e}")
            return False


async def test_server_startup():
    """Test that the server starts up correctly."""
    print("🚀 Testing server startup...")

    try:
        # The fact that we can create a client means the server started
        async with Client(mcp) as client:
            # Test basic connectivity
            await client.list_tools()
            print("✅ Server started and is responding correctly!")
            return True

    except Exception as e:
        print(f"❌ Server startup test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests and report results."""
    print("🧪 Starting Modular MCP Server Tests")
    print("=" * 50)

    tests = [
        ("Server Startup", test_server_startup),
        ("Tool Discovery", test_tool_discovery),
        ("Health Tool", test_health_tool),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 50)
    print("🏁 Test Results Summary:")

    passed = 0
    failed = 0

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}: {test_name}")
        if success:
            passed += 1
        else:
            failed += 1

    print(f"\n📊 Total: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! The modular server is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the logs above.")
        return False


if __name__ == "__main__":
    print("Modular MCP Server Test Suite")
    print("Testing the new modular architecture...")

    # Run the tests
    success = asyncio.run(run_all_tests())

    # Exit with appropriate code
    sys.exit(0 if success else 1)
