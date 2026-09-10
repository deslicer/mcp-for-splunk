"""
Tool for listing Splunk sourcetypes.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.list_paging import (
    LIST_PAGE_DEFAULT,
    METADATA_PAGE_MAX,
    MetadataPageCount,
    PaginationError,
    count_arg_help,
)
from src.core.splunk_metadata_page import fetch_metadata_page
from src.core.utils import log_tool_execution


class ListSourcetypes(BaseTool):
    """
    List sourcetypes from the configured Splunk instance using metadata.
    """

    METADATA = ToolMetadata(
        name="list_sourcetypes",
        description=(
            "Discover sourcetypes using the metadata command. Large environments are paged. "
            "If has_more is true, call again with offset=next_offset.\n\n"
            "Args:\n"
            f"{count_arg_help(max_count=METADATA_PAGE_MAX)}"
            "    offset (int, optional): Result offset (default 0)\n"
            "    index (str, optional): Limit to one index"
        ),
        category="metadata",
        tags=["sourcetypes", "metadata", "discovery"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        count: MetadataPageCount = LIST_PAGE_DEFAULT,
        offset: int = 0,
        index: str | None = None,
    ) -> dict[str, Any]:
        log_tool_execution("list_sourcetypes", count=count, offset=offset, index=index)
        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            return self.format_error_response(error_msg)

        try:
            page = fetch_metadata_page(
                service,
                metadata_type="sourcetypes",
                field="sourcetype",
                count=count,
                offset=offset,
                index=index,
            )
        except PaginationError as e:
            return self.format_error_response(str(e))
        except Exception as e:
            self.logger.error("Failed to retrieve sourcetypes: %s", e)
            await ctx.error(f"Failed to retrieve sourcetypes: {e}")
            return self.format_error_response(str(e))

        await ctx.info(f"Returned {len(page.values)} sourcetypes (offset={offset})")
        return self.format_success_response({"sourcetypes": page.values, **page.paging})
