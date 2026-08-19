"""Shared saved-search helpers used by alert create/update/delete tools."""

from __future__ import annotations

from typing import Any, Literal

from src.core.utils import sanitize_search_query
from src.tools.search.saved_search_tools import (
    DEFAULT_SAVED_SEARCH_APP,
    _apply_saved_search_namespace,
    _find_saved_search,
    _namespace_for_saved_search_create,
)

SharingLevel = Literal["user", "app", "global"]


def default_alert_app() -> str:
    return DEFAULT_SAVED_SEARCH_APP


def find_alert_saved_search(
    service: Any,
    name: str,
    app: str | None = None,
    owner: str | None = None,
) -> Any | None:
    return _find_saved_search(service, name, app, owner)


def namespace_for_create(*, app: str, owner: str, sharing: SharingLevel) -> Any:
    return _namespace_for_saved_search_create(app=app, owner=owner, sharing=sharing)


def apply_saved_search_namespace(service: Any, saved_search: Any) -> Any:
    return _apply_saved_search_namespace(service, saved_search)


def create_alert_config(
    *,
    search: str,
    description: str,
    earliest_time: str,
    latest_time: str,
    cron_schedule: str,
    is_visible: bool,
    alert_type: str,
    alert_comparator: str,
    alert_threshold: str,
    alert_condition: str,
    alert_track: bool,
    alert_severity: int,
    alert_digest_mode: bool,
) -> dict[str, str]:
    config = {
        "search": sanitize_search_query(search),
        "description": description,
        "is_visible": "1" if is_visible else "0",
        "is_scheduled": "1",
        "cron_schedule": cron_schedule,
        "alert_type": alert_type,
        "alert_comparator": alert_comparator,
        "alert_threshold": str(alert_threshold),
        "alert.track": "1" if alert_track else "0",
        "alert.severity": str(alert_severity),
        "alert.digest_mode": "1" if alert_digest_mode else "0",
    }
    if earliest_time:
        config["dispatch.earliest_time"] = earliest_time
    if latest_time:
        config["dispatch.latest_time"] = latest_time
    if alert_condition:
        config["alert_condition"] = alert_condition
    return config
