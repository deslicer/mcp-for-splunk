"""
Tool for listing Splunk data sources.
"""

from typing import Any

from fastmcp import Context
from splunklib.results import ResultsReader

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class ListSources(BaseTool):
    """
    List all available data sources from the configured Splunk instance using metadata command.
    This tool provides a comprehensive inventory of data sources in your Splunk environment.
    """

    METADATA = ToolMetadata(
        name="list_sources",
        description=(
            "Discover and enumerate all available data sources from the configured Splunk instance "
            "using the metadata command. This tool provides a comprehensive inventory of data sources "
            "across all indexes, helping with data discovery, troubleshooting, and understanding "
            "the data landscape in your Splunk environment. Sources represent the origin points "
            "of data such as log files, network streams, databases, and other data inputs.\n\n"
            "Use Cases:\n"
            "- Data discovery and cataloging\n"
            "- Troubleshooting missing data sources\n"
            "- Understanding data flow and origins\n"
            "- Planning data retention and archival\n"
            "- Security analysis and audit trails\n\n"
            "Response Format:\n"
            "Returns a dictionary with 'status' field and 'data' containing:\n"
            "- sources: Sorted array of all data source paths/identifiers\n"
            "- count: Total number of unique sources discovered"
        ),
        category="metadata",
        tags=["sources", "metadata", "discovery"],
        requires_connection=True,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """
        List all data sources.

        Returns:
            Dict containing list of sources and count
        """
        log_tool_execution("list_sources")

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        self.logger.info("Retrieving list of sources...")

        try:
            # Use metadata command to retrieve sources
            job = service.jobs.oneshot("| metadata type=sources index=_* index=* | table source")

            sources = []
            for result in ResultsReader(job):
                if isinstance(result, dict) and "source" in result:
                    sources.append(result["source"])

            self.logger.info(f"Retrieved {len(sources)} sources")
            return self.format_success_response({"sources": sorted(sources), "count": len(sources)})
        except Exception as e:
            self.logger.error(f"Failed to retrieve sources: {str(e)}")
            return self.format_error_response(str(e))
