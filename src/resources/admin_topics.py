"""Verified Splunk admin documentation topics.

Admin Manual chapters come from the help.splunk.com TOC under
``/administer/admin-manual/{version}`` (mapped 2026-08-21). Sibling
administer books stay as fallbacks when a topic lives outside that tree.
"""

from __future__ import annotations

from typing import Any

from src.resources.docs_versions import (
    HELP_BASE,
    resolve_enterprise_fallback,
    resolve_help_target,
)

_ADMIN_MANUAL = "en/{product}/administer/admin-manual/{version}"
_ADMIN_MANUAL_9 = f"{_ADMIN_MANUAL}/welcome-to-splunk-enterprise-administration"

# Chapter slugs from the Admin Manual sitemap / left-nav TOC.
ADMIN_TOPICS: dict[str, dict[str, Any]] = {
    "admin-manual": {
        "title": "Admin manual",
        "description": "Splunk Enterprise administration manual overview",
        "path": _ADMIN_MANUAL,
    },
    "configuration-files": {
        "title": "Configuration files",
        "description": "How Splunk configuration files work and how to edit them",
        "path": f"{_ADMIN_MANUAL}/administer-splunk-enterprise-with-configuration-files/about-configuration-files",
        "path_by_version": {
            "9.0": f"{_ADMIN_MANUAL_9}/administer-splunk-enterprise-with-configuration-files/about-configuration-files",
        },
    },
    "users": {
        "title": "User management",
        "description": "Users, roles, language, and session timeouts",
        "path": f"{_ADMIN_MANUAL}/manage-users/about-users-and-roles",
        "fallback_path": "en/{product}/administer/manage-users-and-security/{version}",
    },
    "roles": {
        "title": "Roles",
        "description": "Role-based access control",
        "path": f"{_ADMIN_MANUAL}/manage-users/about-users-and-roles",
        "fallback_path": "en/{product}/administer/manage-users-and-security/{version}",
    },
    "authentication": {
        "title": "Users and authentication",
        "description": "Authentication, users, and roles",
        "path": f"{_ADMIN_MANUAL}/manage-users/about-users-and-roles",
        "fallback_path": "en/{product}/administer/manage-users-and-security/{version}",
    },
    "licenses": {
        "title": "Licenses",
        "description": "How Splunk Enterprise licensing works",
        "path": f"{_ADMIN_MANUAL}/configure-splunk-licenses",
        "path_by_version": {"9.0": f"{_ADMIN_MANUAL_9}/configure-splunk-licenses"},
    },
    "apps": {
        "title": "Apps and add-ons",
        "description": "Meet Splunk apps and add-ons",
        "path": f"{_ADMIN_MANUAL}/meet-splunk-apps",
        "path_by_version": {"9.0": f"{_ADMIN_MANUAL_9}/meet-splunk-apps"},
    },
    "kvstore": {
        "title": "KV store",
        "description": "Administer the app key value store",
        "path": f"{_ADMIN_MANUAL}/administer-the-app-key-value-store",
        "path_by_version": {"9.0": f"{_ADMIN_MANUAL_9}/administer-the-app-key-value-store"},
    },
    "cli": {
        "title": "CLI",
        "description": "Administer Splunk Enterprise with the command line interface",
        "path": f"{_ADMIN_MANUAL}/administer-splunk-enterprise-with-the-command-line-interface-cli",
        "path_by_version": {
            "9.0": f"{_ADMIN_MANUAL_9}/administer-splunk-enterprise-with-the-command-line-interface-cli",
        },
    },
    "start": {
        "title": "Start and initial tasks",
        "description": "Start Splunk Enterprise and perform initial tasks",
        "path": f"{_ADMIN_MANUAL}/start-splunk-enterprise-and-perform-initial-tasks",
        "path_by_version": {"9.0": f"{_ADMIN_MANUAL_9}/start-splunk-enterprise-and-perform-initial-tasks"},
    },
    "security": {
        "title": "Security",
        "description": "Users, roles, and platform security",
        "path": "en/{product}/administer/manage-users-and-security/{version}",
    },
    "clustering": {
        "title": "Indexer clusters",
        "description": "Indexer clusters and high availability",
        "path": "en/{product}/administer/manage-indexers-and-indexer-clusters/{version}",
    },
    "deployment": {
        "title": "Install and upgrade",
        "description": "Installation, upgrade, and deployment",
        "path": "en/{product}/administer/install-and-upgrade/{version}",
        "fallback_path": "en/{product}/get-started/install-and-upgrade/{version}",
    },
    "distributed-search": {
        "title": "Distributed search",
        "description": "Distributed search configuration",
        "path": (
            "en/{product}/administer/distributed-search/{version}/"
            "overview-of-distributed-search/about-distributed-search"
        ),
    },
    "monitor": {
        "title": "Monitoring",
        "description": "Monitor topology and performance of a Splunk deployment",
        "path": "en/{product}/administer/monitor/{version}",
    },
    "indexes": {
        "title": "Index management",
        "description": "Index management and configuration",
        "path": (
            "en/data-management/manage-splunk-enterprise-indexers/{version}/"
            "manage-indexes/about-managing-indexes"
        ),
        "path_by_version": {
            "9.0": (
                "en/data-management/manage-splunk-enterprise-indexers/{version}/"
                "indexing-overview/indexes-indexers-and-indexer-clusters"
            ),
        },
        "fallback_path": "en/{product}/administer/manage-indexers-and-indexer-clusters/{version}",
    },
    "inputs": {
        "title": "Get data in",
        "description": "Data input configuration",
        "path": "en/{product}/get-started/get-data-in/{version}",
    },
}


def normalize_admin_topic(topic: str) -> str:
    """Normalize an admin topic key."""
    return topic.replace("_", "-").lower()


def resolve_admin_topic(topic: str) -> dict[str, Any] | None:
    """Return the verified catalog entry for a topic, or None."""
    return ADMIN_TOPICS.get(normalize_admin_topic(topic))


def list_admin_topics() -> list[dict[str, str]]:
    """Return discovery rows for tools and resources."""
    return [
        {
            "topic": key,
            "title": info["title"],
            "description": info["description"],
            "example_uri": f"splunk-docs://latest/admin/{key}",
        }
        for key, info in ADMIN_TOPICS.items()
    ]


def _format_admin_path(path: str, target) -> str:
    return f"{HELP_BASE}/{path.format(version=target.help_version, product=target.product)}"


def _path_for_target(info: dict[str, Any], target) -> str:
    override = info.get("path_by_version", {}).get(target.requested)
    return override or info["path"]


def _paths_for_target(info: dict[str, Any], target) -> list[str]:
    paths = [_path_for_target(info, target)]
    fallback_path = info.get("fallback_path")
    if fallback_path:
        paths.append(fallback_path)
    return paths


def build_admin_urls(topic: str, version: str) -> list[str]:
    """Build candidate Help URLs for a verified admin topic."""
    info = resolve_admin_topic(topic)
    if info is None:
        return []
    targets = [resolve_help_target(version)]
    fallback = resolve_enterprise_fallback(version)
    if fallback != targets[0]:
        targets.append(fallback)
    urls: list[str] = []
    for target in targets:
        for path in _paths_for_target(info, target):
            urls.append(_format_admin_path(path, target))
    return list(dict.fromkeys(urls))


def build_admin_url(topic: str, version: str) -> str | None:
    """Build the first Help URL for a verified admin topic."""
    urls = build_admin_urls(topic, version)
    return urls[0] if urls else None
