#!/usr/bin/env python3
"""
Exercise saved-search tools through a real FastMCP Client (not tool.execute).

Credentials via env (never hard-coded):
  SPLUNK_HOST, SPLUNK_PORT, SPLUNK_SCHEME, SPLUNK_VERIFY_SSL
  and either SPLUNK_TOKEN or SPLUNK_USERNAME + SPLUNK_PASSWORD

Optional:
  SAVED_SEARCH_NAME  Name to find (default: "test alert")
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from typing import Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _require_creds() -> None:
    host = os.environ.get("SPLUNK_HOST", "").strip()
    if not host:
        raise SystemExit("SPLUNK_HOST is required")
    token = os.environ.get("SPLUNK_TOKEN", "").strip()
    user = os.environ.get("SPLUNK_USERNAME", "").strip()
    password = os.environ.get("SPLUNK_PASSWORD", "")
    if not token and not (user and password):
        raise SystemExit("Provide SPLUNK_TOKEN or SPLUNK_USERNAME+SPLUNK_PASSWORD")


def _extract(result: Any) -> Any:
    if hasattr(result, "data") and result.data is not None:
        return result.data
    if hasattr(result, "structured_content") and result.structured_content is not None:
        return result.structured_content
    content = getattr(result, "content", None) or []
    texts = [getattr(c, "text", None) for c in content if getattr(c, "text", None)]
    if not texts:
        return None
    try:
        return json.loads(texts[0])
    except Exception:
        return texts[0]


async def _call(client: Any, name: str, args: dict[str, Any] | None = None) -> Any:
    started = time.perf_counter()
    raw = await client.call_tool(name, args or {})
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    payload = _extract(raw)
    is_error = bool(getattr(raw, "is_error", False) or getattr(raw, "isError", False))
    status = "FAIL" if is_error else "PASS"
    if isinstance(payload, dict) and payload.get("status") == "error" and not is_error:
        # Tool returned structured error without raising
        status = "FAIL"
    print(f"[{status}] {name} ({elapsed_ms}ms)")
    return payload, status, elapsed_ms


def _name_matches(candidate: str, target: str) -> bool:
    return candidate.strip().lower() == target.strip().lower()


async def main() -> int:
    _require_creds()
    os.environ.setdefault("MCP_AUTH_DISABLED", "true")
    os.environ.setdefault("SPLUNK_CONNECT_RETRY_COUNT", "1")
    os.environ.setdefault("SPLUNK_CONNECT_RETRY_BASE_DELAY", "0")

    target_name = os.environ.get("SAVED_SEARCH_NAME", "test alert")
    temp_name = f"mcp_client_ss_{uuid.uuid4().hex[:8]}"

    from fastmcp import Client

    from src.server import mcp

    outcomes: list[tuple[str, str, str]] = []
    found: dict[str, Any] | None = None

    async with Client(mcp) as client:
        print("MCP client connected (in-memory transport → live Splunk via server env)")
        tools = await client.list_tools()
        tool_names = {t.name for t in tools}
        required = {
            "list_saved_searches",
            "get_saved_search_details",
            "execute_saved_search",
            "create_saved_search",
            "update_saved_search",
            "delete_saved_search",
            "list_triggered_alerts",
        }
        missing = sorted(required - tool_names)
        if missing:
            print(f"Missing tools on server: {missing}")
            return 1

        # 1) Discover target via list_saved_searches (client path)
        payload, status, _ = await _call(
            client, "list_saved_searches", {"include_disabled": True}
        )
        outcomes.append(("list_saved_searches", status, ""))
        if not isinstance(payload, dict) or payload.get("status") == "error":
            print("list_saved_searches failed:", payload)
            return 1

        searches = payload.get("saved_searches") or []
        matches = [s for s in searches if _name_matches(str(s.get("name", "")), target_name)]
        if not matches:
            soft = [
                s
                for s in searches
                if target_name.lower() in str(s.get("name", "")).lower()
            ]
            print(
                f"Exact match for '{target_name}' not found among {len(searches)} "
                f"saved searches; substring hits={len(soft)}"
            )
            for s in soft[:10]:
                print(f"  - {s.get('name')} (owner={s.get('owner')} app={s.get('app')})")
            outcomes.append(("find_target_saved_search", "FAIL", "not found"))
        else:
            found = matches[0]
            print(
                f"Found saved search '{found.get('name')}' "
                f"(owner={found.get('owner')} app={found.get('app')} "
                f"scheduled={found.get('is_scheduled')} disabled={found.get('disabled')})"
            )
            outcomes.append(("find_target_saved_search", "PASS", found.get("name", "")))

        # Also try filtered list by owner when we already know admin owns it
        filtered, st, _ = await _call(
            client,
            "list_saved_searches",
            {"include_disabled": True, "owner": "admin"},
        )
        outcomes.append(("list_saved_searches(owner=admin)", st, ""))
        if isinstance(filtered, dict):
            admin_hits = [
                s
                for s in (filtered.get("saved_searches") or [])
                if _name_matches(str(s.get("name", "")), target_name)
            ]
            print(f"owner=admin filter hits for '{target_name}': {len(admin_hits)}")

        # 2) Also probe fired-alerts feed for the same name
        alerts_payload, alerts_status, _ = await _call(
            client,
            "list_triggered_alerts",
            {"count": 50, "search": target_name, "earliest_time": "-30d"},
        )
        outcomes.append(("list_triggered_alerts", alerts_status, ""))
        if isinstance(alerts_payload, dict):
            groups = alerts_payload.get("triggered_alerts") or []
            print(f"Triggered alert groups matching filter: {len(groups)}")
            for g in groups[:5]:
                print(
                    f"  - group={g.get('name') or g.get('alert_name')} "
                    f"count={g.get('count')}"
                )

        if found:
            owner = found.get("owner") or "admin"
            app = found.get("app") or "search"
            name = found["name"]

            details, st, _ = await _call(
                client,
                "get_saved_search_details",
                {"name": name, "owner": owner, "app": app},
            )
            outcomes.append(("get_saved_search_details(target)", st, ""))
            if isinstance(details, dict):
                print(
                    "Details keys:",
                    sorted(k for k in details.keys() if k != "status")[:12],
                )

            exec_payload, st, _ = await _call(
                client,
                "execute_saved_search",
                {
                    "name": name,
                    "owner": owner,
                    "app": app,
                    "earliest_time": "-15m",
                    "latest_time": "now",
                    "mode": "oneshot",
                    "max_results": 5,
                },
            )
            outcomes.append(("execute_saved_search(target)", st, ""))
            if isinstance(exec_payload, dict):
                results = exec_payload.get("results") or []
                print(
                    f"Execute target: status={exec_payload.get('status')} "
                    f"result_rows={len(results)}"
                )

        # 3) Full CRUD lifecycle via client for a temp saved search
        create_payload, st, _ = await _call(
            client,
            "create_saved_search",
            {
                "name": temp_name,
                "search": "index=_internal | head 1",
                "description": "MCP client live test saved search",
                "sharing": "user",
                "app": "search",
            },
        )
        outcomes.append(("create_saved_search", st, temp_name))
        if st != "PASS":
            print("create_saved_search failed:", create_payload)
        else:
            details, st, _ = await _call(
                client,
                "get_saved_search_details",
                {"name": temp_name, "owner": "admin", "app": "search"},
            )
            outcomes.append(("get_saved_search_details(temp)", st, ""))

            update_payload, st, _ = await _call(
                client,
                "update_saved_search",
                {
                    "name": temp_name,
                    "owner": "admin",
                    "app": "search",
                    "description": "MCP client live test saved search (updated)",
                },
            )
            outcomes.append(("update_saved_search", st, ""))
            if isinstance(update_payload, dict):
                print("Update status:", update_payload.get("status"))

            exec_temp, st, _ = await _call(
                client,
                "execute_saved_search",
                {
                    "name": temp_name,
                    "owner": "admin",
                    "app": "search",
                    "earliest_time": "-15m",
                    "latest_time": "now",
                    "mode": "oneshot",
                    "max_results": 3,
                },
            )
            outcomes.append(("execute_saved_search(temp)", st, ""))
            if isinstance(exec_temp, dict):
                print(
                    f"Execute temp: status={exec_temp.get('status')} "
                    f"rows={len(exec_temp.get('results') or [])}"
                )

            delete_payload, st, _ = await _call(
                client,
                "delete_saved_search",
                {
                    "name": temp_name,
                    "owner": "admin",
                    "app": "search",
                    "confirm": True,
                },
            )
            outcomes.append(("delete_saved_search", st, ""))
            if isinstance(delete_payload, dict):
                print("Delete status:", delete_payload.get("status"))

    print("\n" + "=" * 72)
    print("SAVED SEARCH MCP CLIENT SUMMARY")
    print("=" * 72)
    failed = [o for o in outcomes if o[1] == "FAIL"]
    passed = [o for o in outcomes if o[1] == "PASS"]
    print(f"PASS: {len(passed)}  FAIL: {len(failed)}  TOTAL: {len(outcomes)}")
    for name, status, detail in outcomes:
        line = f"[{status:4}] {name}"
        if detail:
            line += f" — {detail}"
        print(line)

    if any(o[0] == "find_target_saved_search" and o[1] == "FAIL" for o in outcomes):
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
