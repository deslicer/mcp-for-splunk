#!/usr/bin/env python3
"""
Demonstration script for client-provided Splunk configuration.

This script shows how MCP clients can provide Splunk connection
configuration directly to tools instead of relying on server
environment variables.
"""

import asyncio
import sys

from src.tools.health.status import GetSplunkHealth
from src.core.shared_context import http_headers_context

# Add the project root to the path for imports
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


async def demo_client_configuration():
    """Demonstrate client-provided Splunk configuration."""

    print("🔧 MCP Server for Splunk - Client Configuration Demo")
    print("=" * 60)

    # Create a mock MCP context (in real usage, this comes from the MCP client)
    class MockContext:
        def __init__(self):
            self.request_context = MockRequestContext()

        def info(self, message: str):
            print(f"ℹ️  {message}")

        def error(self, message: str):
            print(f"❌ {message}")

    class MockRequestContext:
        def __init__(self):
            self.lifespan_context = MockLifespanContext()

    class MockLifespanContext:
        def __init__(self):
            self.is_connected = False  # Simulate no server connection
            self.service = None

    # Create tool instance
    health_tool = GetSplunkHealth("get_splunk_health", "Health check tool")
    ctx = MockContext()

    print("\n1️⃣  Testing without any configuration (should fail)")
    print("-" * 50)

    try:
        result = await health_tool.execute(ctx)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Expected failure: {e}")

    print("\n2️⃣  Testing with client-provided HTTP headers (recommended)")
    print("-" * 50)

    # Example client configurations for different environments (converted to headers)
    environments = {
        "Development": {
            "X-Splunk-Host": "dev-splunk.company.local",
            "X-Splunk-Port": "8089",
            "X-Splunk-Username": "dev-user",
            "X-Splunk-Password": "dev-password",
            "X-Splunk-Scheme": "http",
            "X-Splunk-Verify-SSL": "false",
            "X-Session-ID": "dev-session",
        },
        "Production": {
            "X-Splunk-Host": "prod-splunk.company.com",
            "X-Splunk-Port": "8089",
            "X-Splunk-Username": "monitoring-service",
            "X-Splunk-Password": "secure-prod-password",
            "X-Splunk-Scheme": "https",
            "X-Splunk-Verify-SSL": "true",
            "X-Session-ID": "prod-session",
        },
        "Cloud": {
            "X-Splunk-Host": "customer.splunkcloud.com",
            "X-Splunk-Port": "8089",
            "X-Splunk-Username": "cloud-user",
            "X-Splunk-Password": "cloud-token",
            "X-Splunk-Scheme": "https",
            "X-Splunk-Verify-SSL": "true",
            "X-Session-ID": "cloud-session",
        },
    }

    for env_name, config in environments.items():
        print(f"\n🌍 Testing {env_name} Environment:")
        print(f"   Host: {config['X-Splunk-Host']}")
        print(f"   Scheme: {config['X-Splunk-Scheme']}")
        print(f"   SSL Verify: {config['X-Splunk-Verify-SSL']}")

        try:
            # Simulate HTTP header capture (normally set by ASGI middleware in src/server.py)
            http_headers_context.set(config)

            # Execute without kwargs; tool will read client config from headers
            result = await health_tool.execute(ctx)
            print(f"   Result: {result}")
        except Exception as e:
            print(f"   Expected connection failure: {str(e)[:100]}...")

    # Note: When using HTTP transport, headers are preferred and extracted automatically server-side.

    print("\n4️⃣  Real-World Usage Examples")
    print("-" * 50)

    print(
        """
    # Example 1: Cursor IDE Usage
    When using the tool in Cursor, you can provide configuration like this:

    "Please check the health of our production Splunk with these settings:
    - splunk_host: prod-splunk.company.com
    - splunk_username: monitoring-user
    - splunk_password: secure-password
    - splunk_verify_ssl: true"

    # Example 2: MCP Inspector (http://localhost:3001)
    {
      "tool": "get_splunk_health",
      "arguments": {
        "splunk_host": "dev-splunk.company.com",
        "splunk_username": "dev-user",
        "splunk_password": "dev-password",
        "splunk_verify_ssl": false
      }
    }

    # Example 3: Google ADK Integration
    await splunk_agent.execute_tool(
        "get_splunk_health",
        splunk_host="production-splunk.company.com",
        splunk_username="monitoring",
        splunk_password="secure-password",
        splunk_verify_ssl=True
    )
    """
    )

    print("\n5️⃣  Benefits of Client Configuration")
    print("-" * 50)

    benefits = [
        "🎯 Target different Splunk environments per request",
        "🔐 Use different credentials for different clients",
        "🌐 Support multi-tenant deployments",
        "⚡ No server restart needed for new connections",
        "🔄 Automatic fallback to server configuration",
        "🛡️ Keep sensitive credentials with the client",
    ]

    for benefit in benefits:
        print(f"   {benefit}")

    print("\n✅ Demo completed successfully!")
    print("\nNext steps:")
    print("1. Update your tools to use client configuration parameters")
    print("2. Test with MCP Inspector at http://localhost:3001")
    print("3. Configure your MCP clients with Splunk settings")
    print("4. Check the documentation: docs/client_configuration.md")


if __name__ == "__main__":
    print("Starting MCP Splunk Client Configuration Demo...")
    asyncio.run(demo_client_configuration())
