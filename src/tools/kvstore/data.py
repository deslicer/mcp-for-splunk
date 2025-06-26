"""
Tool for retrieving data from Splunk KV Store collections.
"""

from typing import Any, Dict

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class GetKvstoreData(BaseTool):
    """
    Retrieve data from a specific KV Store collection.
    """
    
    METADATA = ToolMetadata(
        name="get_kvstore_data",
        description="Retrieve data from a KV Store collection with optional filtering",
        category="kvstore",
        tags=["kvstore", "data", "query", "storage"],
        requires_connection=True
    )
    
    async def execute(
        self,
        ctx: Context,
        collection: str,
        app: str | None = None,
        query: dict | None = None
    ) -> Dict[str, Any]:
        """
        Retrieve data from a KV Store collection.
        
        Args:
            collection: Name of the collection to retrieve data from
            app: Optional app name where the collection resides
            query: Optional MongoDB-style query filter
            
        Returns:
            Dict containing retrieved documents
        """
        log_tool_execution("get_kvstore_data", collection=collection, app=app)
        
        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        self.logger.info(f"Retrieving data from KV Store collection: {collection}")
        ctx.info(f"Retrieving data from KV Store collection: {collection}")

        try:
            if app:
                collection_obj = service.kvstore[app][collection]
            else:
                collection_obj = service.kvstore[collection]

            documents = collection_obj.data.query(query) if query else collection_obj.data.query()

            ctx.info(f"Retrieved {len(documents)} documents")
            return self.format_success_response({
                "count": len(documents),
                "documents": documents
            })
        except Exception as e:
            self.logger.error(f"Failed to get KV store data: {str(e)}")
            ctx.error(f"Failed to get KV store data: {str(e)}")
            return self.format_error_response(str(e)) 