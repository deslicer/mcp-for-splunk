#!/usr/bin/env python3
"""Probe versioned Splunk Help URLs for admin, studio, SPL, troubleshooting, and specs."""

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
from src.resources.splunk_docs import TroubleshootingResource
from src.resources.studio_topics import build_studio_urls

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def collect() -> list[tuple[str, str, str, list[str]]]:
    rows: list[tuple[str, str, str, list[str]]] = []
    studio_topics = ("datasources", "definition", "visualizations", "configuration", "framework")
    for version in SUPPORTED_DOC_VERSIONS:
        for topic in ADMIN_TOPICS:
            rows.append(("admin", version, topic, build_admin_urls(topic, version)))
        for topic in studio_topics:
            rows.append(("studio", version, topic, build_studio_urls(topic, version)))
        ts_path = TroubleshootingResource.TROUBLESHOOTING_TOPICS["metrics-log"]["url_path"]
        rows.append(
            ("troubleshooting", version, "metrics-log", build_troubleshooting_urls(ts_path, version))
        )
        rows.append(("spl", version, "stats", build_spl_urls("stats", version)))
        rows.append(("spec", version, "indexes.conf", build_spec_urls("indexes.conf", version)))
    return rows


async def _one(client: httpx.AsyncClient, sem: asyncio.Semaphore, row: tuple) -> tuple:
    family, version, topic, urls = row
    async with sem:
        last_status = "ERR"
        last_url = urls[0] if urls else ""
        last_final = last_url
        for url in urls:
            try:
                response = await client.get(url)
                last_status = response.status_code
                last_url = url
                last_final = str(response.url)
                if response.status_code == 200 and not is_soft_404_body(response.text):
                    return family, version, topic, url, 200, last_final
            except Exception as exc:  # pylint: disable=broad-except
                last_status = f"ERR {exc}"
                last_url = url
        return family, version, topic, last_url, last_status, last_final


async def main() -> int:
    rows = collect()
    print(f"Probing {len(rows)} versioned topics ({sum(len(r[3]) for r in rows)} URLs)...\n")
    sem = asyncio.Semaphore(10)
    async with httpx.AsyncClient(timeout=20.0, headers=HEADERS, follow_redirects=True) as client:
        results = await asyncio.gather(*[_one(client, sem, row) for row in rows])

    by_family: dict[str, list] = defaultdict(list)
    for item in results:
        by_family[item[0]].append(item)

    fail = 0
    for family in ("admin", "studio", "troubleshooting", "spl", "spec"):
        print(f"===== {family} =====")
        for _family, version, topic, url, status, final in by_family[family]:
            ok = status == 200
            if not ok:
                fail += 1
            marker = "OK " if ok else "BAD"
            print(f"{marker} {status:>3} {version:>4} {topic}")
            if not ok:
                print(f"     {url}")
                if final != url:
                    print(f"     -> {final}")
        print()

    print(f"{len(results) - fail} ok / {fail} failed / {len(results)} total")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
