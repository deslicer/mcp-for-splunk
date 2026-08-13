#!/usr/bin/env python3
"""
Exercise alert tools through a real FastMCP Client (not tool.execute).

Credentials via env (never hard-coded):
  SPLUNK_HOST, SPLUNK_PORT, SPLUNK_SCHEME, SPLUNK_VERIFY_SSL
  and either SPLUNK_TOKEN or SPLUNK_USERNAME + SPLUNK_PASSWORD
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
    if not os.environ.get("SPLUNK_HOST", "").strip():
        raise SystemExit("SPLUNK_HOST is required")
    token = os.environ.get("SPLUNK_TOKEN", "").strip()
    user = os.environ.get("SPLUNK_USERNAME", "").strip()
    password = os.environ.get("SPLUNK_PASSWORD", "")
    if not token and not (user and password):
        raise SystemExit("Provide SPLUNK_TOKEN or SPLUNK_USERNAME+SPLUNK_PASSWORD")


def _extract(result: Any) -> Any:
    if getattr(result, "data", None) is not None:
        return result.data
    if getattr(result, "structured_content", None) is not None:
        return result.structured_content
    texts = [
        getattr(c, "text", None)
        for c in (getattr(result, "content", None) or [])
        if getattr(c, "text", None)
    ]
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
        status = "FAIL"
    print(f"[{status}] {name} ({elapsed_ms}ms)")
    if status == "FAIL":
        print(f"      {payload}")
    return payload, status


def _ok(payload: Any) -> bool:
    return isinstance(payload, dict) and payload.get("status") == "success"


async def main() -> int:
    _require_creds()
    os.environ.setdefault("MCP_AUTH_DISABLED", "true")
    os.environ.setdefault("SPLUNK_CONNECT_RETRY_COUNT", "1")
    os.environ.setdefault("SPLUNK_CONNECT_RETRY_BASE_DELAY", "0")

    temp_name = f"mcp_cli_alert_{uuid.uuid4().hex[:8]}"
    outcomes: list[tuple[str, str]] = []

    from fastmcp import Client

    from src.server import mcp

    async with Client(mcp) as client:
        print("MCP client connected (in-memory transport → live Splunk via server env)")
        tools = await client.list_tools()
        tool_names = {t.name for t in tools}
        required = {
            "list_alert_actions",
            "create_alert",
            "update_alert",
            "delete_alert",
            "get_saved_search_details",
            "list_triggered_alerts",
        }
        missing = sorted(required - tool_names)
        if missing:
            print(f"Missing tools on server: {missing}")
            return 1
        print(f"Alert tools present: {sorted(required)}")

        payload, status = await _call(client, "list_alert_actions")
        outcomes.append(("list_alert_actions", status))
        if not _ok(payload):
            return 1
        action_entries = payload.get("alert_actions") or []
        action_names = [a.get("name") for a in action_entries]
        print(f"      installed actions ({payload.get('count')}): {action_names[:12]}")
        custom = [a for a in action_entries if a.get("is_custom")]
        if custom:
            sample = custom[0]
            print(
                f"      custom sample: {sample.get('name')} "
                f"params={sample.get('param_keys')}"
            )

        create_actions: list[dict[str, Any]] = []
        if "email" in action_names:
            create_actions.append(
                {
                    "name": "email",
                    "params": {
                        "to": "mcp-test@splunk.com",
                        "subject": "MCP alert",
                    },
                }
            )
        if "rss" in action_names:
            create_actions.append({"name": "rss", "params": {}})
        payload, status = await _call(
            client,
            "create_alert",
            {
                "name": temp_name,
                "search": "index=_internal | head 1",
                "description": "MCP client alert probe",
                "cron_schedule": "0 0 1 1 *",
                "earliest_time": "-15m",
                "latest_time": "now",
                "app": "search",
                "sharing": "user",
                "alert_type": "number of events",
                "alert_comparator": "greater than",
                "alert_threshold": "999999",
                "alert_track": True,
                "actions": create_actions,
            },
        )
        outcomes.append(("create_alert", status))
        created = _ok(payload)
        if created:
            print(f"      created {temp_name} actions={create_actions}")

        try:
            if created:
                details, status = await _call(
                    client,
                    "get_saved_search_details",
                    {"name": temp_name, "app": "search"},
                )
                outcomes.append(("get_saved_search_details", status))
                if _ok(details):
                    alert = (details.get("details") or {}).get("alert") or {}
                    print(f"      alert config: {alert}")

                payload, status = await _call(
                    client,
                    "update_alert",
                    {
                        "name": temp_name,
                        "app": "search",
                        "actions_mode": "patch",
                        "description": "MCP client alert probe (patched)",
                        "alert_threshold": "888888",
                    },
                )
                outcomes.append(("update_alert(patch scalars)", status))

                if any(item["name"] == "email" for item in create_actions):
                    payload, status = await _call(
                        client,
                        "update_alert",
                        {
                            "name": temp_name,
                            "app": "search",
                            "actions_mode": "patch",
                            "actions": [
                                {
                                    "name": "email",
                                    "params": {"subject": "MCP alert patched"},
                                }
                            ],
                        },
                    )
                    outcomes.append(("update_alert(patch email.subject)", status))

                if "deslicer_investigate" in action_names:
                    payload, status = await _call(
                        client,
                        "update_alert",
                        {
                            "name": temp_name,
                            "app": "search",
                            "actions_mode": "patch",
                            "actions": [{"name": "deslicer_investigate", "params": {}}],
                        },
                    )
                    outcomes.append(("update_alert(patch custom action)", status))

                payload, status = await _call(
                    client,
                    "update_alert",
                    {
                        "name": temp_name,
                        "app": "search",
                        "actions_mode": "override",
                        "actions": [{"name": "rss", "params": {}}],
                    },
                )
                outcomes.append(("update_alert(override rss only)", status))

            payload, status = await _call(
                client, "list_triggered_alerts", {"count": 5, "earliest_time": "-1h"}
            )
            outcomes.append(("list_triggered_alerts", status))
        finally:
            if created:
                payload, status = await _call(
                    client,
                    "delete_alert",
                    {"name": temp_name, "app": "search", "confirm": True},
                )
                outcomes.append(("delete_alert", status))
            else:
                outcomes.append(("delete_alert", "SKIP"))

    print("\n=== Alert MCP client summary ===")
    failed = 0
    for name, status in outcomes:
        print(f"  {status:4}  {name}")
        if status != "PASS" and status != "SKIP":
            failed += 1
    print(f"Failed: {failed}/{len(outcomes)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
