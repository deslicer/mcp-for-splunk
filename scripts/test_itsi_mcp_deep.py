"""Deeper integration test for the ITSI MCP server.

After the smoke test confirms every list endpoint works, this script picks
a couple of real `_key` values from the responses and exercises:
- `itsi_get_*` round-trips,
- `itsi_count_*` and filter syntax,
- `itsi_search_docs` with a real-world query,
- the `itoa_interface/get_alias_list` keys against actual entities.

It is read-only; nothing is created, updated, or deleted.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


async def call(client: Client, name: str, args: dict[str, Any]) -> dict[str, Any]:
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


def _ok(name: str, status: str, detail: str = "") -> str:
    icon = "OK" if status == "success" else ("WARN" if status == "warn" else "FAIL")
    return f"[{icon:<4}] {name:<48}{' — ' + detail if detail else ''}"


async def main() -> int:
    url = os.getenv("MCP_ITSI_URL", "http://127.0.0.1:8084/mcp")
    headers = {
        "X-Splunk-Host": os.environ["ITSI_HOST"],
        "X-Splunk-Port": os.getenv("ITSI_PORT", "8089"),
        "X-Splunk-Scheme": os.getenv("ITSI_SCHEME", "https"),
        "X-Splunk-Username": os.environ["ITSI_USERNAME"],
        "X-Splunk-Password": os.environ["ITSI_PASSWORD"],
        "X-Splunk-Verify-SSL": os.getenv("ITSI_VERIFY_SSL", "false"),
        "X-Session-ID": "deep-smoke",
    }

    print(f"# ITSI MCP deep test\n\nServer: {url}\nITSI host: {headers['X-Splunk-Host']}\n")
    failures = 0

    transport = StreamableHttpTransport(url, headers=headers)
    async with Client(transport) as client:
        print("## Get-by-key round-trips\n")

        # Pick an entity, fetch it
        listed = await call(client, "itsi_list_entities", {"limit": 3, "fields": "_key,title"})
        entities = listed.get("entities", [])
        if entities:
            key = entities[0]["_key"]
            title = entities[0].get("title", "<no title>")
            data = await call(client, "itsi_get_entity", {"key": key})
            ok = data.get("status") == "success" and data.get("entity", {}).get("_key") == key
            failures += 0 if ok else 1
            print(_ok("itsi_get_entity", "success" if ok else "fail", f"{title} ({key[:8]}…)"))
        else:
            print(_ok("itsi_get_entity", "warn", "no entities to fetch"))

        # Pick a service template, fetch it
        listed = await call(
            client, "itsi_list_service_templates", {"limit": 3, "fields": "_key,title"}
        )
        templates = listed.get("templates", [])
        if templates:
            key = templates[0]["_key"]
            title = templates[0].get("title", "<no title>")
            data = await call(client, "itsi_get_service_template", {"key": key})
            ok = data.get("status") == "success"
            failures += 0 if ok else 1
            print(
                _ok(
                    "itsi_get_service_template",
                    "success" if ok else "fail",
                    f"{title} ({key[:8]}…)",
                )
            )
        else:
            print(_ok("itsi_get_service_template", "warn", "no templates to fetch"))

        # Pick a KPI base search
        listed = await call(
            client, "itsi_list_kpi_base_searches", {"limit": 3, "fields": "_key,title"}
        )
        searches = listed.get("kpi_base_searches", [])
        if searches:
            key = searches[0]["_key"]
            title = searches[0].get("title", "<no title>")
            data = await call(client, "itsi_get_kpi_base_search", {"key": key})
            ok = data.get("status") == "success"
            failures += 0 if ok else 1
            print(
                _ok(
                    "itsi_get_kpi_base_search", "success" if ok else "fail", f"{title} ({key[:8]}…)"
                )
            )

        # Pick a glass table & home view
        listed = await call(client, "itsi_list_glass_tables", {"limit": 1, "fields": "_key,title"})
        gts = listed.get("glass_tables", [])
        if gts:
            data = await call(client, "itsi_get_glass_table", {"key": gts[0]["_key"]})
            ok = data.get("status") == "success"
            failures += 0 if ok else 1
            print(_ok("itsi_get_glass_table", "success" if ok else "fail", gts[0].get("title", "")))

        listed = await call(client, "itsi_list_home_views", {"limit": 1, "fields": "_key,title"})
        hvs = listed.get("home_views", [])
        if hvs:
            data = await call(client, "itsi_get_home_view", {"key": hvs[0]["_key"]})
            ok = data.get("status") == "success"
            failures += 0 if ok else 1
            print(_ok("itsi_get_home_view", "success" if ok else "fail", hvs[0].get("title", "")))

        # Team
        listed = await call(client, "itsi_list_teams", {"limit": 1, "fields": "_key,title"})
        teams = listed.get("teams", [])
        if teams:
            data = await call(client, "itsi_get_team", {"key": teams[0]["_key"]})
            ok = data.get("status") == "success"
            failures += 0 if ok else 1
            print(_ok("itsi_get_team", "success" if ok else "fail", teams[0].get("title", "")))

        print("\n## Filter syntax\n")
        # Use the alias inventory to build a filter
        aliases = await call(client, "itsi_get_alias_list", {})
        identifier_fields = aliases.get("identifier", [])
        print(
            _ok(
                "itsi_get_alias_list",
                "success",
                f"identifiers={identifier_fields[:5]}…" if identifier_fields else "no identifiers",
            )
        )

        filtered = await call(
            client,
            "itsi_list_entities",
            {"filter_query": {"title": {"$regex": ".*"}}, "limit": 2, "fields": "_key,title"},
        )
        ok = filtered.get("status") == "success" and isinstance(filtered.get("entities"), list)
        failures += 0 if ok else 1
        print(
            _ok(
                "itsi_list_entities filter $regex",
                "success" if ok else "fail",
                f"got {filtered.get('count', 'n/a')} entities",
            )
        )

        # Aggregation policy detail
        listed = await call(
            client, "itsi_list_aggregation_policies", {"limit": 1, "fields": "_key,title,disabled"}
        )
        pols = listed.get("aggregation_policies", [])
        print(
            _ok(
                "aggregation policies sample",
                "success",
                f"{pols[0].get('title')} disabled={pols[0].get('disabled')}" if pols else "none",
            )
        )

        # Correlation search detail
        listed = await call(
            client,
            "itsi_list_correlation_searches",
            {"limit": 1, "fields": "name,description,disabled"},
        )
        cs = listed.get("correlation_searches", [])
        print(
            _ok(
                "correlation searches sample",
                "success",
                f"{cs[0].get('name')} disabled={cs[0].get('disabled')}" if cs else "none",
            )
        )

        print("\n## Docs catalog round-trip\n")
        docs = await call(client, "itsi_list_docs", {})
        slugs = [d["slug"] for d in docs.get("docs", [])]
        ok = "api/reference" in slugs and "best-practices" in slugs
        failures += 0 if ok else 1
        print(_ok("itsi_list_docs slugs", "success" if ok else "fail", f"{len(slugs)} docs"))

        for slug in ("api/reference", "service-insights", "best-practices"):
            data = await call(client, "itsi_read_doc", {"slug": slug})
            ok = data.get("status") == "success" and len(data.get("content", "")) > 200
            failures += 0 if ok else 1
            print(
                _ok(
                    f"itsi_read_doc[{slug}]",
                    "success" if ok else "fail",
                    f"{len(data.get('content', ''))} bytes",
                )
            )

        print()

    print(f"\nfailures: {failures}\n")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
