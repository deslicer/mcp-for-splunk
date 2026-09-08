"""Paginated saved-search listing via Splunk REST."""

from typing import Any, Literal

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.list_paging import PaginationError
from src.core.splunk_rest_page import fetch_rest_collection_page
from src.core.utils import log_tool_execution

_SEARCH_PREVIEW_LEN = 200


def _splunk_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes", "on")
    if isinstance(value, int | float):
        return bool(value)
    return default


def _search_preview(search: str) -> tuple[str, bool]:
    if len(search) <= _SEARCH_PREVIEW_LEN:
        return search, False
    return search[:_SEARCH_PREVIEW_LEN], True


class ListSavedSearches(BaseTool):
    """List saved searches with REST pagination."""

    METADATA = ToolMetadata(
        name="list_saved_searches",
        description=(
            "List saved searches with ownership, schedule, visibility, and permission metadata. "
            "If has_more is true, call again with offset=next_offset. Full SPL is truncated to "
            "200 characters; use get_saved_search_details for the complete search.\n\n"
            "Args:\n"
            "    owner (str, optional): Filter by owner (default all)\n"
            "    app (str, optional): Filter by app (default all)\n"
            "    sharing (str, optional): Filter by sharing level\n"
            "    include_disabled (bool, optional): Include disabled searches (default false)\n"
            "    count (int, optional): Page size 1-200 (default 50)\n"
            "    offset (int, optional): Result offset (default 0)\n"
            "    search_filter (str, optional): Extra REST search filter (e.g. 'name=*alert*')"
        ),
        category="search",
        tags=["saved_searches", "list", "metadata"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        owner: str | None = None,
        app: str | None = None,
        sharing: Literal["user", "app", "global", "system"] | None = None,
        include_disabled: bool = False,
        count: int = 50,
        offset: int = 0,
        search_filter: str = "",
    ) -> dict[str, Any]:
        log_tool_execution(
            "list_saved_searches",
            owner=owner,
            app=app,
            sharing=sharing,
            count=count,
            offset=offset,
        )
        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            await ctx.error(f"List saved searches failed: {error_msg}")
            return self.format_error_response(error_msg, saved_searches=[], total_count=0)

        filters: list[str] = []
        if not include_disabled:
            filters.append("disabled=0")
        if sharing:
            filters.append(f"eai:acl.sharing={sharing}")
        if search_filter:
            filters.append(search_filter)
        ns_owner = owner or "-"
        ns_app = app or "-"
        endpoint = f"/servicesNS/{ns_owner}/{ns_app}/saved/searches"
        try:
            page = fetch_rest_collection_page(
                service,
                endpoint,
                count=count,
                offset=offset,
                search_filter=" ".join(filters),
                extra_params={"sort_key": "name"},
            )
        except PaginationError as e:
            return self.format_error_response(str(e), saved_searches=[], total_count=0)
        except Exception as e:
            self.logger.error("Failed to list saved searches: %s", e)
            await ctx.error(f"Failed to list saved searches: {e}")
            return self.format_error_response(str(e), saved_searches=[], total_count=0)

        saved_searches = [_map_saved_search(entry) for entry in page.entries]
        return self.format_success_response(
            {
                "saved_searches": saved_searches,
                "total_count": page.total_available,
                "filtered_count": page.paging["count"],
                "filters_applied": {
                    "owner": owner,
                    "app": app,
                    "sharing": sharing,
                    "include_disabled": include_disabled,
                },
                **page.paging,
            }
        )


def _map_saved_search(entry: dict[str, Any]) -> dict[str, Any]:
    content = entry.get("content") or {}
    acl = entry.get("acl") or {}
    perms = acl.get("perms") if isinstance(acl.get("perms"), dict) else {}
    preview, truncated = _search_preview(str(content.get("search", "")))
    return {
        "name": entry.get("name", ""),
        "search": preview,
        "search_preview": preview,
        "has_full_search": truncated,
        "description": content.get("description", ""),
        "owner": acl.get("owner", "") or "",
        "app": acl.get("app", "") or "",
        "sharing": acl.get("sharing", "") or "",
        "disabled": _splunk_bool(content.get("disabled"), False),
        "is_scheduled": _splunk_bool(content.get("is_scheduled"), False),
        "is_visible": _splunk_bool(content.get("is_visible"), True),
        "cron_schedule": content.get("cron_schedule", ""),
        "next_scheduled_time": content.get("next_scheduled_time", ""),
        "earliest_time": content.get("dispatch.earliest_time", ""),
        "latest_time": content.get("dispatch.latest_time", ""),
        "updated": content.get("updated", ""),
        "permissions": {
            "read": perms.get("read", []),
            "write": perms.get("write", []),
        },
    }
