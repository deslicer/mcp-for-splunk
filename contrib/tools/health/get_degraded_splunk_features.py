"""
This tool searches the internal Splunk index to identify features with health issues (warning/critical status)
"""

import time
from typing import Any

from fastmcp import Context
from splunklib.results import ResultsReader

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution, sanitize_search_query


class GetLatestFeatureHealthTool(BaseTool):
    """
    This tool searches the internal Splunk index (index=_internal) and returns only features with health issues.

    The tool filters for features that require attention:
    - warning (yellow): Feature has minor issues or degraded performance
    - critical (red): Feature has serious issues requiring immediate attention

    Features with healthy (green) status are excluded from results to focus on actionable items.

    This tool provides functionality for:
    - Identifying Splunk features that currently have issues requiring attention
    - Troubleshooting infrastructure problems by focusing on degraded/critical features
    - Getting a prioritized list of features that need immediate investigation
    - Monitoring for operational issues without noise from healthy features
    - No results are returned if there are no issues
    """

    METADATA = ToolMetadata(
        name="get_latest_feature_health",
        description="This tool identifies Splunk features with health issues (warning/critical status) requiring attention",
        category="health",
        tags=["health", "monitoring", "infrastructure", "troubleshooting", "issues"],
        requires_connection=True,
        version="1.0.0"
    )

    async def execute(self, ctx: Context, max_results: int = 100) -> dict[str, Any]:
        """
        Execute the get-latest-feature-health functionality to identify features with health issues.

        Args:
            max_results: Maximum number of results to return (default: 100)

        Returns:
            Dict containing:
                - results: List of features with health issues (warning/critical) with host, feature, and status
                - results_count: Number of problematic features found
                - query_executed: The actual query that was executed
                - duration: Time taken to execute the query

        Example:
            get_latest_feature_health(max_results=50) -> {
                "results": [
                    {"host": "splunk-server-01", "feature": "IndexProcessor", "status": "warning"},
                    {"host": "splunk-server-02", "feature": "SearchHead", "status": "critical"}
                ],
                "results_count": 2,
                "query_executed": "index=_internal...",
                "duration": 1.234
            }

            Note: Healthy features are excluded from results to focus on actionable issues.
        """
        log_tool_execution("get_latest_feature_health", max_results=max_results)

        self.logger.info("Executing get-latest-feature-health tool")
        ctx.info("Running get-latest-feature-health operation")

        try:
            is_available, service, error_msg = self.check_splunk_available(ctx)
            if not is_available:
                return self.format_error_response(error_msg)

            # Use static time range - search last 15 minutes for latest health status
            kwargs = {
                "earliest_time": "-15m",
                "latest_time": "now",
                "count": max_results
            }
            ctx.info(f"Get-latest-feature-health parameters: {kwargs}")

            # Updated query with more common health status terms
            query = """index=_internal component=PeriodicHealthReporter
                      | stats latest(color) as status by host feature
                      | where status != "green"
                      | eval status = case(
                          status like "green", "healthy",
                          status like "yellow", "warning",
                          true(), "critical"
                      )"""

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
            self.logger.error(f"Failed to execute get-latest-feature-health: {str(e)}")
            ctx.error(f"Failed to execute get-latest-feature-health: {str(e)}")
            return self.format_error_response(str(e))
