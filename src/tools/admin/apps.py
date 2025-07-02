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
        description="List all installed Splunk apps and their properties",
        category="admin",
        tags=["apps", "administration", "management"],
        requires_connection=True,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """
        List all Splunk applications.

        Returns:
            Dict containing list of apps and their properties
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
