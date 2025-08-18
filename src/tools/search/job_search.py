"""
Job-based search tool for complex Splunk searches with progress tracking.
"""

import time
from typing import Any

from fastmcp import Context
from splunklib.results import JSONResultsReader

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution, sanitize_search_query


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
            "Outputs: job id, results (JSON), counts, timing, and job status.\n"
            "Security: results are constrained by the authenticated user's permissions."
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
        ),
        category="search",
        tags=["search", "job", "tracking", "complex"],
        requires_connection=True,
    )

    async def execute(
        self, ctx: Context, query: str, earliest_time: str = "-24h", latest_time: str = "now"
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
            await ctx.info(f"Search job created: {job.sid}")

            # Poll for completion
            while not job.is_done():
                stats = job.content

                # Check if job failed during execution
                if stats.get("isFailed", "0") == "1":
                    # Job failed, get error messages
                    error_messages = []
                    if "messages" in stats:
                        for message in stats["messages"]:
                            # Handle both dictionary and string message formats
                            if isinstance(message, dict):
                                if message.get("type") == "ERROR":
                                    error_messages.append(message.get("text", "Unknown error"))
                            elif isinstance(message, str):
                                # String messages are typically error messages
                                error_messages.append(message)

                    error_detail = (
                        "; ".join(error_messages)
                        if error_messages
                        else "Job failed with no specific error message"
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
                time.sleep(2)

            # Final check for job failure after completion
            await ctx.report_progress(progress=100, total=100)
            final_stats = job.content
            if final_stats.get("isFailed", "0") == "1":
                # Job failed, get error messages
                error_messages = []
                if "messages" in final_stats:
                    for message in final_stats["messages"]:
                        # Handle both dictionary and string message formats
                        if isinstance(message, dict):
                            if message.get("type") == "ERROR":
                                error_messages.append(message.get("text", "Unknown error"))
                        elif isinstance(message, str):
                            # String messages are typically error messages
                            error_messages.append(message)

                error_detail = (
                    "; ".join(error_messages)
                    if error_messages
                    else "Job failed with no specific error message"
                )
                self.logger.error(f"Search job {job.sid} failed after completion: {error_detail}")
                await ctx.error(f"Search job {job.sid} failed: {error_detail}")
                return self.format_error_response(f"Search job failed: {error_detail}")

            # Get the results using JSONResultsReader with output_mode=json
            results = []
            result_count = 0
            await ctx.info(f"Getting results for search job: {job.sid}")

            try:
                # Request results in JSON format and use JSONResultsReader
                reader = JSONResultsReader(job.results(output_mode="json"))
                for result in reader:
                    if isinstance(result, dict):
                        results.append(result)
                        result_count += 1
            except Exception as results_error:
                self.logger.error(f"Error reading results for job {job.sid}: {str(results_error)}")
                await ctx.error(f"Error reading search results: {str(results_error)}")
                return self.format_error_response(
                    f"Error reading search results: {str(results_error)}"
                )

            # Get final job stats
            stats = job.content
            duration = time.time() - start_time

            return self.format_success_response(
                {
                    "job_id": job.sid,
                    "is_done": True,
                    "scan_count": int(float(stats.get("scanCount", 0))),
                    "event_count": int(float(stats.get("eventCount", 0))),
                    "results": results,
                    "earliest_time": stats.get("earliestTime", ""),
                    "latest_time": stats.get("latestTime", ""),
                    "results_count": result_count,
                    "query_executed": query,
                    "duration": round(duration, 3),
                    "job_status": {
                        "progress": 100,
                        "is_finalized": stats.get("isFinalized", "0") == "1",
                        "is_failed": stats.get("isFailed", "0") == "1",
                    },
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
