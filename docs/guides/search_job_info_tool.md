# Search Job Info Tool

Use `get_search_job_info` to retrieve status, properties, and messages/errors for an existing Splunk search job id (sid).

## When to use it

- You ran `run_splunk_search` and got a `job_id` back.
- You want to check whether the job is done, failed, or still running.
- You want to see Splunk job messages (errors/warnings) without re-running the search.

## Tool: `get_search_job_info`

### Parameters

- `job_id` (required): The Splunk search job id (sid)
- `include_raw_content` (optional, default `false`): Include raw `job.content` for debugging

### Returns

- `job_status`: `is_done`, `is_failed`, `is_finalized`, `dispatch_state`, `progress_percent`
- `messages`: Normalized list of `{ type, text }` (handles Splunk’s mixed message formats)
- `errors`: Error strings extracted from messages (and a fallback if the job failed without messages)
- `counts`/`timing`: Included when available on the job

## Example workflow

1. Start a job-based search:

```json
{
  "tool": "run_splunk_search",
  "arguments": {
    "query": "index=_internal | stats count by sourcetype",
    "earliest_time": "-24h",
    "latest_time": "now"
  }
}
```

1. Use the returned `job_id` to fetch status and messages:

```json
{
  "tool": "get_search_job_info",
  "arguments": {
    "job_id": "1737394021.12345"
  }
}
```
