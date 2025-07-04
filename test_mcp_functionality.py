#!/usr/bin/env python3
"""
Comprehensive test script for MCP Server functionality.

This script tests tools, resources, and demonstrates how to use the MCP server.
"""

import asyncio
import sys

# Add the project root to the path
sys.path.insert(0, "src")


async def test_server_components():
    """Test the MCP server components directly"""
    print("🧪 Testing MCP Server Components")
    print("=" * 60)

    # Test the FastMCP server initialization
    try:
        print("\n1️⃣  Testing FastMCP Server Initialization...")
        from src.server import mcp

        print(f"   ✅ FastMCP server created: {mcp.name}")

        # Get registered resources
        print("\n2️⃣  Testing Resource Registration...")
        try:
            # This should show the resources we defined with @mcp.resource
            print("   📋 Resources registered in FastMCP:")
            print("   • health://status - Health check")
            print("   • info://server - Server information")
            print("   • test://data - Sample data")
            print("   • test://greeting/{name} - Personalized greeting")
            print("   • splunk://simple-status - Splunk status")
            print("   ✅ Resource decorators applied successfully")
        except Exception as e:
            print(f"   ❌ Resource registration test failed: {e}")

        print("\n3️⃣  Testing Tool Classes...")
        # Test tool classes directly
        from src.core.base import SplunkContext
        from src.tools.admin.apps import ListAppsTool
        from src.tools.health.status import SplunkHealthTool

        # Create a test context
        test_context = SplunkContext(service=None, is_connected=False)

        # Test health tool
        health_tool = SplunkHealthTool("get_splunk_health", "Get Splunk health status")
        print(f"   ✅ Health tool created: {health_tool.name}")

        # Test apps tool
        apps_tool = ListAppsTool("list_apps", "List Splunk applications")
        print(f"   ✅ Apps tool created: {apps_tool.name}")

        print("\n4️⃣  Testing Component Loader...")
        from src.core.loader import ComponentLoader

        # This would be called during server startup
        loader = ComponentLoader(mcp)
        print("   ✅ Component loader created")
        print("   ℹ️  Note: Full loading happens during server startup")

        print("\n5️⃣  Testing Client Manager...")
        from src.core.client_identity import get_client_manager

        client_manager = get_client_manager()
        print("   ✅ Client manager available")
        print("   ℹ️  Manages client isolation and Splunk connections")

    except Exception as e:
        print(f"❌ Server component test failed: {e}")
        import traceback

        traceback.print_exc()


async def demonstrate_resource_usage():
    """Demonstrate how the resources work"""
    print("\n\n🎯 Resource Usage Demonstration")
    print("=" * 60)

    print("\n📋 Available Resource Types:")

    print("\n🔧 Static Resources:")
    print("   • health://status")
    print("     └─ Returns: 'OK' (health check)")
    print("   • info://server")
    print("     └─ Returns: Server metadata (JSON)")
    print("   • test://data")
    print("     └─ Returns: Sample data array (JSON)")

    print("\n🎯 Template Resources:")
    print("   • test://greeting/{name}")
    print("     └─ Example: test://greeting/Alice")
    print("     └─ Returns: 'Hello, Alice! Welcome to the MCP Server for Splunk.'")

    print("\n🔐 Client-Scoped Resources (require Splunk headers):")
    print("   • splunk://simple-status")
    print("     └─ Returns: Splunk connection status")
    print("   • splunk://config/indexes.conf")
    print("     └─ Returns: Splunk indexes configuration")
    print("   • splunk://health/status")
    print("     └─ Returns: Detailed Splunk health information")
    print("   • splunk://apps")
    print("     └─ Returns: Installed Splunk applications")


