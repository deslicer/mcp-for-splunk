# MCP Tools Audit and Enhancement Summary

## Overview
This document audits all tools under `src/tools/` against LLM tool best practices and records refactors made. For each tool, we capture current definitions, identify gaps, apply improvements, and provide usage examples. Goals: clearer “when to use”, consistent naming, precise parameters, Splunk-aware time/scope controls, helper discovery tools, and reliable invocation by LLMs.

## Best-Practices Reference Applied

- **Descriptions**: Action + when-to-use + constraints; security note about permission-limited results.
- **Names**: `snake_case`, action + object, domain-aware.
- **Arguments**: Clear names/types/defaults; use `Literal` enums for closed sets; time params `earliest_time`/`latest_time`; reasonable result limits; implicit `additionalProperties: false` via signature; conservative defaults.
- **Splunk scope**: Encourage `index`/`sourcetype`/`host` context or provide discovery helpers.
- **Output**: Brief shape and limits stated in description.
- **No overlap**: Unique purposes and guidance on when not to use.

## Added Helper Tool

- **get_metadata** (`src/tools/metadata/get_metadata.py`): New tool to list distinct `host`/`sourcetype`/`source` values for an index with time bounds. Enables LLMs to discover valid filters before constructing searches.

---

## Audit and Refactors by Category

### Search

- **run_oneshot_search** (`OneshotSearch`)
  - Score: Description 3/3, Name 2/2, Params 3/3, Splunk 2/2 ⇒ 10/10
  - Notes: Already includes when-to-use, time bounds, limit; returns immediate results.
  - Examples:
    - NL: “Show failed logins in the last 15 minutes.” → Args: `{ "query": "index=auth action=failure", "earliest_time": "-15m", "latest_time": "now", "max_results": 100 }`
    - NL: “Count events by sourcetype today.” → Args: `{ "query": "| tstats count by sourcetype", "earliest_time": "@d", "latest_time": "now" }`

- **run_splunk_search** (`JobSearch`)
  - Score: 10/10
  - Notes: Clear when-to-use for long/complex jobs; progress/reporting described.
  - Examples:
    - NL: “Scan all indexes for errors in last 24h, track progress.” → Args: `{ "query": "search error", "earliest_time": "-24h", "latest_time": "now" }`
    - NL: “Top sources by volume this week.” → Args: `{ "query": "| tstats count by source", "earliest_time": "-7d@d" }`

- Saved Searches (`saved_search_tools.py`)
  - **list_saved_searches**: Score 9/10 (suggest: explicitly state permission constraints)
  - **execute_saved_search**: Score 10/10; added `Literal["oneshot","job"]` and explicit params; good.
  - **create_saved_search / update_saved_search / delete_saved_search / get_saved_search_details**: Score 9–10/10; parameters and descriptions are strong.
  - Examples:
    - NL: “Run ‘Security Alerts’ for last hour as a job.” → `{ "name": "Security Alerts", "earliest_time": "-1h", "mode": "job" }`
    - NL: “Create a scheduled daily report at 02:00.” → `{ "name": "Daily Volume", "search": "index=main | stats count by sourcetype", "is_scheduled": true, "cron_schedule": "0 2 * * *" }`

### Metadata
- **list_indexes**: Description clarified to include when-to-use and permissions note. Score 10/10.
- **list_sourcetypes** / **list_sources**: Clear, with use-cases and response shapes. Score 10/10.
- **get_metadata** (NEW): Field enum via `Literal`, time bounds, limit; returns distinct values. Score 10/10.
  - Examples:
    - NL: “Which hosts send to `security` index today?” → `{ "index": "security", "field": "host", "earliest_time": "@d" }`
    - NL: “List sourcetypes in `main` over last 24h.” → `{ "index": "main", "field": "sourcetype", "earliest_time": "-24h@h" }`

