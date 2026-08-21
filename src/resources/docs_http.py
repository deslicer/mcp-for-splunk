"""HTTP fetch and cache helpers for Splunk documentation resources."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

logger = logging.getLogger(__name__)

DOC_ERROR_MARKERS = (
    "# Documentation Not Found",
    "# CIM Documentation Not Found",
    "# CIM Documentation Error",
    "# Documentation Error",
    "# Documentation Unavailable",
    "# Configuration Spec Not Found",
)

HELP_SOFT_404_MARKERS = (
    "page not found",
    "the page you requested cannot be found",
    "we couldn't find that page",
    "documentation not found",
)

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def is_error_doc_content(content: str) -> bool:
    """Return True when content is a fetch failure, not live documentation."""
    heading = content.lstrip().splitlines()[0] if content.strip() else ""
    return heading in DOC_ERROR_MARKERS


def is_soft_404_body(text: str) -> bool:
    """Return True when a 200 Help body is a missing-page shell."""
    sample = text[:4000].lower()
    return any(marker in sample for marker in HELP_SOFT_404_MARKERS)


@dataclass(frozen=True)
class DocsFetchResult:
    """Outcome of a documentation HTTP GET."""

    url: str
    ok: bool
    status_code: int | None
    text: str
    final_url: str
    error: str | None = None


class DocumentationCache:
    """In-memory TTL cache that never stores 404/error documentation bodies."""

    def __init__(self, ttl_hours: int = 24):
        self.cache: dict[str, dict[str, Any]] = {}
        self.ttl_hours = ttl_hours

    def cache_key(self, version: str, category: str, topic: str) -> str:
        """Generate cache key for documentation."""
        return f"docs_{version}_{category}_{topic}"

    def is_expired(self, timestamp: datetime) -> bool:
        """Check if cached item is expired."""
        return datetime.now() - timestamp > timedelta(hours=self.ttl_hours)

    async def get_or_fetch(
        self, version: str, category: str, topic: str, fetch_func: Callable[[], Awaitable[str]]
    ) -> str:
        """Get from cache or fetch if expired/missing. Skip caching error pages."""
        key = self.cache_key(version, category, topic)

        if key in self.cache:
            cached_item = self.cache[key]
            if not self.is_expired(cached_item["timestamp"]):
                logger.debug("Cache hit for %s", key)
                return cached_item["content"]

        logger.debug("Cache miss for %s, fetching", key)
        content = await fetch_func()
        if not is_error_doc_content(content):
            self.cache[key] = {
                "content": content,
                "timestamp": datetime.now(),
                "version": version,
            }
        else:
            logger.debug("Not caching error content for %s", key)

        return content

    def invalidate_version(self, version: str) -> None:
        """Invalidate all cached docs for a specific version."""
        keys_to_remove = [k for k in self.cache if k.startswith(f"docs_{version}_")]
        for key in keys_to_remove:
            del self.cache[key]
        logger.info("Invalidated %s cache entries for version %s", len(keys_to_remove), version)


async def fetch_docs_url(url: str, timeout: float = 30.0) -> DocsFetchResult:
    """GET a documentation URL with browser-like headers and redirects."""
    if not HAS_HTTPX:
        return DocsFetchResult(
            url=url,
            ok=False,
            status_code=None,
            text="",
            final_url=url,
            error="httpx is not installed",
        )

    try:
        async with httpx.AsyncClient(
            timeout=timeout, headers=BROWSER_HEADERS, follow_redirects=True
        ) as client:
            response = await client.get(url)
            soft_404 = response.status_code == 200 and is_soft_404_body(response.text)
            return DocsFetchResult(
                url=url,
                ok=response.status_code == 200 and not soft_404,
                status_code=response.status_code,
                text=response.text,
                final_url=str(response.url),
                error="Help page looks like a soft 404" if soft_404 else None,
            )
    except httpx.HTTPError as exc:
        logger.error("Error fetching documentation from %s: %s", url, exc)
        return DocsFetchResult(
            url=url,
            ok=False,
            status_code=None,
            text="",
            final_url=url,
            error=str(exc),
        )


async def fetch_first_ok(urls: list[str], timeout: float = 30.0) -> DocsFetchResult:
    """Try URLs in order and return the first live page (not a soft 404)."""
    last = DocsFetchResult(
        url=urls[0] if urls else "",
        ok=False,
        status_code=None,
        text="",
        final_url=urls[0] if urls else "",
        error="No documentation URLs provided",
    )
    for url in urls:
        last = await fetch_docs_url(url, timeout=timeout)
        if last.ok:
            return last
        logger.debug("Documentation URL failed (%s): %s", last.status_code, url)
    return last
