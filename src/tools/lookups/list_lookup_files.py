"""
List lookup CSV files from Splunk.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.list_paging import PaginationError
from src.core.splunk_rest_page import fetch_rest_collection_page
from src.core.utils import log_tool_execution


class ListLookupFiles(BaseTool):
    """
    List CSV lookup files available in Splunk.

    Retrieves metadata about lookup table files including name, filename, app context,
    owner, permissions, and last updated time. Use this to discover available lookup
    files before querying their contents with the run_splunk_search tool.
    """

    METADATA = ToolMetadata(
        name="list_lookup_files",
        description=(
            "List CSV lookup table files in Splunk. Returns metadata including name, filename, "
            "app, owner, sharing/permissions, and last updated time. Use this to discover available "
            "lookup files. To view the actual CSV content, use run_splunk_search with "
            "'| inputlookup <filename>'.\n\n"
            "Args:\n"
            "    owner (str, optional): Filter by owner. Default: 'nobody' (all users)\n"
            "    app (str, optional): Filter by app context. Default: '-' (all apps)\n"
            "    count (int, optional): Page size 1-200 (default 50). If has_more, use offset=next_offset\n"
            "    offset (int, optional): Result offset for pagination. Default: 0\n"
            "    search_filter (str, optional): Filter results (e.g., 'name=*geo*')"
        ),
        category="lookups",
        tags=["lookups", "csv", "knowledge", "list"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        owner: str = "nobody",
        app: str = "-",
        count: int = 50,
        offset: int = 0,
        search_filter: str = "",
    ) -> dict[str, Any]:
        """
        List lookup CSV files from Splunk.

        Args:
            owner: Filter by owner (default: nobody for all)
            app: Filter by app (default: - for all)
            count: Maximum results (default: 50, max 200)
            offset: Pagination offset
            search_filter: Optional search filter like 'name=*pattern*'

        Returns:
            Dict with status and list of lookup file metadata, includes total_available
            for pagination info
        """
        log_tool_execution(
            "list_lookup_files",
            owner=owner,
            app=app,
            count=count,
            offset=offset,
            search_filter=search_filter,
        )

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            await ctx.error(f"List lookup files failed: {error_msg}")
            return self.format_error_response(error_msg)

        try:
            await ctx.info(f"Retrieving lookup files from Splunk (owner={owner}, app={app})")
            page = fetch_rest_collection_page(
                service,
                f"/servicesNS/{owner}/{app}/data/lookup-table-files",
                count=count,
                offset=offset,
                search_filter=search_filter,
            )
            lookup_files = []

            for entry in page.entries:
                content = entry.get("content", {})
                acl = entry.get("acl", {})

                lookup_file = {
                    "name": entry.get("name", ""),
                    "filename": content.get("filename", ""),
                    "app": acl.get("app", ""),
                    "owner": acl.get("owner", ""),
                    "sharing": acl.get("sharing", ""),
                    "updated": content.get("updated", ""),
                    "size": content.get("size", 0),
                    "permissions": {
                        "read": acl.get("perms", {}).get("read", []),
                        "write": acl.get("perms", {}).get("write", []),
                    },
                    "id": entry.get("id", ""),
                }
                lookup_files.append(lookup_file)

            self.logger.info("Retrieved %d lookup files", len(lookup_files))
            await ctx.info(f"Found {len(lookup_files)} lookup files")

            return self.format_success_response(
                {
                    "lookup_files": lookup_files,
                    **page.paging,
                }
            )

        except PaginationError as e:
            await ctx.error(str(e))
            return self.format_error_response(str(e))
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to list lookup files: %s", str(e), exc_info=True)
            await ctx.error(f"Failed to list lookup files: {str(e)}")

            error_detail = str(e)
            if "404" in error_detail or "Not Found" in error_detail:
                error_detail += " (Endpoint not found - check Splunk version and permissions)"
            elif "403" in error_detail or "Forbidden" in error_detail:
                error_detail += " (Permission denied - check user role and capabilities)"
            elif "401" in error_detail or "Unauthorized" in error_detail:
                error_detail += " (Authentication failed - check credentials)"

            return self.format_error_response(error_detail)
