# ITSI Schema-Aware Tooling — Design Spec

> Status: Implemented
> Date: 2026-06-02
> Scope: `mcp_itsi/` ITSI MCP server

## Regenerating schemas

```bash
# Re-scrape the live docs, parse, and rebuild the bundled doc:
python -m scripts.itsi_schema.refresh

# Or reuse an existing local scrape (no network):
python -m scripts.itsi_schema.refresh --skip-scrape
```

## Problem

Every ITSI create/update tool (`service.py`, `kpi_base_search.py`, and the
other ~11 ITOA CRUD tools) accepts a free-form `payload: dict[str, Any]` with
no schema awareness. ITOA objects are deeply nested — a `service` contains
`kpis[]`, which contain `entity_thresholds` → `threshold_levels[]`; a single
`service_kpi` has ~50 fields and `kpi_base_search` ~30. The only schema
guidance shipped today is a hand-curated, **partial**, prose `content/api/schema.md`.

As a result, an LLM building these payloads is effectively guessing, which
makes CRUD on ITOA objects error-prone and unreliable.

## Goals

1. Give agents authoritative, machine-usable schemas for **every ITOA object type**.
2. Catch payload mistakes **before** they hit ITSI, with actionable messages.
3. Help agents **assemble** nested objects via example/skeleton payloads.
4. Keep the source of truth maintainable and regenerable from Splunk's docs.

## Non-goals

- Hand-authored Pydantic/JSON-Schema models per object type (drift + maintenance).
- Server-side workflow builders (e.g. `itsi_add_kpi_to_service`) — deferred.
- Event Management object coverage — deferred (ITOA first).

## Source of truth

Splunk's [ITSI 4.21 REST API schema](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-schema/itsi-rest-api-schema)
page is a single, highly-structured page: every object type has a
`Field | Type | Description` table plus explicit *subordinate object* links.
This parses mechanically into per-object structured schemas.

**Approach: hybrid.** Parse the docs into bundled structured schemas (offline,
deterministic, version-pinned to 4.21, regenerable). Derive a lightweight
JSON-Schema shape from the `Type` column for validation. Optionally enrich with
a live example object pulled from the connected ITSI instance.

The raw scraped markdown lives in `.research/itsi/` (gitignored) as the
regeneration input. Only the parsed JSON and a regenerated full `schema.md`
get committed.

## Architecture

### 1. Schema knowledge layer — `mcp_itsi/knowledge/schema/`

| File | Responsibility |
|------|----------------|
| `models.py` | `AttributeSpec`, `ObjectSchema`, `SubordinateRef` dataclasses; `to_dict()`, `to_json_schema()` |
| `data/*.json` | Generated structured schema, one file per object type (bundled, version-pinned) |
| `registry.py` | `SchemaRegistry`: load bundled JSON once; `get()`, `list_types()`, `search()` |
| `validator.py` | `PayloadValidator.validate(payload, schema, is_partial)` → `ValidationResult(ok, errors[], warnings[])`; recurses into subordinate objects |
| `examples.py` | Minimal-valid + fully-populated skeleton payloads per type; curated examples for `service` and `kpi_base_search` |

`ValidationResult` semantics:

- **Hard errors** (block writes): unknown/misspelled field, wrong type, missing
  clearly-required field.
- **Warnings** (non-blocking): read-only/server-generated field supplied,
  empty required-ish array, suspect value.

`required` detection is **conservative** — derived from prose hints
("required", "Not required") plus obvious cases (`title`; `_key` on update).
Under-flagging is preferred over false positives that block valid writes.

### 2. Schema generation (dev-time) — `scripts/itsi_schema/`

| File | Responsibility |
|------|----------------|
| `parse_schema_md.py` | Parse saved schema markdown tables + subordinate links → `data/*.json`. A mapping table reconciles doc display names → endpoint object-type ids (e.g. "Service" → `service`, "KPI Base Search" → `kpi_base_search`, "Service KPI" → subordinate of `service`) |
| `refresh.py` | Re-run firecrawl scrape + parser to regenerate schemas when Splunk updates the docs |

Type mapping: `String→string`, `Integer→integer`, `Boolean→boolean`,
`Object/Dict→object`, `Array→array`.

### 3. New tools — `mcp_itsi/tools/schema.py`

| Tool | Behavior | Connection |
|------|----------|------------|
| `itsi_get_object_schema(object_type, include_example=True, include_live_example=False)` | description, endpoint/interface, attribute table, inlined subordinate schemas, derived JSON-Schema, skeleton example(s); optional real sample from the instance | only if `include_live_example` |
| `itsi_list_object_schemas()` | every type: summary, endpoint, attribute count, subordinate objects | no |
| `itsi_validate_object_payload(object_type, payload, is_partial=False)` | dry-run validation → `ok / errors / warnings` | no |

### 4. Pre-flight validation on writes (uniform, DRY)

- `mcp_itsi/tools/_validation.py` — `preflight(object_type, payload, is_partial)`
  + `PayloadValidationError`. Uses a request-scoped `ContextVar` warnings buffer.
- `_itoa_ops.create_object` / `update_object` gain `validate=True`:
  - On **hard errors** → raise `PayloadValidationError`.
  - On **warnings** → push to the `ContextVar` buffer.
- `BaseITSITool.__call__`:
  - Reset the warnings buffer at the start of each call.
  - Catch `PayloadValidationError` → `error_response(message, validation_errors=...)`.
  - After a successful `execute`, drain the buffer and merge
    `validation_warnings` into the success response.

This protects **all** ITOA create/update tools and surfaces warnings inline
with **no per-tool edits**.

### 5. Existing tools & docs

- Enrich `service.py` / `kpi_base_search.py` descriptions to point at
  `itsi_get_object_schema` + `itsi_validate_object_payload` and name key
  required fields.
- Regenerate `content/api/schema.md` from the full parsed schema (replaces the
  partial hand-written version); keep the catalog entry.
- Expose each schema as a resource `itsi://schema/<object_type>` via a
  `schema_resource` builder mirroring `docs_resource`.

### 6. Tests & evaluations

- Unit tests: parser sanity, registry load, validator (unknown field / type
  mismatch / missing required / nested KPI / partial-update skips required),
  example generation, ContextVar warnings drain.
- mcp-builder eval set (XML): an agent fetches a schema and builds a valid
  `service`/`kpi_base_search`; validation catches a planted mistake.

## Module/SRP notes

All new code stays well under the 500-line limit, each file single-purpose:
`SchemaRegistry` (manager), `PayloadValidator` (validation), `examples`
(construction), `schema.py` tools (interface), `_validation.py` (write-path
coordinator). No changes to the generic registration mechanism.

## Rollout

1. Scrape + parser → generate `data/*.json` and full `schema.md`.
2. Schema knowledge layer (`models`, `registry`, `validator`, `examples`).
3. New tools + registration in `all_tools()`; schema resources in `all_resources()`.
4. Write-path pre-flight (`_validation.py`, `_itoa_ops`, `base.py`).
5. Enrich showcase tool descriptions.
6. Tests + evaluations.
