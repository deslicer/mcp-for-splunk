# Search timeouts and server health

`run_oneshot_search`, `run_splunk_search`, and `execute_saved_search` create
tracked jobs and wait up to `MCP_SEARCH_WAIT_SECONDS` (15 seconds by default).
When the job is still running, the response includes `is_done: false`, `job_id`,
and `poll_with: get_search_job_info`. Poll that job and fetch its results with
`get_search_job_results`; do not submit the same search again.

Splunk connection setup, job dispatch, status reads, and result retrieval for
these paths run outside the HTTP event loop. Splunk SDK sockets have a 30-second
connect/read timeout. The search wait budget applies to polling after dispatch;
it is not an overall deadline for authentication, dispatch, TTL, and results.
An unfinished socket read can remain in its worker until its socket timeout,
even after the polling budget returns a job ID.

A timeout during job creation has an unknown dispatch outcome (`search_started:
null`). A known SID is preserved after creation. Neither case is automatically
retried as a new search.

`GET /health` checks the MCP process and loaded components without contacting
Splunk. Its `splunk_connection` value is startup state, identified by
`splunk_connection_check: startup_state`; it does not prove current Splunk
connectivity or successful search execution.

The Docker health check runs curl directly, with a two-second connection timeout
and a four-second total timeout, inside Docker's five-second deadline. Compose
installations must use the same bounded check, since a Compose override replaces
the image's health check. Do not probe `/mcp/`: a redirect or streaming response
is not a liveness check.
