"""
Job-based search tool for complex Splunk searches with progress tracking.
"""

import asyncio
import time
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.list_paging import PaginationError, clamp_search_page_size
from src.core.splunk_job_results_page import (
    JOB_TTL_SECONDS,
    SEARCH_PAGE_MAX,
    JobResultsError,
    apply_job_ttl,
    fetch_job_results_page,
)
from src.core.splunk_job_wait import resolve_search_wait_seconds, wait_for_job
from src.core.splunk_web_urls import web_links_from_service
from src.core.utils import log_tool_execution, sanitize_search_query
from src.tools.search.job_message_parser import JobMessageParser


class JobSearch(BaseTool):
    """
    Execute a normal Splunk search job with progress tracking. Use this tool for complex or
    long-running searches where you need to track progress and get detailed job information.
    Best for complex searches that might take longer to complete.
    """

    METADATA = ToolMetadata(
        name="run_splunk_search",
        description=(
            "Run a Splunk search as a tracked job with progress and stats. Use this for complex or "
            "long‑running queries (joins, transforms, large scans) where you need job status, scan/"
            "event counts, and reliable result retrieval. Prefer this over oneshot when the query may "
            "exceed ~30s or requires progress visibility.\n\n"
            "Waits up to MCP_SEARCH_WAIT_SECONDS (default 15) then returns job_id even if the job "
            "is still running. If is_done is false, poll get_search_job_info, then "
            "get_search_job_results. If has_more is true after completion, page with "
            "offset=next_offset.\n"
            "count/max_results of 0 is treated as the default page size (50), max 100.\n"
            "Security: results are constrained by the authenticated user's permissions.\n\n"
            "Args:\n"
            "    query (str): The Splunk search query (SPL) to execute. Can be any valid SPL command"
            "                or pipeline. Supports complex searches with transforming commands, joins,"
            "                and subsearches. Examples: 'index=* | stats count by sourcetype',"
            "                'search error | eval severity=case(...)'"
            "    earliest_time (str, optional): Search start time in Splunk time format."
            "                Examples: '-24h', '-7d@d', '2023-01-01T00:00:00'"
            "                Default: '-24h'"
            "    latest_time (str, optional): Search end time in Splunk time format."
            "                Examples: 'now', '-1h', '@d', '2023-01-01T23:59:59'"
            "                Default: 'now'"
            "    count (int, optional): Page size 1-100 (default 50; 0 uses default)\n"
            "    max_results (int, optional): Deprecated alias for count\n"
            "    offset (int, optional): Result offset (default 0)"
        ),
        category="search",
        tags=["search", "job", "tracking", "complex"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        query: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        count: int | None = None,
        max_results: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        log_tool_execution(
            "run_splunk_search", query=query, earliest_time=earliest_time, latest_time=latest_time
        )

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            await ctx.error(f"Search job failed: {error_msg}")
            return self.format_error_response(error_msg)

        query = sanitize_search_query(query)
        page_size = clamp_search_page_size(count, max_results, max_count=SEARCH_PAGE_MAX)

        self.logger.info(f"Starting normal search with query: {query}")
        await ctx.info(f"Starting normal search with query: {query}")
        await ctx.report_progress(progress=0, total=100)

        try:
            start_time = time.time()
            job = await asyncio.to_thread(
                service.jobs.create, query, earliest_time=earliest_time, latest_time=latest_time
            )
            apply_job_ttl(job, JOB_TTL_SECONDS)
            await ctx.info(f"Search job created: {job.sid}")

            snapshot = await wait_for_job(
                job, wait_seconds=resolve_search_wait_seconds()
            )
            stats = snapshot.content
            await self._report_progress(ctx, stats)

            if snapshot.is_failed:
                return await self._failed_job_response(ctx, job.sid, stats)

            client_config = await self.get_client_config_from_context(ctx)
            links = web_links_from_service(service, client_config)
            duration = time.time() - start_time
            if not snapshot.is_done:
                return self._incomplete_job_response(
                    job.sid, query, stats, duration, links, offset
                )

            await ctx.info(f"Getting results for search job: {job.sid}")
            try:
                page = await asyncio.to_thread(
                    fetch_job_results_page, job, count=page_size, offset=offset
                )
            except (PaginationError, JobResultsError) as results_error:
                await ctx.error(f"Error reading search results: {results_error}")
                return self.format_error_response(f"Error reading search results: {results_error}")

            return self.format_success_response(
                {
                    "is_done": True,
                    "scan_count": int(float(stats.get("scanCount", 0))),
                    "event_count": int(float(stats.get("eventCount", 0))),
                    "results": page.results,
                    "earliest_time": stats.get("earliestTime", ""),
                    "latest_time": stats.get("latestTime", ""),
                    "results_count": page.paging["count"],
                    "query_executed": query,
                    "duration": round(duration, 3),
                    "job_status": {
                        "progress": 100,
                        "is_finalized": stats.get("isFinalized", "0") == "1",
                        "is_failed": False,
                    },
                    **page.paging,
                    **links.job_links(job.sid),
                }
            )

        except Exception as e:
            self.logger.error(f"Search failed with exception: {str(e)}", exc_info=True)
            await ctx.error(f"Search failed: {str(e)}")
            error_detail = str(e)
            if "Connection" in error_detail or "connection" in error_detail:
                error_detail += " (Check Splunk server connectivity and credentials)"
            elif "Authentication" in error_detail or "authentication" in error_detail:
                error_detail += " (Check Splunk username and password)"
            elif "Permission" in error_detail or "permission" in error_detail:
                error_detail += " (Check user permissions for search and index access)"
            return self.format_error_response(error_detail)

    async def _failed_job_response(
        self, ctx: Context, sid: str, stats: dict[str, Any]
    ) -> dict[str, Any]:
        parsed = JobMessageParser.parse(stats.get("messages"))
        error_detail = (
            "; ".join(parsed.error_texts)
            if parsed.error_texts
            else "Job failed with no specific error message"
        )
        self.logger.error(f"Search job {sid} failed: {error_detail}")
        await ctx.error(f"Search job {sid} failed: {error_detail}")
        return self.format_error_response(f"Search job failed: {error_detail}")

    def _incomplete_job_response(
        self,
        sid: str,
        query: str,
        stats: dict[str, Any],
        duration: float,
        links: Any,
        offset: int,
    ) -> dict[str, Any]:
        progress = int(float(stats.get("doneProgress", 0)) * 100)
        return self.format_success_response(
            {
                "is_done": False,
                "results": [],
                "scan_count": int(float(stats.get("scanCount", 0) or 0)),
                "event_count": int(float(stats.get("eventCount", 0) or 0)),
                "results_count": 0,
                "query_executed": query,
                "duration": round(duration, 3),
                "job_status": {
                    "progress": progress,
                    "is_finalized": stats.get("isFinalized", "0") == "1",
                    "is_failed": False,
                },
                "count": 0,
                "offset": offset,
                "total_available": int(float(stats.get("resultCount", 0) or 0)),
                "has_more": False,
                "next_offset": None,
                "poll_with": "get_search_job_info",
                **links.job_links(sid),
            }
        )

    async def _report_progress(self, ctx: Context, stats: dict[str, Any]) -> None:
        progress = int(float(stats.get("doneProgress", 0)) * 100)
        self.logger.info(
            f"Search job progress {progress}%, "
            f"scanned {stats.get('scanCount', 0)}, matched {stats.get('eventCount', 0)}"
        )
        await ctx.report_progress(progress=progress, total=100)
