# Create Config Tool

## What it does

Creates or updates a stanza in a Splunk `.conf` file at the app level. It uses the REST API first and falls back to the Python SDK when necessary. It never overwrites entire files; it only creates new stanzas or adds/updates keys within a stanza.

- **Overwrite behavior**: Existing keys are updated only when `overwrite=true`. Otherwise, only new keys are added and existing differing keys are skipped.
- **Namespace defaults**: If not provided, the owner defaults to the current session user and the app defaults to `search`.

## Quick start (🚀)

### Prerequisites

- MCP server connected to Splunk (see `docs/getting-started/installation.md`).
- Credentials via headers or environment per `src/server.py` (e.g., `X-Splunk-Host`, `X-Splunk-Username`, etc.).

### First success in 2 minutes

- Create a new stanza in `props.conf`:

```bash
# Creates stanza [myweblogs] in props.conf with two keys
mcp call create_config \
  --conf_file props \
  --stanza myweblogs \
  --settings '{"CHARSET": "UTF-8", "SHOULD_LINEMERGE": "false"}'
```

- Update only new keys (don’t overwrite existing):

```bash
# Adds only keys that do not already exist
mcp call create_config \
  --conf_file transforms \
  --stanza dnslookup \
  --settings '{"fields_list": "clientip"}' \
  --overwrite false
```

- Overwrite existing keys explicitly:

```bash
# Overwrites existing keys where values differ
mcp call create_config \
  --conf_file web \
  --stanza settings \
  --settings '{"httpport": "8001", "mgmtHostPort": "127.0.0.1:8089"}' \
  --overwrite true
```

Expected success output highlights include `action` (`created`, `updated`, or `skipped`), `added_keys`, and `changed_keys`.

## Arguments

- `conf_file` (string, required): Configuration file name without `.conf` (e.g., `props`, `transforms`).
- `stanza` (string, required): Stanza name to create or update.
- `settings` (object, required): Key/value settings to apply in the stanza.
- `app` (string, optional): App namespace. Defaults to `search`.
- `owner` (string, optional): Owner namespace. Defaults to the current session user when available.
- `overwrite` (bool, optional): Overwrite existing differing keys when `true`. Default `false`.

## Behavior details (📚)

- **REST-first**: Uses `GET /services/configs/conf-<conf>/<stanza>` to check existence.
  - If exists, updates only new or changed keys based on `overwrite`.
  - If not found, creates via `POST /servicesNS/{owner}/{app}/configs/conf-<conf>` with `name=<stanza>` and settings.
- **SDK fallback**: When REST fails, falls back to `service.confs[conf][stanza].update(...)` or `service.confs[conf].create(stanza, ...)` if available.
- **Non-destructive**: Never replaces entire files or deletes settings.

## Examples and expected results

- Create:
  - Input: `conf_file=props`, `stanza=myweblogs`, `settings={CHARSET: UTF-8}`
  - Result: `action=created`, `added_keys=[CHARSET]`
- Update without overwrite:
  - Input: existing stanza has `external_cmd=dnslookup.py`; call with `external_cmd=dnslookup_v2.py, fields_list=clientip`, `overwrite=false`
  - Result: `action=updated`, `added_keys=[fields_list]`, `changed_keys=[]`
- Update with overwrite:
  - Input: existing stanza has `httpport=8000`; call with `httpport=8001, mgmtHostPort=127.0.0.1:8089`, `overwrite=true`
  - Result: `action=updated`, `changed_keys=[httpport]`, `added_keys=[mgmtHostPort]`

## Troubleshooting (🔧)

- Ensure the MCP server can reach Splunk’s management port (default `8089`).
- Verify app/owner permissions for configuration writes.
- If REST calls fail (HTTP 4xx/5xx), the tool attempts SDK fallback automatically.

## Related docs

- REST configuration tutorial: `https://docs.splunk.com/Documentation/Splunk/9.4.2/RESTTUT/RESTconfigurations`
- REST configuration endpoints: `https://docs.splunk.com/Documentation/Splunk/9.4.1/RESTREF/RESTconf`
- README guide: `../readme-guide.md`
