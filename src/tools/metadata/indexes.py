"""
Tool for listing Splunk indexes.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class ListIndexes(BaseTool):
    """
    Retrieves a list of all accessible indexes from the configured Splunk instance.
    """

    METADATA = ToolMetadata(
        name="list_indexes",
        description="Retrieves a list of all accessible indexes from the configured Splunk instance",
        category="metadata",
        tags=["indexes", "metadata", "discovery"],
        requires_connection=True
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """
        List all accessible indexes.

        Returns:
            Dict containing list of indexes and count
        """
        log_tool_execution("list_indexes")

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(
                error_msg,
                indexes=[],
                count=0
            )

        try:
            indexes = [index.name for index in service.indexes]
            ctx.info(f"Indexes: {indexes}")
            return self.format_success_response({
                "indexes": sorted(indexes),
                "count": len(indexes)
            })
        except Exception as e:
            self.logger.error(f"Failed to list indexes: {str(e)}")
            ctx.error(f"Failed to list indexes: {str(e)}")
            return self.format_error_response(
                str(e),
                indexes=[],
                count=0
            )
