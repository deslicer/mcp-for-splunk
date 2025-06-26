"""
Tools for managing Splunk KV Store collections.
"""

from typing import Any, Dict
from urllib.parse import quote

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class ListKvstoreCollections(BaseTool):
    """
    List all KV Store collections in Splunk.
    """
    
    METADATA = ToolMetadata(
        name="list_kvstore_collections",
        description="List all KV Store collections with optional app filtering",
        category="kvstore",
        tags=["kvstore", "collections", "storage"],
        requires_connection=True
    )
    
    async def execute(
        self, 
        ctx: Context, 
        app: str | None = None
    ) -> Dict[str, Any]:
        """
        List KV Store collections, optionally filtered by app.
        
        Args:
            app: Optional app name to filter collections
            
        Returns:
            Dict containing collections and their properties
        """
        log_tool_execution("list_kvstore_collections", app=app)
        
        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        self.logger.info(f"Retrieving KV Store collections for app: {app if app else 'all apps'}")
        ctx.info(f"Retrieving KV Store collections for app: {app if app else 'all apps'}")

        try:
            collections = []
            kvstore = service.kvstore

            if app:
                kvstore = service.kvstore[app]

            for collection in kvstore:
                collections.append({
                    "name": collection.name,
                    "fields": collection.content.get("fields", []),
                    "accelerated_fields": collection.content.get("accelerated_fields", {}),
                    "replicated": collection.content.get("replicated", False)
                })

            ctx.info(f"Found {len(collections)} collections")
            return self.format_success_response({
                "count": len(collections),
                "collections": collections
            })
        except Exception as e:
            self.logger.error(f"Failed to list KV Store collections: {str(e)}")
            ctx.error(f"Failed to list KV Store collections: {str(e)}")
            return self.format_error_response(str(e))


class CreateKvstoreCollection(BaseTool):
    """
    Create a new KV Store collection in a specified Splunk app.
    """
    
    METADATA = ToolMetadata(
        name="create_kvstore_collection",
        description="Create a new KV Store collection with optional field definitions",
        category="kvstore",
        tags=["kvstore", "collections", "create", "storage"],
        requires_connection=True
    )
    
    async def execute(
        self,
        ctx: Context,
        app: str,
        collection: str,
        fields: list[dict[str, Any]] | None = None,
        accelerated_fields: dict[str, list[list[str]]] | None = None,
        replicated: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new KV Store collection.
        
        Args:
            app: Name of the app where the collection should be created
            collection: Name for the new collection
            fields: Optional list of field definitions
            accelerated_fields: Optional dict defining indexed fields
            replicated: Whether the collection should be replicated (default: True)
            
        Returns:
            Dict containing creation status and collection details
        """
        log_tool_execution("create_kvstore_collection", app=app, collection=collection)
        
        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        self.logger.info(f"Creating new KV Store collection: {collection} in app: {app}")
        ctx.info(f"Creating new KV Store collection: {collection} in app: {app}")

        try:
            # Validate app name
            if not app:
                raise ValueError("App name is required")

            # Validate collection name - ensure only alphanumeric and underscores
            if not collection.replace("_", "").isalnum():
                raise ValueError("Collection name must contain only alphanumeric characters and underscores")

            # URL encode the app name to handle special characters
            encoded_app = quote(app, safe='')

            # Prepare collection configuration
            collection_config = {
                "name": collection,
                "replicated": replicated
            }

            if fields:
                collection_config["field"] = fields

            if accelerated_fields:
                collection_config["accelerated_fields"] = accelerated_fields

            # Create the collection
            kvstore = service.kvstore[encoded_app]
            new_collection = kvstore.create(
                name=collection,
                **collection_config
            )

            ctx.info(f"Collection {collection} created successfully")
            return self.format_success_response({
                "collection": {
                    "name": new_collection.name,
                    "fields": new_collection.content.get("fields", []),
                    "accelerated_fields": new_collection.content.get("accelerated_fields", {}),
                    "replicated": new_collection.content.get("replicated", False)
                }
            })

        except Exception as e:
            self.logger.error(f"Failed to create KV Store collection: {str(e)}")
            ctx.error(f"Failed to create KV Store collection: {str(e)}")
            return self.format_error_response(f"Failed to create collection: {str(e)}") 