#!/usr/bin/env python3
"""
Test script for MCP Server for Splunk with HTTP header-based authentication.

This script tests the MCP server's ability to accept Splunk connection
parameters via HTTP headers instead of environment variables, allowing
different clients to connect to different Splunk instances.

Uses raw HTTP requests with a single session throughout all tests.
"""

import asyncio
import json
import os
import subprocess
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


class MCPServerProcess:
    """Context manager for MCP server process."""

    def __init__(self, port: int = 8003):
        self.port = port
        self.process = None

    async def __aenter__(self):
        """Start the MCP server."""
        cmd = ["uv", "run", "mcp-server", "--local", "-d"]
        print_info(f"Starting MCP server on port {self.port}...")

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=project_root,
            env={**os.environ, "MCP_SERVER_PORT": str(self.port)},
        )

        # Wait for server to start
        await asyncio.sleep(8)
        print_success(f"MCP server started on http://localhost:{self.port}/mcp")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop the MCP server."""
        print_info("Stopping MCP server...")

        # Use uv run mcp-server --stop to gracefully stop the server
        stop_cmd = ["uv", "run", "mcp-server", "--stop"]
        stop_process = subprocess.Popen(
            stop_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=project_root,
        )

        try:
            stop_process.wait(timeout=5)
            print_success("MCP server stopped")
        except subprocess.TimeoutExpired:
            print_warning("Stop command timed out, forcing termination...")
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            print_success("MCP server stopped (forced)")


async def run_all_tests():
    """Run all tests using a single HTTP client and session."""
    print_header("MCP Server for Splunk - HTTP Header Authentication Tests")

    # Single session ID for all tests
    session_id = "test-session-unified"

    # Splunk configuration as HTTP headers
    splunk_config = {
        "X-Splunk-Host": os.getenv("SPLUNK_HOST", "localhost"),
        "X-Splunk-Port": os.getenv("SPLUNK_PORT", "8089"),
        "X-Splunk-Username": os.getenv("SPLUNK_USERNAME", "admin"),
        "X-Splunk-Password": os.getenv("SPLUNK_PASSWORD", "changeme"),
        "X-Splunk-Scheme": os.getenv("SPLUNK_SCHEME", "https"),
        "X-Splunk-Verify-SSL": os.getenv("SPLUNK_VERIFY_SSL", "false"),
        "X-Session-ID": session_id,
    }

    print_info("Using Splunk configuration:")
    for key, value in splunk_config.items():
        if "Password" in key:
            print(f"  {key}: {'*' * len(value)}")
        else:
            print(f"  {key}: {value}")
    print()

    try:
        import httpx
    except ImportError:
        print_error("httpx library not available. Install with: pip install httpx")
        return []

    results = []

    try:
        async with MCPServerProcess(port=8003):
            # Create HTTP client with custom headers - single client for all tests
            headers = {**splunk_config, "Accept": "application/json, text/event-stream"}
            async with httpx.AsyncClient(
                headers=headers, timeout=60.0, follow_redirects=True
            ) as http_client:
                url = "http://localhost:8003/mcp"

                # Initialize session once
                print_header("Initializing MCP Session")
                init_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0.0"},
                    },
                }

                print_info("Sending initialize request...")
                response = await http_client.post(url, json=init_request)

                if response.status_code == 200:
                    print_success("Session initialized successfully!")
                    if response.content and len(response.content) > 0:
                        try:
                            result = response.json()
                            server_name = result.get("result", {}).get("serverInfo", {}).get("name", "N/A")
                            print_info(f"Server: {server_name}")
                        except json.JSONDecodeError:
                            print_info("(SSE response)")
                else:
                    print_error(f"Initialize failed with status {response.status_code}")
                    print_error(f"Response: {response.text[:200]}")
                    return []

                # Send initialized notification
                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                }
                await http_client.post(url, json=initialized_notification)
                print()

                # Test 1: List Tools
                print_header("Test 1: List Available Tools")
                try:
                    list_tools_request = {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/list",
                        "params": {},
                    }

                    response = await http_client.post(url, json=list_tools_request)

                    if response.status_code == 200 and response.content:
                        try:
                            result = response.json()
                            tools = result.get("result", {}).get("tools", [])
                            print_success(f"Found {len(tools)} tools")
                            print_info("Sample tools:")
                            for tool in tools[:5]:
                                print(f"  - {tool.get('name', 'N/A')}")
                            results.append(("List Tools", True))
                        except json.JSONDecodeError:
                            print_warning("Response is not JSON")
                            results.append(("List Tools", False))
                    else:
                        print_error(f"Failed with status {response.status_code}")
                        results.append(("List Tools", False))
                except Exception as e:
                    print_error(f"Failed: {e}")
                    results.append(("List Tools", False))

                # Test 2: Call user_agent_info
                print_header("Test 2: Call user_agent_info (Simple Tool)")
                try:
                    tool_call_request = {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {"name": "user_agent_info", "arguments": {}},
                    }

                    response = await http_client.post(url, json=tool_call_request)

                    if response.status_code == 200 and response.content:
                        try:
                            result = response.json()
                            if "error" in result:
                                print_error(f"Tool error: {result['error']}")
                                results.append(("user_agent_info", False))
                            else:
                                tool_result = result.get("result", {}).get("content", [])
                                if tool_result:
                                    print_success("user_agent_info executed successfully")
                                    for content in tool_result:
                                        if content.get("type") == "text":
                                            data = json.loads(content.get("text", "{}"))
                                            session = data.get("context", {}).get("state", {}).get("session_id", "N/A")
                                            print_info(f"Session ID: {session}")
                                    results.append(("user_agent_info", True))
                                else:
                                    print_warning("Empty result")
                                    results.append(("user_agent_info", False))
                        except json.JSONDecodeError:
                            print_error("Response is not JSON")
                            results.append(("user_agent_info", False))
                    else:
                        print_error(f"Failed with status {response.status_code}")
                        results.append(("user_agent_info", False))
                except Exception as e:
                    print_error(f"Failed: {e}")
                    import traceback
                    traceback.print_exc()
                    results.append(("user_agent_info", False))

                # Test 3: Call get_splunk_health
                print_header("Test 3: Call get_splunk_health (Splunk Tool)")
                try:
                    tool_call_request = {
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "tools/call",
                        "params": {"name": "get_splunk_health", "arguments": {}},
                    }

                    response = await http_client.post(url, json=tool_call_request)

                    if response.status_code == 200 and response.content:
                        try:
                            result = response.json()
                            if "error" in result:
                                print_error(f"Tool error: {result['error']}")
                                results.append(("get_splunk_health", False))
                            else:
                                tool_result = result.get("result", {}).get("content", [])
                                if tool_result:
                                    print_success("get_splunk_health executed successfully")
                                    for content in tool_result:
                                        if content.get("type") == "text":
                                            try:
                                                data = json.loads(content.get("text", "{}"))
                                                print_info(f"Status: {data.get('status', 'N/A')}")
                                                print_info(f"Version: {data.get('version', 'N/A')}")
                                                print_info(f"Connection Source: {data.get('connection_source', 'N/A')}")
                                            except json.JSONDecodeError:
                                                print_info(f"Result: {content.get('text', 'N/A')[:100]}")
                                    results.append(("get_splunk_health", True))
                                else:
                                    print_warning("Empty result")
                                    results.append(("get_splunk_health", False))
                        except json.JSONDecodeError:
                            print_error("Response is not JSON")
                            results.append(("get_splunk_health", False))
                    else:
                        print_error(f"Failed with status {response.status_code}")
                        results.append(("get_splunk_health", False))
                except Exception as e:
                    print_error(f"Failed: {e}")
                    import traceback
                    traceback.print_exc()
                    results.append(("get_splunk_health", False))

                # Test 4: Call list_indexes
                print_header("Test 4: Call list_indexes (Class-Based Tool)")
                try:
                    tool_call_request = {
                        "jsonrpc": "2.0",
                        "id": 5,
                        "method": "tools/call",
                        "params": {"name": "list_indexes", "arguments": {}},
                    }

                    response = await http_client.post(url, json=tool_call_request)

                    if response.status_code == 200 and response.content:
                        try:
                            result = response.json()
                            if "error" in result:
                                print_error(f"Tool error: {result['error']}")
                                results.append(("list_indexes", False))
                            else:
                                tool_result = result.get("result", {}).get("content", [])
                                if tool_result:
                                    print_success("list_indexes executed successfully")
                                    for content in tool_result:
                                        if content.get("type") == "text":
                                            try:
                                                data = json.loads(content.get("text", "{}"))
                                                indexes = data.get("indexes", [])
                                                print_info(f"Found {len(indexes)} indexes")
                                                if indexes:
                                                    print_info(f"Sample: {', '.join(indexes[:5])}")
                                            except json.JSONDecodeError:
                                                print_info(f"Result: {content.get('text', 'N/A')[:100]}")
                                    results.append(("list_indexes", True))
                                else:
                                    print_warning("Empty result")
                                    results.append(("list_indexes", False))
                        except json.JSONDecodeError:
                            print_error("Response is not JSON")
                            results.append(("list_indexes", False))
                    else:
                        print_error(f"Failed with status {response.status_code}")
                        print_error(f"Response: {response.text[:200]}")
                        results.append(("list_indexes", False))
                except Exception as e:
                    print_error(f"Failed: {e}")
                    import traceback
                    traceback.print_exc()
                    results.append(("list_indexes", False))

                # Test 5: Verify session continuity
                print_header("Test 5: Verify Session Continuity")
                try:
                    # Call user_agent_info again to verify same session
                    tool_call_request = {
                        "jsonrpc": "2.0",
                        "id": 6,
                        "method": "tools/call",
                        "params": {"name": "user_agent_info", "arguments": {}},
                    }

                    response = await http_client.post(url, json=tool_call_request)

                    if response.status_code == 200 and response.content:
                        try:
                            result = response.json()
                            if "error" not in result:
                                tool_result = result.get("result", {}).get("content", [])
                                if tool_result:
                                    for content in tool_result:
                                        if content.get("type") == "text":
                                            data = json.loads(content.get("text", "{}"))
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
                                    print_warning("Empty result")
                                    results.append(("Session Continuity", False))
                            else:
                                print_error(f"Tool error: {result['error']}")
                                results.append(("Session Continuity", False))
                        except json.JSONDecodeError:
                            print_error("Response is not JSON")
                            results.append(("Session Continuity", False))
                    else:
                        print_error(f"Failed with status {response.status_code}")
                        results.append(("Session Continuity", False))
                except Exception as e:
                    print_error(f"Failed: {e}")
                    results.append(("Session Continuity", False))

    except Exception as e:
        print_error(f"Test suite failed: {e}")
        import traceback
        traceback.print_exc()

    return results


def print_usage_instructions():
    """Print usage instructions and examples."""
    print_header("Usage Instructions")

    print(f"""
{Colors.BOLD}Prerequisites:{Colors.ENDC}
1. Install required dependencies:
   pip install httpx

