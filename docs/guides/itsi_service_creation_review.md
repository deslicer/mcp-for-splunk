# ITSI service creation — MCP tools review

**Scope.** Walk the four official steps in
[Overview of creating services in ITSI (4.21)](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/visualize-and-assess-service-health/4.21/create-services)
end-to-end using only the tools shipped by `mcp_itsi`, and be critical
of what works, what is missing and what could be improved.

The scenario was driven by
[`scripts/test_itsi_service_creation_scenario.py`](../../scripts/test_itsi_service_creation_scenario.py)
against a live ITSI 4.21 cluster, mirroring the doc's "Web Store"
example. The script is read-mostly, idempotent, and has a `--cleanup`
flag.

> **Verdict (TL;DR)** — A capable agent **can** stand up a multi-tier
> service hierarchy with KPIs, entity rules and dependencies using only
> our MCP tools, and we proved it end-to-end. But **the surface is too
> low-level** for a model to use safely without prior ITSI knowledge.
> The biggest gaps are documented below as `(major)` findings.

## Run summary

| Documented step | Tool used | Outcome |
|---|---|---|
| Prereqs: discover team / aliases / candidate entities | `itsi_list_teams`, `itsi_get_alias_list`, `itsi_list_entities` | OK |
| Step 1a: create database tier (single service, manual KPIs) | `itsi_create_service` | OK |
| Step 1b: create app tier with `services_depends_on=[db]` | `itsi_create_service` | OK |
| Step 1c: create web tier with deps on app + db, two KPIs | `itsi_create_service` | OK |
| Step 1d: create top-level "Web Store" business service | `itsi_create_service` | OK |
| Step 2: edit entity rules — add a `not` rule | `itsi_update_service` (partial) | OK |
| Step 3: add KPIs (manual, ad-hoc + threshold spec) | `itsi_update_service` (partial) | OK (only because we hand-rolled a 60-key minimum-viable KPI dict) |
| Step 4: add service dependencies | `itsi_update_service` / nested in `itsi_create_service` | OK |
| Doc affordance: clone a service | none — emulated via `get` + `create_service` | OK with caveats |
| Doc affordance: enable/disable | `itsi_update_service` (partial) `enabled=0` | OK |

**Net result on the cluster:** 4 dependent services created, dependency
graph readable from `services_depends_on`, KPIs scheduled (verified
through `itsi_get_service`), entity rules round-trip correctly.

## What worked well

1. **Header-based per-request auth is exactly right** for this kind of
   workflow. An agent can target a different ITSI namespace per call
   simply by changing `X-ITSI-App` / `X-ITSI-User-NS`.
2. **`itsi_create_service` accepts the full nested document** (KPIs,
   entity rules, dependencies in one POST). That's faithful to the REST
   API and lets agents do a "compose then commit" workflow.
3. **`itsi_update_service` partial updates work** for narrow fields like
   `entity_rules` and `enabled` (the verified happy path here).
4. **Discovery flow is solid.** `itsi_list_teams`,
   `itsi_get_alias_list`, `itsi_list_entities` with a regex filter give
   an agent everything it needs to design a service before writing it.
5. **Read-after-write round-trips are clean.** Every field we sent
   round-trips through `itsi_get_service`, so an agent can verify its
   own writes without guessing.
6. **Knowledge bundle pays off.** `itsi_read_doc slug=best-practices`
   surfaced the right mental model (urgency 0–11, KPI per metric,
   entity-rule wildcards), which kept the payloads small and correct.

## What's missing or rough — ranked by impact

### 1. (major) Building a *valid* KPI document is too much ceremony

ITSI's KPI schema is 60+ fields, several of which look optional but are
actually load-bearing (`search_alert_earliest`, `alert_lag`,
`alert_period`, `is_service_entity_filter`, the full
`time_variate_thresholds_specification` skeleton, `aggregate_thresholds`
*and* `entity_thresholds`, etc.). Every iteration that omitted any of
those produced 400/500 errors. Without `mcp_itsi/scripts/test_itsi_service_creation_scenario.py::_adhoc_kpi`
as a template, an agent would not stumble on the right shape.

**Suggested improvements:**

- Ship a dedicated tool `itsi_build_kpi_payload` that takes the small
  set of fields a human actually thinks about (`title`,
  `source_search` or `kpi_base_search_id`, `threshold_field`,
  `urgency`, `cron_schedule`, `is_entity_breakdown`, optional
  `static_thresholds`) and returns a fully-shaped KPI dict. Agents would
  call this and feed the result into `itsi_create_service` /
  `itsi_update_service`.
