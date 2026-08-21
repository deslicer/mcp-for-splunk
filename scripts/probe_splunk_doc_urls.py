#!/usr/bin/env python3
"""Probe catalogued Splunk Help URLs used by MCP docs resources."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.resources.dashboard_studio_docs import DASHBOARD_STUDIO_TOPICS
from src.resources.splunk_cim import SplunkCIMResource
from src.resources.splunk_docs import AdminGuideResource, TroubleshootingResource

COMMON_CONFIG_FILES = [
    "alert_actions.conf",
    "authentication.conf",
    "authorize.conf",
    "indexes.conf",
    "inputs.conf",
    "limits.conf",
    "outputs.conf",
    "props.conf",
    "transforms.conf",
    "savedsearches.conf",
    "server.conf",
    "web.conf",
    "app.conf",
    "commands.conf",
    "datamodels.conf",
    "eventtypes.conf",
    "fields.conf",
    "macros.conf",
    "tags.conf",
    "workflow_actions.conf",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

ADMIN_TOPICS = [
    "indexes",
    "authentication",
    "deployment",
    "apps",
    "users",
    "roles",
    "monitoring",
    "performance",
    "clustering",
    "distributed-search",
    "forwarders",
    "inputs",
    "outputs",
    "licensing",
    "security",
]

SPL_COMMANDS = [
    "search",
    "stats",
    "eval",
    "chart",
    "timechart",
    "table",
    "sort",
    "where",
    "lookup",
    "rex",
    "fields",
    "top",
    "dedup",
    "head",
    "spath",
    "transaction",
]

ITSI_URLS = [
    "https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-reference/itsi-rest-api-reference",
    "https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-schema/itsi-rest-api-schema",
    "https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/visualize-and-assess-service-health/4.21/overview",
    "https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/discover-and-integrate-it-components/4.21",
    "https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/detect-and-act-on-notable-events/4.21/",
    "https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/reduce-time-to-insights/4.18/introduction",
]


def collect_urls() -> list[tuple[str, str]]:
    help_base = "https://help.splunk.com"
    version = "10.0"
    urls: list[tuple[str, str]] = []

    urls.append(
        (
            "cheat-sheet",
            "https://www.splunk.com/en_us/blog/learn/splunk-cheat-sheet-query-spl-regex-commands.html",
        )
    )

    for key, info in TroubleshootingResource.TROUBLESHOOTING_TOPICS.items():
        urls.append(
            (
                f"troubleshooting/{key}",
                f"{help_base}/en/splunk-enterprise/administer/troubleshoot/{version}/{info['url_path']}",
            )
        )

    for command in SPL_COMMANDS:
        urls.append(
            (
                f"spl/{command}",
                f"{help_base}/en/splunk-enterprise/search/spl-search-reference/{version}/search-commands/{command}",
            )
        )

    admin = AdminGuideResource("latest", "indexes")
    for topic in ADMIN_TOPICS:
        admin.topic = topic
        urls.append((f"admin/{topic}", admin._build_topic_url(version)))

    for config in COMMON_CONFIG_FILES:
        minor, full = "10.0", "10.0.0"
        primary = (
            f"{help_base}/en/splunk-enterprise/administer/admin-manual/{minor}/"
            f"configuration-file-reference/{full}-configuration-file-reference/{config}"
        )
        fallback = (
            f"{help_base}/en/data-management/splunk-enterprise-admin-manual/{minor}/"
            f"configuration-file-reference/{full}-configuration-file-reference/{config}"
        )
        urls.append((f"spec-primary/{config}", primary))
        urls.append((f"spec-fallback/{config}", fallback))

    cim_base = f"{help_base}/en/data-management/common-information-model/6.1/data-models"
    for model_key, info in SplunkCIMResource.CIM_DATA_MODELS.items():
        urls.append((f"cim/{model_key}", f"{cim_base}/{info['url_slug']}"))
        if "url_slug_alt" in info:
            urls.append((f"cim-alt/{model_key}", f"{cim_base}/{info['url_slug_alt']}"))

    for topic, info in DASHBOARD_STUDIO_TOPICS.items():
        if "url" in info:
            urls.append((f"studio/{topic}", info["url"]))

    for url in ITSI_URLS:
        urls.append((f"itsi/{url.rsplit('/', 3)[-2]}", url))

    return urls


async def _one(client: httpx.AsyncClient, sem: asyncio.Semaphore, label: str, url: str) -> tuple:
    async with sem:
        try:
            response = await client.get(url)
            return label, url, response.status_code, str(response.url)
        except Exception as exc:  # pylint: disable=broad-except
            return label, url, f"ERR {exc}", url


async def probe() -> int:
    rows = collect_urls()
    print(f"Probing {len(rows)} URLs...\n")
    sem = asyncio.Semaphore(8)
    async with httpx.AsyncClient(timeout=20.0, headers=HEADERS, follow_redirects=True) as client:
        results = await asyncio.gather(*[_one(client, sem, label, url) for label, url in rows])
    ok = fail = 0
    for label, url, status, final in results:
        marker = "OK " if status == 200 else "BAD"
        if status == 200:
            ok += 1
        else:
            fail += 1
        print(f"{marker} {status:>3} {label}\n     {url}")
        if final != url:
            print(f"     -> {final}")
    print(f"\n{ok} ok / {fail} failed / {len(rows)} total")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(probe()))
