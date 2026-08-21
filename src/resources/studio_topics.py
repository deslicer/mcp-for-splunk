"""Dashboard Studio topic catalog and versioned Help URLs."""

from __future__ import annotations

from typing import Any

from src.resources.docs_versions import (
    DEFAULT_STUDIO_VERSION,
    HELP_BASE,
    parse_requested_version,
    resolve_help_target,
)

DASHBOARD_STUDIO_TOPICS: dict[str, dict[str, Any]] = {
    "cheatsheet": {
        "name": "Dashboard Studio Cheatsheet",
        "description": "Comprehensive cheatsheet with definition schema, examples, and best practices",
        "file": "dashboard_studio_cheatsheet.md",
        "tags": ["cheatsheet", "reference", "quick-reference"],
    },
    "definition": {
        "name": "Dashboard Definition Structure",
        "description": "Complete dashboard definition schema and required fields",
        "paths": ["source-code-editor/what-is-a-dashboard-definition"],
        "tags": ["definition", "schema", "structure"],
    },
    "visualizations": {
        "name": "Visualizations Guide",
        "description": "Adding and formatting visualizations in Dashboard Studio",
        "paths": ["visualizations/add-and-format-visualizations"],
        "tags": ["visualizations", "formatting", "configuration"],
    },
    "configuration": {
        "name": "Visualization Configuration Options",
        "description": "Complete reference of visualization configuration options",
        "paths": [
            "configuration-options-reference/visualization-configuration-options",
            "configuration-options-reference/object-options-and-defaults-reference",
        ],
        "tags": ["configuration", "options", "reference"],
    },
    "datasources": {
        "name": "Data Sources Guide",
        "description": "Using ds.search, ds.savedSearch, and ds.chain data sources",
        "paths": ["use-data-sources/create-search-based-visualizations-with-ds.search"],
        "tags": ["datasources", "search", "data"],
    },
    "framework": {
        "name": "Dashboard Framework Introduction",
        "description": "Introduction to Dashboard Framework concepts and architecture",
        "paths": [
            "introduction-to-splunk-dashboard-studio/what-is-splunk-dashboard-studio",
            "introduction-to-splunk-dashboard-studio/create-a-dashboard-in-dashboard-studio",
            "create-a-dashboard-in-dashboard-studio/create-a-dashboard-in-dashboard-studio",
        ],
        "tags": ["framework", "introduction", "concepts"],
    },
}


def build_studio_urls(topic: str, version: str = DEFAULT_STUDIO_VERSION) -> list[str]:
    """Build candidate Dashboard Studio Help URLs for a topic and version."""
    info = DASHBOARD_STUDIO_TOPICS.get(topic, {})
    paths = info.get("paths") or []
    if not paths:
        return []
    target = resolve_help_target(version)
    return [
        (
            f"{HELP_BASE}/en/{target.product}/create-dashboards-and-reports/"
            f"dashboard-studio/{target.help_version}/{path}"
        )
        for path in paths
    ]


def default_studio_url(topic: str) -> str:
    """Default (10.2) Help URL for discovery listings."""
    urls = build_studio_urls(topic, DEFAULT_STUDIO_VERSION)
    return urls[0] if urls else ""


def parse_studio_ref(path: str) -> tuple[str, str]:
    """Split ``[version/]topic`` into ``(topic, version)``."""
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 2:
        candidate = parts[0]
        if parse_requested_version(candidate) == candidate:
            return parts[1], candidate
    return path, DEFAULT_STUDIO_VERSION


for _topic, _info in DASHBOARD_STUDIO_TOPICS.items():
    if "file" not in _info:
        _info["url"] = default_studio_url(_topic)
