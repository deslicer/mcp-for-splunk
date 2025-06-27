"""
testing search template functionality

SPL Query: Searches the internal index and counts events by component
"""

import time
from typing import Any

from fastmcp import Context
from splunklib.results import ResultsReader

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution, sanitize_search_query


class TestSearchTemplateTool(BaseTool):
    """
    testing search template functionality

    This tool executes the following Splunk search:
    Searches the internal index and counts events by component

    SPL Query:
    index=_internal
| stats count by component
    """

    METADATA = ToolMetadata(
        name="test_search_template",
        description="testing search template functionality",
        category="examples",
        tags=["example", "tutorial", "demo", "splunk", "search", "spl", "test", "template"],
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
        Execute the test search template Splunk search.

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
        log_tool_execution("test_search_template", earliest_time=earliest_time, latest_time=latest_time, max_results=max_results)

        self.logger.info("Executing test search template search")
        ctx.info("Running test search template search operation")

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
            query = "index=_internal  | stats count by component"

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
            self.logger.error(f"Failed to execute test search template search: {str(e)}")
            ctx.error(f"Failed to execute test search template search: {str(e)}")
            return self.format_error_response(str(e))
