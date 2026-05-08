"""Smoke-test the X-MCP-Toolsets header against a live MCP-for-Splunk container.

Run after starting the container, e.g.:

    docker run -d --name mcp-itsi-smoke -p 8013:8001 ... mcp-itsi-smoke:local
    uv run --with fastmcp python scripts/smoke_toolset_filter.py

The script lists the tools the server advertises under four selection
modes and prints a short summary table so we can eyeball that:

* No header   → splunk tools only (default ``MCP_DEFAULT_TOOLSETS=splunk``;
                plugins like ITSI are opt-in)
* ``splunk``  → only ``splunk``-tagged tools (no ``itsi_*``)
* ``itsi``    → only ``itsi_*`` tools (plus untagged framework helpers)
* ``splunk,itsi`` → union of the two
"""

from __future__ import annotations

import asyncio
import sys

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


SERVER_URL = "http://localhost:8013/mcp"


def _classify(name: str) -> str:
    return "itsi" if name.startswith("itsi_") else "splunk"


async def list_with(headers: dict[str, str] | None) -> list[str]:
    transport = StreamableHttpTransport(SERVER_URL, headers=headers or {})
    client = Client(transport)
    async with client:
        tools = await client.list_tools()
    return sorted(t.name for t in tools)


async def main() -> int:
    cases: list[tuple[str, dict[str, str] | None]] = [
        ("default (no header)", None),
        ("splunk only", {"X-MCP-Toolsets": "splunk"}),
        ("itsi only", {"X-MCP-Toolsets": "itsi"}),
        ("splunk + itsi", {"X-MCP-Toolsets": "splunk,itsi"}),
    ]

    for label, headers in cases:
        names = await list_with(headers)
        splunk_n = sum(1 for n in names if _classify(n) == "splunk")
        itsi_n = sum(1 for n in names if _classify(n) == "itsi")
        sample_itsi = next((n for n in names if n.startswith("itsi_")), "<none>")
        sample_splunk = next((n for n in names if not n.startswith("itsi_")), "<none>")
        print(f"\n=== {label} ===")
        print(f"  total: {len(names)}  splunk-named: {splunk_n}  itsi-named: {itsi_n}")
        print(f"  sample splunk: {sample_splunk}")
        print(f"  sample itsi  : {sample_itsi}")

    print("\n=== call_tool guard ===")
    transport = StreamableHttpTransport(SERVER_URL, headers={"X-MCP-Toolsets": "splunk"})
    async with Client(transport) as client:
        try:
            await client.call_tool("itsi_list_entities", {})
        except Exception as exc:
            print(f"  blocked itsi_list_entities under splunk-only: {type(exc).__name__}: {exc}")
        else:
            print("  ERROR: itsi_list_entities was NOT blocked under splunk-only header")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
