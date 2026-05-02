# Event Analytics in ITSI (4.21) — distilled

> Source: <https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/detect-and-act-on-notable-events/4.21/>

ITSI Event Analytics ingests events from across your IT estate and
consolidates them into a single, actionable operational console. It is
designed to handle large event volumes while reducing noise via grouping
and policies.

## Workflow

### 1. Ingest events with correlation searches

A **correlation search** is a saved search whose results emit notable
events. Examples: KPI severity transitions, multi-KPI alerts, custom SPL.

REST collection: `/event_management_interface/correlation_search`.

### 2. Group events into episodes via aggregation policies

An **aggregation policy** is a set of rules executed by the ITSI Rules
Engine. Matching notable events are grouped into **episodes** — a
chronological sequence of related events that tells the story of a
problem.

REST collection: `/event_management_interface/notable_event_aggregation_policy`.

### 3. Act on episodes

Actions can be:

- shipped with ITSI (email, ping host),
- ticketing integrations (ServiceNow, Remedy, VictorOps, PagerDuty),
- modular alerts shipped with add-ons,
- custom Python actions via the **notable event action SDK**.

Actions can run automatically (driven by aggregation policy triggers) or
manually from Episode Review.

## Notable event lifecycle

| Status code | Meaning           |
|-------------|-------------------|
| 0           | Unassigned        |
| 1           | New               |
| 2           | In progress       |
| 3           | Pending           |
| 4           | Resolved          |
| 5           | Closed            |

| Severity | Label    |
|----------|----------|
| 1        | Info     |
| 2        | Normal   |
| 3        | Low      |
| 4        | Medium   |
| 5        | High     |
| 6        | Critical |

## REST cheat sheet

```http
GET    /event_management_interface/notable_event?filter={"severity":{"$gte":4}}
GET    /event_management_interface/notable_event/<event_id>
POST   /event_management_interface/notable_event/<event_id>          # update status / owner
POST   /event_management_interface/notable_event_comment             # body: {event_id, comment}
GET    /event_management_interface/notable_event_aggregation_policy
GET    /event_management_interface/notable_event_email_template
GET    /event_management_interface/correlation_search
```

## Best practices

- Define **escalation policies** at the aggregation policy level, not
  per correlation search. Easier to evolve over time.
- Use the **`event_identifier_hash`** field to correlate duplicate events;
  it suppresses notification storms during incidents.
- For high-volume sources, set the correlation search **scheduling
  window** to a higher value than its frequency to avoid skipped runs.
- Keep correlation searches **idempotent** — they should not depend on
  the result of previous runs.
- Triage automation: subscribe a webhook action to your incident
  management platform; only escalate when severity stays above a
  threshold for N consecutive runs.
