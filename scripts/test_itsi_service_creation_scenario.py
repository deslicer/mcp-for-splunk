"""End-to-end ITSI service creation scenario, driven entirely through MCP tools.

This script walks each step from the official ITSI 4.21 "Create services"
documentation and exercises the matching MCP tool. The goal is two-fold:

    1. Demonstrate that an AI agent can stand up a realistic, hierarchical
       service in ITSI using ONLY the tools shipped by mcp_itsi.
    2. Capture the rough edges that an agent would hit, for follow-up.

Scenario (mirrors the doc's "Web Store" example):

    Web Store               (parent business service)
       └── depends on:  Web Tier
                          ├── depends on:  App Tier
                          │                   └── depends on:  Database Tier
                          └── depends on:  Database Tier

Each service has KPIs, entity rules and (where the docs require it)
service dependencies.

Documented workflow                                     -> MCP tool used
1. Manually add service content (Create a single ...)   -> itsi_create_service
2. Define entity rules                                   -> itsi_update_service
3. Add KPIs (define source search, thresholds, etc.)     -> itsi_update_service
4. Add service dependencies                              -> itsi_update_service

The script does not delete its handiwork by default so you can inspect
the results in the Splunk UI. Pass --cleanup to remove them.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(name: str, status: str, detail: str = "") -> str:
    icon = "OK" if status == "success" else ("WARN" if status == "warn" else "FAIL")
    return f"[{icon:<4}] {name:<46}{' — ' + detail if detail else ''}"


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


def _short(value: Any, limit: int = 220) -> str:
    s = json.dumps(value, default=str) if not isinstance(value, str) else value
    s = s.replace("\n", " ")
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _stop(detail: str) -> None:
    raise RuntimeError(detail)


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------


def _entity_rule(field: str, op: str, value: str, field_type: str = "alias") -> dict:
    return {
        "rule_condition": "AND",
        "rule_items": [{"field": field, "rule_type": op, "value": value, "field_type": field_type}],
    }


def _generic_threshold() -> dict:
    """Minimum viable threshold spec accepted by ITSI for adhoc KPIs."""
    return {
        "isMinStatic": True,
        "gaugeMin": 0,
        "gaugeMax": 100,
        "metricField": "count",
        "renderBoundaryMin": 0,
        "baseSeverityValue": 2,
        "renderBoundaryMax": 100,
        "baseSeverityColor": "#99D18B",
        "search": "",
        "baseSeverityColorLight": "#DCEFD7",
        "baseSeverityLabel": "normal",
        "isMaxStatic": False,
        "thresholdLevels": [
            {
                "severityValue": 6,
                "thresholdValue": 90,
                "severityColorLight": "#E5A6A6",
                "severityColor": "#B50101",
                "severityLabel": "critical",
                "dynamicParam": 0,
            },
            {
                "severityValue": 4,
                "thresholdValue": 70,
                "severityColorLight": "#FEE6C1",
                "severityColor": "#FCB64E",
                "severityLabel": "medium",
                "dynamicParam": 0,
            },
        ],
    }


def _time_variate_thresholds() -> dict:
    return {
        "policies": {
            "default_policy": {
                "title": "Default",
                "policy_type": "static",
                "aggregate_thresholds": _generic_threshold(),
                "entity_thresholds": _generic_threshold(),
                "time_blocks": [],
            }
        },
    }


def _adhoc_kpi(
    title: str,
    base_search: str,
    threshold_field: str,
    *,
    urgency: int = 5,
    is_entity_breakdown: bool = False,
    cron_schedule: str = "*/5 * * * *",
) -> dict:
    """Build the minimum viable ITSI 4.21 KPI document.

    Discovered the hard way: ITSI rejects partial KPI dicts very loudly
    on POST /service. The fields here are the ones the engine actually
    requires.
    """
    return {
        "_key": str(uuid.uuid4()),
        "title": title,
        "type": "kpi",
        "search_type": "adhoc",
        "search_alert_earliest": "5",
        "alert_lag": "30",
        "alert_period": "5",
        "alert_on": "always",
        "base_search": base_search,
        "search": base_search,
        "search_aggregate": base_search,
        "search_entities": base_search,
        "search_buckets": base_search,
        "search_occurrences": "1",
        "is_service_entity_filter": True,
        "is_entity_breakdown": is_entity_breakdown,
        "entity_id_fields": "host",
        "entity_alias_filtering_fields": "",
        "entity_breakdown_id_fields": "host",
        "threshold_field": threshold_field,
        "unit": "",
        "urgency": str(urgency),
        "fill_gaps": "null_value",
        "gap_severity": "unknown",
        "gap_severity_color": "#CCCCCC",
        "gap_severity_color_light": "#EEEEEE",
        "gap_severity_value": -1,
        "aggregate_statop": "avg",
        "entity_statop": "avg",
        "datamodel_filter": [],
        "datamodel": {"object": "", "datamodel": "", "field": "", "owner_field": ""},
        "anomaly_detection_is_enabled": False,
        "anomaly_detection_alerting_enabled": False,
        "adaptive_thresholding_training_window": "-7d",
        "adaptive_thresholds_is_enabled": False,
        "time_variate_thresholds": False,
        "time_variate_thresholds_specification": _time_variate_thresholds(),
        "kpi_threshold_template_id": "",
        "kpi_base_search": "",
        "metric_qualifier": "",
        "tz_offset": None,
        "cron_schedule": cron_schedule,
        "aggregate_thresholds": _generic_threshold(),
        "entity_thresholds": _generic_threshold(),
    }


def _service_payload(
    title: str,
    description: str,
    *,
    kpis: list[dict] | None = None,
    entity_rules: list[dict] | None = None,
    services_depends_on: list[dict] | None = None,
    enabled: int = 1,
    tags: list[str] | None = None,
) -> dict:
    return {
        "title": title,
        "description": description,
        "object_type": "service",
        "kpis": kpis or [],
        "entity_rules": entity_rules or [],
        "services_depends_on": services_depends_on or [],
        "services_depending_on_me": [],
        "enabled": enabled,
        "sec_grp": "default_itsi_security_group",
        "service_tags": {"tags": tags or ["mcp-itsi-scenario"], "template_tags": []},
    }


# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------


class Scenario:
    """Mutable state for the scenario, including discovered IDs."""

    def __init__(self, client: Client, run_id: str) -> None:
        self.client = client
        self.run_id = run_id
        self.created_keys: list[tuple[str, str]] = []  # (tool_name, _key)
        self.observations: list[str] = []
        self.findings: list[dict[str, Any]] = []

    def note(self, severity: str, summary: str, detail: str = "") -> None:
        """Record a critical observation about a tool's behaviour."""
        self.findings.append({"severity": severity, "summary": summary, "detail": detail})
        prefix = {"info": "·", "minor": "•", "major": "‼"}.get(severity, "?")
        self.observations.append(f" {prefix} ({severity}) {summary}")
        if detail:
            self.observations.append(f"     {detail}")

    async def step(self, label: str, fn) -> dict[str, Any]:
        print(f"\n--- {label} ---")
        result = await fn()
        return result

    def remember(self, tool: str, key: str) -> None:
        self.created_keys.append((tool, key))


