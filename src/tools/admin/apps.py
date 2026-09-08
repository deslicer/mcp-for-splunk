"""
Tool for listing Splunk applications.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.list_paging import PaginationError
from src.core.splunk_rest_page import fetch_rest_collection_page
from src.core.utils import log_tool_execution


class ListApps(BaseTool):
    """
    List installed Splunk apps with pagination.
    """

    METADATA = ToolMetadata(
        name="list_apps",
        description=(
            "Retrieve installed Splunk applications including name, label, version, "
            "description, author, and visibility. If has_more is true, call again with "
            "offset=next_offset.\n\n"
            "Args:\n"
            "    count (int, optional): Page size 1-200 (default 50)\n"
            "    offset (int, optional): Result offset (default 0)\n"
            "    search_filter (str, optional): Splunk REST search filter (e.g. 'name=*TA*')"
        ),
        category="admin",
        tags=["apps", "administration", "management", "inventory", "catalog", "audit"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        count: int = 50,
        offset: int = 0,
        search_filter: str = "",
    ) -> dict[str, Any]:
        log_tool_execution("list_apps", count=count, offset=offset, search_filter=search_filter)
        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            return self.format_error_response(error_msg)

        try:
            page = fetch_rest_collection_page(
                service,
                "/services/apps/local",
                count=count,
                offset=offset,
                search_filter=search_filter,
                extra_params={"sort_key": "name"},
            )
        except PaginationError as e:
            return self.format_error_response(str(e))
        except Exception as e:
            self.logger.error("Failed to list apps: %s", e)
            await ctx.error(f"Failed to list apps: {e}")
            return self.format_error_response(str(e))

        apps = []
        for entry in page.entries:
            content = entry.get("content") or {}
            apps.append(
                {
                    "name": entry.get("name"),
                    "label": content.get("label"),
                    "version": content.get("version"),
                    "description": content.get("description"),
                    "author": content.get("author"),
                    "visible": content.get("visible"),
                }
            )
        await ctx.info(f"Returned {len(apps)} apps (offset={offset})")
        return self.format_success_response({"apps": apps, **page.paging})
