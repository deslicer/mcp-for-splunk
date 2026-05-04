# ITSI implementation best practices

This is a synthesis of guidance from the ITSI Service Insights, Entity
Integrations, Event Analytics, and Implementation manuals. It is meant as
a quick checklist for AI agents and operators rolling out ITSI.

## Service modelling

- **Map services to business value**, not to infrastructure tiers. A good
  service has a clear consumer ("the storefront", "internal email").
- **Layer services**. Build a small set of low-level technical services
  (database, web tier, queue) and one or more business services that
  *depend on* them. Use `services_depends_on` to capture the graph.
- **Service templates first.** Even for a single service, start by creating
  a template you can reuse. It pays off the second time you onboard a
  similar service.
- **Tag aggressively**. Use `service_tags.tags` for team, environment,
  region. The Service Analyzer and Episode Review filter on tags.

## KPI design

- **One metric per KPI.** Composite KPIs hide root cause.
- **Reuse base searches.** Pay search load once across many KPIs.
- **Pick the right urgency.** `urgency` (0–11) drives the contribution of
  each KPI to the service health score. Reserve high urgency (10–11) for
  KPIs whose breach is genuinely service-impacting.
- **Set sensible cadences.** A 5-minute cron is the default; keep it unless
  you have a reason. Sub-minute KPIs cost a lot and rarely buy fidelity.
- **Choose entity_id_fields carefully.** They must align with entity
  identifier aliases. Mismatch ⇒ "no data" KPIs.
- **Use adaptive thresholds for time-varying signals**, static thresholds
  for SLO/SLI absolutes.

## Entities

- **Canonical alias.** Adopt one identifier alias (typically `host`) and
  use it everywhere — entity creation, KPI base searches, entity rules.
- **Recurring imports beat manual.** Configure a recurring import as soon
  as you've validated the search.
- **Entity types are descriptive, not prescriptive.** Keep them broad and
  put fine-grained classification in `informational` aliases.

## Event Analytics

- **Correlation search idempotency.** A correlation search must produce
  the same notable events given the same input data; don't reach into
  side-effects.
- **Aggregation policies are the contract.** Define escalation logic at
  the policy level, not per search. A small number of policies is easier
  to maintain.
- **Use `event_identifier_hash`** to suppress duplicates during storms.
- **Auto-close clearing events.** When a recovery alert fires, configure
  the policy to close the matching open episode.
- **Action SDK for custom workflows.** Use the Python action SDK to add
  comments, change owner / status / severity, or push to your IM
  platform.

## Operational hygiene

- **Backups.** Use the backup_restore interface to snapshot KV-store
  configuration before bulk changes.
- **Version control.** Keep service / template / KPI definitions under
  source control. Use the `templatize` endpoint to extract definitions.
- **Maintenance windows.** Define recurring windows for known maintenance
  activities so KPIs don't generate noise.
- **RBAC.** Use teams (`sec_grp`) to scope service ownership. Entities
  and templates remain Global.

## Anti-patterns to avoid

- One giant "platform" service with hundreds of KPIs.
- KPIs that depend on subsearches across long time ranges.
- Aggregation policies that group on every field — you'll get one
  episode per event, defeating the purpose.
- Manually editing the KV store collections.
- DELETE without `_key` filters (you can wipe an entire object type).

## CRUD quirks (verified against ITSI 4.21)

The ITSI REST API has a few subtle behaviours that catch automation off
guard. They are all surfaced in the corresponding tool descriptions.

- **Entity create** — every alias field declared in `identifier.fields`
  must *also* be a top-level array on the document. For example, if
  `identifier.fields=["host"]`, the payload must include
  `host: ["my-host"]` at the top level.
- **Service template create** — requires either `service_id` (a `_key`
  of an existing service to derive from) or `base_service_template_id`.
  Use `itsi_templatize_service` to build a ready-made payload.
- **Correlation search update** — ITSI's handler requires the `name`
  field to be present in the body even on partial updates; otherwise
  the server returns 500 with a `'name'` KeyError.
- **Aggregation policy update** — `is_partial_data=1` is honoured on
  the URL but the handler still validates the full schema. Pattern:
  `itsi_get_aggregation_policy` → merge changes → submit with
  `is_partial=False`.
- **Deep dive update** — payload must include `owner`, `_owner` and
  `_user`. Always read the doc first and merge.
- **Delete** — never pass a `filter` to bulk DELETE without an `_key`
  clause; an empty / wrong filter wipes every object of that type.
