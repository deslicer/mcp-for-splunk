# Entity Integrations in ITSI (4.21) — distilled

> Source: <https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/discover-and-integrate-it-components/4.21>

An **entity integration** is built-in content (search-time logic plus
KPIs) that auto-discovers entities and provides vital metrics and
drilldown dashboards for them. After import, entities show up under
**Entity Overview** in the ITSI UI.

## Entity types of interest

Entities can be virtually anything: physical / virtual / cloud hosts,
network gear, AD or LDAP users, storage volumes, OS processes, application
instances, even cell towers. ITSI is used in IT, OT, and telecom contexts.

## Ways to create entities

| Method                                    | When to use                                                    |
|-------------------------------------------|----------------------------------------------------------------|
| Manual single entity (UI / REST `POST /itoa_interface/entity`) | Smoke tests, one-off entities. |
| CSV bulk import                           | Migrating from a CMDB or sheet of hosts.                       |
| Search-based import (recurring)           | Reading from existing Splunk indexes (`| inputlookup`, `| metasearch`). |
| Built-in entity integrations              | Linux/Unix, Windows, VMware vSphere, Splunk Infrastructure Monitoring. |
| ITSI modules / Content Packs              | Bundled add-ons that ship entities + services + KPIs together. |

> Only users with the `itoa_admin` role can import entities from CSV or
> search. Single-entity creation requires write permissions on the Global
> team.

## Entity Type configuration

Entity types power the Entity Overview UI:

- **Data drilldowns** — filters for the raw events or metrics that
  belong to entities of this type.
- **Dashboard drilldowns** — Splunk XML dashboards (`xml_dashboard`) or
  navigation links (`navigation_link`).
- **Vital metrics** — SPL searches whose `val` field is shown in the
  Entity Overview as a histogram (one metric can be flagged `is_key:
  true`).

A single drilldown can be re-used by many entity types.

## Recurring imports

After your initial bulk import, configure a **recurring import** so that
new infrastructure shows up automatically. Imports can also *retire*
entities when they disappear from the source dataset.

## Best practices

- Decide on a **canonical alias field** (typically `host`) and use it
  uniformly across entity definitions, KPI base searches, and entity
  rules.
- Store **business context** (owner team, environment, region, product
  line) in `informational` aliases. They're filterable in the UI but
  don't participate in identity.
- Keep entity types **broad** (e.g. `Linux`, not `RHEL-9-app-servers`).
  Use `informational` fields and entity rules for sub-grouping.
- For **multi-tenant** ITSI deployments, split entity ownership by team
  via `sec_grp` on services (the entities themselves can only be in the
  Global team).
