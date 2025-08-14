"""
One-shot search tool for immediate Splunk search execution.
"""

import time
from typing import Any

from fastmcp import Context
from splunklib.results import JSONResultsReader

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
        description=(
            "Executes a Splunk search query immediately and returns results in a single operation. "
            "Best for simple, fast searches that complete quickly (under 30 seconds). Returns up to "
            "the specified number of results without creating a persistent search job. Ideal for "
            "quick data queries, statistics, and simple reporting."
        ),
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
        Execute a one-shot Splunk search with immediate results.

        Args:
            query (str): The Splunk search query (SPL) to execute. Can be any valid SPL command
                        or pipeline. The 'search' command is automatically prepended if needed.
                        Examples: "index=main error", "| metadata type=hosts", "| stats count by sourcetype"
            earliest_time (str, optional): Search start time in Splunk time format.
                                         Examples: "-15m", "-1h", "-1d@d", "2023-01-01T00:00:00"
                                         Default: "-15m"
            latest_time (str, optional): Search end time in Splunk time format.
                                       Examples: "now", "-1h", "2023-01-01T23:59:59"
                                       Default: "now"
            max_results (int, optional): Maximum number of results to return. Higher values may
                                       cause longer execution times. Range: 1-10000. Default: 100

        Returns:
            Dict containing search results, count, executed query, and execution duration
        """
        log_tool_execution(
            "run_oneshot_search", query=query, earliest_time=earliest_time, latest_time=latest_time
        )

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            await ctx.error(f"One-shot search failed: {error_msg}")
            return self.format_error_response(
                error_msg, results=[], results_count=0, query_executed=query
            )

        # Sanitize and prepare the query
        query = sanitize_search_query(query)

        self.logger.info(f"Executing one-shot search: {query}")
        await ctx.info(f"Executing one-shot search: {query}")

        try:
            kwargs = {
                "earliest_time": earliest_time,
                "latest_time": latest_time,
                "count": max_results,
                "output_mode": "json",  # Request JSON format
            }
            await ctx.info(f"One-shot search parameters: {kwargs}")

            start_time = time.time()
            job = service.jobs.oneshot(query, **kwargs)

            # Process results using JSONResultsReader
            results = []
            result_count = 0

            reader = JSONResultsReader(job)
            for result in reader:
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
            await ctx.error(f"One-shot search failed: {str(e)}")
            return self.format_error_response(
                str(e), results=[], results_count=0, query_executed=query
            )
