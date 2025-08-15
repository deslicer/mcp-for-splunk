"""
Tool for listing Splunk applications.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class ListApps(BaseTool):
    """
    List all installed Splunk apps.
    """

    METADATA = ToolMetadata(
        name="list_apps",
        description=(
            "Retrieve comprehensive inventory of all installed Splunk applications including metadata "
            "(name, label, version, description, author, visibility status). "
            "Use this tool when you need to list all apps in the Splunk environment, such as for "
            "auditing, management, or troubleshooting compatibility. "
            "This tool requires no arguments.\n\n"
            "Returns detailed app catalog with 54+ apps typically found in enterprise environments, "
            "including core Splunk apps, add-ons (TAs), custom applications, and third-party integrations."
        ),
        category="admin",
        tags=["apps", "administration", "management", "inventory", "catalog", "audit"],
        requires_connection=True,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """
        Retrieve comprehensive inventory of all Splunk applications.

        Provides detailed metadata for each app including:
        - name: Internal app directory name
        - label: Display name shown in Splunk Web
        - version: App version number (if available)
        - description: App purpose and functionality
        - author: App developer/vendor
        - visible: UI visibility ("1" = visible, "0" = hidden)

        Returns:
            Dict containing:
                - status: "success" or "error"
                - count: Total number of apps found
                - apps: List of app objects with detailed metadata

        Typical enterprise environments contain 50+ apps including:
        - Core Splunk apps (search, launcher, dmc)
        - Technology Add-ons (Splunk_TA_*)
        - Custom business applications
        - Third-party integrations and visualizations
        """
        log_tool_execution("list_apps")

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        self.logger.info("Retrieving list of Splunk apps")
        ctx.info("Retrieving list of Splunk apps")

        try:
            apps = []
            for app in service.apps:
                apps.append(
                    {
                        "name": app.name,
                        "label": app.content.get("label"),
                        "version": app.content.get("version"),
                        "description": app.content.get("description"),
                        "author": app.content.get("author"),
                        "visible": app.content.get("visible"),
                    }
                )

            ctx.info(f"Found {len(apps)} apps")
            return self.format_success_response({"count": len(apps), "apps": apps})
        except Exception as e:
            self.logger.error(f"Failed to list apps: {str(e)}")
            ctx.error(f"Failed to list apps: {str(e)}")
            return self.format_error_response(str(e))
