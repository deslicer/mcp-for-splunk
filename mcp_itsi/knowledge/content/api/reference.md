# ITSI REST API reference (4.21)

> Source: <https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-reference/itsi-rest-api-reference>

The ITSI REST API is exposed by **splunkd** on the management port (default
`8089`) over **HTTPS**. Always specify the API version `vLatest` (or omit
it). The API performs **capability and RBAC checks** on each call.

```text
https://<splunk-server>:8089/servicesNS/<user>/<app>/itoa_interface/vLatest/...
```

In most deployments `<user>` is `nobody` and `<app>` is `SA-ITOA`.

## Endpoint interface categories

| Interface                       | Purpose                                                                |
|---------------------------------|------------------------------------------------------------------------|
| `itoa_interface`                | CRUD on core ITSI objects (services, entities, KPIs, deep dives, ...). |
| `event_management_interface`    | Notable events, aggregation policies, correlation searches.            |
| `maintenance_services_interface`| Maintenance windows.                                                   |
| `backup_restore_interface`      | Backup / restore jobs.                                                 |
| Glass-table icon interface      | KV-store-backed glass-table icons.                                     |

## ITOA interface object types

```text
team, entity, service, base_service_template, kpi_base_search,
deep_dive, glass_table, home_view, kpi_template, kpi_threshold_template,
event_management_state, entity_filter_rule, entity_type,
custom_threshold_windows, kpi_entity_threshold
```

`entity_relationship`, `entity_filter_rule` and `entity_relationship_rule`
appear in `get_supported_object_types` but are not used.

## Common collection endpoints

For a given `<object>` (e.g. `service`):

| Endpoint                                              | Method  | Purpose                                                                |
|-------------------------------------------------------|---------|------------------------------------------------------------------------|
| `/itoa_interface/<object>`                            | GET     | List with `filter`, `fields`, `sort_key`, `sort_dir`, `limit`, `offset`|
| `/itoa_interface/<object>`                            | POST    | Create or upsert.                                                      |
| `/itoa_interface/<object>`                            | DELETE  | Delete (DANGEROUS — use a filter on `_key`).                           |
| `/itoa_interface/<object>/count`                      | GET     | Count with optional `filter`.                                          |
| `/itoa_interface/<object>/<_key>`                     | GET     | Read a single object.                                                  |
| `/itoa_interface/<object>/<_key>`                     | POST    | Partial or full update (`is_partial_data=1` for partial).              |
| `/itoa_interface/<object>/<_key>`                     | DELETE  | Delete by key.                                                         |
| `/itoa_interface/<object>/bulk_update`                | POST    | Update many at once (array body).                                      |
| `/itoa_interface/<object>/<_key>/templatize`          | GET     | Generate a template (only `service` and `kpi_base_search`).            |
| `/itoa_interface/get_alias_list`                      | GET     | All identifier and informational alias field names.                    |
| `/itoa_interface/get_supported_object_types`          | GET     | Machine-readable list of supported types.                              |

## Filter syntax

Filters are MongoDB-style query documents passed as a URL-encoded JSON
string. Examples:

```http
GET /itoa_interface/service?fields=title,_key&filter={"title":"Web+Service"}
GET /itoa_interface/entity?fields=title&filter={"title":{"$regex":".*mysql"}}
GET /itoa_interface/entity?filter={"entity_type":"API"}
```

> Caution: an **incorrect or empty** filter on `DELETE` can wipe all rows
> for that object type. Always delete by `_key` when possible.

## Event Management interface

Common collection paths under `/event_management_interface`:

```text
notable_event, notable_event_group, notable_event_comment,
notable_event_aggregation_policy, notable_event_email_template,
correlation_search
```

The same query parameters (`filter`, `fields`, `limit`, `offset`) apply.

## Authentication options

| Method            | Header / scheme                               |
|-------------------|-----------------------------------------------|
| Basic auth        | `Authorization: Basic <user:pass-base64>`     |
| Splunk auth token | `Authorization: Bearer <token>`               |

Tokens are issued via `/services/authorization/tokens` on splunkd.

## Tips

- Add `report_as=text` when calling `| rest` for SA-ITOA endpoints (>=4.4.0).
- Keep payloads under the configured `splunkd.max_content_length`.
- Prefer `bulk_update` with `is_partial_data=1` when reconciling many
  objects — this avoids accidentally overwriting fields you didn't intend
  to change.
