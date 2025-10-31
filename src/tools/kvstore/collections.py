"""
Tools for managing Splunk KV Store collections.
"""

from typing import Any

from fastmcp import Context
from splunklib import client as spl_client
from splunklib.binding import HTTPError

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class ListKvstoreCollections(BaseTool):
    """
    List all KV Store collections in Splunk.
    """

    METADATA = ToolMetadata(
        name="list_kvstore_collections",
        description=(
            "List KV Store collections with basic schema details. Use this to discover available KV stores "
            "for lookups, configuration, or caching, optionally filtering by app.\n\n"
            "Outputs: array of collections with name, fields, accelerated_fields, replicated; and total count.\n"
            "Security: results are constrained by the authenticated user's permissions."
            "Args:\n"
            "    app (str, optional): Optional app name to filter collections\n\n"
        ),
        category="kvstore",
        tags=["kvstore", "collections", "storage"],
        requires_connection=True,
    )

    async def execute(self, ctx: Context, app: str | None = None) -> dict[str, Any]:
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
        await ctx.info(f"Retrieving KV Store collections for app: {app if app else 'all apps'}")

        try:
            collections = []
            original_namespace = getattr(service, "namespace", None)
            if app:
                service.namespace = spl_client.namespace(app=app, owner="nobody", sharing="app")

            try:
                kvstore = service.kvstore
                for collection in kvstore:
                    # Derive fields from either 'fields' dict or 'field.<name>' entries
                    content = collection.content or {}
                    fields_dict = content.get("fields")
                    if not fields_dict:
                        fp = {
                            k.split(".", 1)[1]: v
                            for k, v in content.items()
                            if isinstance(k, str) and k.startswith("field.")
                        }
                        fields_dict = fp if fp else {}
                    collections.append(
                        {
                            "name": collection.name,
                            "fields": fields_dict,
                            "accelerated_fields": content.get("accelerated_fields", {}),
                            "replicated": content.get("replicated", False),
                        }
                    )
            finally:
                service.namespace = original_namespace

            await ctx.info(f"Found {len(collections)} collections")
            return self.format_success_response(
                {"count": len(collections), "collections": collections}
            )
        except Exception as e:
            self.logger.error(f"Failed to list KV Store collections: {str(e)}")
            await ctx.error(f"Failed to list KV Store collections: {str(e)}")
            return self.format_error_response(str(e))


