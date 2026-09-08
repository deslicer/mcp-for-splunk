"""
Job-based search tool for complex Splunk searches with progress tracking.
"""

import asyncio
import time
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.list_paging import PaginationError
from src.core.splunk_job_results_page import JobResultsError, fetch_job_results_page
from src.core.splunk_web_urls import web_links_from_service
from src.core.utils import log_tool_execution, sanitize_search_query
from src.tools.search.job_message_parser import JobMessageParser
from src.tools.search.oneshot_search import _resolve_page_size


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
            "Outputs: job id, first result page, paging fields, and Splunk Web job links. "
            "If has_more is true, call get_search_job_results with job_id and offset=next_offset.\n"
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
            "    count (int, optional): Page size 1-100 (default 50)\n"
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
        """
        Execute a Splunk search job with comprehensive progress tracking and statistics.

        Args:
            query (str): The Splunk search query (SPL) to execute. Can be any valid SPL command
                        or pipeline. Supports complex searches with transforming commands, joins,
                        and subsearches. Examples: "index=* | stats count by sourcetype",
                        "search error | eval severity=case(...)"
            earliest_time (str, optional): Search start time in Splunk time format.
                                         Examples: "-24h", "-7d@d", "2023-01-01T00:00:00"
                                         Default: "-24h"
            latest_time (str, optional): Search end time in Splunk time format.
                                       Examples: "now", "-1h", "@d", "2023-01-01T23:59:59"
                                       Default: "now"

        Returns:
            Dict containing search results, job statistics, progress information, and performance metrics
        """
        log_tool_execution(
            "run_splunk_search", query=query, earliest_time=earliest_time, latest_time=latest_time
        )

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            await ctx.error(f"Search job failed: {error_msg}")
            return self.format_error_response(error_msg)

        # Sanitize and prepare the query
        query = sanitize_search_query(query)

        self.logger.info(f"Starting normal search with query: {query}")
        await ctx.info(f"Starting normal search with query: {query}")
        await ctx.report_progress(progress=0, total=100)

        try:
            start_time = time.time()

            # Create the search job
            job = service.jobs.create(query, earliest_time=earliest_time, latest_time=latest_time)
            if hasattr(job, "set_ttl"):
                try:
                    job.set_ttl(1800)
                except Exception:
                    pass
            await ctx.info(f"Search job created: {job.sid}")

            # Poll for completion
            while not job.is_done():
                stats = job.content

                # Check if job failed during execution
                if stats.get("isFailed", "0") == "1":
                    parsed = JobMessageParser.parse(stats.get("messages"))
                    error_detail = "; ".join(parsed.error_texts) if parsed.error_texts else (
                        "Job failed with no specific error message"
                    )
                    self.logger.error(f"Search job {job.sid} failed: {error_detail}")
                    await ctx.error(f"Search job {job.sid} failed: {error_detail}")
                    return self.format_error_response(f"Search job failed: {error_detail}")

                progress_dict = {
                    "done": stats.get("isDone", "0") == "1",
                    "progress": float(stats.get("doneProgress", 0)) * 100,
                    "scan_progress": float(stats.get("scanCount", 0)),
                    "event_progress": float(stats.get("eventCount", 0)),
                }

                # Report progress with just the numeric value
                await ctx.report_progress(progress=int(progress_dict["progress"]), total=100)

                self.logger.info(
                    f"Search job {job.sid} in progress... "
                    f"Progress: {progress_dict['progress']:.1f}%, "
                    f"Scanned: {progress_dict['scan_progress']} events, "
                    f"Matched: {progress_dict['event_progress']} events"
                )
                await asyncio.sleep(2)

            # Final check for job failure after completion
            await ctx.report_progress(progress=100, total=100)
            final_stats = job.content
            if final_stats.get("isFailed", "0") == "1":
                parsed = JobMessageParser.parse(final_stats.get("messages"))
                error_detail = "; ".join(parsed.error_texts) if parsed.error_texts else (
                    "Job failed with no specific error message"
                )
                self.logger.error(f"Search job {job.sid} failed after completion: {error_detail}")
                await ctx.error(f"Search job {job.sid} failed: {error_detail}")
                return self.format_error_response(f"Search job failed: {error_detail}")

            await ctx.info(f"Getting results for search job: {job.sid}")
            page_size = _resolve_page_size(count, max_results)
            try:
                page = await asyncio.to_thread(
                    fetch_job_results_page, job, count=page_size, offset=offset
                )
            except (PaginationError, JobResultsError) as results_error:
                await ctx.error(f"Error reading search results: {results_error}")
                return self.format_error_response(f"Error reading search results: {results_error}")

            # Get final job stats
            stats = job.content
            duration = time.time() - start_time

            client_config = await self.get_client_config_from_context(ctx)
            links = web_links_from_service(service, client_config)
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
                        "is_failed": stats.get("isFailed", "0") == "1",
                    },
                    **page.paging,
                    **links.job_links(job.sid),
                }
            )

        except Exception as e:
            # Enhanced exception logging
            self.logger.error(f"Search failed with exception: {str(e)}", exc_info=True)
            await ctx.error(f"Search failed: {str(e)}")

            # Try to provide more context about the error
            error_detail = str(e)
            if "Connection" in error_detail or "connection" in error_detail:
                error_detail += " (Check Splunk server connectivity and credentials)"
            elif "Authentication" in error_detail or "authentication" in error_detail:
                error_detail += " (Check Splunk username and password)"
            elif "Permission" in error_detail or "permission" in error_detail:
                error_detail += " (Check user permissions for search and index access)"

            return self.format_error_response(error_detail)
