"""
Tool for retrieving common metadata values (hosts, sourcetypes, sources) for an index.
"""

from typing import Any, Literal

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class GetMetadata(BaseTool):
    """
    Get common metadata values for a specific index.

    Retrieves distinct values for selected Splunk metadata fields within a time window to
    help build accurate searches. Supports hosts, sources (via metadata) and sourcetypes
    (via tstats) for a given index.
    """

    METADATA = ToolMetadata(
        name="get_metadata",
        description=(
            "Retrieve distinct metadata values for a given index to aid query construction. "
            "Use this tool when you need to discover which hosts, sourcetypes, or sources are "
            "present in an index within a recent time window. This is useful for building "
            "targeted searches or validating data availability. Results are constrained by "
            "your Splunk permissions.\n\n"
            "Args:\n"
            "    index (str): Target index to inspect (e.g., 'main', 'security')\n"
            "    field (str, optional): Metadata field to list values for. One of 'host', "
            "'sourcetype', or 'source' (default: 'host')\n"
            "    earliest_time (str, optional): Search start time (e.g., '-24h@h') (default: '-24h@h')\n"
            "    latest_time (str, optional): Search end time (e.g., 'now') (default: 'now')\n"
            "    limit (int, optional): Maximum number of distinct values to return (default: 100)\n\n"
            "Response Format:\n"
            "Returns a dictionary with 'status' and 'data' containing:\n"
            "- field: Requested field name\n"
            "- index: Target index\n"
            "- values: Array of distinct values (up to 'limit')\n"
            "- count: Number of values returned"
        ),
        category="metadata",
        tags=["metadata", "discovery", "indexes", "hosts", "sourcetypes", "sources"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        index: str,
        field: Literal["host", "sourcetype", "source"] = "host",
        earliest_time: str = "-24h@h",
        latest_time: str = "now",
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Retrieve distinct metadata values for an index.

        Args:
            index: Target index to inspect
            field: Metadata field to list values for ('host', 'sourcetype', 'source')
            earliest_time: Search start time
            latest_time: Search end time
            limit: Maximum number of values to return

        Returns:
            Dict with metadata values and counts
        """
        log_tool_execution(
            "get_metadata",
            index=index,
            field=field,
            earliest_time=earliest_time,
            latest_time=latest_time,
            limit=limit,
        )

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        self.logger.info("Retrieving metadata values for index '%s' field '%s'", index, field)
        await ctx.info(f"Retrieving {field} values for index '{index}'")

        try:
            values: list[str] = []

            if field == "host":
                # metadata supports hosts directly
                query = f"| metadata type=hosts index={index} | table host | head {int(limit)}"
                job = service.jobs.oneshot(query)
                from splunklib.results import ResultsReader  # lazy import

                for result in ResultsReader(job):
                    if isinstance(result, dict) and "host" in result:
                        values.append(str(result["host"]))

            elif field == "source":
                # metadata supports sources directly
                query = f"| metadata type=sources index={index} | table source | head {int(limit)}"
                job = service.jobs.oneshot(query)
                from splunklib.results import ResultsReader  # lazy import

                for result in ResultsReader(job):
                    if isinstance(result, dict) and "source" in result:
                        values.append(str(result["source"]))

            elif field == "sourcetype":
                # Use tstats for sourcetypes within time bounds
                query = (
                    f"| tstats count where index={index} earliest={earliest_time} latest={latest_time} by sourcetype "
                    f"| fields sourcetype | head {int(limit)}"
                )
                job = service.jobs.oneshot(query)
                from splunklib.results import ResultsReader  # lazy import

                for result in ResultsReader(job):
                    if isinstance(result, dict) and "sourcetype" in result:
                        values.append(str(result["sourcetype"]))

            values = list(dict.fromkeys(values))  # de-duplicate while preserving order

            return self.format_success_response(
                {
                    "index": index,
                    "field": field,
                    "values": values[: int(limit)],
                    "count": len(values[: int(limit)]),
                }
            )

        except Exception as e:
            self.logger.error("Failed to retrieve metadata values: %s", str(e))
            await ctx.error(f"Failed to retrieve metadata values: {str(e)}")
            return self.format_error_response(str(e))
