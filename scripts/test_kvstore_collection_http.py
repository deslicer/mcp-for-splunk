import asyncio
import json
import os
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

MCP_URL = os.environ.get("MCP_URL", "http://localhost:8001/mcp/")

CREATE_ARGS = {
    "app": os.environ.get("KV_APP", "search"),
    "collection": os.environ.get("KV_COLLECTION", "test_mcp"),
    "fields": [
        {"name": "title", "type": "string"},
        {"name": "check_eol_apps", "type": "boolean"},
        {"name": "check_compatible_app_version", "type": "string"},
        {"name": "check_fips_incompatible_app", "type": "string"},
        {"name": "check_fips_compatible_app_version", "type": "string"},
    ],
    # optional inputs supported by tool
    "accelerated_fields": None,
    "replicated": False,
    "create_lookup_definition": True,
}


async def main() -> None:
    print(f"Connecting to MCP server: {MCP_URL}")
    transport = StreamableHttpTransport(url=MCP_URL)
    async with Client(transport) as client:
        # Call create_kvstore_collection
        print("Creating KV Store collection...")
        create_result = await client.call_tool("create_kvstore_collection", CREATE_ARGS)
        create_data = create_result.data if hasattr(create_result, "data") else create_result
        print("Create response:")
        print(json.dumps(create_data, indent=2))

        # If requested, verify lookup definition exists in transforms.conf
        if CREATE_ARGS.get("create_lookup_definition"):
            print("Verifying transforms.conf stanza for lookup definition...")
            gc_args = {
                "conf_file": "transforms",
                "stanza": CREATE_ARGS["collection"],
                "app": CREATE_ARGS["app"],
            }
            gc_result = await client.call_tool("get_configurations", gc_args)
            gc_data = gc_result.data if hasattr(gc_result, "data") else gc_result
            print("GetConfigurations response:")
            print(json.dumps(gc_data, indent=2))

            if gc_data.get("status") == "success":
                settings = gc_data.get("settings", {})
                ok_ext = settings.get("external_type") == "kvstore"
                ok_coll = settings.get("collection") == CREATE_ARGS["collection"]
                ok_fields_list = settings.get("fields_list", "")
                if ok_ext and ok_coll and ok_fields_list:
                    print("✓ Lookup definition found in transforms.conf with expected settings.")
                else:
                    print("✗ Lookup definition settings missing or mismatched.")
            else:
                print("✗ Failed to retrieve transforms.conf stanza for lookup definition.")

        # Call list_kvstore_collections filtered by app
        list_app = CREATE_ARGS["app"]
        print(f"Listing KV Store collections for app='{list_app}'...")
        list_result = await client.call_tool("list_kvstore_collections", {"app": list_app})
        list_data = list_result.data if hasattr(list_result, "data") else list_result

        # Filter to the created collection only
        collections_all = list_data.get("collections", []) if isinstance(list_data, dict) else []
        created_name = CREATE_ARGS["collection"]
        collections_filtered = [c for c in collections_all if c.get("name") == created_name]
        filtered_output = {
            "status": list_data.get("status"),
            "count": len(collections_filtered),
            "collections": collections_filtered,
        }
        print("Filtered list response (created collection only):")
        print(json.dumps(filtered_output, indent=2))

        # Validate presence
        if list_data.get("status") == "success":
            if collections_filtered:
                print("✓ Collection appears in list for the app.")
            else:
                print("✗ Collection not found in list.")
        else:
            print("List call returned non-success status.")


if __name__ == "__main__":
    asyncio.run(main())
