#!/usr/bin/env python3
"""
Test script for MCP Server for Splunk with HTTP header-based authentication.

This script tests the MCP server's ability to accept Splunk connection
parameters via HTTP headers instead of environment variables, allowing
different clients to connect to different Splunk instances.

Uses FastMCP Client with StreamableHttpTransport for proper session management.
Assumes MCP server is already running.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print("=" * 60)


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


async def run_all_tests(server_url: str = "http://localhost:8003/mcp"):
    """Run all tests using FastMCP Client with StreamableHttpTransport."""
    print_header("MCP Server for Splunk - HTTP Header Authentication Tests")

    # Single session ID for all tests
    session_id = "test-session-unified"

    # Splunk configuration as HTTP headers
    headers = {
        "X-Splunk-Host": os.getenv("SPLUNK_HOST", "localhost"),
        "X-Splunk-Port": os.getenv("SPLUNK_PORT", "8089"),
        "X-Splunk-Username": os.getenv("SPLUNK_USERNAME", "admin"),
        "X-Splunk-Password": os.getenv("SPLUNK_PASSWORD", "changeme"),
        "X-Splunk-Scheme": os.getenv("SPLUNK_SCHEME", "https"),
        "X-Splunk-Verify-SSL": os.getenv("SPLUNK_VERIFY_SSL", "false"),
        "X-Session-ID": session_id,
    }

    print_info("Using Splunk configuration:")
    for key, value in headers.items():
        if "Password" in key:
            print(f"  {key}: {'*' * len(value)}")
        else:
            print(f"  {key}: {value}")
    print()

    try:
        from fastmcp import Client
        from fastmcp.client.transports import StreamableHttpTransport
    except ImportError as e:
        print_error(f"Required library not available: {e}")
        print_info("Install with: pip install fastmcp")
        return []

    results = []

    try:
        # Create StreamableHttpTransport with custom headers
        print_info(f"Connecting to MCP server at {server_url}...")
        transport = StreamableHttpTransport(url=server_url, headers=headers)

        # Connect to MCP server - single connection for all tests
        async with Client(transport) as client:
            print_success("Connected to MCP server!\n")

            # Test 1: List available tools
            print_header("Test 1: List Available Tools")
            try:
                tools = await client.list_tools()
                print_success(f"Found {len(tools)} tools")
                print_info("Sample tools:")
                for tool in tools[:5]:
                    print(f"  - {tool.name}")
                results.append(("List Tools", True))
            except Exception as e:  # noqa: BLE001
                print_error(f"Failed: {e}")
                import traceback

                traceback.print_exc()
                results.append(("List Tools", False))

            # Test 2: Call user_agent_info (simple tool)
            print_header("Test 2: Call user_agent_info (Simple Tool)")
            try:
                result = await client.call_tool("user_agent_info", {})
                if result and hasattr(result, "content") and len(result.content) > 0:
                    print_success("user_agent_info executed successfully")
                    content = result.content[0]
                    if hasattr(content, "text"):
                        data = json.loads(content.text)
                        session = data.get("context", {}).get("state", {}).get("session_id", "N/A")
                        print_info(f"Session ID: {session}")
                    results.append(("user_agent_info", True))
                else:
                    print_error("Unexpected result format")
                    results.append(("user_agent_info", False))
            except Exception as e:  # noqa: BLE001
                print_error(f"Failed: {e}")
                import traceback

                traceback.print_exc()
                results.append(("user_agent_info", False))

            # Test 3: Call get_splunk_health (requires Splunk connection)
            print_header("Test 3: Call get_splunk_health (Splunk Tool)")
            try:
                result = await client.call_tool("get_splunk_health", {})
                print_success("get_splunk_health tool called successfully")

                # Print raw result for debugging
                print_info("Raw result:")
                if result and hasattr(result, "content") and len(result.content) > 0:
                    for idx, content in enumerate(result.content):
                        print(f"\n  Content[{idx}]:")
                        if hasattr(content, "type"):
                            print(f"    Type: {content.type}")
                        if hasattr(content, "text"):
                            print(f"    Text: {content.text}")

                        # Try to parse as JSON for structured display
                        try:
                            data = json.loads(content.text)
                            print("\n  Parsed JSON:")
                            for key, value in data.items():
                                print(f"    {key}: {value}")
                        except (json.JSONDecodeError, AttributeError):
                            pass

                    results.append(("get_splunk_health", True))
                else:
                    print_warning("Empty or unexpected result format")
                    print(f"Result: {result}")
                    results.append(("get_splunk_health", False))
            except Exception as e:  # noqa: BLE001
                print_error(f"Failed: {e}")
                import traceback

                traceback.print_exc()
                results.append(("get_splunk_health", False))

            # Test 4: Call list_indexes (class-based tool, requires session)
            print_header("Test 4: Call list_indexes (Class-Based Tool)")
            try:
                result = await client.call_tool("list_indexes", {})
                if result and hasattr(result, "content") and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, "text"):
                        data = json.loads(content.text)
                        indexes = data.get("indexes", [])
                        print_success("list_indexes executed successfully")
                        print_info(f"Found {len(indexes)} indexes")
                        if indexes:
                            print_info(f"Sample: {', '.join(indexes[:5])}")
                        results.append(("list_indexes", True))
                    else:
                        print_error("Unexpected content format")
                        results.append(("list_indexes", False))
                else:
                    print_error("Unexpected result format")
                    results.append(("list_indexes", False))
            except Exception as e:  # noqa: BLE001
                print_error(f"Failed: {e}")
                import traceback

                traceback.print_exc()
                results.append(("list_indexes", False))

            # Test 5: Verify session continuity and header config
            print_header("Test 5: Verify Session Continuity & Header Config")
            try:
                # Call user_agent_info again to verify same session
                result = await client.call_tool("user_agent_info", {})
                if result and hasattr(result, "content") and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, "text"):
                        data = json.loads(content.text)
                        state = data.get("context", {}).get("state", {})
                        session = state.get("session_id", "N/A")
                        client_config = state.get("client_config", {})

                        print_success("Session continuity verified")
                        print_info(f"Session ID: {session}")
                        if client_config:
                            print_info(f"Client config present: {list(client_config.keys())}")
                            print_info(f"Splunk Host: {client_config.get('splunk_host', 'N/A')}")
                            results.append(("Session Continuity", True))
                        else:
                            print_warning(
                                "No client config in session state (may be using server defaults)"
                            )
                            results.append(("Session Continuity", False))
                    else:
                        print_error("Unexpected content format")
                        results.append(("Session Continuity", False))
                else:
                    print_error("Unexpected result format")
                    results.append(("Session Continuity", False))
            except Exception as e:  # noqa: BLE001
                print_error(f"Failed: {e}")
                import traceback

                traceback.print_exc()
                results.append(("Session Continuity", False))

    except Exception as e:  # noqa: BLE001
        print_error(f"Test suite failed: {e}")
        import traceback

        traceback.print_exc()

    return results


def print_usage_instructions():
    """Print usage instructions and examples."""
    print_header("Usage Instructions")

    print(f"""
{Colors.BOLD}Prerequisites:{Colors.ENDC}
1. Start the MCP server:
   uv run mcp-server --local -d

