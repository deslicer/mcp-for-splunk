"""
Tool for retrieving common metadata values (hosts, sourcetypes, sources) for an index.
"""

from typing import Any, Literal

from fastmcp import Context
from splunklib.results import JSONResultsReader

from src.core.base import BaseTool, ToolMetadata
from src.core.list_paging import PaginationError, build_paging, validate_pagination
from src.core.splunk_metadata_page import fetch_metadata_page, validate_index_name
from src.core.utils import log_tool_execution


class GetMetadata(BaseTool):
    """
    Get common metadata values for a specific index.
    """

    METADATA = ToolMetadata(
        name="get_metadata",
        description=(
            "Retrieve distinct metadata values for a given index to aid query construction. "
            "Use this when you need hosts, sourcetypes, or sources in an index. "
            "If has_more is true, call again with offset=next_offset.\n\n"
            "Args:\n"
            "    index (str): Target index (e.g. 'main')\n"
            "    field (str, optional): 'host', 'sourcetype', or 'source' (default 'host')\n"
            "    earliest_time (str, optional): Start time (default '-24h@h')\n"
            "    latest_time (str, optional): End time (default 'now')\n"
            "    limit (int, optional): Page size. Default 100. Maximum 100. "
            "Values above 100 are capped; 0 uses 50. Do not send a larger limit.\n"
            "    offset (int, optional): Result offset (default 0)"
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
        offset: int = 0,
    ) -> dict[str, Any]:
        log_tool_execution(
            "get_metadata",
            index=index,
            field=field,
            earliest_time=earliest_time,
            latest_time=latest_time,
            limit=limit,
            offset=offset,
        )
        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            return self.format_error_response(error_msg)

        try:
            if field in {"host", "source"}:
                metadata_type = "hosts" if field == "host" else "sources"
                page = fetch_metadata_page(
                    service,
                    metadata_type=metadata_type,
                    field=field,
                    count=limit,
                    offset=offset,
                    index=index,
                )
                values = page.values
                paging = page.paging
            else:
                params = validate_pagination(count=limit, offset=offset, max_count=100)
                values, total = self._page_sourcetypes(
                    service, index, earliest_time, latest_time, params.count, params.offset
                )
                paging = build_paging(
                    returned=len(values),
                    total_available=total,
                    offset=params.offset,
                    count=params.count,
                )
        except PaginationError as e:
            return self.format_error_response(str(e))
        except Exception as e:
            self.logger.error("Failed to retrieve metadata values: %s", e)
            await ctx.error(f"Failed to retrieve metadata values: {e}")
            return self.format_error_response(str(e))

        return self.format_success_response(
            {
                "index": index,
                "field": field,
                "values": values,
                **paging,
            }
        )

    @staticmethod
    def _page_sourcetypes(
        service: Any,
        index: str,
        earliest_time: str,
        latest_time: str,
        count: int,
        offset: int,
    ) -> tuple[list[str], int]:
        index = validate_index_name(index)
        total_query = (
            f"| tstats count where index={index} earliest={earliest_time} "
            f"latest={latest_time} by sourcetype | stats count"
        )
        page_query = (
            f"| tstats count where index={index} earliest={earliest_time} "
            f"latest={latest_time} by sourcetype | sort sourcetype "
            f"| streamstats count as row | where row > {offset} "
            f"| head {count} | fields sourcetype"
        )
        total = 0
        for result in JSONResultsReader(service.jobs.oneshot(total_query, output_mode="json")):
            if isinstance(result, dict) and "count" in result:
                total = int(float(result["count"]))
                break
        values: list[str] = []
        for result in JSONResultsReader(service.jobs.oneshot(page_query, output_mode="json")):
            if isinstance(result, dict) and "sourcetype" in result:
                values.append(str(result["sourcetype"]))
        return values, total
