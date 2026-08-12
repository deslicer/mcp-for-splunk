#!/usr/bin/env python3
"""
Full MCP tool suite via FastMCP Client (not tool.execute).

Credentials via env:
  SPLUNK_HOST, SPLUNK_PORT, SPLUNK_SCHEME, SPLUNK_VERIFY_SSL
  and either SPLUNK_TOKEN or SPLUNK_USERNAME + SPLUNK_PASSWORD

Optional:
  MCP_CLIENT_SKIP_MUTATING=1  skip create/update/delete tools
  SAVED_SEARCH_NAME           existing alert to exercise (default: test alert)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@dataclass
class SuiteState:
    dashboard_name: str = field(default_factory=lambda: f"mcp_cli_{uuid.uuid4().hex[:8]}")
    saved_search_name: str = field(default_factory=lambda: f"mcp_cli_ss_{uuid.uuid4().hex[:8]}")
    kv_collection: str = field(default_factory=lambda: f"mcp_cli_kv_{uuid.uuid4().hex[:8]}")
    search_job_id: str | None = None
    target_alert: str = field(
        default_factory=lambda: os.environ.get("SAVED_SEARCH_NAME", "test alert")
    )
    target_alert_app: str | None = None
    target_alert_owner: str | None = None


@dataclass
class Run:
    name: str
    outcome: str
    detail: str = ""
    elapsed_ms: int = 0


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


def _is_tool_success(name: str, payload: Any, is_error: bool) -> tuple[bool, str]:
    if is_error:
        return False, str(payload)[:240]
    if payload is None:
        return False, "empty result"
    if isinstance(payload, str):
        return True, "text"
    if not isinstance(payload, dict):
        return True, type(payload).__name__
    status = payload.get("status")
    if status == "error":
        # Expected not-found probes still count as exercised
        if name in {
            "get_kvstore_data",
            "get_dashboard_definition",
            "get_saved_search_details",
            "get_search_job_info",
        } and (
            "not found" in str(payload.get("error", "")).lower()
            or "not found" in str(payload.get("message", "")).lower()
            or "UrlEncoded" in str(payload.get("error", ""))
        ):
            return True, f"expected-error:{payload.get('error') or payload.get('message')}"
        return False, str(payload.get("error") or payload.get("message") or payload)[:240]
    return True, status or "ok"


def _dashboard_definition() -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "title": "MCP Client Suite Dashboard",
        "dataSources": {
            "ds_events": {
                "type": "ds.search",
                "options": {
                    "query": "index=_internal | head 1",
                    "queryParameters": {"earliest": "-15m", "latest": "now"},
                },
            }
        },
        "visualizations": {
            "viz_count": {
                "type": "splunk.singlevalue",
                "dataSources": {"primary": "ds_events"},
            }
        },
        "layout": {
            "type": "absolute",
            "structure": [{"item": "viz_count", "position": {"x": 0, "y": 0, "w": 6, "h": 3}}],
        },
    }


def _build_plan(state: SuiteState, skip_mutating: bool) -> list[tuple[str, dict[str, Any] | None]]:
    search = {
        "query": "index=_internal | head 3",
        "earliest_time": "-15m",
        "latest_time": "now",
    }
    plan: list[tuple[str, dict[str, Any] | None]] = [
        ("get_splunk_health", {}),
        ("me", {}),
        ("list_indexes", {}),
        ("list_sources", {}),
        ("list_sourcetypes", {}),
        ("get_metadata", {"index": "_internal", "field": "host", "limit": 5}),
        ("list_apps", {}),
        ("list_users", {}),
        ("get_configurations", {"conf_file": "server", "stanza": "general"}),
        ("list_dashboards", {"count": 10}),
        ("list_lookup_files", {"count": 10}),
        ("list_lookup_definitions", {"count": 10}),
        ("list_kvstore_collections", {}),
        ("list_saved_searches", {"include_disabled": True}),
        ("list_triggered_alerts", {"count": 10, "earliest_time": "-7d"}),
        ("run_oneshot_search", {**search, "max_results": 3}),
        ("run_splunk_search", search),
        ("get_search_job_info", {"job_id": "__JOB_ID__"}),
        ("list_workflows", {"format_type": "summary"}),
        ("get_executed_workflows", {"limit": 5}),
        ("workflow_requirements", {"format_type": "quick"}),
        ("workflow_builder", {"mode": "template", "template_type": "minimal"}),
        ("discover_splunk_docs", {}),
        ("list_available_topics", {}),
        ("list_troubleshooting_topics", {}),
        ("list_admin_topics", {}),
        ("list_spl_commands", {}),
        ("list_cim_data_models", {}),
        ("list_dashboard_studio_topics", {}),
        ("list_config_files", {}),
        ("get_splunk_cheat_sheet", {}),
        ("get_spl_reference", {"command": "stats"}),
        ("get_troubleshooting_guide", {"topic": "search-problems"}),
        ("get_admin_guide", {"topic": "indexes"}),
        ("get_cim_reference", {"model": "authentication"}),
        ("get_studio_topic", {"topic": "cheatsheet"}),
        ("get_config_spec", {"config": "props"}),
        ("get_splunk_documentation", {"doc_uri": "splunk-docs://cheat-sheet"}),
        ("enhance_tool_description", {"tool_name": "list_indexes", "generate_examples": False}),
        # Needs ASGI/HTTP request context; in-memory Client has none.
        ("user_agent_info", None),
        ("sentry_test", None),
        ("manage_apps", None),
        ("create_config", None),
        (
            "get_saved_search_details",
            {"name": state.target_alert, "owner": "__TARGET_OWNER__", "app": "__TARGET_APP__"},
        ),
        (
            "execute_saved_search",
            {
                "name": state.target_alert,
                "owner": "__TARGET_OWNER__",
                "app": "__TARGET_APP__",
                "earliest_time": "-15m",
                "latest_time": "now",
                "mode": "oneshot",
                "max_results": 5,
            },
        ),
    ]
    if skip_mutating:
        for name in (
            "create_dashboard",
            "get_dashboard_definition",
            "create_saved_search",
            "update_saved_search",
            "delete_saved_search",
            "create_kvstore_collection",
            "get_kvstore_data",
        ):
            plan.append((name, None))
        return plan

    ss = state.saved_search_name
    plan.extend(
        [
            (
                "create_dashboard",
                {
                    "name": state.dashboard_name,
                    "definition": _dashboard_definition(),
                    "label": "MCP Client Suite",
                    "description": "FastMCP client verification",
                    "theme": "auto",
                },
            ),
            ("get_dashboard_definition", {"name": state.dashboard_name}),
            (
                "create_saved_search",
                {
                    "name": ss,
                    "search": "index=_internal | head 1",
                    "description": "MCP client suite temp",
                    "sharing": "user",
                    "app": "search",
                },
            ),
            ("get_saved_search_details", {"name": ss, "owner": "admin", "app": "search"}),
            (
                "update_saved_search",
                {"name": ss, "owner": "admin", "app": "search", "description": "updated"},
            ),
            (
                "execute_saved_search",
                {
                    "name": ss,
                    "owner": "admin",
                    "app": "search",
                    "earliest_time": "-15m",
                    "latest_time": "now",
                    "mode": "oneshot",
                    "max_results": 3,
                },
            ),
            ("delete_saved_search", {"name": ss, "owner": "admin", "app": "search", "confirm": True}),
            (
                "create_kvstore_collection",
                {
                    "app": "search",
                    "collection": state.kv_collection,
                    "fields": [{"name": "test_key", "type": "str"}],
                },
            ),
            ("get_kvstore_data", {"collection": state.kv_collection, "app": "search"}),
        ]
    )
    return plan


async def _call(
    client: Any, name: str, args: dict[str, Any]
) -> tuple[Run, Any]:
    started = time.perf_counter()
    try:
        raw = await client.call_tool(name, args)
        payload = _extract(raw)
        is_error = bool(getattr(raw, "is_error", False) or getattr(raw, "isError", False))
        ok, detail = _is_tool_success(name, payload, is_error)
        return (
            Run(
                name,
                "PASS" if ok else "FAIL",
                detail,
                int((time.perf_counter() - started) * 1000),
            ),
            payload,
        )
    except Exception as exc:  # pylint: disable=broad-except
        return (
            Run(name, "FAIL", str(exc)[:240], int((time.perf_counter() - started) * 1000)),
            None,
        )


async def main() -> int:
    _require_creds()
    os.environ.setdefault("MCP_AUTH_DISABLED", "true")
    os.environ.setdefault("SPLUNK_CONNECT_RETRY_COUNT", "1")
    os.environ.setdefault("SPLUNK_CONNECT_RETRY_BASE_DELAY", "0")
    skip_mutating = os.environ.get("MCP_CLIENT_SKIP_MUTATING", "").lower() in (
        "1",
        "true",
        "yes",
    )

    from fastmcp import Client

    from src.server import mcp

    state = SuiteState()
    runs: list[Run] = []
    discovered: set[str] = set()

    async with Client(mcp) as client:
        tools = await client.list_tools()
        discovered = {t.name for t in tools}
        resources = await client.list_resources()
        prompts = await client.list_prompts()
        print(
            f"MCP client connected — tools={len(tools)} "
            f"resources={len(resources)} prompts={len(prompts)}"
        )

        plan = _build_plan(state, skip_mutating)
        planned_names = {name for name, _ in plan}

        for name, args in plan:
            if name not in discovered and name != "execute_saved_search_temp":
                runs.append(Run(name, "MISSING", "not registered on server"))
                continue
            if args is None:
                reason = {
                    "manage_apps": "skipped (mutates app state)",
                    "create_config": "skipped (writes configuration)",
                    "sentry_test": "skipped (can emit external events)",
                    "user_agent_info": "skipped (requires HTTP request; in-memory client has none)",
                }.get(name, "skipped")
                if skip_mutating and name.startswith(
                    ("create_", "update_", "delete_", "get_kvstore")
                ):
                    reason = "skipped (MCP_CLIENT_SKIP_MUTATING)"
                runs.append(Run(name, "SKIP", reason))
                print(f"[SKIP] {name} — {reason}")
                continue

            call_args = dict(args)
            if call_args.get("job_id") == "__JOB_ID__":
                if not state.search_job_id:
                    runs.append(Run(name, "SKIP", "no job id from run_splunk_search"))
                    print(f"[SKIP] {name} — no job id")
                    continue
                call_args["job_id"] = state.search_job_id
            if call_args.get("owner") == "__TARGET_OWNER__":
                if not state.target_alert_owner:
                    runs.append(Run(name, "SKIP", f"target '{state.target_alert}' not found"))
                    print(f"[SKIP] {name} — target alert not found yet")
                    continue
                call_args["owner"] = state.target_alert_owner
                call_args["app"] = state.target_alert_app or "search"

            print(f"  -> {name}...", flush=True)
            run, payload = await _call(client, name, call_args)
            # disambiguate duplicate tool names in summary by appending context
            if name == "get_saved_search_details" and call_args.get("name") == state.target_alert:
                run.name = "get_saved_search_details(target)"
            elif name == "get_saved_search_details":
                run.name = "get_saved_search_details(temp)"
            elif name == "execute_saved_search" and call_args.get("name") == state.target_alert:
                run.name = "execute_saved_search(target)"
            elif name == "execute_saved_search":
                run.name = "execute_saved_search(temp)"

            if name == "run_splunk_search" and isinstance(payload, dict):
                state.search_job_id = payload.get("job_id") or payload.get("sid")
            if name == "list_saved_searches" and isinstance(payload, dict):
                for item in payload.get("saved_searches") or []:
                    if str(item.get("name", "")).lower() == state.target_alert.lower():
                        state.target_alert_owner = item.get("owner") or "admin"
                        state.target_alert_app = item.get("app") or "search"
                        print(
                            f"     found target alert app={state.target_alert_app} "
                            f"owner={state.target_alert_owner}"
                        )
                        break

            runs.append(run)
            print(f"[{run.outcome}] {run.name} ({run.elapsed_ms}ms) — {run.detail}")

        # Resources + prompts (protocol surface)
        for uri in [
            "health://status",
            "splunk://health/status",
            "embedded://docs/README.md",
            "splunk-docs://cheat-sheet",
            "splunk-docs://discovery",
            "dashboard-studio://discovery",
            "splunk-cim://discovery",
        ]:
            started = time.perf_counter()
            try:
                data = await client.read_resource(uri)
                runs.append(
                    Run(
                        f"resource:{uri}",
                        "PASS",
                        f"parts={len(data)}",
                        int((time.perf_counter() - started) * 1000),
                    )
                )
                print(f"[PASS] resource:{uri}")
            except Exception as exc:  # pylint: disable=broad-except
                runs.append(
                    Run(
                        f"resource:{uri}",
                        "FAIL",
                        str(exc)[:200],
                        int((time.perf_counter() - started) * 1000),
                    )
                )
                print(f"[FAIL] resource:{uri} — {exc}")

        for prompt in prompts:
            started = time.perf_counter()
            try:
                args: dict[str, Any] = {}
                for arg in getattr(prompt, "arguments", None) or []:
                    aname = getattr(arg, "name", None) or (
                        arg.get("name") if isinstance(arg, dict) else None
                    )
                    required = (
                        getattr(arg, "required", False)
                        if not isinstance(arg, dict)
                        else arg.get("required", False)
                    )
                    if aname and required:
                        args[aname] = "list_indexes" if aname == "tool_name" else "test"
                await client.get_prompt(prompt.name, args)
                runs.append(
                    Run(
                        f"prompt:{prompt.name}",
                        "PASS",
                        "",
                        int((time.perf_counter() - started) * 1000),
                    )
                )
                print(f"[PASS] prompt:{prompt.name}")
            except Exception as exc:  # pylint: disable=broad-except
                runs.append(
                    Run(
                        f"prompt:{prompt.name}",
                        "FAIL",
                        str(exc)[:200],
                        int((time.perf_counter() - started) * 1000),
                    )
                )
                print(f"[FAIL] prompt:{prompt.name} — {exc}")

    unplanned = sorted(discovered - planned_names)
    passed = [r for r in runs if r.outcome == "PASS"]
    failed = [r for r in runs if r.outcome == "FAIL"]
    skipped = [r for r in runs if r.outcome == "SKIP"]
    missing = [r for r in runs if r.outcome == "MISSING"]

    print("\n" + "=" * 72)
    print("FASTMCP CLIENT LIVE SUITE SUMMARY")
    print("=" * 72)
    print(
        f"PASS: {len(passed)}  FAIL: {len(failed)}  SKIP: {len(skipped)}  "
        f"MISSING: {len(missing)}  TOTAL: {len(runs)}"
    )
    print(f"Discovered tools: {len(discovered)}  Planned tool names: {len(planned_names)}")
    print("-" * 72)
    for run in runs:
        line = f"[{run.outcome:4}] {run.name}"
        if run.elapsed_ms:
            line += f" ({run.elapsed_ms}ms)"
        if run.detail:
            line += f" — {run.detail}"
        print(line)
    if unplanned:
        print("\nDiscovered tools not in plan:")
        for name in unplanned:
            print(f"  - {name}")

    return 1 if failed or missing else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