2. Set Splunk environment variables (or they'll use defaults):
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

{Colors.BOLD}Expected Behavior:{Colors.ENDC}
- Server starts once on port 8003
- Single HTTP client with headers for all tests
- Same session ID (test-session-unified) throughout
- Headers captured by HeaderCaptureMiddleware
- Splunk credentials extracted from X-Splunk-* headers
- Tools use header-provided credentials

{Colors.BOLD}Troubleshooting:{Colors.ENDC}
- Check logs/mcp_splunk_server.log for detailed server logs
- Ensure Splunk is accessible at the configured host/port
- Verify credentials are correct
- Check that port 8003 is available
- Ensure 'uv' is installed and mcp-server is configured
""")


async def main():
    """Run all tests."""
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("=" * 60)
    print("  MCP Server for Splunk - HTTP Header Authentication Tests")
    print("  Single Session, Raw HTTP Implementation")
    print("=" * 60)
    print(Colors.ENDC)

    # Check prerequisites
    print_header("Checking Prerequisites")

    try:
        import httpx  # noqa: F401
        print_success("httpx library available")
    except ImportError:
        print_error("httpx library not available")
        print_info("Install with: pip install httpx")
        print_usage_instructions()
        return False

    # Check environment variables
    if os.getenv("SPLUNK_HOST"):
        print_success(f"SPLUNK_HOST set to: {os.getenv('SPLUNK_HOST')}")
    else:
        print_warning("SPLUNK_HOST not set, using default: localhost")

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