async def step_prereqs(s: Scenario) -> None:
    teams = await _call(s.client, "itsi_list_teams", {"fields": "_key,title"})
    if teams.get("status") != "success":
        _stop(_short(teams))
    print(_ok("itsi_list_teams", "success", f"{teams.get('count', 0)} teams"))

    aliases = await _call(s.client, "itsi_get_alias_list", {})
    print(
        _ok(
            "itsi_get_alias_list",
            "success",
            f"identifiers={aliases.get('identifier', [])[:5]}",
        )
    )
    if not aliases.get("identifier"):
        s.note(
            "major",
            "alias inventory empty",
            "An agent has no way to validate entity rules without itsi_get_alias_list.",
        )

    # Check that the `host` alias is present, so our entity rules will match
    if "host" not in aliases.get("identifier", []):
        s.note(
            "major",
            "expected `host` alias missing",
            "scenario assumes db-*/login-*/api-* hosts; rules may match nothing",
        )

    # Verify we have entities to attach to
    db_entities = await _call(
        s.client,
        "itsi_list_entities",
        {"filter_query": {"title": {"$regex": "^db-"}}, "limit": 10, "fields": "title"},
    )
    print(
        _ok(
            "itsi_list_entities (filter db-*)",
            "success",
            f"{db_entities.get('count', 0)} db hosts",
        )
    )
    if not db_entities.get("entities"):
        s.note(
            "minor",
            "no db-* entities found",
            "the scenario will still create services but their KPIs may have no data",
        )


