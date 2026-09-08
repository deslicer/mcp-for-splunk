"""
Tool for listing Splunk indexes.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.list_paging import PaginationError
from src.core.splunk_rest_page import fetch_rest_collection_page
from src.core.utils import log_tool_execution


class ListIndexes(BaseTool):
    """
    Retrieves a page of accessible indexes from the configured Splunk instance.
    """

    METADATA = ToolMetadata(
        name="list_indexes",
        description=(
            "Retrieve accessible data indexes from the Splunk instance. "
            "Use this to discover which indexes you can query when building searches. "
            "Excludes internal indexes (name starts with _) unless include_internal is true. "
            "If has_more is true, call again with offset=next_offset.\n\n"
            "Args:\n"
            "    count (int, optional): Page size 1-200 (default 50)\n"
            "    offset (int, optional): Result offset (default 0)\n"
            "    search_filter (str, optional): Splunk REST search filter (e.g. 'name=*sec*')\n"
            "    include_internal (bool, optional): Include _internal-style indexes (default false)"
        ),
        category="metadata",
        tags=["indexes", "metadata", "discovery"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        count: int = 50,
        offset: int = 0,
        search_filter: str = "",
        include_internal: bool = False,
    ) -> dict[str, Any]:
        log_tool_execution(
            "list_indexes",
            count=count,
            offset=offset,
            search_filter=search_filter,
            include_internal=include_internal,
        )
        try:
            service = await self.get_splunk_service(ctx)
        except Exception as e:
            return self.format_error_response(str(e), indexes=[], count=0)

        filters = []
        if not include_internal:
            filters.append("NOT name=_*")
        if search_filter:
            filters.append(search_filter)
        try:
            page = fetch_rest_collection_page(
                service,
                "/services/data/indexes",
                count=count,
                offset=offset,
                search_filter=" ".join(filters),
                extra_params={"sort_key": "name"},
            )
        except PaginationError as e:
            return self.format_error_response(str(e), indexes=[], count=0)
        except Exception as e:
            self.logger.error("Failed to list indexes: %s", e)
            await ctx.error(f"Failed to list indexes: {e}")
            return self.format_error_response(str(e), indexes=[], count=0)

        names = [entry.get("name", "") for entry in page.entries]
        await ctx.info(f"Returned {len(names)} indexes (offset={offset})")
        return self.format_success_response(
            {
                "indexes": names,
                **page.paging,
                "include_internal": include_internal,
            }
        )
