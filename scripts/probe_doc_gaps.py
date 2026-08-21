#!/usr/bin/env python3
"""Probe advertised docs URLs and report 404s plus uncatalogued administer books."""

from __future__ import annotations

import asyncio
import sys
from collections import defaultdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.resources.admin_topics import ADMIN_TOPICS, build_admin_urls
from src.resources.docs_http import is_soft_404_body
from src.resources.docs_versions import (
    SUPPORTED_DOC_VERSIONS,
    build_spec_urls,
    build_spl_urls,
    build_troubleshooting_urls,
)
from src.resources.studio_topics import DASHBOARD_STUDIO_TOPICS, build_studio_urls

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

TS_TOPICS = {
    "splunk-logs": "splunk-enterprise-log-files/what-splunk-software-logs-about-itself",
    "metrics-log": "splunk-enterprise-log-files/about-metrics.log",
    "troubleshoot-inputs": "splunk-enterprise-log-files/troubleshoot-inputs-with-metrics.log",
    "platform-instrumentation": (
        "platform-instrumentation/about-splunk-enterprise-platform-instrumentation"
    ),
    "platform-instrumentation-logs": (
        "platform-instrumentation/what-does-platform-instrumentation-log"
    ),
    "platform-instrumentation-searches": (
        "platform-instrumentation/sample-platform-instrumentation-searches"
    ),
    "search-problems": "splunk-web-and-search-problems/i-cant-find-my-data",
    "authentication-timeouts": (
        "splunk-web-and-search-problems/intermittent-authentication-timeouts-on-search-peers"
    ),
    "indexing-performance": (
        "data-acquisition-problems/identify-and-triage-indexing-performance-problems"
    ),
    "indexing-delay": "data-acquisition-problems/event-indexing-delay",
}

SPL_COMMANDS = (
    "search",
    "stats",
    "eval",
    "where",
    "rex",
    "lookup",
    "timechart",
    "chart",
    "table",
    "sort",
    "top",
    "rare",
    "transaction",
    "streamstats",
    "eventstats",
    "bucket",
    "dedup",
    "head",
    "tail",
    "regex",
    "replace",
    "convert",
    "makemv",
    "mvexpand",
    "spath",
    "xmlkv",
    "kvform",
)

SPEC_FILES = (
    "alert_actions.conf",
    "limits.conf",
    "indexes.conf",
    "inputs.conf",
    "outputs.conf",
    "props.conf",
    "transforms.conf",
    "server.conf",
    "web.conf",
    "authentication.conf",
    "authorize.conf",
    "savedsearches.conf",
)

CIM_MODELS = (
    ("alerts", "alerts", True),
    ("application-state", "application-state", False),
    ("authentication", "authentication", True),
    ("certificates", "certificates", True),
    ("change", "change", True),
    ("change-analysis", "change-analysis", False),
    ("data-access", "data-access", True),
    ("databases", "databases", True),
    ("dlp", "data-loss-prevention", True),
    ("email", "email", True),
    ("endpoint", "endpoint", True),
    ("event-signatures", "event-signatures", True),
    ("interprocess-messaging", "interprocess-messaging", True),
    ("intrusion-detection", "intrusion-detection", True),
    ("inventory", "inventory", True),
    ("jvm", "java-virtual-machines-jvm", True),
    ("malware", "malware", True),
    ("network-resolution", "network-resolution-dns", True),
    ("network-sessions", "network-sessions", True),
    ("network-traffic", "network-traffic", True),
    ("performance", "performance", True),
    ("splunk-audit", "splunk-audit-logs", True),
    ("ticket-management", "ticket-management", True),
    ("updates", "updates", True),
    ("vulnerabilities", "vulnerabilities", True),
    ("web", "web", True),
)

UNCATALOGUED_BOOKS = (
    ("inherit-deployment", "en/splunk-enterprise/administer/inherit-a-splunk-deployment"),
    ("update-deployment", "en/splunk-enterprise/administer/update-your-deployment"),
    ("workloads", "en/splunk-enterprise/administer/manage-workloads"),
    ("upgrade-readiness", "en/splunk-enterprise/administer/upgrade-readiness-app"),
    ("python3", "en/splunk-enterprise/administer/python-3-migration"),
    ("distributed-deployment", "en/splunk-enterprise/administer/distributed-deployment-manual"),
)