### Health
- **get_splunk_health**: Strong description; includes optional connection overrides. Score 10/10.
  - Examples:
    - NL: “Check the server health.” → `{}`
    - NL: “Test connectivity to staging Splunk.” → `{ "splunk_host": "staging.splunk.local", "splunk_port": 8089, "splunk_scheme": "https", "splunk_verify_ssl": false }`

### Admin
- **list_apps**: Clear inventory tool; no args. Score 10/10. Example: `{}`
- **manage_apps**: Updated param typing to `Literal["enable","disable","restart","reload"]`; clarified description and response. Score 10/10.
  - Examples:
    - NL: “Enable the monitoring console.” → `{ "action": "enable", "app_name": "splunk_monitoring_console" }`
    - NL: “Restart the search app.” → `{ "action": "restart", "app_name": "search" }`
- **list_users**: Clear; no args. Score 10/10. Example: `{}`
- **me**: Clear; no args. Score 10/10. Example: `{}`
- **get_configurations**: Strong; added argument normalization and namespace fallbacks. Score 10/10.
  - Example: `{ "conf_file": "props", "stanza": "monitor:///var/log/messages" }`
- **enhance_tool_description**: Docs utility; non-Splunk connection. Score 9/10.

### Alerts
- **list_triggered_alerts**: Clear purpose; added explicit args and response details. Score 9/10.
  - Risk note: Splunk `fired_alerts` collection has limited time filtering; `earliest_time/latest_time` are documented but may not strictly filter server-side. Kept `count` cap to bound output.
  - Examples:
    - NL: “List fired alerts containing ‘quota’ last 24h (max 20).” → `{ "search": "quota", "count": 20, "earliest_time": "-24h@h" }`

### KV Store
- **list_kvstore_collections**: Clear; optional `app`. Score 10/10. Example: `{ "app": "search" }`
- **get_kvstore_data**: Clear; `collection`, optional `app`, optional Mongo-style `query`. Score 9/10 (consider schema example for `query`).
- **create_kvstore_collection**: Clear; parameters and validation improved. Score 10/10.

### Workflows
These tools are primarily internal to the workflow system; descriptions are already comprehensive with schemas and validation logic:
- **workflow_runner**, **list_workflows**, **workflow_builder**, **workflow_requirements**, **summarization_tool**: Score 9–10/10.

---

## Global Risk Notes and Mitigations
- **Index names and enums**: Actual index lists vary per deployment. Use `list_indexes` and `get_metadata` before constructing filters.
- **Time window defaults**: Conservative defaults (`-15m` oneshot, `-24h` job). LLMs should narrow windows as needed.
- **Permissions**: All results are constrained by the authenticated user; descriptions now explicitly state this where relevant.
- **Alert time filtering**: Documented limitation for `list_triggered_alerts` due to Splunk API semantics.

## Open Questions
- Should we include environment-specific enums (e.g., common indexes like `main`, `summary`) for faster grounding? Proposed to keep discovery-first via helpers to avoid stale configs.
- For `get_kvstore_data.query`, do we want to support a validated JSON schema or keep free-form Mongo-style filters? Currently documented as free-form.

---

## Summary of Code Changes
- Added `get_metadata` tool with `Literal` enums and time-bound querying: `src/tools/metadata/get_metadata.py`.
- Registered the tool in `src/tools/metadata/__init__.py` and exported in `src/tools/__init__.py` via package import.
- Strengthened `manage_apps` param schema with `Literal` enum; clarified validation comment.
- Clarified `list_indexes` description (when-to-use + permission note).
- No breaking changes to names; backward-compatible improvements.

## Example Invocation Triggers and Arguments
- “What indexes can I use?” → Tool: `list_indexes` → `{}`
- “Which hosts write to `security` today?” → Tool: `get_metadata` → `{ "index": "security", "field": "host", "earliest_time": "@d" }`
- “Run a quick check for errors in `main` last 15m.” → Tool: `run_oneshot_search` → `{ "query": "index=main error", "earliest_time": "-15m" }`
- “Enable the monitoring console app.” → Tool: `manage_apps` → `{ "action": "enable", "app_name": "splunk_monitoring_console" }`

