"""Invoked by check_wheel.py with only the extracted wheel on PYTHONPATH."""

import asyncio
import os
import socket
import subprocess
import sys
import tempfile
from importlib.metadata import distribution
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastmcp import Client

import mcp_server_for_splunk
from mcp_server_for_splunk.core.base import BaseTool, SplunkContext
from mcp_server_for_splunk.resources.dashboard_studio_content import load_cheatsheet_markdown
from mcp_server_for_splunk.server import ensure_components_loaded, load_plugins, mcp


async def check_cli() -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    launch = (
        "from importlib.metadata import distribution; "
        "entry = next(e for e in distribution('mcp-server-for-splunk').entry_points "
        "if e.name == 'mcp-server'); raise SystemExit(entry.load()())"
    )
    with tempfile.TemporaryFile(mode="w+") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-P",
                "-c",
                launch,
                "--local",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            url = f"http://127.0.0.1:{port}"
            async with httpx.AsyncClient(timeout=1, trust_env=False) as http:
                for _ in range(100):
                    if process.poll() is not None:
                        log.seek(0)
                        raise AssertionError(log.read())
                    try:
                        response = await http.get(f"{url}/health")
                        if response.status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    await asyncio.sleep(0.1)
                else:
                    raise AssertionError("Installed CLI did not become healthy")
            async with Client(f"{url}/mcp") as client:
                assert "run_splunk_search" in {tool.name for tool in await client.list_tools()}
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


async def check_tools() -> None:
    job = Mock()
    job.sid = "wheel-smoke-job"
    job.is_done.return_value = True
    job.content = {"isDone": "1", "isFailed": "0", "resultCount": "1"}
    job.results.side_effect = lambda **kwargs: [{"count": "1"}]
    service = Mock(host="splunk.example.test", scheme="https", port=8089)
    service.jobs.create.return_value = job
    service.jobs.__getitem__ = Mock(return_value=job)
    context = SplunkContext(service=service, is_connected=True)
    if os.environ["MCP_DISABLE_PLUGINS"] == "false":
        assert load_plugins(mcp) > 0
    await ensure_components_loaded(mcp)
    with (
        patch.object(BaseTool, "_get_splunk_context", return_value=context),
        patch.object(BaseTool, "_resolve_client_config_sync", return_value=None),
        patch.object(BaseTool, "get_client_config_from_context", AsyncMock(return_value={})),
    ):
        async with Client(mcp) as client:
            names = {tool.name for tool in await client.list_tools()}
            assert {"run_oneshot_search", "run_splunk_search", "get_search_job_results"} <= names
            if os.environ["MCP_DISABLE_PLUGINS"] == "false":
                assert "itsi_get_supported_object_types" in names
            for name in ("run_oneshot_search", "run_splunk_search"):
                result = await client.call_tool(name, {"query": "| makeresults | stats count"})
                assert not result.is_error, result
                assert result.structured_content["results"] == [{"count": "1"}]
            result = await client.call_tool("get_search_job_info", {"job_id": job.sid})
            assert not result.is_error, result
            result = await client.call_tool("get_search_job_results", {"job_id": job.sid})
            assert not result.is_error, result
            workflows = await client.call_tool("list_workflows", {"include_contrib": False})
            assert not workflows.is_error, workflows
            assert workflows.structured_content["total_workflows"] > 0, workflows


def main() -> None:
    installed = Path(sys.argv[1])
    assert Path(mcp_server_for_splunk.__file__).is_relative_to(installed)
    assert "src" not in sys.modules
    assert "Dashboard Studio" in load_cheatsheet_markdown()
    entry = next(
        entry
        for entry in distribution("mcp-server-for-splunk").entry_points
        if entry.name == "mcp-server"
    )
    assert entry.value.startswith("mcp_server_for_splunk.")
    try:
        entry.load()(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    asyncio.run(check_tools())
    asyncio.run(check_cli())


if __name__ == "__main__":
    main()
