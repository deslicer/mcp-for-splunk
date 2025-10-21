"""
Get a specific dashboard's definition (Simple XML or Dashboard Studio JSON).
"""

import json
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class GetDashboardDefinition(BaseTool):
    """
    Get the raw definition of a specific dashboard (Simple XML or Dashboard Studio JSON).

    Returns the complete dashboard definition along with metadata and Splunk Web URL.
    For Simple XML dashboards, returns XML as string. For Dashboard Studio, returns
    parsed JSON object.
    """

    METADATA = ToolMetadata(
        name="get_dashboard_definition",
        description=(
            "Get the raw definition of a specific dashboard. Returns the complete dashboard "
            "source (Simple XML or Dashboard Studio JSON), type, app context, owner, and "
            "Splunk Web viewing URL.\n\n"
            "Args:\n"
            "    name (str): Dashboard name (required)\n"
            "    owner (str, optional): Dashboard owner. Default: 'nobody'\n"
            "    app (str, optional): App context. Default: 'search'"
        ),
        category="dashboards",
        tags=["dashboards", "visualization", "ui", "view", "xml", "json"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        name: str,
        owner: str = "nobody",
        app: str = "search",
    ) -> dict[str, Any]:
        """
        Get dashboard definition from Splunk.

        Args:
            name: Dashboard name (required)
            owner: Dashboard owner (default: nobody)
            app: App context (default: search)

        Returns:
            Dict with dashboard definition, metadata, and Web URL
        """
        log_tool_execution(
            "get_dashboard_definition",
            name=name,
            owner=owner,
            app=app,
        )

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            await ctx.error(f"Get dashboard definition failed: {error_msg}")
            return self.format_error_response(error_msg)

        try:
            await ctx.info(f"Retrieving dashboard '{name}' from Splunk (owner={owner}, app={app})")

            # Build request parameters
            params = {
                "output_mode": "json",
            }

            # Get Splunk Web base URL from service
            splunk_host = service.host
            # Use HTTPS by default for web UI (typically port 8000)
            web_port = 8000  # Standard Splunk Web port
            web_scheme = "https"
            web_base = f"{web_scheme}://{splunk_host}:{web_port}"

            # Call the REST endpoint for specific dashboard
            endpoint = f"/servicesNS/{owner}/{app}/data/ui/views/{name}"
            response = service.get(endpoint, **params)

            # Parse JSON response
            response_body = response.body.read()
            data = json.loads(response_body)

            # Extract entry (should be single dashboard)
            entries = data.get("entry", [])

            if not entries:
                error_msg = f"Dashboard '{name}' not found (owner={owner}, app={app})"
                await ctx.error(error_msg)
                return self.format_error_response(error_msg)

            entry = entries[0]
            content = entry.get("content", {})
            acl = entry.get("acl", {})

            # Get dashboard definition from eai:data
            eai_data = content.get("eai:data", "")
            dashboard_type = "classic"
            definition = eai_data

            if eai_data:
                # Dashboard Studio can be in two formats:
                # 1. Pure JSON (direct Studio format)
                # 2. Hybrid XML with <definition> tag containing JSON in CDATA

                # Check for hybrid format: <definition> tag (Dashboard Studio specific)
                if "<definition>" in eai_data:
                    dashboard_type = "studio"
                    definition = eai_data  # Keep as XML string (hybrid format)
                else:
                    # Try to parse as pure JSON (Dashboard Studio format)
                    try:
                        parsed_json = json.loads(eai_data)
                        dashboard_type = "studio"
                        definition = parsed_json  # Return as parsed JSON object
                    except (json.JSONDecodeError, TypeError):
                        # Falls back to classic XML string
                        dashboard_type = "classic"
                        definition = eai_data

            # Build Splunk Web URL
            dashboard_app = acl.get("app", app)
            web_url = f"{web_base}/en-US/app/{dashboard_app}/{name}"

            self.logger.info("Retrieved dashboard '%s' (type=%s)", name, dashboard_type)
            await ctx.info(f"Successfully retrieved dashboard '{name}' (type={dashboard_type})")

            return self.format_success_response(
                {
                    "name": name,
                    "label": content.get("label", name),
                    "type": dashboard_type,
                    "app": dashboard_app,
                    "owner": acl.get("owner", ""),
                    "sharing": acl.get("sharing", ""),
                    "description": content.get("description", ""),
                    "updated": content.get("updated", ""),
                    "version": content.get("version", ""),
                    "definition": definition,
                    "permissions": {
                        "read": acl.get("perms", {}).get("read", []),
                        "write": acl.get("perms", {}).get("write", []),
                    },
                    "web_url": web_url,
                    "id": entry.get("id", ""),
                }
            )

        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to get dashboard definition: %s", str(e), exc_info=True)
            await ctx.error(f"Failed to get dashboard definition: {str(e)}")

            error_detail = str(e)
            if "404" in error_detail or "Not Found" in error_detail:
                error_detail += (
                    f" (Dashboard '{name}' not found in app '{app}' for owner '{owner}')"
                )
            elif "403" in error_detail or "Forbidden" in error_detail:
                error_detail += " (Permission denied - check user role and capabilities)"
            elif "401" in error_detail or "Unauthorized" in error_detail:
                error_detail += " (Authentication failed - check credentials)"

            return self.format_error_response(error_detail)
