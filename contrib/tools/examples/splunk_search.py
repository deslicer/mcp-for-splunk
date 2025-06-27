"""
This tool searches splunk health reporter to get infrastructure health indicators
"""

import time
from typing import Any, Dict

from fastmcp import Context
from splunklib.results import ResultsReader
from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution, sanitize_search_query


class SplunkSearchTool(BaseTool):
    """
    This tool searches splunk health reporter to get infrastructure health indicators

    This tool provides functionality for:
    - TODO: Add use cases
    - TODO: Add examples
    """

    METADATA = ToolMetadata(
        name="splunk_search",
        description="This tool searches splunk health reporter to get infrastructure health indicators",
        category="examples",
        tags=["example", "tutorial", "demo", "demo"],
        requires_connection=True,
        version="1.0.0"
    )

    async def execute(self, ctx: Context, earliest_time: str = "-15m", latest_time: str = "now", max_results: int = 100) -> Dict[str, Any]:
        """
        Execute the splunk-search functionality.

        Args:
            earliest_time: Search start time (default: "-15m")
            latest_time: Search end time (default: "now")
            max_results: Maximum number of results to return (default: 100)

        Returns:
            Dict containing:
                - results: List of search results as dictionaries
                - results_count: Number of results returned
                - query_executed: The actual query that was executed

        Example:
            splunk_search(
                earliest_time="-1h",
                max_results=10
            ) -> {"result": "TODO: Add example result"}
        """
        log_tool_execution("splunk_search", earliest_time=earliest_time, latest_time=latest_time, max_results=max_results)

        self.logger.info(f"Executing splunk-search tool")
        ctx.info(f"Running splunk-search operation")

        try:
            is_available, service, error_msg = self.check_splunk_available(ctx)
            if not is_available:
                return self.format_error_response(error_msg)

            kwargs = {
                "earliest_time": earliest_time,
                "latest_time": latest_time,
                "count": max_results
            }
            ctx.info(f"Splunk-search parameters: {kwargs}")

            query = "index=_internal component=PeriodicHealthReporter | stats latest(color) as status by host feature | eval status = case(status like \"green\", \"healthy\", status like \"yellow\", \"degraded\",true(), \"issues\")"
            
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
            self.logger.error(f"Failed to execute splunk-search: {str(e)}")
            ctx.error(f"Failed to execute splunk-search: {str(e)}")
            return self.format_error_response(str(e))
