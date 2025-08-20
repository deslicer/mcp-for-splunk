import argparse
import asyncio
import json
import os
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


def get_orange_ab_headers() -> dict[str, str]:
    """Headers matching the orange-ab-splunk config in ~/.cursor/mcp.json.

    Adjust here if your mcp.json changes. Environment variables can override.
    """
    return {
        "X-Splunk-Host": os.getenv("X_SPLUNK_HOST", "orange-ab.splunkcloud.com"),
        "X-Splunk-Port": os.getenv("X_SPLUNK_PORT", "8089"),
        "X-Splunk-Username": os.getenv(
            "X_SPLUNK_USERNAME", "daniel.young@orangecyberdefense.com"
        ),
        "X-Splunk-Password": os.getenv("X_SPLUNK_PASSWORD", "7kG5iT&Py6T6^CdM"),
        "X-Splunk-Scheme": os.getenv("X_SPLUNK_SCHEME", "https"),
        "X-Splunk-Verify-SSL": os.getenv("X_SPLUNK_VERIFY_SSL", "true"),
        # Session correlation id for per-tenant isolation
        "X-Session-ID": os.getenv("X_SESSION_ID", "orange-ab-splunk-session2"),
        # Useful for some proxies/debugging
        "Accept": os.getenv("HTTP_ACCEPT", "application/json, text/event-stream"),
    }
def get_show_headers() -> dict[str, str]:
    """Headers matching the show config in ~/.cursor/mcp.json.

    Adjust here if your mcp.json changes. Environment variables can override.
    """
    return {
        "X-Splunk-Host": os.getenv("X_SPLUNK_HOST", "dev1666-i-035e95d7e4ea1c310.splunk.show"),
        "X-Splunk-Port": os.getenv("X_SPLUNK_PORT", "8089"),
        "X-Splunk-Username": os.getenv("X_SPLUNK_USERNAME", "admin"),
        "X-Splunk-Password": os.getenv("X_SPLUNK_PASSWORD", "$plunk@C1sc0"),
        "X-Splunk-Scheme": os.getenv("X_SPLUNK_SCHEME", "https"),
        "X-Splunk-Verify-SSL": os.getenv("X_SPLUNK_VERIFY_SSL", "true"),
        "X-Session-ID": os.getenv("X_SESSION_ID", "splunk-show-session"),
    }

def get_on_prem_headers() -> dict[str, str]:
    """Headers matching the splunk-on-prem config in ~/.cursor/mcp.json.

    Adjust here if your mcp.json changes. Environment variables can override.
    """
    return {
        "X-Splunk-Host": os.getenv("X_SPLUNK_HOST_LOCAL", "so1"),
        "X-Splunk-Port": os.getenv("X_SPLUNK_PORT_LOCAL", "8089"),
        "X-Splunk-Username": os.getenv("X_SPLUNK_USERNAME_LOCAL", "admin"),
        "X-Splunk-Password": os.getenv("X_SPLUNK_PASSWORD_LOCAL", "Chang3d!"),
        "X-Splunk-Scheme": os.getenv("X_SPLUNK_SCHEME_LOCAL", "http"),
        "X-Splunk-Verify-SSL": os.getenv("X_SPLUNK_VERIFY_SSL_LOCAL", "false"),
        # Session correlation id for per-tenant isolation
        "X-Session-ID": os.getenv("X_SESSION_ID_LOCAL", "splunk-on-prem-session2"),
        # Useful for some proxies/debugging
        "Accept": os.getenv("HTTP_ACCEPT", "application/json, text/event-stream"),
    }


async def run_profile(name: str, url: str, headers: dict[str, str]) -> None:
    transport = StreamableHttpTransport(url=url, headers=headers)
    client = Client(transport)

    def to_jsonable(obj: Any) -> Any:
        """Recursively convert FastMCP content objects to JSON-serializable types."""
        try:
            # Pydantic BaseModel
            if hasattr(obj, "model_dump") and callable(obj.model_dump):
                return to_jsonable(obj.model_dump())
        except Exception:
            pass
        # Dataclasses
        try:
            import dataclasses

            if dataclasses.is_dataclass(obj):
                return to_jsonable(dataclasses.asdict(obj))
        except Exception:
            pass
        # Mappings
        if isinstance(obj, dict):
            return {k: to_jsonable(v) for k, v in obj.items()}
        # Sequences
        if isinstance(obj, (list, tuple, set)):
            return [to_jsonable(v) for v in obj]
        # Primitives
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        # Fallback: string representation
        return str(obj)

    async with client:
        # Call the debug tool to verify headers and session state as seen by the server
        result: dict[str, Any] = await client.call_tool("get_errors")

        # Lightweight header/session summary first
        summary = {
            "profile": name,
            "url": url,
            "session_id": headers.get("X-Session-ID"),
            "headers_used": {
                "X-Splunk-Host": headers.get("X-Splunk-Host"),
                "X-Splunk-Port": headers.get("X-Splunk-Port"),
                "X-Splunk-Username": headers.get("X-Splunk-Username"),
                "X-Splunk-Scheme": headers.get("X-Splunk-Scheme"),
                "X-Splunk-Verify-SSL": headers.get("X-Splunk-Verify-SSL"),
                "X-Session-ID": headers.get("X-Session-ID"),
            },
        }
        print(json.dumps(summary, indent=2))
        print("\nServer response:\n")
        print(json.dumps(to_jsonable(result), indent=2))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test tenant config via Streamable HTTP transport")
    parser.add_argument(
        "profile",
        choices=["remote", "local", "all", "show"],
        nargs="?",
        default="all",
        help="Choose which config to test: remote (orange-ab-splunk), local (splunk-on-prem), show (splunk.show), or all",
    )
    args = parser.parse_args()

    # Default URL matches both entries in your mcp.json
    url = os.getenv("MCP_URL", "http://localhost:8002/mcp/")

    if args.profile in ("remote", "all"):
        await run_profile("remote", url, get_orange_ab_headers())
        if args.profile == "all":
            print("\n" + "=" * 80 + "\n")

    if args.profile in ("local", "all"):
        await run_profile("local", url, get_on_prem_headers())

    if args.profile in ("show", "all"):
        await run_profile("show", url, get_show_headers())



if __name__ == "__main__":
    asyncio.run(main())


