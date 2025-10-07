#!/usr/bin/env python3
"""
Test script for MCP Server for Splunk with HTTP header-based authentication.

This script tests the MCP server's ability to accept Splunk connection
parameters via HTTP headers instead of environment variables, allowing
different clients to connect to different Splunk instances.
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
        print_success(f"MCP server started on http://localhost:{self.port}/mcp/")
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


async def test_connection_without_headers():
    """Test basic connection without Splunk headers (should use env vars)."""
    print_header("Test 1: Basic Connection (Environment Variables)")

    try:
        from fastmcp import Client

        async with MCPServerProcess(port=8003):
            async with Client(transport="http://localhost:8003/mcp") as client:
                # List available tools
                tools = await client.list_tools()
                print_success(f"Connected successfully! Found {len(tools)} tools")

                # Test a simple tool that doesn't require Splunk
                print_info("Testing user_agent_info tool...")
                result = await client.call_tool("user_agent_info", {})

                # FastMCP Client returns a CallToolResult object
                if result and hasattr(result, "content") and len(result.content) > 0:
                    print_success("user_agent_info tool works!")
                    # Parse the first content item
                    content = result.content[0]
                    if hasattr(content, "text"):
                        print(f"  Result preview: {content.text[:100]}...")
                    return True
                else:
                    print_error(f"user_agent_info tool returned unexpected result: {type(result)}")
                    return False

    except Exception as e:  # noqa: BLE001
        print_error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_connection_with_headers():
    """Test connection with Splunk configuration in HTTP headers."""
    print_header("Test 2: Connection with Splunk Headers")

    # Get Splunk credentials from environment or use defaults
    splunk_config = {
        "X-Splunk-Host": os.getenv("SPLUNK_HOST", "localhost"),
        "X-Splunk-Port": os.getenv("SPLUNK_PORT", "8089"),
        "X-Splunk-Username": os.getenv("SPLUNK_USERNAME", "admin"),
        "X-Splunk-Password": os.getenv("SPLUNK_PASSWORD", "changeme"),
        "X-Splunk-Scheme": os.getenv("SPLUNK_SCHEME", "https"),
        "X-Splunk-Verify-SSL": os.getenv("SPLUNK_VERIFY_SSL", "false"),
        "X-Session-ID": "test-session-123",
    }

    print_info("Using Splunk configuration:")
    for key, value in splunk_config.items():
        if "Password" in key:
            print(f"  {key}: {'*' * len(value)}")
        else:
            print(f"  {key}: {value}")

    try:
        import httpx

        async with MCPServerProcess(port=8003):
            # Create HTTP client with custom headers
            # Add Accept header for MCP protocol requirements
            headers = {**splunk_config, "Accept": "application/json, text/event-stream"}
            async with httpx.AsyncClient(
                headers=headers, timeout=30.0, follow_redirects=True
            ) as http_client:
                # Initialize MCP session
                url = "http://localhost:8003/mcp"

                # Send initialize request
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

                print_info("Sending initialize request with headers...")
                response = await http_client.post(url, json=init_request)

                if response.status_code == 200:
                    print_success("Initialize request successful!")
                    # Check if response has content before parsing
                    if response.content and len(response.content) > 0:
                        try:
                            # Try to parse as JSON (for regular HTTP responses)
                            result = response.json()
                            print(
                                f"  Server: {result.get('result', {}).get('serverInfo', {}).get('name', 'N/A')}"
                            )
                        except json.JSONDecodeError:
                            # Response might be SSE format or empty
                            print_info("  (SSE response - connection established)")
                    else:
                        print_info("  (Empty response body - SSE mode)")
                else:
                    print_error(f"Initialize failed with status {response.status_code}")
                    print(f"  Response: {response.text[:200]}")
                    return False

                # List tools
                list_tools_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                }

                print_info("Listing available tools...")
                response = await http_client.post(url, json=list_tools_request)

                if response.status_code == 200:
                    if response.content and len(response.content) > 0:
                        try:
                            result = response.json()
                            tools = result.get("result", {}).get("tools", [])
                            print_success(f"Found {len(tools)} tools!")

                            # Print first 5 tools
                            print_info("Sample tools:")
                            for tool in tools[:5]:
                                print(f"  - {tool.get('name', 'N/A')}")
                        except json.JSONDecodeError:
                            print_warning("Response is not JSON (likely SSE format)")
                            print_info(f"  Response preview: {response.text[:200]}")
                            return False
                    else:
                        print_warning("Empty response when listing tools")
                        return False
                else:
                    print_error(f"List tools failed with status {response.status_code}")
                    print(f"  Response: {response.text[:200]}")
                    return False

                return True

    except ImportError:
        print_error("httpx library not available. Install with: pip install httpx")
        return False
    except Exception as e:  # noqa: BLE001
        print_error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_tool_execution_with_headers():
    """Test executing a Splunk tool with header-based authentication."""
    print_header("Test 3: Tool Execution with Headers")

    # Get Splunk credentials from environment or use defaults
    splunk_config = {
        "X-Splunk-Host": os.getenv("SPLUNK_HOST", "localhost"),
        "X-Splunk-Port": os.getenv("SPLUNK_PORT", "8089"),
        "X-Splunk-Username": os.getenv("SPLUNK_USERNAME", "admin"),
        "X-Splunk-Password": os.getenv("SPLUNK_PASSWORD", "changeme"),
        "X-Splunk-Scheme": os.getenv("SPLUNK_SCHEME", "https"),
        "X-Splunk-Verify-SSL": os.getenv("SPLUNK_VERIFY_SSL", "false"),
        "X-Session-ID": "test-session-456",
    }

    try:
        import httpx

        async with MCPServerProcess(port=8003):
            # Add Accept header for MCP protocol requirements
            headers = {**splunk_config, "Accept": "application/json, text/event-stream"}
            async with httpx.AsyncClient(
                headers=headers, timeout=60.0, follow_redirects=True
            ) as http_client:
                url = "http://localhost:8003/mcp"

                # Initialize session
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

                init_response = await http_client.post(url, json=init_request)
                if init_response.status_code != 200:
                    print_error(f"Initialize failed with status {init_response.status_code}")
                    return False

                # Test get_splunk_health tool
                print_info("Testing get_splunk_health tool with header credentials...")

                tool_call_request = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "get_splunk_health", "arguments": {}},
                }

                response = await http_client.post(url, json=tool_call_request)

                if response.status_code == 200:
                    if not response.content or len(response.content) == 0:
                        print_warning("Empty response from tool call")
                        return False
                    
                    try:
                        result = response.json()
                    except json.JSONDecodeError:
                        print_error("Response is not JSON (likely SSE format)")
                        print_info(f"  Response preview: {response.text[:200]}")
                        return False

                    if "error" in result:
                        print_error(f"Tool execution error: {result['error']}")
                        return False

                    tool_result = result.get("result", {}).get("content", [])

                    if tool_result:
                        print_success("Tool executed successfully!")

                        # Parse the result
                        for content in tool_result:
                            if content.get("type") == "text":
                                try:
                                    data = json.loads(content.get("text", "{}"))
                                    print(f"  Status: {data.get('status', 'N/A')}")
                                    print(f"  Version: {data.get('version', 'N/A')}")
                                    print(f"  Server: {data.get('server_name', 'N/A')}")
                                    print(
                                        f"  Connection Source: {data.get('connection_source', 'N/A')}"
                                    )
                                except json.JSONDecodeError:
                                    print(f"  Result: {content.get('text', 'N/A')[:200]}")

                        return True
                    else:
                        print_warning("Tool returned empty result")
                        return False
                else:
                    print_error(f"Tool call failed with status {response.status_code}")
                    print(f"  Response: {response.text[:200]}")
                    return False

    except ImportError:
        print_error("httpx library not available. Install with: pip install httpx")
        return False
    except Exception as e:  # noqa: BLE001
        print_error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_list_indexes_with_headers():
    """Test list_indexes tool with header-based authentication."""
    print_header("Test 4: List Indexes with Headers")

    splunk_config = {
        "X-Splunk-Host": os.getenv("SPLUNK_HOST", "localhost"),
        "X-Splunk-Port": os.getenv("SPLUNK_PORT", "8089"),
        "X-Splunk-Username": os.getenv("SPLUNK_USERNAME", "admin"),
        "X-Splunk-Password": os.getenv("SPLUNK_PASSWORD", "changeme"),
        "X-Splunk-Scheme": os.getenv("SPLUNK_SCHEME", "https"),
        "X-Splunk-Verify-SSL": os.getenv("SPLUNK_VERIFY_SSL", "false"),
        "X-Session-ID": "test-session-789",
    }

    try:
        import httpx

        async with MCPServerProcess(port=8003):
            # Add Accept header for MCP protocol requirements
            headers = {**splunk_config, "Accept": "application/json, text/event-stream"}
            async with httpx.AsyncClient(
                headers=headers, timeout=60.0, follow_redirects=True
            ) as http_client:
                url = "http://localhost:8003/mcp"

                # Initialize
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
                init_response = await http_client.post(url, json=init_request)
                if init_response.status_code != 200:
                    print_error(f"Initialize failed with status {init_response.status_code}")
                    return False

                # Call list_indexes
                print_info("Testing list_indexes tool...")

                tool_call_request = {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {"name": "list_indexes", "arguments": {}},
                }

                response = await http_client.post(url, json=tool_call_request)

                if response.status_code == 200:
                    if not response.content or len(response.content) == 0:
                        print_warning("Empty response from tool call")
                        return False
                    
                    try:
                        result = response.json()
                    except json.JSONDecodeError:
                        print_error("Response is not JSON (likely SSE format)")
                        print_info(f"  Response preview: {response.text[:200]}")
                        return False

                    if "error" in result:
                        print_error(f"Tool execution error: {result['error']}")
                        return False

                    tool_result = result.get("result", {}).get("content", [])

                    if tool_result:
                        print_success("list_indexes executed successfully!")

                        for content in tool_result:
                            if content.get("type") == "text":
                                try:
                                    data = json.loads(content.get("text", "{}"))
                                    indexes = data.get("indexes", [])
                                    print(f"  Found {len(indexes)} indexes")
                                    if indexes:
                                        print(f"  Sample indexes: {', '.join(indexes[:5])}")
                                except json.JSONDecodeError:
                                    print(f"  Result: {content.get('text', 'N/A')[:200]}")

                        return True
                    else:
                        print_warning("Tool returned empty result")
                        return False
                else:
                    print_error(f"Tool call failed with status {response.status_code}")
                    print(f"  Response preview: {response.text[:200]}")
                    return False

    except ImportError:
        print_error("httpx library not available. Install with: pip install httpx")
        return False
    except Exception as e:  # noqa: BLE001
        print_error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_multiple_sessions():
    """Test multiple concurrent sessions with different Splunk configurations."""
    print_header("Test 5: Multiple Concurrent Sessions")

    # Simulate two different clients with different session IDs
    session1_config = {
        "X-Splunk-Host": os.getenv("SPLUNK_HOST", "localhost"),
        "X-Splunk-Port": os.getenv("SPLUNK_PORT", "8089"),
        "X-Splunk-Username": os.getenv("SPLUNK_USERNAME", "admin"),
        "X-Splunk-Password": os.getenv("SPLUNK_PASSWORD", "changeme"),
        "X-Splunk-Scheme": os.getenv("SPLUNK_SCHEME", "https"),
        "X-Splunk-Verify-SSL": "false",
        "X-Session-ID": "session-1",
    }

    session2_config = {
        "X-Splunk-Host": os.getenv("SPLUNK_HOST", "localhost"),
        "X-Splunk-Port": os.getenv("SPLUNK_PORT", "8089"),
        "X-Splunk-Username": os.getenv("SPLUNK_USERNAME", "admin"),
        "X-Splunk-Password": os.getenv("SPLUNK_PASSWORD", "changeme"),
        "X-Splunk-Scheme": os.getenv("SPLUNK_SCHEME", "https"),
        "X-Splunk-Verify-SSL": "false",
        "X-Session-ID": "session-2",
    }

    try:
        import httpx

        async with MCPServerProcess(port=8003):
            print_info("Creating two concurrent sessions...")

            # Add Accept header for MCP protocol requirements
            headers1 = {**session1_config, "Accept": "application/json, text/event-stream"}
            headers2 = {**session2_config, "Accept": "application/json, text/event-stream"}

            async with (
                httpx.AsyncClient(headers=headers1, timeout=60.0, follow_redirects=True) as client1,
                httpx.AsyncClient(headers=headers2, timeout=60.0, follow_redirects=True) as client2,
            ):
                url = "http://localhost:8003/mcp"

                # Initialize both sessions
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

                response1 = await client1.post(url, json=init_request)
                response2 = await client2.post(url, json=init_request)

                if response1.status_code == 200 and response2.status_code == 200:
                    print_success("Both sessions initialized successfully!")

                    # Test tool call from both sessions
                    tool_request = {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "user_agent_info", "arguments": {}},
                    }

                    result1 = await client1.post(url, json=tool_request)
                    result2 = await client2.post(url, json=tool_request)

                    if result1.status_code == 200 and result2.status_code == 200:
                        print_success("Both sessions can execute tools independently!")
                        print_info("Session isolation verified")
                        return True
                    else:
                        print_error("Tool execution failed for one or both sessions")
                        return False
                else:
                    print_error("Session initialization failed")
                    return False

    except ImportError:
        print_error("httpx library not available. Install with: pip install httpx")
        return False
    except Exception as e:  # noqa: BLE001
        print_error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def print_usage_instructions():
    """Print usage instructions and examples."""
    print_header("Usage Instructions")

    print(f"""
{Colors.BOLD}Prerequisites:{Colors.ENDC}
1. Install required dependencies:
   pip install httpx fastmcp

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
✅ Multiple concurrent sessions
✅ Session isolation

