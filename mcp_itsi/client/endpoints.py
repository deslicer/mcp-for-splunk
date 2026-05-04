"""Canonical paths for the ITSI REST API.

Keeping the URL fragments in one place makes it easy to audit the surface
area we expose, and reduces the chance of typos in tools.

Reference: ITSI 4.21 REST API reference
https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-reference/itsi-rest-api-reference
"""

from __future__ import annotations

from typing import Final

ITOA_INTERFACE: Final[str] = "/itoa_interface"
EVENT_MGMT_INTERFACE: Final[str] = "/event_management_interface"
MAINTENANCE_INTERFACE: Final[str] = "/maintenance_services_interface"
BACKUP_INTERFACE: Final[str] = "/backup_restore_interface"

ITOA_OBJECT_TYPES: Final[tuple[str, ...]] = (
    "team",
    "entity",
    "service",
    "base_service_template",
    "kpi_base_search",
    "deep_dive",
    "glass_table",
    "home_view",
    "kpi_template",
    "kpi_threshold_template",
    "event_management_state",
    "entity_filter_rule",
    "entity_type",
    "custom_threshold_windows",
    "kpi_entity_threshold",
)

EVENT_MGMT_OBJECT_TYPES: Final[tuple[str, ...]] = (
    "notable_event",
    "notable_event_group",
    "notable_event_comment",
    "notable_event_aggregation_policy",
    "notable_event_email_template",
    "correlation_search",
)


def itoa_collection(object_type: str) -> str:
    """Return the path for a collection of ITOA objects, e.g. ``/itoa_interface/service``."""
    return f"{ITOA_INTERFACE}/{object_type}"


def itoa_item(object_type: str, key: str) -> str:
    """Return the path for a single ITOA object."""
    return f"{ITOA_INTERFACE}/{object_type}/{key}"


def itoa_count(object_type: str) -> str:
    return f"{ITOA_INTERFACE}/{object_type}/count"


def itoa_bulk_update(object_type: str) -> str:
    return f"{ITOA_INTERFACE}/{object_type}/bulk_update"


def itoa_templatize(object_type: str, key: str) -> str:
    return f"{ITOA_INTERFACE}/{object_type}/{key}/templatize"


def event_collection(object_type: str) -> str:
    return f"{EVENT_MGMT_INTERFACE}/{object_type}"


def event_item(object_type: str, key: str) -> str:
    return f"{EVENT_MGMT_INTERFACE}/{object_type}/{key}"
