"""
List lookup definitions (transforms) from Splunk.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.list_paging import LIST_PAGE_DEFAULT, ListPageCount, PaginationError, count_arg_help
from src.core.splunk_rest_page import fetch_rest_collection_page
from src.core.utils import log_tool_execution


class ListLookupDefinitions(BaseTool):
    """
    List lookup definitions (transforms) configured in Splunk.

    Retrieves metadata about lookup definitions including name, type, filename,
    fields configuration, and app context. Lookup definitions define how lookup
    files are used in searches.
    """

    METADATA = ToolMetadata(
        name="list_lookup_definitions",
        description=(
            "List lookup definitions (transforms) in Splunk. Returns metadata including name, "
            "type, associated filename, fields configuration, app, owner, and permissions. "
            "Lookup definitions specify how CSV files or external lookups are used in searches.\n\n"
            "Args:\n"
            "    owner (str, optional): Filter by owner. Default: 'nobody' (all users)\n"
            "    app (str, optional): Filter by app context. Default: '-' (all apps)\n"
            f"{count_arg_help()}"
            "    If has_more is true, call again with offset=next_offset.\n"
            "    offset (int, optional): Result offset for pagination. Default: 0\n"
            "    search_filter (str, optional): Filter results (e.g., 'filename=*.csv')"
        ),
        category="lookups",
        tags=["lookups", "transforms", "knowledge", "list"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        owner: str = "nobody",
        app: str = "-",
        count: ListPageCount = LIST_PAGE_DEFAULT,
        offset: int = 0,
        search_filter: str = "",
    ) -> dict[str, Any]:
        """
        List lookup definitions from Splunk.

        Args:
            owner: Filter by owner (default: nobody for all)
            app: Filter by app (default: - for all)
            count: Maximum results (default: 50 for performance, 0 for all)
            offset: Pagination offset
            search_filter: Optional search filter

        Returns:
            Dict with status and list of lookup definition metadata, includes total_available
            for pagination info
        """
        log_tool_execution(
            "list_lookup_definitions",
            owner=owner,
            app=app,
            count=count,
            offset=offset,
            search_filter=search_filter,
        )

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            await ctx.error(f"List lookup definitions failed: {error_msg}")
            return self.format_error_response(error_msg)

        try:
            await ctx.info(f"Retrieving lookup definitions from Splunk (owner={owner}, app={app})")
            page = fetch_rest_collection_page(
                service,
                f"/servicesNS/{owner}/{app}/data/transforms/lookups",
                count=count,
                offset=offset,
                search_filter=search_filter,
            )
            definitions = []

            for entry in page.entries:
                content = entry.get("content", {})
                acl = entry.get("acl", {})

                definition = {
                    "name": entry.get("name", ""),
                    "filename": content.get("filename", ""),
                    "type": content.get("type", ""),
                    "match_type": content.get("match_type", ""),
                    "fields_list": content.get("fields_list", ""),
                    "external_cmd": content.get("external_cmd", ""),
                    "external_type": content.get("external_type", ""),
                    "min_matches": content.get("min_matches", 0),
                    "max_matches": content.get("max_matches", 1),
                    "default_match": content.get("default_match", ""),
                    "case_sensitive_match": content.get("case_sensitive_match", True),
                    "app": acl.get("app", ""),
                    "owner": acl.get("owner", ""),
                    "sharing": acl.get("sharing", ""),
                    "updated": content.get("updated", ""),
                    "permissions": {
                        "read": acl.get("perms", {}).get("read", []),
                        "write": acl.get("perms", {}).get("write", []),
                    },
                    "id": entry.get("id", ""),
                }
                definitions.append(definition)

            self.logger.info("Retrieved %d lookup definitions", len(definitions))
            await ctx.info(f"Found {len(definitions)} lookup definitions")

            return self.format_success_response(
                {
                    "lookup_definitions": definitions,
                    **page.paging,
                }
            )

        except PaginationError as e:
            await ctx.error(str(e))
            return self.format_error_response(str(e))
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to list lookup definitions: %s", str(e), exc_info=True)
            await ctx.error(f"Failed to list lookup definitions: {str(e)}")

            error_detail = str(e)
            if "404" in error_detail or "Not Found" in error_detail:
                error_detail += " (Endpoint not found - check Splunk version and permissions)"
            elif "403" in error_detail or "Forbidden" in error_detail:
                error_detail += " (Permission denied - check user role and capabilities)"
            elif "401" in error_detail or "Unauthorized" in error_detail:
                error_detail += " (Authentication failed - check credentials)"

            return self.format_error_response(error_detail)
