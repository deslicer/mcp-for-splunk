"""
One-shot search tool for immediate Splunk search execution.
"""

import time
from typing import Any

from fastmcp import Context
from splunklib.results import ResultsReader

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution, sanitize_search_query


class OneshotSearch(BaseTool):
    """
    Execute a one-shot Splunk search that returns results immediately. Use this tool for quick,
    simple searches where you need immediate results and don't need to track job progress.
    Best for simple searches that return quickly.
    """

    METADATA = ToolMetadata(
        name="run_oneshot_search",
        description="Execute a one-shot Splunk search that returns results immediately",
        category="search",
        tags=["search", "oneshot", "quick"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        query: str,
        earliest_time: str = "-15m",
        latest_time: str = "now",
        max_results: int = 100,
    ) -> dict[str, Any]:
        """
        Execute a one-shot Splunk search.

        Args:
            query: The Splunk search query (SPL) to execute. The 'search' command will be automatically
                added if not present (e.g., "index=main" becomes "search index=main")
            earliest_time: Search start time (default: "-15m")
            latest_time: Search end time (default: "now")
            max_results: Maximum number of results to return (default: 100)

        Returns:
            Dict containing:
                - results: List of search results as dictionaries
                - results_count: Number of results returned
                - query_executed: The actual query that was executed

        Example:
            run_oneshot_search(
                query="index=_internal | stats count by log_level",
                earliest_time="-1h",
                max_results=10
            )
        """
        log_tool_execution(
            "run_oneshot_search", query=query, earliest_time=earliest_time, latest_time=latest_time
        )

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            ctx.error(f"One-shot search failed: {error_msg}")
            return self.format_error_response(
                error_msg, results=[], results_count=0, query_executed=query
            )

        # Sanitize and prepare the query
        query = sanitize_search_query(query)

        self.logger.info(f"Executing one-shot search: {query}")
        ctx.info(f"Executing one-shot search: {query}")

        try:
            kwargs = {
                "earliest_time": earliest_time,
                "latest_time": latest_time,
                "count": max_results,
            }
            ctx.info(f"One-shot search parameters: {kwargs}")

            start_time = time.time()
            job = service.jobs.oneshot(query, **kwargs)

            # Process results
            results = []
            result_count = 0

            for result in ResultsReader(job):
                if isinstance(result, dict):
                    results.append(result)
                    result_count += 1
                    if result_count >= max_results:
                        break

            duration = time.time() - start_time

            return self.format_success_response(
                {
                    "results": results,
                    "results_count": result_count,
                    "query_executed": query,
                    "duration": round(duration, 3),
                }
            )

        except Exception as e:
            self.logger.error(f"One-shot search failed: {str(e)}")
            ctx.error(f"One-shot search failed: {str(e)}")
            return self.format_error_response(
                str(e), results=[], results_count=0, query_executed=query
            )
