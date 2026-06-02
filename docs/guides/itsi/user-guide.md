# ITSI MCP Server — User Guide

This guide shows how to **drive the ITSI MCP server effectively** — whether you're an operator prompting an AI client or an LLM agent calling tools directly. It assumes you already have a server running and connected; if not, start with [Getting Started](getting-started.md).

The server exposes **73 `itsi_*` tools**, **27 read-only resources**, and **3 workflow prompts** against Splunk IT Service Intelligence (ITSI 4.21).

> **Agents:** read the bundled [`itsi://llms.txt`](../../../mcp_itsi/llms.txt) resource first — it's the condensed version of this guide.

## The mental model

ITSI configuration objects (called **ITOA objects**) are **deeply nested JSON documents**:

- A **service** contains `kpis[]` (KPI definitions) and `entity_rules[]` (which entities belong to it).
- A **KPI** references a `kpi_base_search` and carries threshold settings.
- An **entity** is matched to services by alias fields (`host`, `ip`, ...).
- **Notable events** are produced by **correlation searches** and grouped by **aggregation policies** into episodes.

Every object is addressed by a `_key` (notable events use `event_id`). The nesting is why hand-written payloads fail: a single misspelled or invented field name is rejected by ITSI. The fix is to always work **schema-first**.

## The golden path

Follow these five steps for **every** create or update. They turn an error-prone guess into a validated write.

1. **Discover** — `itsi_list_object_schemas` lists every object type, its REST endpoint, required fields, and nested objects.
2. **Get the schema** — `itsi_get_object_schema(object_type)` returns every documented field with type and description, inlined schemas for nested objects, a derived JSON Schema, and example payloads (minimal, full, curated). Add `include_live_example=true` to copy the exact shape of a real object from your instance.
3. **Build** the payload from the returned examples — never invent field names.
4. **Validate** — `itsi_validate_object_payload(object_type, payload)` dry-runs validation without writing. Fix every `error`; review every `warning`.
5. **Write** — `itsi_create_*` / `itsi_update_*`. The server re-validates: hard errors block *before* the API call and return `validation_errors`; warnings come back inline under `validation_warnings`.

```text
itsi_list_object_schemas  →  itsi_get_object_schema  →  itsi_validate_object_payload  →  itsi_create_* / itsi_update_*
        (discover)                 (learn the shape)            (dry-run check)                  (write, re-validated)
```

## Reading data

All `itsi_list_*` tools share a common, efficient query interface.

| Parameter | Purpose | Example |
|---|---|---|
| `filter_query` | MongoDB-style filter (object or JSON string) | `{"title": {"$regex": ".*Web.*"}}` |
| `fields` | Comma-separated projection to shrink responses | `"title,_key,enabled"` |
| `limit` / `offset` | Pagination | `limit=50, offset=100` |
| `sort_key` / `sort_dir` | Ordering (`1` asc, `-1` desc) | `sort_key="title"` |

**Resolve a `_key` first.** Before `itsi_get_*`, `itsi_update_*`, or `itsi_delete_*`, list or count to find the object's `_key`. Use `itsi_count_services` (and similar) when you only need a number.

```jsonc
// "List the 10 most recently modified services that are enabled, titles only"
itsi_list_services({
  "filter_query": { "enabled": 1 },
  "fields": "title,_key",
  "sort_key": "mod_time",
  "sort_dir": -1,
  "limit": 10
})
```

## Creating and updating safely

### Partial vs. full updates

`itsi_update_*` is **partial by default** — only the fields you send change. Set `is_partial=false` for a full overwrite of the document.

### The GET → merge → PUT pattern

Some ITSI endpoints validate the **entire** document even on a partial update. If a partial update returns a 5xx, fall back to:

1. `itsi_get_<object>(key)` to fetch the current document.
2. Merge your changes into it locally.
3. `itsi_update_<object>(key, merged, is_partial=false)` to write it back whole.

### What the validator catches

`itsi_validate_object_payload` and the write-path pre-flight recurse into nested objects (service KPIs, entity rules, threshold settings) and report two severities:

- **Errors (block the write):** unknown or misspelled fields (with a "did you mean?" suggestion), wrong types, and missing required fields.
- **Warnings (allowed, surfaced inline):** read-only/server-generated fields (`_key`, `object_type`, `create_time`, `mod_time`, `acl`, ...) and fields not in the documented 4.21 schema.

Booleans accept either `true/false` or `1/0` — ITSI uses both.

## Recipes

### Create a service with a KPI

```text
1. itsi_get_object_schema("service", include_live_example=true)
   → study `kpis[]` (a "service_kpi" subordinate) and `entity_rules[]`.
2. (If using a shared base search) itsi_list_kpi_base_searches → pick a _key.
3. Build the service payload from the curated example.
4. itsi_validate_object_payload("service", payload)  → fix errors.
5. itsi_create_service(payload)  → note the returned _key and any validation_warnings.
```

### Onboard an entity

Entities match services via alias fields. **Every field named in `identifier.fields` must also appear at the document root**, as a list:

```jsonc
itsi_create_entity({
  "title": "web-1",
  "identifier": { "fields": ["host"], "values": ["web-1"] },
  "host": ["web-1"]            // required: mirrors identifier.fields
})
```

### Triage episodes

```text
1. itsi_list_notable_events({ "filter_query": {"severity": {"$gte": 4}}, "limit": 20 })
2. itsi_get_notable_event(event_id)              → inspect details
3. itsi_acknowledge_notable_event(event_id)      → status = in progress
4. itsi_close_notable_event(event_id, comment)   → status = closed
```

Or invoke the `itsi_episode_triage` prompt for a guided runbook.

## Common pitfalls

| Symptom | Cause / fix |
|---|---|
| `Unknown field 'X'. Did you mean 'Y'?` | Typo or invented field — re-fetch `itsi_get_object_schema` and copy field names. |
| `Missing required field 'title'` | Required field omitted — check `required_fields` from the schema. |
| Update 5xxs on a partial change | Endpoint validates the full doc — use GET → merge → PUT with `is_partial=false`. |
| Entity created but never matches a service | Alias field missing at the document root (must mirror `identifier.fields`). |
| `404 ITSI API` | Wrong namespace — pass `X-ITSI-App` / `X-ITSI-User-NS` (defaults `SA-ITOA` / `nobody`). |
| `No Splunk credentials provided` | Client sent no auth headers and no env defaults — see [Authentication](getting-started.md#authentication). |

## Resources and prompts

Read-only resources need no credentials and are ideal for grounding an agent:

- `itsi://llms.txt` — condensed agent usage guide (this document's TL;DR).
- `itsi://schema/<object_type>` — structured schema JSON per type (e.g. `itsi://schema/service`).
- `itsi://docs/overview` — map of the bundled knowledge corpus.
- `itsi://docs/api/schema`, `itsi://docs/api/reference` — full ITSI 4.21 REST schema and endpoint/filter reference.
- `itsi://docs/service-insights`, `itsi://docs/entity-integrations`, `itsi://docs/event-analytics`, `itsi://docs/best-practices` — concept guides.

The same docs are also callable as tools: `itsi_list_docs`, `itsi_read_doc`, `itsi_search_docs`.

Workflow prompts: `itsi_service_onboarding`, `itsi_kpi_design`, `itsi_episode_triage`.

## Where next

- **[Getting Started](getting-started.md)** — install, connect a client, run the smoke tests.
- **[Deployment Guide](deployment.md)** — standalone vs. plugin, networking, scaling.
- **[Package README](../../../mcp_itsi/README.md)** — full tool catalog, auth headers, environment variables.