2. Install required dependencies:
   pip install fastmcp

3. Set Splunk environment variables (or they'll use defaults):
   export SPLUNK_HOST=localhost
   export SPLUNK_PORT=8089
   export SPLUNK_USERNAME=admin
   export SPLUNK_PASSWORD=your_password
   export SPLUNK_VERIFY_SSL=false

{Colors.BOLD}Running the Tests:{Colors.ENDC}
   python scripts/test_mcp_with_headers.py

{Colors.BOLD}What This Tests:{Colors.ENDC}
✅ Basic MCP server connectivity
✅ HTTP header-based Splunk authentication
✅ Tool execution with header credentials
✅ Single session ID throughout all tests
✅ Session continuity verification
✅ FastMCP Client with StreamableHttpTransport

{Colors.BOLD}Expected Behavior:{Colors.ENDC}
- Connects to MCP server at http://localhost:8003/mcp
- FastMCP Client with StreamableHttpTransport handles session management
- Same session ID (test-session-unified) throughout
- Headers captured by HeaderCaptureMiddleware
- Splunk credentials extracted from X-Splunk-* headers
- Tools use header-provided credentials

{Colors.BOLD}Architecture:{Colors.ENDC}
- Uses StreamableHttpTransport with custom headers
- Proper session management (no "Missing session ID" errors)
- Single connection for all tests (efficient)
- Works with class-based tools like list_indexes

{Colors.BOLD}Troubleshooting:{Colors.ENDC}
- Ensure MCP server is running: uv run mcp-server --local -d
- Check logs/mcp_splunk_server.log for detailed server logs
- Ensure Splunk is accessible at the configured host/port
- Verify credentials are correct
- Check that port 8003 is available

{Colors.BOLD}Reference:{Colors.ENDC}
- FastMCP Transports: https://gofastmcp.com/clients/transports#remote-transports
""")


async def main():
    """Run all tests."""
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("=" * 60)
    print("  MCP Server for Splunk - HTTP Header Authentication Tests")
    print("  Using FastMCP Client with StreamableHttpTransport")
    print("=" * 60)
    print(Colors.ENDC)

    # Check prerequisites
    print_header("Checking Prerequisites")

    try:
        from fastmcp import Client  # noqa: F401, used in run_all_tests
        from fastmcp.client.transports import StreamableHttpTransport  # noqa: F401

        print_success("fastmcp library available")
    except ImportError:
        print_error("fastmcp library not available")
        print_info("Install with: pip install fastmcp")
        print_usage_instructions()
        return False

    # Check environment variables
    if os.getenv("SPLUNK_HOST"):
        print_success(f"SPLUNK_HOST set to: {os.getenv('SPLUNK_HOST')}")
    else:
        print_warning("SPLUNK_HOST not set, using default: localhost")

    print_warning("⚠️  Ensure MCP server is running: uv run mcp-server --local -d")
    print()

    # Run all tests
    results = await run_all_tests()

    # Print summary
    print_header("Test Results Summary")

    for test_name, passed in results:
        status = (
            f"{Colors.OKGREEN}✅ PASSED{Colors.ENDC}"
            if passed
            else f"{Colors.FAIL}❌ FAILED{Colors.ENDC}"
        )
        print(f"{test_name:.<40} {status}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print(f"\n{Colors.BOLD}Total: {passed_count}/{total_count} tests passed{Colors.ENDC}")

    if passed_count == total_count:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 ALL TESTS PASSED!{Colors.ENDC}")
        print_usage_instructions()
        return True
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}⚠️  SOME TESTS FAILED{Colors.ENDC}")
        print_info("Check the logs above for details")
        print_usage_instructions()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
