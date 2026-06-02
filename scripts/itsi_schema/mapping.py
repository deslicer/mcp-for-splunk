"""Static mapping between schema-doc section titles and ITSI object types.

The ITSI REST API schema page documents object types and their subordinate
data structures using human-readable section titles (e.g. "Service Template",
"Service KPI"). The REST API itself addresses objects by machine ids
(``base_service_template``, and ``kpis`` nested inside ``service``).

This module is the single source of truth for reconciling the two, plus the
``interface`` an object lives under and the nesting relationships used to
validate deeply nested payloads.
"""

from __future__ import annotations

from typing import Final

ITOA_INTERFACE: Final = "/itoa_interface"
EVENT_MGMT_INTERFACE: Final = "/event_management_interface"
MAINTENANCE_INTERFACE: Final = "/maintenance_services_interface"

# Doc section title -> top-level REST object type id.
TOP_LEVEL_OBJECTS: Final[dict[str, str]] = {
    "Entity": "entity",
    "Service": "service",
    "Service Template": "base_service_template",
    "Entity Type": "entity_type",
    "KPI Threshold Templates": "kpi_threshold_template",
    "KPI Base Search": "kpi_base_search",
    "Glass Table": "glass_table",
    "Deep Dive": "deep_dive",
    "Maintenance Calendar": "maintenance_calendar",
    "Event Management State": "event_management_state",
    "Notable Event Group": "notable_event_group",
    "Notable Event Comment": "notable_event_comment",
    "Notable Event Aggregation Policy": "notable_event_aggregation_policy",
    "Notable Event Email Template": "notable_event_email_template",
    "Correlation Search": "correlation_search",
    "Service Analyzer": "home_view",
    "Team": "team",
}

# Doc section title -> subordinate (nested) structure slug.
SUBORDINATE_OBJECTS: Final[dict[str, str]] = {
    "Entity Rules": "entity_rules",
    "Entity Type Dashboard Drilldown": "entity_type_dashboard_drilldown",
    "Entity Type Data Drilldown": "entity_type_data_drilldown",
    "Entity Type Vital Metrics": "entity_type_vital_metrics",
    "Service KPI": "service_kpi",
    "Service Template KPI": "service_template_kpi",
    "KPI Threshold Settings": "kpi_threshold_settings",
    "KPI Threshold Levels": "kpi_threshold_levels",
    "Glass Table Widget Configuration": "glass_table_widget_configuration",
    "Glass Table Icon": "glass_table_icon",
    "Deep Dive Lane Setting": "deep_dive_lane_setting",
    "Time Variate Thresholds Specification": "time_variate_thresholds_specification",
    "Anomaly Detection Algorithm Settings": "anomaly_detection_algorithm_settings",
    "Event Management Export": "event_management_export",
}

# Sections that are not object schemas.
SKIP_SECTIONS: Final[frozenset[str]] = frozenset({"General details"})

# Doc capitalises some fields whose real API name is lower-cased. Most camelCase
# fields (gaugeMin, thresholdValue, severityColor, laneType, ...) are genuine,
# so only known quirks are overridden.
FIELD_NAME_OVERRIDES: Final[dict[str, str]] = {
    "Enabled": "enabled",
    "Time_variate_thresholds_specification": "time_variate_thresholds_specification",
}

# object_type ids that live under the event management interface.
_EVENT_MGMT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "notable_event_group",
        "notable_event_comment",
        "notable_event_aggregation_policy",
        "notable_event_email_template",
        "correlation_search",
        "event_management_state",
    }
)

# Nesting relationships: (parent slug, field name) -> child schema slug.
# Used to embed per-field subordinate references so the runtime validator can
# recurse into nested payloads without a separate map.
NESTING: Final[dict[tuple[str, str], str]] = {
    ("service", "kpis"): "service_kpi",
    ("service", "entity_rules"): "entity_rules",
    ("base_service_template", "kpis"): "service_template_kpi",
    ("base_service_template", "entity_rules"): "entity_rules",
    ("entity_type", "data_drilldown"): "entity_type_data_drilldown",
    ("entity_type", "dashboard_drilldowns"): "entity_type_dashboard_drilldown",
    ("entity_type", "vital_metrics"): "entity_type_vital_metrics",
    ("service_kpi", "entity_thresholds"): "kpi_threshold_settings",
    ("service_kpi", "aggregate_thresholds"): "kpi_threshold_settings",
    ("service_kpi", "time_variate_thresholds_specification"): (
        "time_variate_thresholds_specification"
    ),
    ("service_kpi", "trending_ad"): "anomaly_detection_algorithm_settings",
    ("service_kpi", "cohesive_ad"): "anomaly_detection_algorithm_settings",
    ("service_template_kpi", "entity_thresholds"): "kpi_threshold_settings",
    ("service_template_kpi", "aggregate_thresholds"): "kpi_threshold_settings",
    ("kpi_threshold_settings", "thresholdLevels"): "kpi_threshold_levels",
    ("deep_dive", "lane_settings_collection"): "deep_dive_lane_setting",
}

# Fields that are server-generated/read-only: setting them on create/update is
# a warning, not an error. Keyed by the canonical (lower-cased) field name.
READ_ONLY_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "object_type",
        "create_by",
        "create_source",
        "create_time",
        "mod_source",
        "mod_time",
        "mod_timestamp",
        "_owner",
        "_user",
        "version",
        "_version",
        "acl",
        "identifying_name",
    }
)

# Minimal required fields per object type (conservative; see spec).
REQUIRED_FIELDS: Final[dict[str, tuple[str, ...]]] = {
    "entity": ("title",),
    "service": ("title",),
    "base_service_template": ("title",),
    "entity_type": ("title",),
    "kpi_threshold_template": ("title",),
    "kpi_base_search": ("title",),
    "glass_table": ("title",),
    "deep_dive": ("title",),
    "team": ("title",),
    "correlation_search": ("title",),
}


def interface_for(object_type: str) -> str:
    """Return the REST interface path prefix for a top-level object type."""
    if object_type in _EVENT_MGMT_TYPES:
        return EVENT_MGMT_INTERFACE
    if object_type == "maintenance_calendar":
        return MAINTENANCE_INTERFACE
    return ITOA_INTERFACE
