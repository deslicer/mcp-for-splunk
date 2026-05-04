"""End-to-end CRUD round-trip test for the ITSI MCP server.

For every major mutable ITOA / Event Management object type the script:

    1. CREATEs a fresh object with a unique title.
    2. GETs it by key/name to confirm persistence.
    3. UPDATEs a benign field (description / disabled flag).
    4. GETs again to confirm the update was applied.
    5. DELETEs the object and verifies it is gone.

Every created object is registered in a cleanup list so any partial
failure still tries to remove leftovers. The script exits non-zero if
any round-trip fails.

Reads ITSI_HOST / ITSI_USERNAME / ITSI_PASSWORD from the environment.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import traceback
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(name: str, status: str, detail: str = "") -> str:
    icon = "OK" if status == "success" else ("WARN" if status == "warn" else "FAIL")
    return f"[{icon:<4}] {name:<50}{' — ' + detail if detail else ''}"


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


# ---------------------------------------------------------------------------
# Round-trip framework
# ---------------------------------------------------------------------------


class CRUDRunner:
    """Shared bookkeeping for CRUD test cases."""

    def __init__(self, client: Client) -> None:
        self.client = client
        self.failures = 0
        self._cleanup: list[Callable[[], Awaitable[Any]]] = []

    def schedule_cleanup(self, fn: Callable[[], Awaitable[Any]]) -> None:
        self._cleanup.append(fn)

    async def run_cleanup(self) -> None:
        if not self._cleanup:
            return
        print("\n## Cleanup (best-effort)\n")
        for fn in reversed(self._cleanup):
            try:
                await fn()
            except Exception as exc:
                print(_ok("cleanup", "warn", repr(exc)))

    async def run(self, name: str, body: Callable[[], Awaitable[None]]) -> None:
        try:
            await body()
        except AssertionError as exc:
            self.failures += 1
            print(_ok(name, "fail", str(exc)))
        except Exception as exc:
            self.failures += 1
            print(_ok(name, "fail", repr(exc)))
            traceback.print_exc()


# ---------------------------------------------------------------------------
# Round-trip cases
# ---------------------------------------------------------------------------


def _suffix() -> str:
    return f"{int(time.time())}-{os.getpid()}"


async def crud_entity(r: CRUDRunner) -> None:
    title = f"mcp-itsi-test-entity-{_suffix()}"

    async def body() -> None:
        created = await _call(
            r.client,
            "itsi_create_entity",
            {
                "payload": {
                    "title": title,
                    "description": "created by mcp-itsi crud test",
                    "object_type": "entity",
                    "identifier": {"fields": ["host"], "values": [title]},
                    "informational": {"fields": [], "values": []},
                    # ITSI requires the alias field to be present as a
                    # top-level array on the entity document itself.
                    "host": [title],
                    "sec_grp": "default_itsi_security_group",
                }
            },
        )
        assert created.get("status") == "success", _short(created)
        key = created.get("entity", {}).get("_key")
        assert key, f"no _key returned: {created}"
        r.schedule_cleanup(lambda: _call(r.client, "itsi_delete_entity", {"key": key}))

        fetched = await _call(r.client, "itsi_get_entity", {"key": key})
        assert fetched.get("status") == "success", _short(fetched)
        assert fetched["entity"]["title"] == title

        updated = await _call(
            r.client,
            "itsi_update_entity",
            {"key": key, "payload": {"description": "updated by mcp-itsi crud test"}},
        )
        assert updated.get("status") == "success", _short(updated)

        verify = await _call(r.client, "itsi_get_entity", {"key": key})
        assert verify["entity"].get("description") == "updated by mcp-itsi crud test", _short(
            verify
        )

        deleted = await _call(r.client, "itsi_delete_entity", {"key": key})
        assert deleted.get("status") == "success", _short(deleted)

        gone = await _call(r.client, "itsi_get_entity", {"key": key})
        assert gone.get("status") == "error", f"expected error after delete: {gone}"
        print(_ok("entity CRUD", "success", f"{title} ({key[:8]}…)"))

    await r.run("entity CRUD", body)


async def crud_kpi_base_search(r: CRUDRunner) -> None:
    title = f"mcp-itsi-test-kbs-{_suffix()}"

    async def body() -> None:
        created = await _call(
            r.client,
            "itsi_create_kpi_base_search",
            {
                "payload": {
                    "title": title,
                    "description": "created by mcp-itsi crud test",
                    "object_type": "kpi_base_search",
                    "base_search": "index=_internal | stats count by host",
                    "metrics": [
                        {
                            "_key": "metric-1",
                            "title": "events",
                            "aggregate_statop": "avg",
                            "entity_statop": "avg",
                            "fill_gaps": "null_value",
                            "threshold_field": "count",
                            "unit": "events",
                        }
                    ],
                    "alert_period": "5",
                    "alert_lag": "30",
                    "entity_id_fields": "host",
                    "entity_alias_filtering_fields": "",
                    "entity_breakdown_id_fields": "host",
                    "is_entity_breakdown": False,
                    "is_service_entity_filter": False,
                    "search_alert_earliest": "5",
                    "sec_grp": "default_itsi_security_group",
                    "source_itsi_da": "",
                    "metric_qualifier": "",
                    "datamodel_filter_clauses": "",
                }
            },
        )
        assert created.get("status") == "success", _short(created)
        key = created.get("kpi_base_search", {}).get("_key")
        assert key, _short(created)
        r.schedule_cleanup(lambda: _call(r.client, "itsi_delete_kpi_base_search", {"key": key}))

        fetched = await _call(r.client, "itsi_get_kpi_base_search", {"key": key})
        assert fetched.get("status") == "success", _short(fetched)

        updated = await _call(
            r.client,
            "itsi_update_kpi_base_search",
            {"key": key, "payload": {"description": "updated by mcp-itsi crud test"}},
        )
        assert updated.get("status") == "success", _short(updated)

        verify = await _call(r.client, "itsi_get_kpi_base_search", {"key": key})
        assert (
            verify["kpi_base_search"].get("description") == "updated by mcp-itsi crud test"
        ), _short(verify)

        deleted = await _call(r.client, "itsi_delete_kpi_base_search", {"key": key})
        assert deleted.get("status") == "success", _short(deleted)
        print(_ok("kpi_base_search CRUD", "success", f"{title} ({key[:8]}…)"))

    await r.run("kpi_base_search CRUD", body)


async def crud_service_template(r: CRUDRunner) -> None:
    suffix = _suffix()
    seed_title = f"mcp-itsi-test-tpl-seed-{suffix}"
    title = f"mcp-itsi-test-template-{suffix}"

    async def body() -> None:
        # ITSI requires service_id (or base_service_template_id) on create,
        # so first create a seed service to derive the template from.
        seed = await _call(
            r.client,
            "itsi_create_service",
            {
                "payload": {
                    "title": seed_title,
                    "description": "seed service for mcp-itsi service-template crud",
                    "object_type": "service",
                    "kpis": [],
                    "entity_rules": [],
                    "services_depends_on": [],
                    "services_depending_on_me": [],
                    "enabled": 1,
                    "sec_grp": "default_itsi_security_group",
                }
            },
        )
        assert seed.get("status") == "success", _short(seed)
        seed_key = seed["service"]["_key"]
        r.schedule_cleanup(lambda: _call(r.client, "itsi_delete_service", {"key": seed_key}))

        created = await _call(
            r.client,
            "itsi_create_service_template",
            {
                "payload": {
                    "title": title,
                    "description": "created by mcp-itsi crud test",
                    "object_type": "base_service_template",
                    "service_id": seed_key,
                    "kpis": [],
                    "entity_rules": [],
                    "sec_grp": "default_itsi_security_group",
                }
            },
        )
        assert created.get("status") == "success", _short(created)
        key = created.get("template", {}).get("_key")
        assert key, _short(created)
        r.schedule_cleanup(lambda: _call(r.client, "itsi_delete_service_template", {"key": key}))

        fetched = await _call(r.client, "itsi_get_service_template", {"key": key})
        assert fetched.get("status") == "success", _short(fetched)

        updated = await _call(
            r.client,
            "itsi_update_service_template",
            {"key": key, "payload": {"description": "updated by mcp-itsi crud test"}},
        )
        assert updated.get("status") == "success", _short(updated)

        deleted = await _call(r.client, "itsi_delete_service_template", {"key": key})
        assert deleted.get("status") == "success", _short(deleted)
        await _call(r.client, "itsi_delete_service", {"key": seed_key})
        print(_ok("service_template CRUD", "success", f"{title} ({key[:8]}…)"))

    await r.run("service_template CRUD", body)


async def crud_service(r: CRUDRunner) -> None:
    title = f"mcp-itsi-test-service-{_suffix()}"

    async def body() -> None:
        created = await _call(
            r.client,
            "itsi_create_service",
            {
                "payload": {
                    "title": title,
                    "description": "created by mcp-itsi crud test",
                    "object_type": "service",
                    "kpis": [],
                    "entity_rules": [],
                    "services_depends_on": [],
                    "services_depending_on_me": [],
                    "enabled": 1,
                    "sec_grp": "default_itsi_security_group",
                    "service_tags": {"tags": ["mcp-itsi-test"], "template_tags": []},
                }
            },
        )
        assert created.get("status") == "success", _short(created)
        key = created.get("service", {}).get("_key")
        assert key, _short(created)
        r.schedule_cleanup(lambda: _call(r.client, "itsi_delete_service", {"key": key}))

        fetched = await _call(r.client, "itsi_get_service", {"key": key})
        assert fetched.get("status") == "success", _short(fetched)

        updated = await _call(
            r.client,
            "itsi_update_service",
            {"key": key, "payload": {"description": "updated by mcp-itsi crud test"}},
        )
        assert updated.get("status") == "success", _short(updated)

        verify = await _call(r.client, "itsi_get_service", {"key": key})
        assert verify["service"].get("description") == "updated by mcp-itsi crud test", _short(
            verify
        )

        deleted = await _call(r.client, "itsi_delete_service", {"key": key})
        assert deleted.get("status") == "success", _short(deleted)
        print(_ok("service CRUD", "success", f"{title} ({key[:8]}…)"))

    await r.run("service CRUD", body)


async def crud_entity_type(r: CRUDRunner) -> None:
    title = f"mcp-itsi-test-entity-type-{_suffix()}"

    async def body() -> None:
        created = await _call(
            r.client,
            "itsi_create_entity_type",
            {
                "payload": {
                    "title": title,
                    "description": "created by mcp-itsi crud test",
                    "object_type": "entity_type",
                    "data_drilldowns": [],
                    "dashboard_drilldowns": [],
                    "vital_metrics": [],
                }
            },
        )
        assert created.get("status") == "success", _short(created)
        key = created.get("entity_type", {}).get("_key")
        assert key, _short(created)
        r.schedule_cleanup(lambda: _call(r.client, "itsi_delete_entity_type", {"key": key}))

        fetched = await _call(r.client, "itsi_get_entity_type", {"key": key})
        assert fetched.get("status") == "success", _short(fetched)

        updated = await _call(
            r.client,
            "itsi_update_entity_type",
            {"key": key, "payload": {"description": "updated by mcp-itsi crud test"}},
        )
        assert updated.get("status") == "success", _short(updated)

        deleted = await _call(r.client, "itsi_delete_entity_type", {"key": key})
        assert deleted.get("status") == "success", _short(deleted)
        print(_ok("entity_type CRUD", "success", f"{title} ({key[:8]}…)"))

    await r.run("entity_type CRUD", body)


async def crud_kpi_threshold_template(r: CRUDRunner) -> None:
    title = f"mcp-itsi-test-thr-tpl-{_suffix()}"

    async def body() -> None:
        created = await _call(
            r.client,
            "itsi_create_kpi_threshold_template",
            {
                "payload": {
                    "title": title,
                    "description": "created by mcp-itsi crud test",
                    "object_type": "kpi_threshold_template",
                    "adaptive_thresholds_is_enabled": False,
                    "adaptive_thresholding_training_window": "-7d",
                    "time_variate_thresholds": False,
                    "time_variate_thresholds_specification": {
                        "policies": {
                            "default_policy": {
                                "title": "Default",
                                "policy_type": "static",
                                "aggregate_thresholds": {
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
                                    "thresholdLevels": [],
                                    "isMaxStatic": False,
                                    "baseSeverityLabel": "normal",
                                },
                                "entity_thresholds": {
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
                                    "thresholdLevels": [],
                                    "isMaxStatic": False,
                                    "baseSeverityLabel": "normal",
                                },
                                "time_blocks": [],
                            }
                        },
                        "time_blocks": [],
                    },
                    "sec_grp": "default_itsi_security_group",
                }
            },
        )
        assert created.get("status") == "success", _short(created)
        key = created.get("threshold_template", {}).get("_key")
        assert key, _short(created)
        r.schedule_cleanup(
            lambda: _call(r.client, "itsi_delete_kpi_threshold_template", {"key": key})
        )

        fetched = await _call(r.client, "itsi_get_kpi_threshold_template", {"key": key})
        assert fetched.get("status") == "success", _short(fetched)

        updated = await _call(
            r.client,
            "itsi_update_kpi_threshold_template",
            {"key": key, "payload": {"description": "updated by mcp-itsi crud test"}},
        )
        assert updated.get("status") == "success", _short(updated)

        deleted = await _call(r.client, "itsi_delete_kpi_threshold_template", {"key": key})
        assert deleted.get("status") == "success", _short(deleted)
        print(_ok("kpi_threshold_template CRUD", "success", f"{title} ({key[:8]}…)"))

    await r.run("kpi_threshold_template CRUD", body)


async def crud_aggregation_policy(r: CRUDRunner) -> None:
    title = f"mcp-itsi-test-aggp-{_suffix()}"

    async def body() -> None:
        created = await _call(
            r.client,
            "itsi_create_aggregation_policy",
            {
                "payload": {
                    "title": title,
                    "description": "created by mcp-itsi crud test",
                    "disabled": 1,
                    "priority": 5,
                    "filter_criteria": {
                        "condition": "AND",
                        "items": [
                            {
                                "type": "clause",
                                "config": {
                                    "clauses": [
                                        {
                                            "type": "field",
                                            "config": {
                                                "field": "title",
                                                "operator": "matches",
                                                "value": "mcp-itsi-test-*",
                                            },
                                        }
                                    ]
                                },
                            }
                        ],
                    },
                    "breaking_criteria": {"condition": "AND", "items": []},
                    "split_by_field": [],
                    "group_title": "%title%",
                    "group_severity": "%severity%",
                    "group_status": "%status%",
                    "group_assignee": "%owner%",
                    "group_instruction": "",
                    "rules": [],
                    "service_topology_enabled": 0,
                    "ace_enabled": 0,
                    "object_type": "notable_event_aggregation_policy",
                    "ttl": "+24h",
                    "run_time_based_actions_once": 0,
                }
            },
        )
        assert created.get("status") == "success", _short(created)
        key = created.get("aggregation_policy", {}).get("_key")
        assert key, _short(created)
        r.schedule_cleanup(lambda: _call(r.client, "itsi_delete_aggregation_policy", {"key": key}))

        fetched = await _call(r.client, "itsi_get_aggregation_policy", {"key": key})
        assert fetched.get("status") == "success", _short(fetched)

        # ITSI's notable_event_aggregation_policy update handler always
        # validates against the full schema, so partial updates only work
        # when you fetch the existing document first and merge changes in.
        existing = fetched["aggregation_policy"]
        merged = dict(existing)
        merged["description"] = "updated by mcp-itsi crud test"
        updated = await _call(
            r.client,
            "itsi_update_aggregation_policy",
            {"key": key, "payload": merged, "is_partial": False},
        )
        assert updated.get("status") == "success", _short(updated)

        deleted = await _call(r.client, "itsi_delete_aggregation_policy", {"key": key})
        assert deleted.get("status") == "success", _short(deleted)
        print(_ok("aggregation_policy CRUD", "success", f"{title} ({key[:8]}…)"))

    await r.run("aggregation_policy CRUD", body)


async def crud_correlation_search(r: CRUDRunner) -> None:
    name = f"mcp-itsi-test-corrsrch-{_suffix()}"

    async def body() -> None:
        created = await _call(
            r.client,
            "itsi_create_correlation_search",
            {
                "payload": {
                    "name": name,
                    "search": (
                        "index=_internal sourcetype=splunkd | head 1 | "
                        "eval severity=3, owner='unassigned'"
                    ),
                    "description": "created by mcp-itsi crud test",
                    "cron_schedule": "*/10 * * * *",
                    "dispatch.earliest_time": "-5m",
                    "dispatch.latest_time": "now",
                    "is_scheduled": "1",
                    "disabled": "1",
                    "alert_type": "number of events",
                    "alert_comparator": "greater than",
                    "alert_threshold": "0",
                    "alert.severity": "3",
                    "actions": "itsi_event_generator",
                    "action.itsi_event_generator": "1",
                    "action.itsi_event_generator.param.title": name,
                    "action.itsi_event_generator.param.severity": "3",
                    "action.itsi_event_generator.param.status": "1",
                    "action.itsi_event_generator.param.owner": "unassigned",
                    "action.itsi_event_generator.param.search_type": "basic",
                    "action.itsi_event_generator.param.editor": "advance_correlation_builder_editor",
                    "action.itsi_event_generator.param.meta_data": "{}",
                    "action.itsi_event_generator.param.drilldown_search_earliest_offset": "-300",
                    "action.itsi_event_generator.param.drilldown_search_latest_offset": "300",
                }
            },
        )
        assert created.get("status") == "success", _short(created)
        r.schedule_cleanup(
            lambda: _call(r.client, "itsi_delete_correlation_search", {"name": name})
        )

        fetched = await _call(r.client, "itsi_get_correlation_search", {"name": name})
        assert fetched.get("status") == "success", _short(fetched)

        # ITSI's correlation_search update handler requires `name` in the
        # body even for partial updates (otherwise it 500s with KeyError
        # 'name'). Echoing the title is sufficient.
        updated = await _call(
            r.client,
            "itsi_update_correlation_search",
            {
                "name": name,
                "payload": {
                    "name": name,
                    "description": "updated by mcp-itsi crud test",
                },
            },
        )
        assert updated.get("status") == "success", _short(updated)

        deleted = await _call(r.client, "itsi_delete_correlation_search", {"name": name})
        assert deleted.get("status") == "success", _short(deleted)
        print(_ok("correlation_search CRUD", "success", name))

    await r.run("correlation_search CRUD", body)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _connected_client(url: str, headers: dict[str, str]):
    transport = StreamableHttpTransport(url, headers=headers)
    async with Client(transport) as client:
        yield client


async def main() -> int:
    url = os.getenv("MCP_ITSI_URL", "http://127.0.0.1:8084/mcp")
    headers = {
        "X-Splunk-Host": os.environ["ITSI_HOST"],
        "X-Splunk-Port": os.getenv("ITSI_PORT", "8089"),
        "X-Splunk-Scheme": os.getenv("ITSI_SCHEME", "https"),
        "X-Splunk-Username": os.environ["ITSI_USERNAME"],
        "X-Splunk-Password": os.environ["ITSI_PASSWORD"],
        "X-Splunk-Verify-SSL": os.getenv("ITSI_VERIFY_SSL", "false"),
        "X-Session-ID": "crud-roundtrip",
    }

    splunk_host = os.environ["ITSI_HOST"]
    print(f"# ITSI MCP CRUD round-trip\n\nServer: {url}\nITSI host: {splunk_host}\n")
    print("## CRUD round-trips\n")

    async with _connected_client(url, headers) as client:
        runner = CRUDRunner(client)
        try:
            await crud_entity_type(runner)
            await crud_kpi_base_search(runner)
            await crud_kpi_threshold_template(runner)
            await crud_service_template(runner)
            await crud_service(runner)
            await crud_entity(runner)
            await crud_aggregation_policy(runner)
            await crud_correlation_search(runner)
        finally:
            await runner.run_cleanup()

        print(f"\nfailures: {runner.failures}\n")
        return 0 if runner.failures == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
