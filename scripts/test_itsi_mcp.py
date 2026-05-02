"""Smoke test the running ITSI MCP server against a real ITSI instance.

Usage:
    uv run python scripts/test_itsi_mcp.py

Reads MCP_ITSI_URL (default http://127.0.0.1:8084/mcp) and the X-Splunk-*
headers from environment variables ITSI_HOST, ITSI_USERNAME, ITSI_PASSWORD,
ITSI_VERIFY_SSL, ITSI_PORT, ITSI_SCHEME. Prints a markdown-friendly report.

This script intentionally only calls *read-only* and idempotent tools so it
is safe to run against shared environments.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import textwrap
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


def _short(value: Any, limit: int = 240) -> str:
    s = json.dumps(value, default=str) if not isinstance(value, str) else value
    s = s.replace("\n", " ")
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _ok(name: str, status: str, detail: str = "") -> str:
    icon = "OK" if status == "success" else ("WARN" if status == "warn" else "FAIL")
    return f"[{icon:<4}] {name:<42}{' — ' + detail if detail else ''}"


async def main() -> int:
    url = os.getenv("MCP_ITSI_URL", "http://127.0.0.1:8084/mcp")
    headers = {
        "X-Splunk-Host": os.environ["ITSI_HOST"],
        "X-Splunk-Port": os.getenv("ITSI_PORT", "8089"),
        "X-Splunk-Scheme": os.getenv("ITSI_SCHEME", "https"),
        "X-Splunk-Username": os.environ["ITSI_USERNAME"],
        "X-Splunk-Password": os.environ["ITSI_PASSWORD"],
        "X-Splunk-Verify-SSL": os.getenv("ITSI_VERIFY_SSL", "false"),
        "X-Session-ID": "smoke-test",
    }

    print(f"# ITSI MCP smoke test\n\nServer: {url}\nITSI host: {headers['X-Splunk-Host']}\n")

    transport = StreamableHttpTransport(url, headers=headers)
    async with Client(transport) as client:
        await _section_inventory(client)
        results = await _section_no_connection_tools(client)
        results += await _section_meta_tools(client)
        results += await _section_read_only_tools(client)
        results += await _section_resources_and_prompts(client)

        print("\n## Summary\n")
        passed = sum(1 for r in results if r["status"] == "success")
        warned = sum(1 for r in results if r["status"] == "warn")
        failed = sum(1 for r in results if r["status"] == "fail")
        print(f"- success: {passed}\n- warn: {warned}\n- fail: {failed}\n")
        return 0 if failed == 0 else 1


async def _section_inventory(client: Client) -> None:
    print("## Server inventory\n")
    tools = await client.list_tools()
    resources = await client.list_resources()
    prompts = await client.list_prompts()
    print(f"- tools: {len(tools)}")
    print(f"- resources: {len(resources)}")
    print(f"- prompts: {len(prompts)}\n")


async def _section_no_connection_tools(client: Client) -> list[dict[str, Any]]:
    print("## Docs tools (no Splunk connection required)\n")
    cases = [
        ("itsi_list_docs", {}),
        ("itsi_search_docs", {"query": "KPI"}),
        ("itsi_read_doc", {"slug": "best-practices"}),
    ]
    return await _run_cases(client, cases)


async def _section_meta_tools(client: Client) -> list[dict[str, Any]]:
    print("\n## ITSI meta tools\n")
    cases = [
        ("itsi_get_supported_object_types", {}),
        ("itsi_get_alias_list", {}),
    ]
    return await _run_cases(client, cases)


async def _section_read_only_tools(client: Client) -> list[dict[str, Any]]:
    print("\n## ITSI read-only tools\n")
    cases = [
        ("itsi_count_services", {}),
        ("itsi_list_services", {"limit": 5}),
        ("itsi_list_service_templates", {"limit": 5}),
        ("itsi_list_entities", {"limit": 5}),
        ("itsi_list_entity_types", {"limit": 5}),
        ("itsi_list_kpi_base_searches", {"limit": 5}),
        ("itsi_list_kpi_threshold_templates", {"limit": 5}),
        ("itsi_list_glass_tables", {"limit": 5}),
        ("itsi_list_home_views", {"limit": 5}),
        ("itsi_list_deep_dives", {"limit": 5}),
        ("itsi_list_teams", {"limit": 5}),
        ("itsi_list_notable_events", {"limit": 5}),
        ("itsi_list_aggregation_policies", {"limit": 5}),
        ("itsi_list_correlation_searches", {"limit": 5}),
        ("itsi_list_maintenance_windows", {"limit": 5}),
    ]
    return await _run_cases(client, cases)


async def _section_resources_and_prompts(client: Client) -> list[dict[str, Any]]:
    print("\n## Resources & prompts\n")
    results: list[dict[str, Any]] = []
    try:
        content = await client.read_resource("itsi://docs/api/reference")
        text = ""
        if content:
            first = content[0]
            text = getattr(first, "text", "") or ""
        if "ITSI REST API reference" in text:
            results.append({"name": "resource itsi://docs/api/reference", "status": "success"})
            print(_ok("resource itsi://docs/api/reference", "success", f"{len(text)} bytes"))
        else:
            results.append({"name": "resource itsi://docs/api/reference", "status": "fail"})
            print(_ok("resource itsi://docs/api/reference", "fail", "unexpected content"))
    except Exception as exc:
        results.append({"name": "resource itsi://docs/api/reference", "status": "fail"})
        print(_ok("resource itsi://docs/api/reference", "fail", repr(exc)))

    for prompt_name, args in [
        ("itsi_service_onboarding", {"service_name": "MCP-Demo"}),
        ("itsi_kpi_design", {"service_name": "MCP-Demo"}),
        ("itsi_episode_triage", {"event_id": "demo-123"}),
    ]:
        try:
            res = await client.get_prompt(prompt_name, arguments=args)
            messages = getattr(res, "messages", [])
            txt = ""
            if messages:
                first = messages[0]
                content = getattr(first, "content", None)
                txt = getattr(content, "text", "") if content else ""
            ok = bool(txt)
            results.append({"name": f"prompt {prompt_name}", "status": "success" if ok else "fail"})
            print(_ok(f"prompt {prompt_name}", "success" if ok else "fail", f"{len(txt)} bytes"))
        except Exception as exc:
            results.append({"name": f"prompt {prompt_name}", "status": "fail"})
            print(_ok(f"prompt {prompt_name}", "fail", repr(exc)))
    return results


async def _run_cases(
    client: Client, cases: list[tuple[str, dict[str, Any]]]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name, kwargs in cases:
        try:
            res = await client.call_tool(name, kwargs)
            data = getattr(res, "structured_content", None) or getattr(res, "data", None)
            if data is None and getattr(res, "content", None):
                first = res.content[0]
                text = getattr(first, "text", None)
                if text:
                    try:
                        data = json.loads(text)
                    except Exception:
                        data = {"raw": text}
            status = data.get("status", "unknown") if isinstance(data, dict) else "unknown"
            if status == "success":
                detail = _summarise(data)
                print(_ok(name, "success", detail))
                out.append({"name": name, "status": "success"})
            elif status == "error":
                err = data.get("error", "")
                print(_ok(name, "warn", _short(err, 160)))
                out.append({"name": name, "status": "warn", "error": err})
            else:
                print(_ok(name, "warn", _short(data, 160)))
                out.append({"name": name, "status": "warn"})
        except Exception as exc:
            print(_ok(name, "fail", repr(exc)))
            out.append({"name": name, "status": "fail", "error": repr(exc)})
    return out


def _summarise(data: dict[str, Any]) -> str:
    summary_keys = (
        "count",
        "object_types",
        "services",
        "templates",
        "entities",
        "entity_types",
        "kpi_base_searches",
        "threshold_templates",
        "glass_tables",
        "home_views",
        "deep_dives",
        "teams",
        "notable_events",
        "aggregation_policies",
        "correlation_searches",
        "maintenance_windows",
        "docs",
        "hits",
        "identifier",
        "informational",
    )
    parts: list[str] = []
    if "count" in data:
        parts.append(f"count={data['count']}")
    for k in summary_keys:
        if k == "count":
            continue
        v = data.get(k)
        if isinstance(v, list):
            parts.append(f"{k}[{len(v)}]")
        elif isinstance(v, str):
            parts.append(f"{k}={textwrap.shorten(v, 60)}")
    return ", ".join(parts) or "ok"


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
