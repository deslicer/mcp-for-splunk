"""Tests for the verified admin documentation catalog."""

from unittest.mock import AsyncMock

import pytest

from src.resources.admin_topics import (
    ADMIN_TOPICS,
    build_admin_url,
    list_admin_topics,
    resolve_admin_topic,
)
from src.resources.splunk_docs import AdminGuideResource


def test_catalog_only_contains_verified_keys() -> None:
    """Guessed administer/{topic} slugs are not advertised."""
    keys = set(ADMIN_TOPICS)
    assert "indexes" in keys
    assert "users" in keys
    assert "configuration-files" in keys
    assert "forwarders" not in keys
    assert "licensing" not in keys


def test_indexes_url_matches_live_help_path() -> None:
    """Index docs stay on the probed data-management path."""
    url = build_admin_url("indexes", "10.0")
    assert url == (
        "https://help.splunk.com/en/data-management/"
        "manage-splunk-enterprise-indexers/10.0/"
        "manage-indexes/about-managing-indexes"
    )


def test_indexes_url_uses_9_0_overview_path() -> None:
    """9.0 index docs live under indexing-overview, not manage-indexes."""
    url = build_admin_url("indexes", "9.0")
    assert url == (
        "https://help.splunk.com/en/data-management/"
        "manage-splunk-enterprise-indexers/9.0/"
        "indexing-overview/indexes-indexers-and-indexer-clusters"
    )


def test_cloud_admin_url_uses_published_token() -> None:
    """10.5 user docs use the Cloud Admin Manual chapter."""
    url = build_admin_url("authentication", "10.5")
    assert url == (
        "https://help.splunk.com/en/splunk-cloud-platform/"
        "administer/admin-manual/10.5.2605/manage-users/about-users-and-roles"
    )


def test_users_url_is_admin_manual_chapter() -> None:
    """User topics resolve under admin-manual/{version}, not a guessed slug."""
    url = build_admin_url("users", "10.4")
    assert url == (
        "https://help.splunk.com/en/splunk-enterprise/"
        "administer/admin-manual/10.4/manage-users/about-users-and-roles"
    )


def test_nine_dot_zero_config_chapter_uses_welcome_prefix() -> None:
    """9.0 nests Admin Manual chapters under welcome-to-splunk-enterprise-administration."""
    url = build_admin_url("configuration-files", "9.0")
    assert url == (
        "https://help.splunk.com/en/splunk-enterprise/"
        "administer/admin-manual/9.0/welcome-to-splunk-enterprise-administration/"
        "administer-splunk-enterprise-with-configuration-files/about-configuration-files"
    )


def test_unknown_topic_returns_none() -> None:
    """Unknown keys do not invent a 404 URL."""
    assert resolve_admin_topic("forwarders") is None
    assert build_admin_url("forwarders", "10.0") is None


def test_list_admin_topics_matches_catalog() -> None:
    """Discovery tools and the catalog stay in lockstep."""
    listed = {row["topic"] for row in list_admin_topics()}
    assert listed == set(ADMIN_TOPICS)


@pytest.mark.asyncio
async def test_unknown_admin_resource_returns_catalog(monkeypatch) -> None:
    """Admin resources refuse to fetch guessed URLs."""
    resource = AdminGuideResource("latest", "forwarders")
    content = await resource.get_content(AsyncMock())
    assert "Topic Not Catalogued" in content
    assert "indexes" in content
    assert "help.splunk.com/en/splunk-enterprise/administer/forwarders" not in content