- Alternatively (or additionally): add an `itsi_add_kpi_to_service` tool
  that does `get → append-to-kpis → update with full payload`,
  documenting the merge semantics.

### 2. (major) No way to ask "did my entity rule match anything?"

ITSI does not return resolved/matched entities on `service` documents
(`itsi_get_service` confirmed: no `entities`, `matched_entities`,
`resolved_entities` fields). Without that, an agent cannot tell whether
its rule is doing nothing, matching too much, or matching the wrong
hosts.

**Suggested improvements:**

- Add an `itsi_preview_entity_rules` tool that takes a `service._key`
  *or* a list of rules and returns `{entities: [...], count: N}` after
  resolving them server-side (this is achievable via `itoa_interface/entity`
  with a derived MongoDB filter).
- Alternatively, add an `itsi_get_service_entities` tool that resolves
  the rules of a given service and returns matching entity titles. This
  would dramatically shorten the design–verify loop.

### 3. (major) No native "clone service"

The docs explicitly call out cloning as a UI affordance. We don't ship
it. Emulating it via `get → mutate → create_service` works but it is
fragile:

- Have to drop ITSI-managed system fields (`_key`, `create_time`,
  `mod_time`, `create_by`, `mod_by`, `_owner`, `_user`, `mod_source`,
  `mod_timestamp`).
- Have to **regenerate every nested KPI's `_key`** — otherwise the
  source service's KPIs are silently overwritten or duplicates appear.
- The auto-generated `ServiceHealthScore` KPI is *not* an editable
  user KPI; cloning copies it and ITSI re-creates it again, producing
  duplicates (we observed two `ServiceHealthScore` entries on the clone).
- `services_depends_on` references cannot be carried verbatim (the
  parent `_key` of the SHKPI changes) and must be rewritten.

**Suggested improvement:**

- Add an `itsi_clone_service` tool that does the right things
  server-side: drop system fields, regenerate KPI keys, optionally
  clear or rewrite `services_depends_on`, optionally move to a different
  team. This is a high-value 60-line tool.

### 4. (major) Service dependencies need pre-computed `kpis_depending_on`

The docs say "select the specific KPIs from the impacting service that
you want ITSI to include in the health score calculation" — but the
REST schema requires you to send `kpis_depending_on` as a list of KPI
`_key`s up front, *before* you know what the new service's
`ServiceHealthScore` KPI key is. The convention `SHKPI-<service-key>`
works (we used it successfully) but it is undocumented in the schema and
brittle.

**Suggested improvement:**

- Add an `itsi_add_service_dependency` tool that takes
  `{service_key, depends_on_service_key, mode: "service_health" |
  "kpi_keys", kpi_keys?: [...]}` and computes `kpis_depending_on`
  server-side (defaulting to `[SHKPI-<dep_key>]` for the common case).
- Document `SHKPI-<key>` in `itsi://docs/api/schema`.

### 5. (minor) `itsi_search_docs` is too literal

`itsi_search_docs query="service template"` returned 0 hits even though
`service-insights` and `best-practices` both mention service templates
extensively. The search is substring-only on title/description/tags.

**Suggested improvement:**

- Tokenise queries (split on whitespace, score per token) and search
  the **content** of each doc, not just the metadata. ~30 lines of
  Python in `mcp_itsi/knowledge/catalog.py::search`.

### 6. (minor) `services_depends_on` round-trip drops titles

After creating a service with `services_depends_on=[{serviceid: ...}]`,
`itsi_get_service` returns the dependency entries but with `title:
None`. ITSI requires the agent to do a separate `itsi_get_service` per
dep to display anything human-readable.

**Suggested improvement:**

- Have `itsi_list_services` and `itsi_get_service` enrich
  `services_depends_on[].title` from the service catalog before
  returning. Single extra MongoDB filter; saves N round trips in the
  agent.

### 7. (minor) Partial update of nested `entity_rules` is array-replace

Sending a partial update with `payload={"entity_rules": [...]}`
**replaces** the array, even when `is_partial=True`. That is consistent
with ITSI semantics, but is a footgun for agents that think "partial =
merge". I caught it during the scenario.

**Suggested improvement:**

- Add an `itsi_add_entity_rule` and `itsi_remove_entity_rule` tool that
  fetch → append/filter → POST with the full array. Even simpler:
  document the array-replace semantics explicitly in
  `itsi_update_service`'s description (already partly there for
  aggregation policies; do the same for services).