async def step_create_database_service(s: Scenario) -> str:
    title = f"mcp-scenario-database-tier-{s.run_id}"
    payload = _service_payload(
        title,
        "Database tier for the demo Web Store. Created by the MCP service-creation scenario.",
        entity_rules=[
            _entity_rule("host", "matches", "db-*", field_type="alias"),
        ],
        kpis=[
            _adhoc_kpi(
                title="Database event volume",
                base_search="search index=_internal sourcetype=splunkd | stats count by host",
                threshold_field="count",
                urgency=8,
                is_entity_breakdown=True,
            )
        ],
        tags=["mcp-itsi-scenario", "database", "demo"],
    )
    created = await _call(s.client, "itsi_create_service", {"payload": payload})
    if created.get("status") != "success":
        s.note(
            "major",
            "itsi_create_service rejected an example payload",
            _short(created.get("error") or created),
        )
        _stop(_short(created))
    key = created["service"]["_key"]
    s.remember("itsi_delete_service", key)
    print(_ok("itsi_create_service (database)", "success", f"{title} ({key[:8]}…)"))

    # Verify entity-rule matching surfaced
    fetched = await _call(s.client, "itsi_get_service", {"key": key})
    rules = fetched.get("service", {}).get("entity_rules", [])
    if not rules:
        s.note(
            "minor",
            "entity_rules round-trip lost the rule",
            "POST returned the rule we sent? — verify with itsi_get_service.",
        )
    else:
        print(_ok("entity_rules round-trip", "success", _short(rules)))
    return key


async def step_create_app_service(s: Scenario, db_key: str) -> str:
    title = f"mcp-scenario-app-tier-{s.run_id}"
    payload = _service_payload(
        title,
        "App tier — depends on the database tier.",
        entity_rules=[_entity_rule("host", "matches", "app-*")],
        services_depends_on=[
            {
                "serviceid": db_key,
                "kpis_depending_on": ["SHKPI-" + db_key],
                "overloaded_urgencies": {},
                "overloaded_thresholds": {},
            }
        ],
        kpis=[
            _adhoc_kpi(
                title="App tier health proxy",
                base_search="search index=_internal sourcetype=splunkd | stats count by host",
                threshold_field="count",
                urgency=7,
                is_entity_breakdown=True,
            )
        ],
        tags=["mcp-itsi-scenario", "app", "demo"],
    )
    created = await _call(s.client, "itsi_create_service", {"payload": payload})
    if created.get("status") != "success":
        s.note(
            "major",
            "service create with services_depends_on rejected",
            _short(created.get("error") or created),
        )
        _stop(_short(created))
    key = created["service"]["_key"]
    s.remember("itsi_delete_service", key)

    deps = (
        (await _call(s.client, "itsi_get_service", {"key": key}))
        .get("service", {})
        .get("services_depends_on", [])
    )
    dep_ids = [d.get("serviceid") for d in deps]
    if db_key in dep_ids:
        print(_ok("itsi_create_service (app, depends_on db)", "success", f"deps={dep_ids}"))
    else:
        s.note(
            "major",
            "service dependencies dropped on create",
            f"sent serviceid={db_key} but read back deps={dep_ids}",
        )
    return key


async def step_create_web_service(s: Scenario, app_key: str, db_key: str) -> str:
    title = f"mcp-scenario-web-tier-{s.run_id}"
    payload = _service_payload(
        title,
        "Web tier — depends on app and database tiers.",
        entity_rules=[
            _entity_rule("host", "matches", "www*", field_type="alias"),
            _entity_rule("host", "matches", "lb-*", field_type="alias"),
        ],
        services_depends_on=[
            {
                "serviceid": app_key,
                "kpis_depending_on": ["SHKPI-" + app_key],
                "overloaded_urgencies": {},
                "overloaded_thresholds": {},
            },
            {
                "serviceid": db_key,
                "kpis_depending_on": ["SHKPI-" + db_key],
                "overloaded_urgencies": {},
                "overloaded_thresholds": {},
            },
        ],
        kpis=[
            _adhoc_kpi(
                title="Web tier requests",
                base_search="search index=_internal sourcetype=splunkd | stats count by host",
                threshold_field="count",
                urgency=9,
                is_entity_breakdown=True,
            ),
            _adhoc_kpi(
                title="Web tier errors",
                base_search="search index=_internal sourcetype=splunkd log_level=ERROR | stats count by host",
                threshold_field="count",
                urgency=10,
                is_entity_breakdown=True,
                cron_schedule="*/5 * * * *",
            ),
        ],
        tags=["mcp-itsi-scenario", "web", "demo"],
    )
    created = await _call(s.client, "itsi_create_service", {"payload": payload})
    if created.get("status") != "success":
        _stop(_short(created))
    key = created["service"]["_key"]
    s.remember("itsi_delete_service", key)
    print(_ok("itsi_create_service (web)", "success", f"{title} ({key[:8]}…)"))
    return key


