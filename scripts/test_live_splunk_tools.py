#!/usr/bin/env python3
"""
Live Splunk tool smoke test.

Exercises registered MCP tools against a real Splunk instance. Credentials must
be supplied via environment variables (never hard-coded):

  SPLUNK_HOST, SPLUNK_PORT, SPLUNK_USERNAME, SPLUNK_PASSWORD,
  SPLUNK_SCHEME, SPLUNK_VERIFY_SSL
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
from unittest.mock import AsyncMock, Mock
from urllib.parse import urlparse

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _normalize_host(raw_host: str) -> str:
    value = raw_host.strip()
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        return parsed.hostname or value
    return value


def _splunk_env_config() -> dict[str, Any]:
    host = _normalize_host(os.environ.get("SPLUNK_HOST", ""))
    if not host:
        raise SystemExit("SPLUNK_HOST is required")

    password = os.environ.get("SPLUNK_PASSWORD")
    username = os.environ.get("SPLUNK_USERNAME")
    if not username or not password:
        raise SystemExit("SPLUNK_USERNAME and SPLUNK_PASSWORD are required")

    return {
        "splunk_host": host,
        "splunk_port": int(os.environ.get("SPLUNK_PORT", "8089")),
        "splunk_username": username,
        "splunk_password": password,
        "splunk_scheme": os.environ.get("SPLUNK_SCHEME", "https"),
        "splunk_verify_ssl": os.environ.get("SPLUNK_VERIFY_SSL", "false").lower()
        in ("true", "1", "yes"),
    }


class LiveSplunkContext:
    """Minimal FastMCP-like context wired to a live Splunk service."""

    def __init__(self, service: Any) -> None:
        self.request_context = Mock()
        self.request_context.lifespan_context = Mock()
        self.request_context.lifespan_context.service = service
        self.request_context.lifespan_context.is_connected = True
        self.info = AsyncMock()
        self.debug = AsyncMock()
        self.warning = AsyncMock()
        self.error = AsyncMock()
        self.report_progress = AsyncMock()
        self.read_resource = AsyncMock()
        self.sample = AsyncMock()
        self.request_id = "live-test"
        self.client_id = "live-test"
        self.session_id = "live-test"


@dataclass
class LiveTestState:
    dashboard_name: str = field(default_factory=lambda: f"mcp_live_{uuid.uuid4().hex[:8]}")
    saved_search_name: str = field(default_factory=lambda: f"mcp_live_ss_{uuid.uuid4().hex[:8]}")
    kv_collection: str = field(default_factory=lambda: f"mcp_live_kv_{uuid.uuid4().hex[:8]}")
    search_job_id: str | None = None
    first_dashboard_name: str | None = None


def _is_success(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    status = result.get("status")
    if status == "success":
        return True
    if status == "error":
        return False
    # Some tools return payload without explicit status
    return "error" not in result


@dataclass
class ToolRun:
    name: str
    outcome: str
    detail: str = ""
    elapsed_ms: int = 0


async def _run_tool(
    registry: Any,
    ctx: LiveSplunkContext,
    name: str,
    args: dict[str, Any],
    state: LiveTestState,
) -> ToolRun:
    tool = registry.get_tool(name)
    if tool is None:
        return ToolRun(name, "MISSING", "Tool not registered")

    started = time.perf_counter()
    try:
        result = await tool.execute(ctx, **args)
        elapsed = int((time.perf_counter() - started) * 1000)
        if _is_success(result):
            _update_state_from_result(name, result, state)
            return ToolRun(name, "PASS", elapsed_ms=elapsed)
        error = result.get("error") or result.get("message") or json.dumps(result)[:200]
        return ToolRun(name, "FAIL", str(error)[:300], elapsed)
    except Exception as exc:  # pylint: disable=broad-except
        elapsed = int((time.perf_counter() - started) * 1000)
        return ToolRun(name, "FAIL", str(exc)[:300], elapsed)


def _update_state_from_result(name: str, result: dict[str, Any], state: LiveTestState) -> None:
    if name == "run_splunk_search":
        state.search_job_id = result.get("job_id") or result.get("sid")
    if name == "list_dashboards" and not state.first_dashboard_name:
        dashboards = result.get("dashboards") or []
        if dashboards:
            state.first_dashboard_name = dashboards[0].get("name")
    if name == "create_dashboard":
        state.dashboard_name = result.get("name", state.dashboard_name)


def _tool_plan(state: LiveTestState) -> list[tuple[str, dict[str, Any] | None]]:
    """Return (tool_name, args). None args means invoke with defaults only."""
    return [
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
        (
            "create_dashboard",
            {
                "name": state.dashboard_name,
                "definition": {
                    "version": "1.0.0",
                    "title": "MCP Live Test Dashboard",
                    "uiSettings": {"theme": "dark"},
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
                            "title": "Events",
                            "dataSources": {"primary": "ds_events"},
                            "options": {"majorValue": {"field": "_serial"}},
                        }
                    },
                    "layout": {
                        "type": "absolute",
                        "structure": [
                            {"item": "viz_count", "position": {"x": 0, "y": 0, "w": 6, "h": 3}}
                        ],
                    },
                },
                "label": "MCP Live Test",
                "description": "Automated live tool verification",
                "theme": "auto",
            },
        ),
        (
            "get_dashboard_definition",
            {"name": state.dashboard_name},
        ),
        ("list_lookup_files", {"count": 10}),
        ("list_lookup_definitions", {"count": 10}),
        ("list_kvstore_collections", {}),
        ("list_saved_searches", {"include_disabled": True}),
        (
            "create_saved_search",
            {
                "name": state.saved_search_name,
                "search": "index=_internal | head 1",
                "description": "MCP live test saved search",
                "sharing": "user",
            },
        ),
        ("get_saved_search_details", {"name": state.saved_search_name, "owner": "admin"}),
        (
            "execute_saved_search",
            {
                "name": state.saved_search_name,
                "owner": "admin",
                "earliest_time": "-15m",
                "latest_time": "now",
            },
        ),
        (
            "update_saved_search",
            {
                "name": state.saved_search_name,
                "owner": "admin",
                "description": "MCP live test saved search (updated)",
            },
        ),
        (
            "run_oneshot_search",
            {
                "query": "index=_internal | head 3",
                "earliest_time": "-15m",
                "latest_time": "now",
                "max_results": 3,
            },
        ),
        (
            "run_splunk_search",
            {
                "query": "index=_internal | head 3",
                "earliest_time": "-15m",
                "latest_time": "now",
            },
        ),
        ("get_search_job_info", {"job_id": "__JOB_ID__"}),
        ("list_triggered_alerts", {"count": 5}),
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
        ("delete_saved_search", {"name": state.saved_search_name, "owner": "admin", "confirm": True}),
        (
            "create_kvstore_collection",
            {
                "app": "search",
                "collection": state.kv_collection,
                "fields": [{"name": "test_key", "type": "str"}],
            },
        ),
        (
            "get_kvstore_data",
            {"collection": state.kv_collection, "app": "search"},
        ),
        ("manage_apps", None),  # skipped – mutates app state
        ("create_config", None),  # skipped – writes conf files
        ("workflow_runner", None),  # skipped unless OPENAI_API_KEY set
    ]


async def main() -> int:
    config = _splunk_env_config()

    from src.client.splunk_client import get_splunk_service
    from src.core.discovery import discover_tools
    from src.core.registry import tool_registry

    print("Connecting to Splunk...")
    service = get_splunk_service(config)
    print(f"Connected to {config['splunk_scheme']}://{config['splunk_host']}:{config['splunk_port']}")

    discover_tools()
    ctx = LiveSplunkContext(service)
    state = LiveTestState()

    runs: list[ToolRun] = []
    for tool_name, args in _tool_plan(state):
        if args is None:
            if tool_name == "workflow_runner":
                api_key = os.environ.get("OPENAI_API_KEY", "")
                if api_key and "your_ope" not in api_key.lower() and api_key.startswith("sk-"):
                    args = {
                        "workflow_id": "missing_data_troubleshooting",
                        "problem_description": "Live MCP smoke test",
                        "focus_index": "_internal",
                    }
                else:
                    runs.append(
                        ToolRun(
                            tool_name,
                            "SKIP",
                            "skipped (requires valid OPENAI_API_KEY for agent execution)",
                        )
                    )
                    continue
            else:
                reason = {
                    "manage_apps": "skipped (mutates app state on live instance)",
                    "create_config": "skipped (writes configuration files)",
                }.get(tool_name, "skipped")
                runs.append(ToolRun(tool_name, "SKIP", reason))
                continue

        if tool_name == "get_search_job_info":
            if not state.search_job_id:
                runs.append(ToolRun(tool_name, "SKIP", "no search job id from run_splunk_search"))
                continue
            args = {"job_id": state.search_job_id}

        if tool_name == "get_dashboard_definition" and args.get("name") == state.dashboard_name:
            pass  # uses freshly created dashboard
        elif tool_name == "get_dashboard_definition" and state.first_dashboard_name:
            args = {"name": state.first_dashboard_name}

        print(f"  -> {tool_name}...", flush=True)
        runs.append(await _run_tool(tool_registry, ctx, tool_name, args, state))

    passed = [r for r in runs if r.outcome == "PASS"]
    failed = [r for r in runs if r.outcome == "FAIL"]
    skipped = [r for r in runs if r.outcome == "SKIP"]

    print("\n" + "=" * 72)
    print("LIVE SPLUNK TOOL TEST SUMMARY")
    print("=" * 72)
    print(f"PASS: {len(passed)}  FAIL: {len(failed)}  SKIP: {len(skipped)}  TOTAL: {len(runs)}")
    print("-" * 72)

    for run in runs:
        timing = f" ({run.elapsed_ms}ms)" if run.elapsed_ms else ""
        line = f"[{run.outcome:4}] {run.name}{timing}"
        if run.detail:
            line += f" — {run.detail}"
        print(line)

    if failed:
        print("\nFailed tools need attention before merge.")
        return 1

    print("\nAll executed tools passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
