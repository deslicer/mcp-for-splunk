"""
Tool for listing Splunk users.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.list_paging import LIST_PAGE_DEFAULT, ListPageCount, PaginationError, count_arg_help
from src.core.splunk_rest_page import fetch_rest_collection_page
from src.core.utils import log_tool_execution


class ListUsers(BaseTool):
    """
    List Splunk users with pagination.
    """

    METADATA = ToolMetadata(
        name="list_users",
        description=(
            "Retrieve Splunk users and their properties (username, realname, email, roles, "
            "type, defaultApp). If has_more is true, call again with offset=next_offset.\n\n"
            "Args:\n"
            f"{count_arg_help()}"
            "    offset (int, optional): Result offset (default 0)\n"
            "    search_filter (str, optional): Splunk REST search filter (e.g. 'name=*admin*')"
        ),
        category="admin",
        tags=["users", "administration", "management"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        count: ListPageCount = LIST_PAGE_DEFAULT,
        offset: int = 0,
        search_filter: str = "",
    ) -> dict[str, Any]:
        log_tool_execution("list_users", count=count, offset=offset, search_filter=search_filter)
        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            return self.format_error_response(error_msg)

        try:
            page = fetch_rest_collection_page(
                service,
                "/services/authentication/users",
                count=count,
                offset=offset,
                search_filter=search_filter,
                extra_params={"sort_key": "name"},
            )
        except PaginationError as e:
            return self.format_error_response(str(e))
        except Exception as e:
            self.logger.error("Failed to list users: %s", e)
            await ctx.error(f"Failed to list users: {e}")
            return self.format_error_response(str(e))

        users = []
        for entry in page.entries:
            content = entry.get("content") or {}
            users.append(
                {
                    "username": entry.get("name"),
                    "realname": content.get("realname"),
                    "email": content.get("email"),
                    "roles": content.get("roles", []),
                    "type": content.get("type"),
                    "defaultApp": content.get("defaultApp"),
                }
            )
        await ctx.info(f"Returned {len(users)} users (offset={offset})")
        return self.format_success_response({"users": users, **page.paging})