class CreateKvstoreCollection(BaseTool):
    """
    Create a new KV Store collection in a specified Splunk app.
    """

    METADATA = ToolMetadata(
        name="create_kvstore_collection",
        description=(
            "Create a KV Store collection with optional fields and indexing. Use this to provision "
            "a new collection for lookups or persisted configuration in a specific app.\n\n"
            "Args:\n"
            "    app (str): Target Splunk application where the collection will be created. Examples:\n"
            "        - 'search': Default search app\n"
            "        - 'my_app': Custom application\n"
            "        - 'splunk_monitoring_console': Monitoring console app\n"
            "    collection (str): Name for the new collection (alphanumeric and underscores only). Examples:\n"
            "        - 'users': User information store\n"
            "        - 'configurations': Application settings\n"
            "        - 'lookup_table': Data enrichment table\n"
            "    fields (list[dict], optional): Field definitions specifying data types and constraints\n"
            "    accelerated_fields (dict, optional): Index definitions for faster queries\n"
            "    replicated (bool, optional): Whether to replicate across cluster (default: True)\n"
            "    create_lookup_definition (bool, optional): Also create a transforms.conf lookup definition (default: False)\n\n"
            "Outputs: created collection with name, fields, accelerated_fields, replicated.\n"
            "Security: creation is constrained by app-level permissions."
        ),
        category="kvstore",
        tags=["kvstore", "collections", "create", "storage"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        app: str,
        collection: str,
        fields: list[dict[str, Any]] | None = None,
        accelerated_fields: dict[str, list[list[str]]] | None = None,
        replicated: bool = True,
        create_lookup_definition: bool = False,
    ) -> dict[str, Any]:
        """
        Create a new KV Store collection.

        Args:
            app: Name of the app where the collection should be created
            collection: Name for the new collection
            fields: Optional list of field definitions
            accelerated_fields: Optional dict defining indexed fields
            replicated: Whether the collection should be replicated (default: True)
            create_lookup_definition: Whether to create a transforms.conf lookup definition

        Returns:
            Dict containing creation status and collection details
        """
        log_tool_execution("create_kvstore_collection", app=app, collection=collection)

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        self.logger.info(f"Creating new KV Store collection: {collection} in app: {app}")
        await ctx.info(f"Creating new KV Store collection: {collection} in app: {app}")

        try:
            # Validate app name
            if not app:
                raise ValueError("App name is required")

            # Validate collection name - ensure only alphanumeric and underscores
            if not collection.replace("_", "").isalnum():
                raise ValueError(
                    "Collection name must contain only alphanumeric characters and underscores"
                )

            # Prepare collection configuration (do not duplicate 'name' argument)
            # Note: Some Splunk versions/handlers do not support a 'replicated' flag at create time
            # Keep parameter for API compatibility but ignore its value here.
            _replication_requested = bool(replicated)
            collection_config: dict[str, Any] = {}

            # Normalize fields: accept list of {name,type} or list of strings (default to string)
            field_params: dict[str, str] = {}
            normalized_fields: dict[str, str] = {}
            if fields:
                for f in fields:
                    if isinstance(f, dict):
                        field_name = f.get("name") or f.get("field")
                        field_type = (f.get("type") or "string").lower()
                        if field_name:
                            normalized_fields[str(field_name)] = str(field_type)
                    elif isinstance(f, str):
                        normalized_fields[f] = "string"
                if normalized_fields:
                    # Prefer REST-compatible 'field.<name>' parameters for creation
                    field_params = {f"field.{k}": v for k, v in normalized_fields.items()}
                    # Include in config for the initial attempt
                    collection_config.update(field_params)

            if accelerated_fields:
                collection_config["accelerated_fields"] = accelerated_fields

            # Switch namespace to the target app (owner=nobody, sharing=app) for creation
            original_namespace = getattr(service, "namespace", None)
            service.namespace = spl_client.namespace(app=app, owner="nobody", sharing="app")
            try:
                # Create collection with robust handling (skip create if it already exists)
                if collection in service.kvstore:
                    new_collection = service.kvstore[collection]
                else:
                    try:
                        # First try positional signature
                        new_collection = service.kvstore.create(collection, **collection_config)
                    except (TypeError, KeyError):
                        # Retry using keyword name
                        new_collection = service.kvstore.create(
                            name=collection, **collection_config
                        )
                    except HTTPError as e:
                        # Retry with 'fields' dict if REST-style params were not accepted
                        if field_params and e.status == 400:
                            fallback_config = {
                                k: v
                                for k, v in collection_config.items()
                                if not k.startswith("field.")
                            }
                            fallback_config["fields"] = {
                                k.split(".", 1)[1]: v for k, v in field_params.items()
                            }
                            try:
                                new_collection = service.kvstore.create(
                                    collection, **fallback_config
                                )
                            except (TypeError, KeyError):
                                new_collection = service.kvstore.create(
                                    name=collection, **fallback_config
                                )
                        elif e.status == 409:
                            # Already exists - treat as idempotent success by returning existing collection
                            new_collection = service.kvstore[collection]
                        else:
                            raise

                # Ensure schema via update_field for each normalized field (best-effort)
                if normalized_fields:
                    for fname, ftype in normalized_fields.items():
                        try:
                            new_collection.update_field(fname, ftype)
                        except Exception:
                            # Ignore schema update errors; surface only creation failures
                            pass

                # Optionally create a transforms.conf lookup definition in this app
                lookup_info: dict[str, Any] | None = None
                if create_lookup_definition:
                    try:
                        transforms = service.confs["transforms"]
                        lookup_name = collection
                        fields_list = (
                            ", ".join(["_key"] + list(normalized_fields.keys()))
                            if normalized_fields
                            else "_key"
                        )
                        if lookup_name not in transforms:
                            transforms.create(
                                lookup_name,
                                **{
                                    "external_type": "kvstore",
                                    "collection": collection,
                                    "fields_list": fields_list,
                                    "case_sensitive_match": "false",
                                },
                            )
                        lookup_info = {"name": lookup_name, "fields_list": fields_list}
                    except Exception:
                        # Non-fatal; continue without lookup creation data
                        lookup_info = {"name": collection, "created": False}
            finally:
                # Restore original namespace
                service.namespace = original_namespace

            await ctx.info(f"Collection {collection} created successfully")
            return self.format_success_response(
                {
                    "collection": {
                        "name": new_collection.name,
                        "fields": new_collection.content.get("fields", []),
                        "accelerated_fields": new_collection.content.get("accelerated_fields", {}),
                        "replicated": new_collection.content.get("replicated", False),
                    },
                    **({"lookup_definition": lookup_info} if lookup_info else {}),
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to create KV Store collection: {str(e)}")
            await ctx.error(f"Failed to create KV Store collection: {str(e)}")
            return self.format_error_response(f"Failed to create collection: {str(e)}")
