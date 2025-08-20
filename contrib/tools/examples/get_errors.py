"""
This tools retrieves any existing errors in a splunk internal index.

SPL Query: search for any errors in the splunk internal index
"""

import time
from typing import Any

from fastmcp import Context
from splunklib.results import ResultsReader

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution, sanitize_search_query


class GetErrorsTool(BaseTool):
    """
    This tools retrieves any existing errors in a splunk internal index.

    This tool executes the following Splunk search:
    search for any errors in the splunk internal index

    SPL Query:
    index=_internal log_level=ERROR
    """

    METADATA = ToolMetadata(
        name="get_errors",
        description="This tools retrieves any existing errors in a splunk internal index.",
        category="examples",
        tags=["example", "tutorial", "demo", "splunk", "search", "spl", "example"],
        requires_connection=True,
        version="1.0.0"
    )

    async def execute(
        self,
        ctx: Context,
        earliest_time: str = "-15m",
        latest_time: str = "now",
        max_results: int = 100
    ) -> dict[str, Any]:
        """
        Execute the get_errors Splunk search.

        Args:
            earliest_time: Search start time (default: "-15m")
            latest_time: Search end time (default: "now")
            max_results: Maximum number of results to return (default: 100)

        Returns:
            Dict containing:
                - results: List of search results as dictionaries
                - results_count: Number of results returned
                - query_executed: The actual query that was executed
                - duration: Search execution time in seconds
        """
        log_tool_execution("get_errors", earliest_time=earliest_time, latest_time=latest_time, max_results=max_results)

        self.logger.info("Executing get_errors search")
        ctx.info("Running get_errors search operation")

        try:
            is_available, service, error_msg = self.check_splunk_available(ctx)
            if not is_available:
                return self.format_error_response(error_msg)

            kwargs = {
                "earliest_time": earliest_time,
                "latest_time": latest_time,
                "count": max_results
            }
            ctx.info(f"Search parameters: {kwargs}")

            # The SPL query for this tool
            query = "index=_internal log_level=ERROR"

            # Sanitize and prepare the query
            query = sanitize_search_query(query)
            start_time = time.time()
            job = service.jobs.oneshot(query, **kwargs)
            results = []
            result_count = 0

            for result in ResultsReader(job):
                if isinstance(result, dict):
                    results.append(result)
                    result_count += 1
                    if result_count >= max_results:
                        break

            duration = time.time() - start_time

            return self.format_success_response({
                "results": results,
                "results_count": result_count,
                "query_executed": query,
                "duration": round(duration, 3)
            })

        except Exception as e:
            self.logger.error(f"Failed to execute get_errors search: {str(e)}")
            ctx.error(f"Failed to execute get_errors search: {str(e)}")
            return self.format_error_response(str(e))