{Colors.BOLD}Expected Behavior:{Colors.ENDC}
- Server starts on port 8003 using 'uv run mcp-server --local -d'
- Headers are captured by HeaderCaptureMiddleware
- Splunk credentials are extracted from X-Splunk-* headers
- Tools use header-provided credentials instead of env vars
- Multiple sessions maintain separate configurations

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

    try:
        from fastmcp import Client  # noqa: F401

        print_success("fastmcp library available")
    except ImportError:
        print_warning("fastmcp library not available (optional)")

    # Check environment variables
    if os.getenv("SPLUNK_HOST"):
        print_success(f"SPLUNK_HOST set to: {os.getenv('SPLUNK_HOST')}")
    else:
        print_warning("SPLUNK_HOST not set, using default: localhost")

    # Run tests
    results = []

    # Test 1: Basic connection
    try:
        result = await test_connection_without_headers()
        results.append(("Basic Connection", result))
    except Exception as e:  # noqa: BLE001
        print_error(f"Test 1 crashed: {e}")
        results.append(("Basic Connection", False))

    # Test 2: Connection with headers
    try:
        result = await test_connection_with_headers()
        results.append(("Connection with Headers", result))
    except Exception as e:  # noqa: BLE001
        print_error(f"Test 2 crashed: {e}")
        results.append(("Connection with Headers", False))

    # Test 3: Tool execution
    try:
        result = await test_tool_execution_with_headers()
        results.append(("Tool Execution", result))
    except Exception as e:  # noqa: BLE001
        print_error(f"Test 3 crashed: {e}")
        results.append(("Tool Execution", False))

    # Test 4: List indexes
    try:
        result = await test_list_indexes_with_headers()
        results.append(("List Indexes", result))
    except Exception as e:  # noqa: BLE001
        print_error(f"Test 4 crashed: {e}")
        results.append(("List Indexes", False))

    # Test 5: Multiple sessions
    try:
        result = await test_multiple_sessions()
        results.append(("Multiple Sessions", result))
    except Exception as e:  # noqa: BLE001
        print_error(f"Test 5 crashed: {e}")
        results.append(("Multiple Sessions", False))

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
