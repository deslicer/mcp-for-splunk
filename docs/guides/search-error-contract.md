# Search error contract

`run_oneshot_search` and `run_splunk_search` return structured diagnostics so clients can distinguish a failure before dispatch from a search that may already exist. The existing `status` and human-readable `error` fields remain available. MCP results retain `isError: true` and the readable message in `content`; clients read the additional fields from `structuredContent`.

## Availability

This contract is unreleased. It is introduced by the PR linked from [issue #334](https://github.com/deslicer/mcp-for-splunk/issues/334); no published version or image is claimed to contain it yet. Use a build containing that PR and verify the deployed response before enabling contract-dependent recovery. The minimum source revision is [`30d6aa0`](https://github.com/deslicer/mcp-for-splunk/commit/30d6aa06854d8aaa80994800eea015ca99273314); after squash-merging, use the corresponding commit on `main`.

Version 0.6.12 and the earlier degraded-mode message improvement do not establish support for these fields. When fields are absent, treat the execution state as unknown. A release tag or image must contain the implementation and return these fields; a matching message alone is insufficient.

## Fields

A certificate failure in the availability check returns this shape:

```json
{
  "status": "error",
  "error": "Splunk service is not available. MCP server is running in degraded mode. Cause: CERTIFICATE_VERIFY_FAILED: untrusted issuer.",
  "error_code": "certificate_verify_failed",
  "execution_stage": "pre_execution",
  "search_started": false
}
```

| Field | Meaning |
| --- | --- |
| `error_code` | Stable classification based on the exception and its causes, independent of execution state. |
| `execution_stage` | The operation that failed; values appear below. |
| `search_started` | `false`: this invocation did not attempt job creation. `true`: creation returned a job. `null`: creation was attempted but its outcome is unknown. |
| `job_id` | The known Splunk SID, retained after creation. Omitted when no SID was returned. |

`true` means Splunk returned a job, not that the search completed or produced results. Connection failures are classified from typed causes, including wrapped exceptions; arbitrary server text mentioning certificates is not enough to assign a TLS code.

| Error codes | Meaning |
| --- | --- |
| `certificate_verify_failed`, `tls_error` | Certificate verification failed, or another TLS error occurred. |
| `dns_resolution_failed`, `connection_refused`, `connection_timeout`, `network_unreachable` | Distinct network failures. |
| `authentication_failed`, `permission_denied` | Authentication failed (including HTTP 401), or Splunk denied access (HTTP 403). |
| `connection_failed`, `splunk_unavailable` | Other availability-check failure, or unavailable service without a retained cause. |
| `invalid_pagination`, `job_results_error` | Invalid pagination, or a job that cannot provide results. |
| `search_job_failed`, `search_failed` | Splunk reported a failed tracked job, or another search operation failed. |

Clients should tolerate additional error codes and stages by treating them as unknown until supported.

## Retry and reconciliation

| Execution stage | Search state | Client action |
| --- | --- | --- |
| `pre_execution` | `false`, no SID | Correct connection, trust, DNS, or authentication configuration before retrying. This invocation made no `jobs.create` call. |
| `job_creation` | `null`, no SID | Reconcile with Splunk or ask the operator before resubmitting; the failed request may have created a job. |
| `job_ttl`, `job_wait`, `result_retrieval`, `response_formatting` | `true`, known SID | Reuse `job_id` with `get_search_job_info` and `get_search_job_results`. Avoid creating a duplicate search. |

One-shot search uses blocking job creation. A timeout or TLS failure within that operation remains `job_creation` / `null` until a SID is returned. Tracked search uses a separate `job_wait` stage. TTL extension remains best effort: an SDK TTL failure does not prevent a successful result; unexpected errors escaping the TTL helper still retain the SID.

Never use TLS wording, HTTP status, or `error_code` alone to infer whether a search started. A missing response, client timeout, cancellation, or a legacy result without these fields leaves the outcome unknown. This contract does not disable certificate verification or automatically retry job creation.

Credential fields, authorization headers, and URL userinfo are redacted from diagnostic errors and associated connection/search error logs. Unquoted credential values are conservatively redacted through the end of their line. Clients should use the structured fields rather than parse the prose, which may evolve.

## Verification

`tests/test_search_failure_contract.py` exercises pre-dispatch certificate failures, uncertain creation outcomes, known SIDs after creation, network/authentication classifications, and credential redaction. It also calls both tools through the production `ToolLoader`, FastMCP client, and production HTTP app to verify `structuredContent` and `isError` survive serialization.

`tests/test_search_error_telemetry.py` verifies that structured failures retain error status in OpenTelemetry and Sentry spans.

These tests inject Splunk failures. They do not establish that a released image is deployed or that a particular live Splunk certificate configuration works.
