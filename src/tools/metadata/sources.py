"""
Tool for listing Splunk data sources.
"""

from typing import Any, Dict

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
        description="List all available data sources from the configured Splunk instance",
        category="metadata",
        tags=["sources", "metadata", "discovery"],
        requires_connection=True
    )
    
    async def execute(self, ctx: Context) -> Dict[str, Any]:
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
            return self.format_success_response({
                "sources": sorted(sources),
                "count": len(sources)
            })
        except Exception as e:
            self.logger.error(f"Failed to retrieve sources: {str(e)}")
            return self.format_error_response(str(e)) 