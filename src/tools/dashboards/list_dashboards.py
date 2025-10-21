"""
List dashboards from Splunk (Simple XML and Dashboard Studio).
"""

import json
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class ListDashboards(BaseTool):
    """
    List dashboards available in Splunk (both Simple XML and Dashboard Studio).

    Retrieves metadata about dashboards including name, label, type (classic or studio),
    app context, owner, permissions, and Splunk Web URLs for viewing.
    """

    METADATA = ToolMetadata(
        name="list_dashboards",
        description=(
            "List dashboards in Splunk (Simple XML and Dashboard Studio). Returns metadata "
            "including name, label, type (classic/studio), app, owner, permissions, sharing level, "
            "last updated, and Splunk Web viewing URLs.\n\n"
            "Args:\n"
            "    owner (str, optional): Filter by owner. Use 'me' for current user's dashboards, "
            "'nobody' for shared dashboards, or a specific username. Default: 'nobody'\n"
            "    app (str, optional): Filter by app context. Default: '-' (all apps)\n"
            "    count (int, optional): Max results to return. 0=all, default: 50 for performance\n"
            "    offset (int, optional): Result offset for pagination. Default: 0\n"
            "    search_filter (str, optional): Filter results (e.g., 'name=*security*')\n"
            "    type_filter (str, optional): Filter by type: 'classic', 'studio', or 'any'. Default: 'any'\n"
            "    my_dashboards_only (bool, optional): If True, only return dashboards owned by the "
            "current user. Overrides 'owner' parameter. Default: False\n"
            "    private_only (bool, optional): If True, only return private dashboards (sharing='user'). "
            "Works with any owner filter. Default: False"
        ),
        category="dashboards",
        tags=["dashboards", "visualization", "ui", "list"],
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
        type_filter: str = "any",
        my_dashboards_only: bool = False,
        private_only: bool = False,
    ) -> dict[str, Any]:
        """
        List dashboards from Splunk.

        Args:
            owner: Filter by owner (use 'me' for current user, default: nobody for all)
            app: Filter by app (default: - for all)
            count: Maximum results (default: 50 for performance, 0 for all)
            offset: Pagination offset
            search_filter: Optional search filter
            type_filter: Filter by dashboard type (classic/studio/any)
            my_dashboards_only: If True, only return current user's dashboards
            private_only: If True, only return private dashboards (sharing='user')

        Returns:
            Dict with status and list of dashboard metadata, includes total_available
            for pagination info, and sharing level for each dashboard
        """
        log_tool_execution(
            "list_dashboards",
            owner=owner,
            app=app,
            count=count,
            offset=offset,
            search_filter=search_filter,
            type_filter=type_filter,
            my_dashboards_only=my_dashboards_only,
            private_only=private_only,
        )

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            await ctx.error(f"List dashboards failed: {error_msg}")
            return self.format_error_response(error_msg)

        try:
            # Get current username if my_dashboards_only is True or owner is 'me'
            if my_dashboards_only or owner == "me":
                current_username = service.username
                if not current_username:
                    error_msg = "Unable to determine current username"
                    await ctx.error(error_msg)
                    return self.format_error_response(error_msg)
                owner = current_username
                await ctx.info(f"Filtering dashboards for current user: {current_username}")

            # Add info about private_only filter
            if private_only:
                await ctx.info("Filtering for private dashboards only (sharing='user')")

            await ctx.info(f"Retrieving dashboards from Splunk (owner={owner}, app={app})")

            # Build request parameters
            params = {
                "output_mode": "json",
                "count": count,
                "offset": offset,
            }

            # Filter for dashboards only
            base_filter = "isDashboard=1"
            if search_filter:
                params["search"] = f"{base_filter} {search_filter}"
            else:
                params["search"] = base_filter

            # Get Splunk Web base URL from service
            splunk_host = service.host
            # Use HTTPS by default for web UI (typically port 8000)
            web_port = 8000  # Standard Splunk Web port
            web_scheme = "https"
            web_base = f"{web_scheme}://{splunk_host}:{web_port}"

            # Call the REST endpoint
            endpoint = f"/servicesNS/{owner}/{app}/data/ui/views"
            response = service.get(endpoint, **params)

            # Parse JSON response
            response_body = response.body.read()
            data = json.loads(response_body)

            # Extract and format entries
            entries = data.get("entry", [])
            dashboards = []

            for entry in entries:
                content = entry.get("content", {})
                acl = entry.get("acl", {})
                dashboard_name = entry.get("name", "")
                dashboard_app = acl.get("app", "")

                # Detect dashboard type by checking eai:data
                eai_data = content.get("eai:data", "")
                dashboard_type = "classic"  # Default to classic Simple XML

                if eai_data:
                    # Dashboard Studio can be in two formats:
                    # 1. Pure JSON (direct Studio format)
                    # 2. Hybrid XML with <definition> tag containing JSON in CDATA

                    # Check for hybrid format: <definition> tag (Dashboard Studio specific)
                    if "<definition>" in eai_data:
                        dashboard_type = "studio"
                    else:
                        # Try to parse as pure JSON (Dashboard Studio format)
                        try:
                            json.loads(eai_data)
                            dashboard_type = "studio"
                        except (json.JSONDecodeError, TypeError):
                            # Falls back to classic XML
                            dashboard_type = "classic"

                # Apply type filter
                if type_filter != "any":
                    if type_filter != dashboard_type:
                        continue

                # Get sharing level
                sharing = acl.get("sharing", "unknown")

                # Apply private_only filter
                if private_only and sharing != "user":
                    continue  # Skip non-private dashboards

                # Build Splunk Web URL
                web_url = f"{web_base}/en-US/app/{dashboard_app}/{dashboard_name}"

                # Safely handle perms which could be None
                perms = acl.get("perms") or {}

                dashboard = {
                    "name": dashboard_name,
                    "label": content.get("label", dashboard_name),
                    "type": dashboard_type,
                    "app": dashboard_app,
                    "owner": acl.get("owner", ""),
                    "sharing": sharing,
                    "description": content.get("description", ""),
                    "updated": content.get("updated", ""),
                    "version": content.get("version", ""),
                    "permissions": {
                        "read": perms.get("read", []),
                        "write": perms.get("write", []),
                    },
                    "web_url": web_url,
                    "id": entry.get("id", ""),
                }
                dashboards.append(dashboard)

            self.logger.info("Retrieved %d dashboards", len(dashboards))
            await ctx.info(f"Found {len(dashboards)} dashboards")

            return self.format_success_response(
                {
                    "dashboards": dashboards,
                    "count": len(dashboards),
                    "total_available": data.get("paging", {}).get("total", len(dashboards)),
                    "offset": offset,
                    "type_filter": type_filter,
                    "private_only": private_only,
                    "owner_filter": owner,
                }
            )

        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to list dashboards: %s", str(e), exc_info=True)
            await ctx.error(f"Failed to list dashboards: {str(e)}")

            error_detail = str(e)
            if "404" in error_detail or "Not Found" in error_detail:
                error_detail += " (Endpoint not found - check Splunk version and permissions)"
            elif "403" in error_detail or "Forbidden" in error_detail:
                error_detail += " (Permission denied - check user role and capabilities)"
            elif "401" in error_detail or "Unauthorized" in error_detail:
                error_detail += " (Authentication failed - check credentials)"

            return self.format_error_response(error_detail)
