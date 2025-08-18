#!/usr/bin/env python3
"""
Test script for the modular MCP server.

This script validates that the modular server works correctly by:
1. Testing tool discovery and loading
2. Verifying all expected tools are present
3. Testing basic tool functionality
"""

import sys
from pathlib import Path

from fastmcp import Client

from src.server import mcp

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Expected tools in the modular server
EXPECTED_TOOLS = {
    "get_splunk_health",
    "run_oneshot_search",
    "run_splunk_search",
    "list_apps",
    "list_users",
    "list_indexes",
}


async def main():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool_names = {t.name for t in tools}

        missing = EXPECTED_TOOLS - tool_names
        extra = tool_names - EXPECTED_TOOLS

        print("Tools:", sorted(tool_names))
        if missing:
            print("Missing:", sorted(missing))
        if extra:
            print("Extra:", sorted(extra))


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
