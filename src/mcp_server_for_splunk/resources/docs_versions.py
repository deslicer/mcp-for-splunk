"""Published Splunk Help version mapping.

help.splunk.com does not publish every requested major.minor on
``splunk-enterprise``. Cloud-only trains use a YYMM token
(``10.5.2605``, ``10.3.2512``, ``10.1.2507``). Families that Cloud does
not host (SPL, troubleshooting, .conf specs) fall back to the nearest
Enterprise book.
"""

from __future__ import annotations

from dataclasses import dataclass

HELP_BASE = "https://help.splunk.com"
ENTERPRISE = "splunk-enterprise"
CLOUD = "splunk-cloud-platform"

# Versions agents may request. Probed 2026-08-21.
SUPPORTED_DOC_VERSIONS = (
    "10.5",
    "10.4",
    "10.3",
    "10.2",
    "10.1",
    "10.0",
    "9.4",
    "9.3",
    "9.2",
    "9.1",
    "9.0",
)

DEFAULT_DOC_VERSION = "10.2"
DEFAULT_STUDIO_VERSION = "10.2"


@dataclass(frozen=True)
class HelpTarget:
    """Resolved help.splunk.com product + version token."""

    requested: str
    help_version: str
    product: str
    spec_full: str


# Exact Help tokens that return HTTP 200 for Studio (and most admin books).
_PUBLISHED: dict[str, HelpTarget] = {
    "10.5": HelpTarget("10.5", "10.5.2605", CLOUD, "10.5.2605"),
    "10.4": HelpTarget("10.4", "10.4", ENTERPRISE, "10.4.0"),
    "10.3": HelpTarget("10.3", "10.3.2512", CLOUD, "10.3.2512"),
    "10.2": HelpTarget("10.2", "10.2", ENTERPRISE, "10.2.0"),
    "10.1": HelpTarget("10.1", "10.1.2507", CLOUD, "10.1.2507"),
    "10.0": HelpTarget("10.0", "10.0", ENTERPRISE, "10.0.0"),
    "9.4": HelpTarget("9.4", "9.4", ENTERPRISE, "9.4.0"),
    "9.3": HelpTarget("9.3", "9.3", ENTERPRISE, "9.3.0"),
    "9.2": HelpTarget("9.2", "9.2", ENTERPRISE, "9.2.0"),
    "9.1": HelpTarget("9.1", "9.1", ENTERPRISE, "9.1.0"),
    "9.0": HelpTarget("9.0", "9.0", ENTERPRISE, "9.0.0"),
}

# Cloud trains without Enterprise books for SPL / specs / troubleshooting.
_ENTERPRISE_FALLBACK = {
    "10.5": "10.4",
    "10.3": "10.2",
    "10.1": "10.0",
}


def parse_requested_version(version: str) -> str:
    """Normalize a version string to major.minor, or the default."""
    if version in {"latest", "auto", ""}:
        return DEFAULT_DOC_VERSION
    parts = version.split(".")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        requested = f"{parts[0]}.{parts[1]}"
        if requested in _PUBLISHED:
            return requested
    return DEFAULT_DOC_VERSION


def resolve_help_target(version: str) -> HelpTarget:
    """Resolve a requested version to the published Help target."""
    return _PUBLISHED[parse_requested_version(version)]


def resolve_enterprise_fallback(version: str) -> HelpTarget:
    """Nearest Enterprise Help target when a Cloud book is missing."""
    requested = parse_requested_version(version)
    fallback = _ENTERPRISE_FALLBACK.get(requested, requested)
    return _PUBLISHED[fallback]


def is_doc_version(value: str) -> bool:
    """Return True when value is a supported major.minor docs version."""
    return parse_requested_version(value) == value or value in _PUBLISHED


def version_mapping() -> dict[str, str]:
    """Compatibility map used by older SplunkDocsResource callers."""
    mapping = {version: version for version in SUPPORTED_DOC_VERSIONS}
    mapping["latest"] = DEFAULT_DOC_VERSION
    mapping["auto"] = DEFAULT_DOC_VERSION
    for version in SUPPORTED_DOC_VERSIONS:
        mapping[f"{version}.0"] = version
    mapping["9.2.1"] = "9.2"
    return mapping


def build_spl_urls(command: str, version: str) -> list[str]:
    """Candidate SPL command Help URLs, Cloud first then Enterprise."""
    command_lower = command.lower()
    targets = _unique_targets(version)
    return [
        (
            f"{HELP_BASE}/en/{target.product}/search/spl-search-reference/"
            f"{target.help_version}/search-commands/{command_lower}"
        )
        for target in targets
    ]


def build_troubleshooting_urls(url_path: str, version: str) -> list[str]:
    """Candidate troubleshooting Help URLs, Cloud first then Enterprise."""
    targets = _unique_targets(version)
    return [
        (
            f"{HELP_BASE}/en/{target.product}/administer/troubleshoot/"
            f"{target.help_version}/{url_path}"
        )
        for target in targets
    ]


def build_spec_urls(config: str, version: str) -> list[str]:
    """Candidate .conf spec Help URLs (Enterprise books only)."""
    target = resolve_enterprise_fallback(version)
    minor = target.help_version
    tokens = _spec_patch_tokens(target)
    if target.requested == "9.0":
        return [
            (
                f"{HELP_BASE}/en/splunk-enterprise/administer/admin-manual/{minor}/"
                f"welcome-to-splunk-enterprise-administration/"
                f"configuration-file-reference/{token}-configuration-file-reference/{config}"
            )
            for token in tokens
        ] + [
            (
                f"{HELP_BASE}/en/data-management/splunk-enterprise-admin-manual/{minor}/"
                f"welcome-to-splunk-enterprise-administration/"
                f"configuration-file-reference/9.0.10-configuration-file-reference/{config}"
            ),
        ]
    urls: list[str] = []
    for token in tokens:
        urls.append(
            f"{HELP_BASE}/en/splunk-enterprise/administer/admin-manual/{minor}/"
            f"configuration-file-reference/{token}-configuration-file-reference/{config}"
        )
        urls.append(
            f"{HELP_BASE}/en/data-management/splunk-enterprise-admin-manual/{minor}/"
            f"configuration-file-reference/{token}-configuration-file-reference/{config}"
        )
    return urls


def _spec_patch_tokens(target: HelpTarget) -> list[str]:
    """Try newest published patch specs first (10.4.2, then 10.4.1, then 10.4.0)."""
    parts = target.spec_full.split(".")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        return [f"{parts[0]}.{parts[1]}.{patch}" for patch in (2, 1, 0)]
    return [target.spec_full]


def _unique_targets(version: str) -> list[HelpTarget]:
    primary = resolve_help_target(version)
    fallback = resolve_enterprise_fallback(version)
    if fallback.help_version == primary.help_version and fallback.product == primary.product:
        return [primary]
    return [primary, fallback]
