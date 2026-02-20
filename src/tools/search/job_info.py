"""
Search job info tool for Splunk MCP server.

Retrieves status/properties/messages for an existing Splunk search job by sid.
This is useful for polling a job created by `run_splunk_search` without re-running it.
"""

import time
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution
from src.tools.search.job_message_parser import JobMessageParser


class GetSearchJobInfo(BaseTool):
    """
    Get status/properties/messages for an existing Splunk search job by job id (sid).

    Use this tool after creating a job with `run_splunk_search` when you want to:
    - check progress or completion status
    - inspect job properties (counts, timing, dispatch state)
    - view warning/error messages produced by the job
    """

    METADATA = ToolMetadata(
        name="get_search_job_info",
        description=(
            "Get status/properties/messages for a Splunk search job by job id (sid). Use this after "
            "run_splunk_search returns a job_id when you want to poll progress or inspect errors "
            "without re-running the search.\n\n"
            "Args:\n"
            "    job_id (str): Splunk search job id (sid)\n"
            "    include_raw_content (bool, optional): Include raw job.content for debugging "
            "(default: False)\n"
        ),
        category="search",
        tags=["search", "job", "status", "errors", "messages"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        job_id: str,
        include_raw_content: bool = False,
    ) -> dict[str, Any]:
        log_tool_execution(
            "get_search_job_info", job_id=job_id, include_raw_content=include_raw_content
        )

        if not job_id or not job_id.strip():
            return self.format_error_response("job_id is required", job_id=job_id)

        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            await ctx.error(f"Get search job info failed: {error_msg}")
            return self.format_error_response(error_msg, job_id=job_id)

        try:
            # Fetch job by sid via Splunk SDK.
            try:
                job = service.jobs[job_id]
            except Exception as e:
                # splunklib can raise KeyError or HTTPError depending on failure mode.
                message = f"Search job not found or inaccessible: {job_id} ({type(e).__name__}: {e})"
                await ctx.error(message)
                return self.format_error_response(message, job_id=job_id)

            # Refresh to ensure we have current properties.
            try:
                job.refresh()
            except Exception:
                # If refresh fails, continue with best-effort content access.
                pass

            stats: dict[str, Any] = dict(job.content or {})

            parsed = JobMessageParser.parse(stats.get("messages"))

            # Job status flags are typically "0"/"1" strings.
            is_done = stats.get("isDone", "0") == "1"
            is_failed = stats.get("isFailed", "0") == "1"
            is_finalized = stats.get("isFinalized", "0") == "1"

            # Prefer doneProgress (0..1) -> percent, otherwise fallback.
            progress_percent = 0
            try:
                if "doneProgress" in stats:
                    progress_percent = int(float(stats.get("doneProgress", 0)) * 100)
            except Exception:
                progress_percent = 0

            dispatch_state = stats.get("dispatchState", "") or stats.get("dispatch_state", "")

            counts: dict[str, int] = {}
            for key, out_key in [
                ("scanCount", "scan_count"),
                ("eventCount", "event_count"),
                ("resultCount", "result_count"),
            ]:
                if key in stats and stats.get(key) is not None:
                    try:
                        counts[out_key] = int(float(stats.get(key, 0)))
                    except Exception:
                        pass

            timing: dict[str, Any] = {}
            if stats.get("earliestTime") is not None:
                timing["earliest_time"] = stats.get("earliestTime", "")
            if stats.get("latestTime") is not None:
                timing["latest_time"] = stats.get("latestTime", "")
            if stats.get("runDuration") is not None:
                timing["run_duration"] = stats.get("runDuration", "")

            errors: list[str] = list(parsed.error_texts)
            if is_failed and not errors:
                errors = ["Job failed with no specific error message"]

            response: dict[str, Any] = {
                "job_id": job_id,
                "job_status": {
                    "is_done": is_done,
                    "is_failed": is_failed,
                    "is_finalized": is_finalized,
                    "dispatch_state": dispatch_state,
                    "progress_percent": max(0, min(100, progress_percent)),
                },
                "messages": parsed.messages,
                "errors": errors,
                "retrieved_at": time.time(),
            }

            if counts:
                response["counts"] = counts
            if timing:
                response["timing"] = timing
            if include_raw_content:
                response["raw_content"] = stats

            return self.format_success_response(response)

        except Exception as e:
            self.logger.error("Failed to get search job info for '%s': %s", job_id, e)
            await ctx.error(f"Failed to get search job info for '{job_id}': {str(e)}")
            return self.format_error_response(str(e), job_id=job_id)
