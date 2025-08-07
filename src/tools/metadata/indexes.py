"""
Tool for listing Splunk indexes.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import filter_customer_indexes, log_tool_execution


class ListIndexes(BaseTool):
    """
    Retrieves a list of all accessible indexes from the configured Splunk instance.
    """

    METADATA = ToolMetadata(
        name="list_indexes",
        description=(
            "Retrieves a list of all accessible data indexes from the Splunk instance. "
            "Returns customer indexes (excludes internal Splunk system indexes like _internal, "
            "_audit for better readability). Useful for discovering available data sources and "
            "understanding the data structure of the Splunk environment."
        ),
        category="metadata",
        tags=["indexes", "metadata", "discovery"],
        requires_connection=True,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """
        List all accessible data indexes from the Splunk instance.

        Returns:
            Dict containing:
                - indexes: Sorted list of customer index names (excludes internal indexes)
                - count: Number of customer indexes found
                - total_count_including_internal: Total number of all indexes including system indexes
        """
        log_tool_execution("list_indexes")

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg, indexes=[], count=0)

        try:
            # Filter out internal indexes for better performance and relevance
            customer_indexes = filter_customer_indexes(service.indexes)
            index_names = [index.name for index in customer_indexes]

            await ctx.info(f"Customer indexes: {index_names}")
            return self.format_success_response(
                {
                    "indexes": sorted(index_names),
                    "count": len(index_names),
                    "total_count_including_internal": len(list(service.indexes)),
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to list indexes: {str(e)}")
            await ctx.error(f"Failed to list indexes: {str(e)}")
            return self.format_error_response(str(e), indexes=[], count=0)
