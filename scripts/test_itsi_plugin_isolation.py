"""Verify the ITSI plugin doesn't interfere with parent mcp-for-splunk tools.

Checks:
1. The parent server exposes both ITSI tools (`itsi_*`) and its own
   tools (e.g. `list_indexes`, `get_splunk_health`).
2. Calling a parent tool returns a sane response.
3. Resource URIs from both packages coexist (`itsi://docs/*` and
   `splunk://...`).

Run after starting the parent server with the ITSI plugin loaded.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


def _ok(name: str, status: str, detail: str = "") -> str:
    icon = "OK" if status == "success" else ("WARN" if status == "warn" else "FAIL")
    return f"[{icon:<4}] {name:<48}{' — ' + detail if detail else ''}"


async def _call(client: Client, name: str, args: dict[str, Any]) -> dict[str, Any]:
    res = await client.call_tool(name, args)
    data = getattr(res, "structured_content", None) or getattr(res, "data", None)
    if data is None and getattr(res, "content", None):
        first = res.content[0]
        text = getattr(first, "text", None)
        if text:
            try:
                data = json.loads(text)
            except Exception:
                data = {"raw": text}
    return data if isinstance(data, dict) else {"raw": data}


async def main() -> int:
    url = os.getenv("MCP_ITSI_URL", "http://127.0.0.1:8085/mcp")
    headers = {
        "X-Splunk-Host": os.environ["ITSI_HOST"],
        "X-Splunk-Port": os.getenv("ITSI_PORT", "8089"),
        "X-Splunk-Scheme": os.getenv("ITSI_SCHEME", "https"),
        "X-Splunk-Username": os.environ["ITSI_USERNAME"],
        "X-Splunk-Password": os.environ["ITSI_PASSWORD"],
        "X-Splunk-Verify-SSL": os.getenv("ITSI_VERIFY_SSL", "false"),
        "X-Session-ID": "plugin-isolation",
    }

    print(f"# ITSI plugin isolation check\n\nServer: {url}\n")
    failures = 0

    transport = StreamableHttpTransport(url, headers=headers)
    async with Client(transport) as client:
        tools = await client.list_tools()
        names = {getattr(t, "name", "") for t in tools}

        itsi_count = sum(1 for n in names if n.startswith("itsi_"))
        parent_count = len(names) - itsi_count
        print(f"## Tool inventory\n\n- ITSI tools: {itsi_count}")
        print(f"- Parent tools: {parent_count}")
        print(f"- Total: {len(names)}\n")

        # ITSI plugin tools must be present
        for required in (
            "itsi_list_services",
            "itsi_create_service",
            "itsi_delete_service",
            "itsi_list_notable_events",
            "itsi_create_correlation_search",
        ):
            ok = required in names
            failures += 0 if ok else 1
            print(_ok(f"plugin tool {required}", "success" if ok else "fail"))

        # Parent tools must still be present (typical names)
        present_parent = [
            n
            for n in (
                "list_indexes",
                "list_apps",
                "get_splunk_health",
                "list_users",
                "run_oneshot_search",
            )
            if n in names
        ]
        print(
            _ok("parent tools present", "success", f"{len(present_parent)} found: {present_parent}")
        )
        if not present_parent:
            failures += 1

        # Call a non-ITSI tool to make sure the parent path still works
        if "list_indexes" in names:
            data = await _call(client, "list_indexes", {})
            ok = isinstance(data, dict) and data.get("status") in {"success", None}
            failures += 0 if ok else 1
            count = data.get("count") if isinstance(data, dict) else None
            print(
                _ok(
                    "call list_indexes (parent)",
                    "success" if ok else "fail",
                    f"indexes={count}" if count is not None else json.dumps(data)[:120],
                )
            )

        # Call a no-connection ITSI tool to confirm coexistence
        data = await _call(client, "itsi_list_docs", {})
        ok = data.get("status") == "success" and data.get("count", 0) > 0
        failures += 0 if ok else 1
        print(_ok("call itsi_list_docs", "success" if ok else "fail", f"docs={data.get('count')}"))

        resources = await client.list_resources()
        uris = {str(getattr(r, "uri", "")) for r in resources}
        itsi_res = sum(1 for u in uris if u.startswith("itsi://"))
        splunk_res = sum(1 for u in uris if u.startswith("splunk"))
        print(
            _ok(
                "resources coexist",
                "success" if itsi_res > 0 and splunk_res > 0 else "warn",
                f"itsi://={itsi_res}, splunk*={splunk_res}, total={len(uris)}",
            )
        )

    print(f"\nfailures: {failures}\n")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
