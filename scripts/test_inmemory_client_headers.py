#!/usr/bin/env python3
"""
In-memory FastMCP client test (per docs) that passes client configuration
equivalent to HTTP headers and verifies the tool uses client_config.

Reference: FastMCP in-memory testing
https://gofastmcp.com/deployment/testing#in-memory-testing

This script:
- Uses the in-memory FastMCP Client (no network, no HTTP headers path)
- Calls get_splunk_health with splunk_* arguments (same values you'd send as headers)
- Verifies connection_source == "client_config"
"""

import asyncio
import sys
from pathlib import Path


async def main() -> int:
    # Ensure project root on path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from fastmcp import Client  # type: ignore

    from src.server import mcp

    # Build client configuration from env (mirrors X-Splunk-* headers)
    cfg = {
        "splunk_host": "orange-ab.splunkcloud.com",
        "splunk_port": 8089,
        "splunk_username": "daniel.young@orangecyberdefense.com",
        "splunk_password": "7kG5iT&Py6T6^CdM",
        "splunk_scheme": "https",
        "splunk_verify_ssl": True,
    }

    print("🧪 In-memory header-equivalent client_config test")
    print(f"   Host: {cfg['splunk_host']}  Port: {cfg['splunk_port']}  Scheme: {cfg['splunk_scheme']}")

    async with Client(mcp) as client:  # in-memory per FastMCP docs
        # Discover tools (sanity)
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]
        print(f"🧰 Discovered {len(tool_names)} tools")
        if "get_splunk_health" not in tool_names:
            print("❌ get_splunk_health not found")
            return 1

        # Invoke with client-provided config
        result = await client.call_tool("get_splunk_health", cfg)

        # FastMCP returns tool result objects; normalize
        data = getattr(result, "data", result)
        print(f"📡 Health result: {data}")

        source = (data or {}).get("connection_source") if isinstance(data, dict) else None
        if source == "client_config":
            print("✅ Tool used client_config (in-memory path)")
            return 0
        else:
            print("⚠️ Expected connection_source == 'client_config' but got:", source)
            return 2


if __name__ == "__main__":
    try:
        rc = asyncio.run(main())
    except KeyboardInterrupt:
        rc = 130
    sys.exit(rc)