UNCATALOGUED_CHAPTERS = (
    ("sidecars", "splunk-sidecars"),
    ("proxies", "configure-splunk-enterprise-to-use-proxies"),
    ("splunk-web", "administer-splunk-enterprise-with-splunk-web"),
    ("windows", "get-the-most-out-of-splunk-enterprise-on-windows"),
    ("linux", "get-the-most-out-of-splunk-enterprise-on-linux"),
)

def _looks_like_404(status: int, text: str) -> bool:
    if status != 200:
        return True
    return is_soft_404_body(text)


def collect() -> list[tuple[str, str, str, list[str]]]:
    rows: list[tuple[str, str, str, list[str]]] = []
    studio_topics = [key for key, info in DASHBOARD_STUDIO_TOPICS.items() if "paths" in info]
    for version in SUPPORTED_DOC_VERSIONS:
        for topic in ADMIN_TOPICS:
            rows.append(("admin", version, topic, build_admin_urls(topic, version)))
        for topic in studio_topics:
            rows.append(("studio", version, topic, build_studio_urls(topic, version)))
        for topic, path in TS_TOPICS.items():
            rows.append(("troubleshooting", version, topic, build_troubleshooting_urls(path, version)))
        for command in SPL_COMMANDS:
            rows.append(("spl", version, command, build_spl_urls(command, version)))
        for config in SPEC_FILES:
            rows.append(("spec", version, config, build_spec_urls(config, version)))
        if version not in {"10.5", "10.3", "10.1"}:
            prefix = (
                "welcome-to-splunk-enterprise-administration/" if version == "9.0" else ""
            )
            for slug, chapter in UNCATALOGUED_CHAPTERS:
                url = (
                    "https://help.splunk.com/en/splunk-enterprise/administer/admin-manual/"
                    f"{version}/{prefix}{chapter}"
                )
                rows.append(("uncatalogued-chapter", version, slug, [url]))
    for slug, suffix in UNCATALOGUED_BOOKS:
        rows.append(("uncatalogued-book", "-", slug, [f"https://help.splunk.com/{suffix}"]))
    for model, slug, live in CIM_MODELS:
        if not live:
            continue
        url = f"https://help.splunk.com/en/data-management/common-information-model/6.1/data-models/{slug}"
        rows.append(("cim", "6.1", model, [url]))
    return rows


async def _one(client: httpx.AsyncClient, sem: asyncio.Semaphore, row: tuple) -> tuple:
    family, version, topic, urls = row
    async with sem:
        last_status = "ERR"
        last_url = urls[0] if urls else ""
        for url in urls:
            try:
                response = await client.get(url)
                last_status = response.status_code
                last_url = url
                if not _looks_like_404(response.status_code, response.text):
                    return family, version, topic, url, 200
            except Exception as exc:  # pylint: disable=broad-except
                last_status = f"ERR {exc}"
                last_url = url
        return family, version, topic, last_url, last_status


async def main() -> int:
    rows = collect()
    print(f"Probing {len(rows)} advertised + sibling topics...\n")
    sem = asyncio.Semaphore(12)
    async with httpx.AsyncClient(timeout=25.0, headers=HEADERS, follow_redirects=True) as client:
        results = await asyncio.gather(*[_one(client, sem, row) for row in rows])

    by_family: dict[str, list] = defaultdict(list)
    for item in results:
        by_family[item[0]].append(item)

    fail = 0
    for family in (
        "admin",
        "studio",
        "troubleshooting",
        "spl",
        "spec",
        "cim",
        "uncatalogued-book",
        "uncatalogued-chapter",
    ):
        bad = [item for item in by_family[family] if item[4] != 200]
        ok = len(by_family[family]) - len(bad)
        print(f"===== {family}: {ok} ok / {len(bad)} failed =====")
        if not bad:
            print()
            continue
        grouped: dict[str, list] = defaultdict(list)
        for _family, version, topic, url, status in bad:
            fail += 1
            grouped[topic].append((version, status, url))
        for topic, hits in grouped.items():
            versions = ", ".join(f"{version}={status}" for version, status, _url in hits)
            print(f"  BAD {topic}: {versions}")
            print(f"      {hits[0][2]}")
        print()

    print(f"{len(results) - fail} ok / {fail} failed / {len(results)} total")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
