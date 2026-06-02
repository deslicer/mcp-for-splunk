"""Build example/skeleton payloads from object schemas.

Two flavors are produced:

* ``minimal`` — only required fields, ready to fill in.
* ``full`` — every writable field with a typed placeholder, including one
  example item for each subordinate array/object.

Curated, known-good examples are provided for the two showcase object types
(``service`` and ``kpi_base_search``); everything else is generated.
"""

from __future__ import annotations

from typing import Any

from mcp_itsi.knowledge.schema.models import AttributeSpec, ObjectSchema
from mcp_itsi.knowledge.schema.registry import SchemaRegistry
from mcp_itsi.knowledge.schema.registry import registry as _default_registry

_PLACEHOLDERS: dict[str, Any] = {
    "string": "",
    "integer": 0,
    "number": 0,
    "boolean": False,
    "object": {},
    "array": [],
}


def _placeholder(attr: AttributeSpec) -> Any:
    return _PLACEHOLDERS.get(attr.type, "")


def build_skeleton(
    schema: ObjectSchema,
    *,
    mode: str = "minimal",
    schema_registry: SchemaRegistry | None = None,
) -> dict[str, Any]:
    reg = schema_registry or _default_registry
    return _build(schema, mode, reg, _seen=set())


def _build(
    schema: ObjectSchema,
    mode: str,
    reg: SchemaRegistry,
    _seen: set[str],
) -> dict[str, Any]:
    if schema.slug in _seen:
        return {}
    seen = _seen | {schema.slug}
    out: dict[str, Any] = {}
    for attr in schema.attributes:
        if attr.read_only:
            continue
        include = attr.required or mode == "full"
        if not include:
            continue
        if attr.subordinate:
            child = reg.get(attr.subordinate)
            if child is None:
                out[attr.name] = _placeholder(attr)
                continue
            child_skel = _build(child, mode, reg, seen)
            out[attr.name] = [child_skel] if attr.type == "array" else child_skel
        else:
            out[attr.name] = _placeholder(attr)
    return out


# Hand-tuned, valid minimal payloads for the showcase object types.
CURATED_EXAMPLES: dict[str, dict[str, Any]] = {
    "service": {
        "title": "Buttercup Store",
        "description": "Customer-facing storefront.",
        "enabled": 1,
        "sec_grp": "default_itsi_security_group",
        "entity_rules": [
            {
                "rule_condition": "AND",
                "rule_items": [
                    {
                        "field": "category",
                        "rule_type": "matches",
                        "value": "*Web*",
                        "field_type": "alias",
                    }
                ],
            }
        ],
        "kpis": [
            {
                "title": "Average response time",
                "type": "kpi_primary",
                "kpi_base_search": "<kpi_base_search _key>",
                "base_search": "index=web | stats avg(response_time) as response_time by host",
                "threshold_field": "response_time",
                "entity_statop": "avg",
                "aggregate_statop": "avg",
                "alert_on": "aggregate",
                "alert_period": "5",
                "urgency": 5,
                "entity_breakdown_id_field": "host",
            }
        ],
    },
    "kpi_base_search": {
        "title": "Web server response times",
        "description": "Base search powering web latency KPIs.",
        "base_search": "index=web sourcetype=access_combined | stats avg(response_time) as response_time by host",
        "is_entity_breakdown": True,
        "entity_id_fields": "host",
        "entity_alias_filtering_fields": "host",
        "alert_period": "5",
        "search_alert_earliest": "5",
        "metrics": [
            {
                "title": "Average response time",
                "threshold_field": "response_time",
                "aggregate_statop": "avg",
                "entity_statop": "avg",
                "unit": "ms",
            }
        ],
        "sec_grp": "default_itsi_security_group",
    },
}


def examples_for(
    schema: ObjectSchema,
    *,
    schema_registry: SchemaRegistry | None = None,
) -> dict[str, Any]:
    """Return ``{minimal, full, curated?}`` example payloads for a schema."""
    examples: dict[str, Any] = {
        "minimal": build_skeleton(
            schema, mode="minimal", schema_registry=schema_registry
        ),
        "full": build_skeleton(schema, mode="full", schema_registry=schema_registry),
    }
    curated = CURATED_EXAMPLES.get(schema.slug)
    if curated is not None:
        examples["curated"] = curated
    return examples
