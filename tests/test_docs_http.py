"""Tests for documentation HTTP cache and fetch helpers."""

from unittest.mock import AsyncMock, patch

import pytest

from src.resources.docs_http import (
    DocsFetchResult,
    DocumentationCache,
    fetch_docs_url,
    fetch_first_ok,
    is_error_doc_content,
    is_soft_404_body,
)


def test_soft_404_help_bodies_are_detected() -> None:
    """help.splunk.com often returns HTTP 200 with a missing-page shell."""
    assert is_soft_404_body("<html><title>Page not found</title></html>")
    assert is_soft_404_body("The page you requested cannot be found.")
    assert not is_soft_404_body("<html><h1>About users and roles</h1></html>")


@pytest.mark.asyncio
async def test_fetch_docs_url_rejects_soft_404(monkeypatch) -> None:
    """A 200 Help shell must not be treated as a successful fetch."""

    class _Response:
        status_code = 200
        text = "<html>Page not found</html>"
        url = "https://help.splunk.com/missing"

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url: str):
            return _Response()

    monkeypatch.setattr("src.resources.docs_http.httpx.AsyncClient", _Client)
    result = await fetch_docs_url("https://help.splunk.com/missing")
    assert result.ok is False
    assert result.error == "Help page looks like a soft 404"


def test_error_markers_are_detected() -> None:
    """404-style markdown must not look like successful documentation."""
    assert is_error_doc_content("# Documentation Not Found\n\nmissing")
    assert is_error_doc_content("# CIM Documentation Not Found\n")
    assert is_error_doc_content("# CIM Documentation Error\n")
    assert not is_error_doc_content("# SPL Command: stats\n\nUsage...")


@pytest.mark.asyncio
async def test_cache_skips_error_bodies() -> None:
    """Failed fetches stay uncached so a later retry can succeed."""
    cache = DocumentationCache(ttl_hours=24)
    fetch = AsyncMock(return_value="# Documentation Not Found\n\n404")

    first = await cache.get_or_fetch("10.0", "admin", "apps", fetch)
    second = await cache.get_or_fetch("10.0", "admin", "apps", fetch)

    assert first.startswith("# Documentation Not Found")
    assert second.startswith("# Documentation Not Found")
    assert fetch.await_count == 2


@pytest.mark.asyncio
async def test_cache_stores_successful_bodies() -> None:
    """Successful documentation is reused until TTL expires."""
    cache = DocumentationCache(ttl_hours=24)
    fetch = AsyncMock(return_value="# About managing indexes\n")

    await cache.get_or_fetch("10.0", "admin", "indexes", fetch)
    await cache.get_or_fetch("10.0", "admin", "indexes", fetch)

    assert fetch.await_count == 1


@pytest.mark.asyncio
async def test_fetch_first_ok_uses_second_candidate() -> None:
    """Candidate lists skip 404s and return the first live page."""
    missing = DocsFetchResult(
        url="https://example.test/missing",
        ok=False,
        status_code=404,
        text="",
        final_url="https://example.test/missing",
    )
    found = DocsFetchResult(
        url="https://example.test/live",
        ok=True,
        status_code=200,
        text="<html>ok</html>",
        final_url="https://example.test/live",
    )

    with patch("src.resources.docs_http.fetch_docs_url", new=AsyncMock(side_effect=[missing, found])):
        result = await fetch_first_ok(["https://example.test/missing", "https://example.test/live"])

    assert result.ok
    assert result.final_url == "https://example.test/live"
