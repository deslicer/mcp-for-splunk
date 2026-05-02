# ITSI REST API schema (4.21) — distilled

> Source: <https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-schema/itsi-rest-api-schema>

ITSI stores its configuration in the splunkd KV store. **Do not** write to
the KV store directly — always go through the REST endpoints documented in
the API reference. This file lists the JSON shapes you'll most often need.

## Common attributes

Every ITSI object has these system fields (omitted from the per-type schemas
below to keep them readable):

| Field           | Type   | Notes                                                  |
|-----------------|--------|--------------------------------------------------------|
| `object_type`   | string | E.g. `service`, `entity`.                              |
| `create_by`     | string | Splunk user that created the object.                   |
| `create_time`   | string | UTC timestamp.                                         |
| `mod_source`    | string | `manual` for user actions.                             |
| `mod_time`      | string | UTC timestamp of the last modification.                |
| `_owner`        | string | Always `nobody`.                                       |
| `_user`         | string | Last user that touched the object.                     |
| `version`       | string | Same as the ITSI app version.                          |

## entity

```json
{
  "_key": "<uuid>",
  "title": "mysql-04",
  "description": "",
  "object_type": "entity",
  "identifier": { "fields": ["host"], "values": ["mysql-04"] },
  "informational": { "fields": ["itsi_role"], "values": ["operating_system_host"] },
  "services": [ { "_key": "<service-uuid>", "title": "Database Service" } ],
  "entity_type_ids": ["<entity-type-uuid>"],
  "sec_grp": "default_itsi_security_group"
}
```

`entity` may belong only to the Global team
(`default_itsi_security_group`).

## service

```json
{
  "_key": "<uuid>",
  "title": "Buttercup Store",
  "description": "Customer-facing storefront.",
  "kpis": [ /* Service KPI objects, see below */ ],
  "entity_rules": [
    {
      "rule_condition": "AND",
      "rule_items": [
        { "field": "category", "rule_type": "matches", "value": "*Web*", "field_type": "alias" }
      ]
    }
  ],
  "services_depends_on": [
    { "service_id": "<id>", "kpis_depending_on": ["<kpi-id>"] }
  ],
  "services_depending_on_me": [],
  "enabled": 1,
  "sec_grp": "default_itsi_security_group",
  "base_service_template_id": "",
  "service_tags": { "tags": ["unix", "seattle"], "template_tags": ["cloud_systems"] }
}
```

## base_service_template

```json
{
  "_key": "<uuid>",
  "title": "Web Server (template)",
  "description": "Reusable KPI bundle for web servers.",
  "kpis": [ /* Service Template KPI objects */ ],
  "entity_rules": [ /* same shape as service */ ],
  "service_id": "<service-uuid-this-was-derived-from>",
  "sec_grp": "default_itsi_security_group",
  "linked_services": [ /* abbreviated service objects */ ],
  "total_linked_services": 12,
  "sync_status": "synced",
  "scheduled_time": null,
  "scheduled_job": {},
  "template_tags": ["web", "infra"]
}
```

`base_service_template` belongs only to the Global team.

## entity_rules

Top level: array of OR'd rule groups. Each group AND's `rule_items`.

```json
[
  {
    "rule_condition": "AND",
    "rule_items": [
      { "field": "title",   "rule_type": "matches", "value": "Foo",       "field_type": "title" },
      { "field": "category","rule_type": "matches", "value": "*Bar*",     "field_type": "alias" },
      { "field": "subcat",  "rule_type": "not",     "value": "Foo",       "field_type": "info"  }
    ]
  }
]
```

`rule_type` accepts `matches`, `not`, `matchesblank`, `doesnotmatchblank`.

## entity_type

```json
{
  "_key": "<uuid>",
  "title": "Linux",
  "description": "Linux hosts.",
  "data_drilldown": [
    { "title": "syslog", "type": "events",
      "static_filter": { "sourcetype": "linux_syslog" },
      "entity_field_filter": ["host"] }
  ],
  "dashboard_drilldowns": [
    { "title": "Linux dashboard", "id": "linux_overview",
      "is_splunk_dashboard": true, "dashboard_type": "xml_dashboard",
      "params": { "host": "$alias.host$" } }
  ],
  "vital_metrics": [
    {
      "metric_name": "Average CPU usage",
      "search": "| mstats avg(cpu.usage) WHERE index=os ... by host span=5m",
      "split_by_fields": ["host"],
      "matching_entity_fields": ["host"],
      "is_key": true,
      "unit": "%",
      "alert_rule": {
        "is_enabled": true, "cron_schedule": "*/5 * * * *",
        "critical_threshold": "90", "warning_threshold": "75"
      }
    }
  ]
}
```

## Service KPI (`service.kpis[]`)

```json
{
  "_key": "<kpi-uuid>",
  "title": "ServiceHealthScore",
  "type": "service_health",
  "kpi_base_search": "<base-search-uuid>",
  "search_type": "shared_base",
  "base_search": "...",
  "threshold_field": "aggregate",
  "entity_statop": "avg",
  "aggregate_statop": "avg",
  "urgency": 11,
  "cron_schedule": "*/5 * * * *",
  "alert_on": "both",
  "is_entity_breakdown": true,
  "entity_id_fields": "host",
  "entity_alias_filtering_fields": null,
  "entity_thresholds": { /* threshold object */ },
  "aggregate_thresholds": { /* threshold object */ },
  "kpi_threshold_template_id": "<template-uuid>",
  "time_variate_thresholds": false,
  "time_variate_thresholds_specification": { "policies": { "default_policy": { "title": "Default" } } },
  "anomaly_detection_is_enabled": false,
  "anomaly_detection_alerting_enabled": false,
  "alert_lag": "30"
}
```

## Notable event (Event Management)

Notable events are addressed by `event_id` (string) under
`/event_management_interface/notable_event/<event_id>`. Important fields:

- `severity` — integer, 1=info, 6=critical
- `status` — integer, 0=unassigned, 1=new, 2=in progress, 3=pending, 4=resolved, 5=closed
- `owner` — Splunk user assigned to the event
- `service_ids` / `service_titles` — affected services
- `description`, `title`, `event_identifier_hash`
- `drilldown_search_*` and `drilldown_uri` for triage

Aggregation policies (`notable_event_aggregation_policy`) carry filter
criteria, group titles, and action rules. Correlation searches
(`correlation_search`) are saved searches in `splunk_search` that produce
notable events.
