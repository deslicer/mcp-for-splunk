"""Search I/O must leave the HTTP event loop available for liveness probes."""

import asyncio
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastmcp import FastMCP
from splunklib import client as spl_client

from src.client import splunk_client
from src.core.base import SplunkContext
from src.core.splunk_job_wait import wait_for_job
from src.routes.health import setup_health_routes
from src.tools.search import saved_search_tools
from src.tools.search.job_info import GetSearchJobInfo
from src.tools.search.job_results import GetSearchJobResults
from src.tools.search.job_search import JobSearch
from src.tools.search.oneshot_search import OneshotSearch
from src.tools.search.saved_search_tools import ExecuteSavedSearch


@pytest.mark.parametrize(
    "tool_class",
    [OneshotSearch, JobSearch, GetSearchJobInfo, GetSearchJobResults, ExecuteSavedSearch],
)
async def test_connection_does_not_block_health(tool_class, monkeypatch):
    tool = tool_class(tool_class.METADATA.name, "test")
    entered, release = threading.Event(), threading.Event()

    def connect(_config):
        entered.set()
        release.wait(1)
        raise TimeoutError("Splunk stalled")

    monkeypatch.setattr(splunk_client, "get_splunk_service", connect)
    monkeypatch.setattr(tool, "_resolve_client_config_sync", lambda ctx: {"splunk_host": "test"})
    monkeypatch.setattr(tool, "_get_splunk_context", lambda ctx: SplunkContext(None, False))
    ctx = SimpleNamespace(info=AsyncMock(), error=AsyncMock(), report_progress=AsyncMock())
    server = FastMCP("responsiveness")
    setup_health_routes(server)
    args = (
        {"query": "| makeresults"}
        if tool_class in (OneshotSearch, JobSearch)
        else {"job_id": "sid"}
    )
    if tool_class is ExecuteSavedSearch:
        args = {"name": "slow saved search"}
    task = asyncio.create_task(tool.execute(ctx, **args))
    try:
        while not entered.is_set():
            await asyncio.sleep(0)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=server.http_app()), base_url="http://test"
        ) as http:
            response = await http.get("/health")
        assert response.status_code == 200
        assert not task.done(), "Search connection blocked the event loop until it timed out"
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("tool_class", [GetSearchJobInfo, GetSearchJobResults])
async def test_job_lookup_and_refresh_run_off_event_loop(tool_class, monkeypatch):
    owner_thread = threading.get_ident()
    threads = []
    job = Mock()
    job.content = {"isDone": "1", "isFailed": "0", "resultCount": "1"}
    job.results.return_value = [{"n": "1"}]
    job.refresh.side_effect = lambda: threads.append(threading.get_ident())

    def lookup(sid):
        threads.append(threading.get_ident())
        return job

    service = Mock(host="splunk.example", scheme="https", port=8089)
    service.jobs.__getitem__ = Mock(side_effect=lookup)
    tool = tool_class(tool_class.METADATA.name, "test")
    monkeypatch.setattr(tool, "_get_splunk_context", lambda ctx: SplunkContext(service, True))
    monkeypatch.setattr(tool, "_resolve_client_config_sync", lambda ctx: None)
    monkeypatch.setattr(tool, "get_client_config_from_context", AsyncMock(return_value={}))
    result = await tool.execute(SimpleNamespace(error=AsyncMock()), job_id="sid")
    assert result["status"] == "success", result
    assert threads and all(t != owner_thread for t in threads)


@pytest.mark.parametrize(
    "tool_class", [OneshotSearch, JobSearch, GetSearchJobInfo, GetSearchJobResults]
)
async def test_sdk_lazy_server_info_discovery_runs_off_event_loop(tool_class, monkeypatch):
    threads = []

    class LazyService(spl_client.Service):
        @property
        def info(self):
            threads.append(threading.get_ident())
            return {"version": "9.0.0"}

    service = LazyService(host="splunk.example", token="synthetic-test-token")
    job = Mock(sid="sid")
    job.content = {"isDone": "1", "isFailed": "0", "resultCount": "1"}
    job.is_done.return_value = True
    job.results.return_value = [{"n": "1"}]
    monkeypatch.setattr(spl_client.Jobs, "create", lambda *args, **kwargs: job)
    monkeypatch.setattr(spl_client.Jobs, "__getitem__", lambda *args, **kwargs: job)
    tool = tool_class(tool_class.METADATA.name, "test")
    monkeypatch.setattr(tool, "_get_splunk_context", lambda ctx: SplunkContext(service, True))
    monkeypatch.setattr(tool, "_resolve_client_config_sync", lambda ctx: None)
    monkeypatch.setattr(tool, "get_client_config_from_context", AsyncMock(return_value={}))
    ctx = SimpleNamespace(info=AsyncMock(), error=AsyncMock(), report_progress=AsyncMock())
    args = (
        {"query": "| makeresults"}
        if tool_class in (OneshotSearch, JobSearch)
        else {"job_id": "sid"}
    )
    result = await tool.execute(ctx, **args)
    assert result["status"] == "success", result
    assert threads and all(t != threading.get_ident() for t in threads)


