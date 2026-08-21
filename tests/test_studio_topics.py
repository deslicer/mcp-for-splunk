"""Tests for versioned Dashboard Studio Help URLs."""

from src.resources.studio_topics import (
    build_studio_urls,
    default_studio_url,
    parse_studio_ref,
)


def test_default_datasources_url_is_10_2() -> None:
    """Unversioned Studio datasources default to Enterprise 10.2."""
    url = default_studio_url("datasources")
    assert "/dashboard-studio/10.2/" in url
    assert "create-search-based-visualizations-with-ds.search" in url
    assert "splunk-enterprise" in url


def test_studio_datasources_urls_cover_requested_versions() -> None:
    """Each advertised version produces a concrete datasources Help URL."""
    expected = {
        "10.5": ("splunk-cloud-platform", "10.5.2605"),
        "10.4": ("splunk-enterprise", "10.4"),
        "10.3": ("splunk-cloud-platform", "10.3.2512"),
        "10.2": ("splunk-enterprise", "10.2"),
        "10.1": ("splunk-cloud-platform", "10.1.2507"),
        "10.0": ("splunk-enterprise", "10.0"),
        "9.4": ("splunk-enterprise", "9.4"),
        "9.3": ("splunk-enterprise", "9.3"),
        "9.2": ("splunk-enterprise", "9.2"),
        "9.1": ("splunk-enterprise", "9.1"),
        "9.0": ("splunk-enterprise", "9.0"),
    }
    for version, (product, token) in expected.items():
        urls = build_studio_urls("datasources", version)
        assert urls
        assert f"/{product}/" in urls[0]
        assert f"/dashboard-studio/{token}/" in urls[0]


def test_parse_studio_ref_accepts_version_prefix() -> None:
    """URI paths can carry an explicit version segment."""
    assert parse_studio_ref("datasources") == ("datasources", "10.2")
    assert parse_studio_ref("10.5/datasources") == ("datasources", "10.5")
