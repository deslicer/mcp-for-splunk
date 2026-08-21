"""Tests for published Splunk Help version mapping."""

from src.resources.docs_versions import (
    CLOUD,
    DEFAULT_DOC_VERSION,
    DEFAULT_STUDIO_VERSION,
    ENTERPRISE,
    SUPPORTED_DOC_VERSIONS,
    build_spec_urls,
    build_spl_urls,
    parse_requested_version,
    resolve_enterprise_fallback,
    resolve_help_target,
)


def test_requested_versions_are_first_class() -> None:
    """Every advertised version maps to a published Help token."""
    assert DEFAULT_DOC_VERSION == "10.2"
    assert DEFAULT_STUDIO_VERSION == "10.2"
    for version in SUPPORTED_DOC_VERSIONS:
        target = resolve_help_target(version)
        assert target.requested == version
        assert target.help_version


def test_cloud_trains_use_yymm_tokens() -> None:
    """Unpublished Enterprise 10.x trains resolve to Cloud Help tokens."""
    assert resolve_help_target("10.5").help_version == "10.5.2605"
    assert resolve_help_target("10.5").product == CLOUD
    assert resolve_help_target("10.3").help_version == "10.3.2512"
    assert resolve_help_target("10.1").help_version == "10.1.2507"


def test_enterprise_trains_keep_major_minor() -> None:
    """Published Enterprise books keep major.minor URL tokens."""
    for version in ("10.4", "10.2", "10.0", "9.4", "9.0"):
        target = resolve_help_target(version)
        assert target.help_version == version
        assert target.product == ENTERPRISE


def test_latest_and_patch_versions_normalize() -> None:
    """latest/auto and X.Y.Z collapse to the documented major.minor."""
    assert parse_requested_version("latest") == "10.2"
    assert parse_requested_version("auto") == "10.2"
    assert parse_requested_version("10.5.2605") == "10.5"
    assert parse_requested_version("9.2.1") == "9.2"


def test_enterprise_fallback_for_cloud_only_families() -> None:
    """SPL/spec families fall back to the nearest Enterprise book."""
    assert resolve_enterprise_fallback("10.5").requested == "10.4"
    assert resolve_enterprise_fallback("10.3").requested == "10.2"
    assert resolve_enterprise_fallback("10.1").requested == "10.0"
    assert resolve_enterprise_fallback("10.2").requested == "10.2"


def test_spec_urls_include_9_0_welcome_path() -> None:
    """9.0 specs live under welcome-to-splunk-enterprise-administration."""
    urls = build_spec_urls("indexes.conf", "9.0")
    assert any("welcome-to-splunk-enterprise-administration" in url for url in urls)
    assert any("9.0.0-configuration-file-reference" in url for url in urls)


def test_cloud_spl_url_is_tried_before_enterprise() -> None:
    """10.5 SPL tries Cloud first, then Enterprise 10.4."""
    urls = build_spl_urls("stats", "10.5")
    assert "splunk-cloud-platform" in urls[0]
    assert "10.5.2605" in urls[0]
    assert "splunk-enterprise" in urls[1]
    assert "/10.4/" in urls[1]