### 8. (info) No tool to backfill or trigger a KPI dry-run

The docs cover "Enable 7 days of backfill" as a service-level switch.
We expose nothing equivalent. An agent that just created a service has
no MCP-native way to ask ITSI "run my KPI now to confirm it produces
data". It has to fall back to the parent `mcp-for-splunk` server's
`run_oneshot_search` tool (only available when running in plugin mode).

**Suggested improvement:**

- Add `itsi_backfill_service_kpis` (set
  `enable_backfill_for_all_kpis=true` on the service for 7d).
- Add `itsi_run_kpi_now` that takes a `kpi.search` and runs it via
  the saved-search endpoint, returning the latest value and summary.
  This closes the "did my service work?" loop.

### 9. (info) No CSV bulk-import or saved-search-import surface

The docs cover three ways to create services: single, CSV import, and
search import. We only support "single"; bulk is a `itsi_bulk_update`
on `service` away (the underlying endpoint exists). For an enterprise
rollout, an agent that can take a CSV / SPL search and import N
services in one call is a much better experience than orchestrating N
`itsi_create_service` calls.

**Suggested improvement:**

- Add `itsi_bulk_create_services` (wrap `itsi_interface/service/bulk_update`)
  and document the size cap (200–300 if any link to a template).
- Add `itsi_import_services_from_search` that wraps `itsiimportobjects`
  via the saved-search endpoint.

### 10. (info) Tool descriptions could surface KPI mental model

The current `itsi_create_service` description points at the schema
doc, but doesn't tell an agent the *minimum* set of fields it must
provide for KPIs. Adding two short examples (one ad-hoc KPI, one
base-search KPI) directly in the tool description would prevent the
trial-and-error loop the scenario script had to do.

## Concrete additions that would unlock most of the wins above

These are small, focused tools that address findings 1–4 directly:

```
itsi_build_kpi_payload(title, source_search, threshold_field,
                       urgency=5, cron_schedule="*/5 * * * *",
                       is_entity_breakdown=False, kpi_base_search=None,
                       kpi_threshold_template_id=None,
                       static_thresholds=None) -> kpi_payload
itsi_add_kpi_to_service(service_key, kpi_payload) -> service
itsi_remove_kpi_from_service(service_key, kpi_key) -> service
itsi_clone_service(source_key, new_title, *,
                   target_team=None, copy_dependencies=False) -> service
itsi_preview_entity_rules(rules) -> {entities, count}
itsi_get_service_entities(service_key) -> {entities, count}
itsi_add_service_dependency(service_key, depends_on_key,
                            kpi_keys=None) -> service
```

All of them can sit in `mcp_itsi/tools/service.py` (or a new
`tools/service_helpers.py`) and use the existing `_itoa_ops` helpers.
None of them require new endpoints — they all wrap operations the agent
already does manually. They each easily fit in <80 LOC.

## How to reproduce

```bash
# Standalone server (default 8084)
uv run mcp-itsi-server --host 127.0.0.1 --port 8084

# Or plugin mode via parent server (default :8085)

# Run the scenario:
ITSI_HOST=<host> ITSI_USERNAME=<user> ITSI_PASSWORD=<pass> \
  ITSI_VERIFY_SSL=false \
  uv run python scripts/test_itsi_service_creation_scenario.py
```

Pass `--cleanup` to remove every object the script creates. Without it,
the services persist in your ITSI cluster so you can inspect them in the
UI; rerunning the scenario is safe (titles include a unique run ID).

## References

- [Overview of creating services in ITSI (4.21)](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/visualize-and-assess-service-health/4.21/create-services)
- [Create a single service in ITSI](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/visualize-and-assess-service-health/4.21/create-services/create-a-single-service-in-itsi)
- [Define entity rules for a service in ITSI](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/visualize-and-assess-service-health/4.21/create-services/define-entity-rules-for-a-service-in-itsi)
- [Add service dependencies in ITSI](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/visualize-and-assess-service-health/4.21/create-services/add-service-dependencies-in-itsi)
- [Import services from a CSV in ITSI](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/visualize-and-assess-service-health/4.21/create-services/import-services-from-a-csv-in-itsi)
- [Overview of creating KPIs in ITSI](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/visualize-and-assess-service-health/4.21/create-kpis/overview-of-creating-kpis-in-itsi)
- [Define a KPI source search in ITSI](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/visualize-and-assess-service-health/4.21/create-kpis/define-a-kpi-source-search-in-itsi)