async def test_concurrent_saved_searches_do_not_mutate_shared_service_namespace(monkeypatch):
    service = spl_client.Service(
        host="splunk.example", token="synthetic-test-token", app="original"
    )
    original = dict(service.namespace)
    release = threading.Event()
    contexts = []

    def find(local_service, name, app, owner):
        local_service.namespace = spl_client.namespace(app=app)
        contexts.append(local_service)
        release.wait(1)
        return None

    monkeypatch.setattr(saved_search_tools, "_find_saved_search", find)
    tool = ExecuteSavedSearch("execute_saved_search", "test")
    monkeypatch.setattr(tool, "_get_splunk_context", lambda ctx: SplunkContext(service, True))
    monkeypatch.setattr(tool, "_resolve_client_config_sync", lambda ctx: None)
    ctx = SimpleNamespace(info=AsyncMock(), error=AsyncMock())
    tasks = [
        asyncio.create_task(tool.execute(ctx, name="report", app=app)) for app in ("app-a", "app-b")
    ]

    async def wait_until_entered():
        while len(contexts) < 2:
            await asyncio.sleep(0)

    try:
        await asyncio.wait_for(wait_until_entered(), timeout=1)
        assert service.namespace == original
        assert contexts[0] is not contexts[1]
        assert {context.namespace["app"] for context in contexts} == {"app-a", "app-b"}
    finally:
        release.set()
        await asyncio.gather(*tasks)
    assert service.namespace == original


async def test_stalled_job_poll_respects_wait_budget():
    release = threading.Event()
    job = Mock()
    job.is_done.side_effect = lambda: release.wait(1)
    job.content = {"isDone": "0"}
    task = asyncio.create_task(wait_for_job(job, wait_seconds=0.02))
    try:
        await asyncio.sleep(0.1)
        assert task.done(), "A stuck Splunk status read exceeded the search wait budget"
        snapshot = await task
        assert snapshot.is_done is False
        job.cancel.assert_not_called()
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("verify", [True, False])
def test_splunk_sdk_connections_have_a_finite_timeout(monkeypatch, verify):
    connect = Mock(return_value=Mock())
    monkeypatch.setattr(splunk_client.client, "connect", connect)
    handler = Mock()
    monkeypatch.setattr(splunk_client.binding, "handler", handler)
    splunk_client.get_splunk_service(
        {"splunk_token": "test", "splunk_host": "example", "splunk_verify_ssl": verify}
    )
    assert 0 < handler.call_args.kwargs["timeout"] <= 30
    assert handler.call_args.kwargs["verify"] is verify
    assert connect.call_args.kwargs["handler"] is handler.return_value


@pytest.mark.parametrize("mode", ["oneshot", "job"])
async def test_saved_search_returns_running_job_without_blocking(mode, monkeypatch):
    monkeypatch.setenv("MCP_SEARCH_WAIT_SECONDS", "0")
    threads = []
    job = Mock(sid="saved.sid")
    job.is_done.return_value = False
    job.content = {"isDone": "0", "isFailed": "0"}
    saved = Mock()
    saved.name = "slow saved search"

    def dispatch(**kwargs):
        threads.append(threading.get_ident())
        return job

    saved.dispatch.side_effect = dispatch
    tool = ExecuteSavedSearch("execute_saved_search", "test")
    ctx = SimpleNamespace(info=AsyncMock(), error=AsyncMock(), report_progress=AsyncMock())
    execute = tool._execute_oneshot if mode == "oneshot" else tool._execute_job
    result = await asyncio.wait_for(execute(ctx, saved, {}, 50, 0), timeout=0.2)
    assert result["is_done"] is False
    assert result["job_id"] == "saved.sid"
    assert result["poll_with"] == "get_search_job_info"
    assert threads and all(t != threading.get_ident() for t in threads)
    job.results.assert_not_called()


@pytest.mark.parametrize("send_headers", [False, True])
def test_sdk_socket_timeout_covers_headers_and_result_body(monkeypatch, send_headers):
    release = threading.Event()

    class StalledSplunk(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            if send_headers:
                self.send_response(200)
                self.send_header("Content-Type", "text/xml")
                self.send_header("Content-Length", "1000")
                self.end_headers()
                self.wfile.write(b"<response>")
                self.wfile.flush()
            release.wait(1)

    server = ThreadingHTTPServer(("127.0.0.1", 0), StalledSplunk)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(splunk_client, "SPLUNK_REQUEST_TIMEOUT_SECONDS", 0.05)
    service = splunk_client.get_splunk_service(
        {
            "splunk_host": "127.0.0.1",
            "splunk_port": server.server_port,
            "splunk_scheme": "http",
            "splunk_token": "synthetic-test-token",
        }
    )
    # Isolate the search request; lazy server/info discovery is covered separately.
    service._splunk_version = (9, 0, 0)
    service._instance_type = "enterprise"
    start = time.monotonic()
    try:
        with pytest.raises(TimeoutError):
            service.jobs.create("| makeresults")
        assert time.monotonic() - start < 0.5
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("stage", ["job_creation", "job_ttl", "result_retrieval"])
async def test_saved_search_timeout_preserves_dispatch_outcome(stage, monkeypatch):
    job = Mock(sid="known-sid")
    job.is_done.return_value = True
    job.content = {"isDone": "1", "isFailed": "0"}
    saved = Mock()
    saved.name = "report"
    saved.dispatch.return_value = job
    error = TimeoutError("Splunk stalled")
    if stage == "job_creation":
        saved.dispatch.side_effect = error
    else:
        target = "apply_job_ttl" if stage == "job_ttl" else "fetch_job_results_page"
        monkeypatch.setattr(saved_search_tools, target, Mock(side_effect=error))
    tool = ExecuteSavedSearch("execute_saved_search", "test")
    response = await tool._execute_bounded(SimpleNamespace(), saved, {}, 50, time.time(), "oneshot")
    assert response["status"] == "error"
    assert response["execution_stage"] == stage
    if stage == "job_creation":
        assert response["search_started"] is None
        assert "job_id" not in response
    else:
        assert response["search_started"] is True
        assert response["job_id"] == "known-sid"
    assert saved.dispatch.call_count == 1
