# ITSI MCP Knowledge Bundle

This bundle contains curated, distilled documentation for Splunk IT Service
Intelligence (ITSI) 4.21 (with the legacy 4.18 modules manual where current
docs no longer exist). Every entry is also available via the
`itsi_read_doc` tool.

## Map of contents

| Slug                       | Subject                                                               |
|----------------------------|-----------------------------------------------------------------------|
| `overview`                 | This document.                                                        |
| `api/reference`            | ITOA / Event Management / Maintenance / Backup REST endpoints.        |
| `api/schema`               | JSON shapes for every supported ITSI object type.                     |
| `service-insights`         | Services, KPIs, glass tables, deep dives, adaptive thresholds.        |
| `entity-integrations`      | Entities, entity types, OS / vSphere / SIM integrations.              |
| `event-analytics`          | Notable events, correlation searches, aggregation policies, episodes. |
| `modules`                  | Legacy modules and the Splunk App for Content Packs.                  |
| `best-practices`           | Implementation playbook distilled from Splunk recommendations.        |
| `cookbook/header-auth`     | Header-based authentication recipe for the MCP server.                |

## How agents should use this bundle

1. Start with `overview` to see what is available.
2. When the user asks "how do I do X in ITSI?", call `itsi_search_docs`
   with a few keywords from the request and read the top hit.
3. Before calling **mutating** tools (`itsi_create_*`, `itsi_update_*`,
   `itsi_delete_*`) check `api/schema` to make sure the payload is well
   formed.
4. For workflow-level guidance, prefer `service-insights`, `entity-integrations`
   or `event-analytics` over the raw API docs.

## Versioning

The corpus targets ITSI **4.21** for everything except modules, which only
has a 4.18 manual page. ITSI modules are being phased out in favour of
content packs — see `modules` for the migration story.
