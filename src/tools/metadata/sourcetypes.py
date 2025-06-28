"""
Tool for listing Splunk sourcetypes.
"""

from typing import Any

from fastmcp import Context
from splunklib.results import ResultsReader

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class ListSourcetypes(BaseTool):
    """
    List all available sourcetypes from the configured Splunk instance using metadata command.
    This tool returns a comprehensive list of sourcetypes present in your Splunk environment.
    """

    METADATA = ToolMetadata(
        name="list_sourcetypes",
        description="List all available sourcetypes from the configured Splunk instance",
        category="metadata",
        tags=["sourcetypes", "metadata", "discovery"],
        requires_connection=True
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """
        List all sourcetypes.

        Returns:
            Dict containing list of sourcetypes and count
        """
        log_tool_execution("list_sourcetypes")

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        self.logger.info("Retrieving list of sourcetypes...")

        try:
            # Use metadata command to retrieve sourcetypes
            job = service.jobs.oneshot("| metadata type=sourcetypes index=_* index=* | table sourcetype")

            sourcetypes = []
            for result in ResultsReader(job):
                if isinstance(result, dict) and "sourcetype" in result:
                    sourcetypes.append(result["sourcetype"])

            self.logger.info(f"Retrieved {len(sourcetypes)} sourcetypes")
            ctx.info(f"Sourcetypes: {sourcetypes}")
            return self.format_success_response({
                "sourcetypes": sorted(sourcetypes),
                "count": len(sourcetypes)
            })
        except Exception as e:
            self.logger.error(f"Failed to retrieve sourcetypes: {str(e)}")
            ctx.error(f"Failed to retrieve sourcetypes: {str(e)}")
            return self.format_error_response(str(e))
