#!/usr/bin/env python3
"""
Test script for MCP Server for Splunk transport modes.

This script demonstrates and tests both stdio and HTTP transport modes,
and provides instructions for using the MCP Inspector.
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_stdio_mode():
    """Test the MCP server in stdio mode."""
    print("🔧 Testing STDIO Mode")
    print("=" * 50)

    try:
        # Test stdio mode by checking if it starts without errors
        cmd = [sys.executable, "src/server_new.py", "--transport", "stdio"]

        print(f"Command: {' '.join(cmd)}")
        print("Starting server in stdio mode (will timeout after 5 seconds)...")

        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=project_root
        )

        # Wait a bit for startup
        time.sleep(5)
        process.terminate()

        output, _ = process.communicate(timeout=5)

        # Check for successful indicators
        if "Starting MCP server" in output and "Loaded 13 tools" in output:
            print("✅ STDIO mode: SUCCESS - All 13 tools loaded!")
            return True
        else:
            print("❌ STDIO mode: FAILED")
            print("Output:", output[-500:])  # Last 500 chars
            return False

    except Exception as e:
        print(f"❌ STDIO mode error: {e}")
        return False


async def test_http_mode():
    """Test the MCP server in HTTP mode."""
    print("\n🌐 Testing HTTP Mode")
    print("=" * 50)

    try:
        import httpx
        from fastmcp import Client

        # Start server in background
        cmd = [sys.executable, "src/server_new.py", "--transport", "http", "--port", "8005"]
        print(f"Command: {' '.join(cmd)}")
        print("Starting server in HTTP mode on port 8005...")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=project_root,
            env={"MCP_SERVER_PORT": "8005"},
        )

        # Wait for server to start
        await asyncio.sleep(8)

        # Test the server
        try:
            async with Client(transport="http://localhost:8005/mcp/") as client:
                tools = await client.list_tools()
                if len(tools) == 13:
                    print(f"✅ HTTP mode: SUCCESS - Found {len(tools)} tools!")
                    print("Sample tools:")
                    for tool in tools[:3]:
                        print(f"  - {tool.name}: {tool.description}")
                    success = True
                else:
                    print(f"❌ HTTP mode: Expected 13 tools, found {len(tools)}")
                    success = False
        except Exception as e:
            print(f"❌ HTTP mode client error: {e}")
            success = False
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        return success

    except ImportError:
        print("❌ HTTP mode: FastMCP client not available")
        return False
    except Exception as e:
        print(f"❌ HTTP mode error: {e}")
        return False


def print_inspector_instructions():
    """Print instructions for using the MCP Inspector."""
    print("\n🔍 MCP Inspector Instructions")
    print("=" * 50)

    print("""
The MCP Inspector is running and ready to use!

🌐 **Web Interface**: http://localhost:3001

📡 **Connect to MCP Server**:
   Server URL: http://localhost:8001/mcp/

🔧 **Manual Connection Steps**:
   1. Open http://localhost:3001 in your browser
   2. Click "Add Server" or "Connect"
   3. Enter server URL: http://localhost:8001/mcp/
   4. Click "Connect"
   5. You should see all 13 tools available!

📊 **Expected Tools in Inspector**:
   ✅ get_configurations - Splunk config management
   ✅ create_kvstore_collection - KV Store management
   ✅ get_kvstore_data - KV Store queries
   ✅ list_kvstore_collections - KV Store listing
   ✅ run_splunk_search - Splunk search execution
   ✅ run_oneshot_search - Quick Splunk searches
   ✅ hello_world - Example tool
   ✅ list_apps, list_users, get_splunk_health
   ✅ list_indexes, list_sources, list_sourcetypes

🚀 **Docker Status**:
   - MCP Server: Running on http://localhost:8001/mcp/
   - Inspector UI: Running on http://localhost:3001
   - Splunk: Running on http://localhost:9000
""")


def print_usage_examples():
    """Print usage examples for different transport modes."""
    print("\n📋 Usage Examples")
    print("=" * 50)

    print("""
🔧 **STDIO Mode** (for direct MCP client integration):
   python src/server_new.py --transport stdio

🌐 **HTTP Mode** (for web-based clients and Inspector):
   python src/server_new.py --transport http --port 8000

🐳 **Docker Mode** (full production setup):
   docker-compose -f docker-compose-modular.yml up

🧪 **Testing with Python Client**:
   ```python
   from fastmcp import Client

   # HTTP transport
   async with Client(transport='http://localhost:8001/mcp/') as client:
       tools = await client.list_tools()
       result = await client.call_tool('get_splunk_health', {})
   ```

📝 **Environment Variables**:
   - MCP_SERVER_PORT=8000      # HTTP server port
   - MCP_SERVER_HOST=0.0.0.0   # HTTP server host
   - SPLUNK_HOST=so1           # Splunk server
   - SPLUNK_PASSWORD=Chang3d!  # Splunk password
""")


async def main():
    """Run all transport tests."""
    print("🚀 MCP Server for Splunk - Transport Mode Testing")
    print("=" * 60)

    # Test both modes
    stdio_success = test_stdio_mode()
    http_success = await test_http_mode()

    # Print results
    print("\n📊 Test Results Summary")
    print("=" * 50)
    print(f"STDIO Mode: {'✅ PASSED' if stdio_success else '❌ FAILED'}")
    print(f"HTTP Mode:  {'✅ PASSED' if http_success else '❌ FAILED'}")

    if stdio_success and http_success:
        print("\n🎉 ALL TESTS PASSED! Both transport modes are working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.")

    # Print instructions
    print_inspector_instructions()
    print_usage_examples()

    return stdio_success and http_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
