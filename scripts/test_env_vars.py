#!/usr/bin/env python3
"""Test script to verify Splunk-related environment variables are loaded."""

import os
import sys


def test_env_vars():
    """Test if environment variables are properly loaded."""
    print("🔍 Testing Environment Variables")
    print("=" * 50)

    required_vars = {
        "SPLUNK_HOST": "Splunk server hostname",
        "SPLUNK_USERNAME": "Splunk username",
        "SPLUNK_PASSWORD": "Splunk password",
    }

    optional_vars = {
        "SPLUNK_PORT": "Splunk management port (default: 8089)",
        "SPLUNK_VERIFY_SSL": "Verify SSL certificates (default: true)",
        "MCP_HOT_RELOAD": "Enable hot reload (development)",
        "MCP_SERVER_MODE": "Server mode (docker/local)",
        "MCP_STATELESS_HTTP": "Stateless HTTP for handshake-era clients (default: true)",
        "FASTMCP_HTTP_HOST_ORIGIN_PROTECTION": "Host/Origin protection (default: auto)",
    }

    all_good = True

    print("📋 Required Variables:")
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if value:
            if "PASSWORD" in var_name or "KEY" in var_name:
                display_value = f"***{value[-3:]}" if len(value) > 3 else "***"
            else:
                display_value = value
            print(f"  ✅ {var_name}: {display_value}")
        else:
            print(f"  ❌ {var_name}: NOT SET - {description}")
            all_good = False

    print("\n📋 Optional Variables:")
    for var_name, description in optional_vars.items():
        value = os.getenv(var_name)
        if value:
            print(f"  ✅ {var_name}: {value}")
        else:
            print(f"  ⚪ {var_name}: Not set - {description}")

    print("\n🔌 Splunk Client Configuration Test:")
    try:
        from src.client.splunk_client import get_splunk_config

        config = get_splunk_config()
        print("  ✅ Splunk configuration loaded successfully")
        print(f"  🌐 Host: {config.get('host', 'Not set')}")
        print(f"  🔌 Port: {config.get('port', 'Not set')}")
        print(f"  👤 Username: {config.get('username', 'Not set')}")
        print(f"  🔐 Password: {'(set)' if config.get('password') else 'Not set'}")
        print(f"  🔒 SSL Verify: {config.get('verify', 'Not set')}")
    except Exception as e:
        print(f"  ❌ Splunk configuration failed: {e}")
        all_good = False

    print("\n" + "=" * 50)
    if all_good:
        print("✅ Environment check passed")
        return 0
    print("❌ Environment check failed")
    return 1


if __name__ == "__main__":
    sys.exit(test_env_vars())