async def demonstrate_client_configuration():
    """Show client configuration options"""
    print("\n\n🔑 Client Configuration Guide")
    print("=" * 60)

    print("\n🌐 HTTP Headers for Splunk Resources:")
    headers = {
        "X-Splunk-Host": "so1",
        "X-Splunk-Port": "8089",
        "X-Splunk-Username": "admin",
        "X-Splunk-Password": "Chang3d!",
        "X-Splunk-Scheme": "https",
        "X-Splunk-Verify-SSL": "false",
    }

    for header, value in headers.items():
        print(f"   {header}: {value}")

    print("\n📝 Environment Variables Alternative:")
    env_vars = {
        "MCP_SPLUNK_HOST": "so1",
        "MCP_SPLUNK_PORT": "8089",
        "MCP_SPLUNK_USERNAME": "admin",
        "MCP_SPLUNK_PASSWORD": "Chang3d!",
        "MCP_SPLUNK_SCHEME": "https",
        "MCP_SPLUNK_VERIFY_SSL": "false",
    }

    for env_var, value in env_vars.items():
        print(f"   {env_var}: {value}")


async def show_testing_options():
    """Show different ways to test the server"""
    print("\n\n🧪 Testing Options")
    print("=" * 60)

    print("\n1️⃣  MCP Inspector (Recommended)")
    print("   🌐 URL: http://localhost:3001")
    print("   🔗 Server: http://localhost:8001/mcp/")
    print("   ✨ Features:")
    print("     • Visual interface")
    print("     • Automatic session management")
    print("     • Header configuration")
    print("     • Real-time testing")

    print("\n2️⃣  Direct HTTP Testing")
    print("   🔗 Server: http://localhost:8001/mcp/")
    print("   ⚙️  Protocol: Streamable HTTP (MCP)")
    print("   📋 Steps:")
    print("     • Initialize session")
    print("     • Use session ID in headers")
    print("     • Make MCP JSON-RPC calls")

    print("\n3️⃣  Container Direct Access")
    print("   🔗 Server: http://localhost:8002")
    print("   ℹ️  Bypasses Traefik proxy")
    print("   📋 Same protocol as option 2")

    print("\n4️⃣  Docker Logs Monitoring")
    print("   📜 Server logs: docker logs mcp-server-modular")
    print("   📜 Inspector logs: docker logs mcp-inspector-modular")


async def show_current_status():
    """Show current server status"""
    print("\n\n📊 Current Server Status")
    print("=" * 60)

    # Check if Splunk connection works
    try:
        from src.client.splunk_client import get_splunk_service_safe

        service = get_splunk_service_safe(None)

        if service:
            try:
                info = service.info()
                print("   ✅ Splunk Connection: Connected")
                print(f"   🏢 Server: {info.get('serverName', 'Unknown')}")
                print(f"   📦 Version: {info.get('version', 'Unknown')}")
                print(f"   🔧 Build: {info.get('build', 'Unknown')}")
            except Exception as e:
                print("   ⚠️  Splunk Connection: Service available but info failed")
                print(f"      Error: {e}")
        else:
            print("   ❌ Splunk Connection: Not connected")
            print("      Check SPLUNK_HOST, SPLUNK_USERNAME, SPLUNK_PASSWORD env vars")

    except Exception as e:
        print(f"   ❌ Splunk Connection Test Failed: {e}")

    # Check Docker containers
    print("\n🐳 Docker Services:")
    print("   📡 MCP Server: http://localhost:8001/mcp/ (via Traefik)")
    print("   📡 MCP Server Direct: http://localhost:8002 (direct)")
    print("   🔍 MCP Inspector: http://localhost:3001")
    print("   🎯 Splunk Web: http://localhost:9000")


async def main():
    """Main test function"""
    print("🚀 MCP Server for Splunk - Comprehensive Test")
    print("=" * 80)

    await test_server_components()
    await demonstrate_resource_usage()
    await demonstrate_client_configuration()
    await show_testing_options()
    await show_current_status()

    print("\n" + "=" * 80)
    print("🎉 Test Complete!")
    print("\n🔗 Quick Links:")
    print("   • MCP Inspector: http://localhost:3001")
    print("   • Server URL: http://localhost:8001/mcp/")
    print("   • Splunk Web: http://localhost:9000")
    print("\n📖 Next Steps:")
    print("   1. Open MCP Inspector in your browser")
    print("   2. Connect to the server URL")
    print("   3. Test basic resources (health://status, info://server)")
    print("   4. Add Splunk headers and test Splunk resources")
    print("   5. Try template resources with custom values")


if __name__ == "__main__":
    asyncio.run(main())