async def step_create_business_service(s: Scenario, web_key: str) -> str:
    title = f"mcp-scenario-web-store-{s.run_id}"
    payload = _service_payload(
        title,
        "Top-level business service for the demo Web Store; depends on Web Tier.",
        entity_rules=[],
        services_depends_on=[
            {
                "serviceid": web_key,
                "kpis_depending_on": ["SHKPI-" + web_key],
                "overloaded_urgencies": {},
                "overloaded_thresholds": {},
            }
        ],
        kpis=[],
        tags=["mcp-itsi-scenario", "business", "demo"],
    )
    created = await _call(s.client, "itsi_create_service", {"payload": payload})
    if created.get("status") != "success":
        _stop(_short(created))
    key = created["service"]["_key"]
    s.remember("itsi_delete_service", key)
    print(_ok("itsi_create_service (Web Store)", "success", f"{title} ({key[:8]}…)"))
    return key


async def step_update_entity_rules(s: Scenario, key: str) -> None:
    """Documented step 2: edit a service's entity rules after creation."""
    new_rules = [
        _entity_rule("host", "matches", "db-*"),
        _entity_rule("host", "not", "db-99"),
    ]
    updated = await _call(
        s.client,
        "itsi_update_service",
        {"key": key, "payload": {"entity_rules": new_rules}, "is_partial": True},
    )
    if updated.get("status") != "success":
        s.note(
            "major",
            "itsi_update_service partial-update of entity_rules failed",
            _short(updated.get("error") or updated),
        )
        return

    refetched = await _call(s.client, "itsi_get_service", {"key": key})
    rules = refetched.get("service", {}).get("entity_rules", [])
    if len(rules) == 2:
        print(_ok("entity_rules update (add not-match)", "success", f"{len(rules)} rules"))
    else:
        s.note(
            "minor",
            "entity_rules partial update reshaped the array",
            f"sent 2 rules, read back {len(rules)}",
        )


async def step_clone_service(s: Scenario, key: str) -> None:
    """Documented step: clone a service. We have no clone tool, so we
    emulate it via get → re-create with a new title."""
    src = (await _call(s.client, "itsi_get_service", {"key": key})).get("service")
    if not src:
        s.note("major", "could not read source service for clone")
        return

    s.note(
        "minor",
        "no native itsi_clone_service tool",
        "agents must read+rewrite to clone; nontrivial because _key, kpi _keys, "
        "kpi_base_search refs, and dependencies must all be regenerated.",
    )

    cloned_payload = {
        k: v
        for k, v in src.items()
        if k
        not in {
            "_key",
            "create_time",
            "create_by",
            "mod_time",
            "mod_timestamp",
            "_user",
            "mod_by",
            "_owner",
        }
    }
    cloned_payload["title"] = f"mcp-scenario-database-tier-clone-{s.run_id}"
    # Regenerate KPI _keys to avoid collision
    for kpi in cloned_payload.get("kpis", []) or []:
        kpi["_key"] = str(uuid.uuid4())
    cloned = await _call(s.client, "itsi_create_service", {"payload": cloned_payload})
    if cloned.get("status") == "success":
        s.remember("itsi_delete_service", cloned["service"]["_key"])
        print(_ok("emulated clone", "success", cloned_payload["title"]))
    else:
        s.note(
            "major",
            "emulated clone failed",
            _short(cloned.get("error") or cloned),
        )


