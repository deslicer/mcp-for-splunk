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
            "Retrieve all accessible data indexes from the Splunk instance. "
            "Use this to discover which indexes you can query when building searches or troubleshooting data availability. "
            "Returns customer indexes (excludes internal system indexes like _internal and _audit for readability). "
            "Results are constrained by the current user's permissions."
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

        # Prefer client-provided configuration (HTTP headers or env) when available
        try:
            service = await self.get_splunk_service(ctx)
        except Exception as e:
            return self.format_error_response(str(e), indexes=[], count=0)

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
