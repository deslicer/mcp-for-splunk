"""
Job-based search tool for complex Splunk searches with progress tracking.
"""

import time
from typing import Any

from fastmcp import Context
from splunklib.results import ResultsReader

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
            "Executes a Splunk search query as a background job with progress tracking and detailed "
            "statistics. Best for complex, long-running searches that may take more than 30 seconds. "
            "Creates a persistent search job that can be monitored for progress and provides detailed "
            "execution statistics including scan count, event count, and performance metrics."
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
            ctx.error(f"Search job failed: {error_msg}")
            return self.format_error_response(error_msg)

        # Sanitize and prepare the query
        query = sanitize_search_query(query)

        self.logger.info(f"Starting normal search with query: {query}")
        ctx.info(f"Starting normal search with query: {query}")

        try:
            start_time = time.time()

            # Create the search job
            job = service.jobs.create(query, earliest_time=earliest_time, latest_time=latest_time)
            ctx.info(f"Search job created: {job.sid}")

            # Poll for completion
            while not job.is_done():
                stats = job.content
                progress = {
                    "done": stats.get("isDone", "0") == "1",
                    "progress": float(stats.get("doneProgress", 0)) * 100,
                    "scan_progress": float(stats.get("scanCount", 0)),
                    "event_progress": float(stats.get("eventCount", 0)),
                }
                ctx.report_progress(progress)
                self.logger.info(
                    f"Search job {job.sid} in progress... "
                    f"Progress: {progress['progress']:.1f}%, "
                    f"Scanned: {progress['scan_progress']} events, "
                    f"Matched: {progress['event_progress']} events"
                )
                time.sleep(2)

            # Get the results using ResultsReader for consistent parsing
            results = []
            result_count = 0
            ctx.info(f"Getting results for search job: {job.sid}")
            for result in ResultsReader(job.results()):
                if isinstance(result, dict):
                    results.append(result)
                    result_count += 1

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
                    "status": {
                        "progress": 100,
                        "is_finalized": stats.get("isFinalized", "0") == "1",
                        "is_failed": stats.get("isFailed", "0") == "1",
                    },
                }
            )

        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            ctx.error(f"Search failed: {str(e)}")
            return self.format_error_response(str(e))
