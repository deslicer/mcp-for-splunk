#!/usr/bin/env python3
"""
Demonstration script for client-provided Splunk configuration.

This script shows how MCP clients can provide Splunk connection
configuration directly to tools instead of relying on server
environment variables.
"""

import asyncio
import os
import sys

# Add the project root to the path for imports
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.tools.health.status import GetSplunkHealth


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

    print("\n2️⃣  Testing with client-provided configuration")
    print("-" * 50)

    # Example client configurations for different environments
    environments = {
        "Development": {
            "splunk_host": "dev-splunk.company.local",
            "splunk_port": 8089,
            "splunk_username": "dev-user",
            "splunk_password": "dev-password",
            "splunk_scheme": "http",
            "splunk_verify_ssl": False,
        },
        "Production": {
            "splunk_host": "prod-splunk.company.com",
            "splunk_port": 8089,
            "splunk_username": "monitoring-service",
            "splunk_password": "secure-prod-password",
            "splunk_scheme": "https",
            "splunk_verify_ssl": True,
        },
        "Cloud": {
            "splunk_host": "customer.splunkcloud.com",
            "splunk_port": 8089,
            "splunk_username": "cloud-user",
            "splunk_password": "cloud-token",
            "splunk_scheme": "https",
            "splunk_verify_ssl": True,
        },
    }

    for env_name, config in environments.items():
        print(f"\n🌍 Testing {env_name} Environment:")
        print(f"   Host: {config['splunk_host']}")
        print(f"   Scheme: {config['splunk_scheme']}")
        print(f"   SSL Verify: {config['splunk_verify_ssl']}")

        try:
            # This would fail with real connections, but demonstrates the parameter passing
            result = await health_tool.execute(ctx, **config)
            print(f"   Result: {result}")
        except Exception as e:
            print(f"   Expected connection failure: {str(e)[:100]}...")

    print("\n3️⃣  Configuration Parameter Extraction Demo")
    print("-" * 50)

    # Demonstrate how the tool extracts client configuration
    test_kwargs = {
        "splunk_host": "example.com",
        "splunk_username": "user",
        "splunk_password": "pass",
        "other_param": "should_remain",
        "splunk_port": 8089,
    }

    print(f"Original parameters: {test_kwargs}")

    client_config = health_tool.extract_client_config(test_kwargs)
    print(f"Extracted client config: {client_config}")
    print(f"Remaining parameters: {test_kwargs}")

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