async def step_disable_service(s: Scenario, key: str) -> None:
    """Documented: enable/disable a service via its `enabled` flag."""
    res = await _call(
        s.client,
        "itsi_update_service",
        {"key": key, "payload": {"enabled": 0}, "is_partial": True},
    )
    if res.get("status") != "success":
        s.note(
            "minor",
            "could not toggle service.enabled via partial update",
            _short(res.get("error") or res),
        )
        return
    refetch = await _call(s.client, "itsi_get_service", {"key": key})
    if refetch.get("service", {}).get("enabled") == 0:
        print(_ok("disable service", "success", f"enabled=0 for {key[:8]}…"))
    else:
        s.note(
            "minor",
            "disable service partial update did not stick",
            f"enabled is still {refetch.get('service', {}).get('enabled')}",
        )


async def step_search_docs_for_guidance(s: Scenario) -> None:
    hits = await _call(s.client, "itsi_search_docs", {"query": "service template"})
    if hits.get("status") == "success" and hits.get("count"):
        slugs = [h["slug"] for h in hits["hits"]]
        print(_ok("itsi_search_docs", "success", f"{slugs}"))
    else:
        s.note(
            "minor",
            "itsi_search_docs missed 'service template'",
            "expected at least the service-insights or best-practices doc",
        )


async def cleanup(s: Scenario) -> None:
    print("\n--- Cleanup ---")
    # Reverse order to satisfy dependencies (parent first, then children)
    for tool, key in reversed(s.created_keys):
        try:
            await _call(s.client, tool, {"key": key})
            print(_ok(f"{tool}({key[:8]}…)", "success"))
        except Exception as exc:
            print(_ok(f"{tool}({key[:8]}…)", "warn", repr(exc)))


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _connected_client(url: str, headers: dict[str, str]):
    transport = StreamableHttpTransport(url, headers=headers)
    async with Client(transport) as client:
        yield client


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleanup", action="store_true", help="Delete created objects at the end.")
    parser.add_argument("--findings", default="logs/itsi_scenario_findings.json")
    args = parser.parse_args()

    url = os.getenv("MCP_ITSI_URL", "http://127.0.0.1:8084/mcp")
    headers = {
        "X-Splunk-Host": os.environ["ITSI_HOST"],
        "X-Splunk-Port": os.getenv("ITSI_PORT", "8089"),
        "X-Splunk-Scheme": os.getenv("ITSI_SCHEME", "https"),
        "X-Splunk-Username": os.environ["ITSI_USERNAME"],
        "X-Splunk-Password": os.environ["ITSI_PASSWORD"],
        "X-Splunk-Verify-SSL": os.getenv("ITSI_VERIFY_SSL", "false"),
        "X-Session-ID": "service-creation-scenario",
    }

    splunk_host = os.environ["ITSI_HOST"]
    run_id = f"{int(time.time())}-{os.getpid()}"
    print(f"# ITSI service creation scenario (run {run_id})\n")
    print(f"Server: {url}\nITSI host: {splunk_host}\n")

    async with _connected_client(url, headers) as client:
        s = Scenario(client, run_id)
        try:
            await s.step("Prerequisites", lambda: step_prereqs(s))
            db_key = await s.step(
                "Step 1a: Create Database tier", lambda: step_create_database_service(s)
            )
            app_key = await s.step(
                "Step 1b: Create App tier", lambda: step_create_app_service(s, db_key)
            )
            web_key = await s.step(
                "Step 1c: Create Web tier",
                lambda: step_create_web_service(s, app_key=app_key, db_key=db_key),
            )
            biz_key = await s.step(
                "Step 1d: Create top-level Web Store",
                lambda: step_create_business_service(s, web_key),
            )

            await s.step(
                "Step 2: Update entity rules with not-match",
                lambda: step_update_entity_rules(s, db_key),
            )
            await s.step(
                "Step 4 alt: Disable service via partial update",
                lambda: step_disable_service(s, biz_key),
            )
            await s.step("Clone (emulated)", lambda: step_clone_service(s, db_key))
            await s.step("Discoverability check", lambda: step_search_docs_for_guidance(s))

        finally:
            print("\n## Findings\n")
            for line in s.observations:
                print(line)
            os.makedirs(os.path.dirname(args.findings), exist_ok=True)
            with open(args.findings, "w") as fh:
                json.dump({"run_id": run_id, "findings": s.findings}, fh, indent=2)
            print(f"\nFindings JSON: {args.findings}")

            if args.cleanup:
                await cleanup(s)
            else:
                print("\n(--cleanup not set; created objects left in ITSI for inspection)")
                print("Created keys:")
                for tool, key in s.created_keys:
                    print(f"  - {tool} {key}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
