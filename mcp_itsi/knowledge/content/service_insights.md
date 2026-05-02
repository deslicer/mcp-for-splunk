# Service Insights in ITSI (4.21) — distilled

> Source: <https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/visualize-and-assess-service-health/4.21/overview>

Service Insights is the core of ITSI: it maps your business and technical
services, monitors them with KPIs, and surfaces health through scores,
glass tables and deep dives.

## Building blocks

### Service

A logical mapping of IT objects that delivers a business outcome (e.g.
"Online Store"). Services contain:

- **KPIs** — recurring saved searches that measure a metric.
- **Entity rules** — describe which entities the service monitors.
- **Service dependencies** — `services_depends_on` and
  `services_depending_on_me` capture upstream / downstream relationships.

### KPI (Key Performance Indicator)

A KPI is a saved search that returns a numeric value at a fixed cadence
(default `cron_schedule`: every 5 minutes). The KPI compares the value to a
threshold to assign a **severity** (info, normal, low, medium, high,
critical) and a colour. Service Health scores aggregate KPI severities.

### Service health score

A weighted average of KPI severities and dependency health. Implemented as
the special `service_health` KPI on every service. Health scores drive the
colours in the Service Analyzer and glass tables.

### Glass tables

Custom canvases combining KPIs, health scores, images, and charts. Useful
for executive dashboards that capture business context (revenue, NPS,
customer-impact metrics) alongside infrastructure metrics.

### Deep dives

Side-by-side views of KPIs and health scores over time. Designed for
incident investigation and root-cause analysis.

### Entities

IT components (hosts, containers, network devices, applications, users,
even cell towers). Entities are added to a service via entity rules at
search time. Entities are *never* services themselves.

### Adaptive thresholds

Statistical thresholds derived from historical KPI data. ITSI recomputes
them nightly so slow drift doesn't generate false alerts. Best for KPIs
whose normal range varies by time of day or day of week.

### Anomaly detection

Generates notable events when a KPI departs from its own historical
behaviour. Models run continuously per KPI. Useful for KPIs whose absolute
value is less interesting than its trend.

## Workflow

```text
1. Define entities          → /itoa_interface/entity
2. Build entity types       → /itoa_interface/entity_type   (data + dashboard drilldowns + vital metrics)
3. Author KPI base searches → /itoa_interface/kpi_base_search
4. Create services          → /itoa_interface/service       (with kpis[] and entity_rules[])
5. Optional: create templates → /itoa_interface/base_service_template (or templatize an existing service)
6. Visualise                → glass_table, home_view (Service Analyzer), deep_dive
7. Alert / triage           → see event-analytics doc
```

## Best practices

- **Start with one critical service.** Onboard one business service end-to-end
  before scaling out. It exposes data quality issues early.
- **Re-use KPI base searches.** A single base search powers many KPIs across
  templates. This is cheaper to compute and easier to maintain.
- **Prefer service templates** for groups of similar services (e.g. all
  Linux hosts). Push template changes via "Sync now" once stabilised.
- **Use adaptive thresholds for time-varying metrics**, static thresholds
  for SLOs and absolutes (e.g. `error_rate > 1%`).
- **Keep entity_id_fields consistent** with entity identifier aliases.
  Mismatched fields are the #1 cause of "no data" KPIs.
- **Tag services** (`service_tags.tags`) by team, region, environment. ITSI
  search filters and the home view rely on tags heavily.
