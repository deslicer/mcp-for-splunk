"""
Tool for listing Splunk data sources.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.list_paging import PaginationError
from src.core.splunk_metadata_page import fetch_metadata_page
from src.core.utils import log_tool_execution


class ListSources(BaseTool):
    """
    List data sources from the configured Splunk instance using metadata.
    """

    METADATA = ToolMetadata(
        name="list_sources",
        description=(
            "Discover data sources using the metadata command. Sources can be numerous; "
            "results are paged. If has_more is true, call again with offset=next_offset.\n\n"
            "Args:\n"
            "    count (int, optional): Page size 1-100 (default 50)\n"
            "    offset (int, optional): Result offset (default 0)\n"
            "    index (str, optional): Limit to one index"
        ),
        category="metadata",
        tags=["sources", "metadata", "discovery"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        count: int = 50,
        offset: int = 0,
        index: str | None = None,
    ) -> dict[str, Any]:
        log_tool_execution("list_sources", count=count, offset=offset, index=index)
        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            return self.format_error_response(error_msg)

        try:
            page = fetch_metadata_page(
                service,
                metadata_type="sources",
                field="source",
                count=count,
                offset=offset,
                index=index,
            )
        except PaginationError as e:
            return self.format_error_response(str(e))
        except Exception as e:
            self.logger.error("Failed to retrieve sources: %s", e)
            return self.format_error_response(str(e))

        return self.format_success_response({"sources": page.values, **page.paging})
