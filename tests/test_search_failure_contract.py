"""Search failures distinguish safe pre-dispatch recovery from reconciliation."""

import errno
import json
import socket
import ssl
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from urllib.error import URLError

import pytest
from fastmcp import Client, FastMCP
from mcp_types import CLIENT_CAPABILITIES_META_KEY, CLIENT_INFO_META_KEY, PROTOCOL_VERSION_META_KEY
from splunklib.binding import HTTPError
from starlette.testclient import TestClient

from src import server as production_server
from src.client import splunk_client
from src.core.base import SplunkContext
from src.core.loader import ToolLoader
from src.tools.search.job_search import JobSearch
from src.tools.search.oneshot_search import OneshotSearch


@pytest.fixture(params=[OneshotSearch, JobSearch], ids=["oneshot", "job"])
def search(request, monkeypatch):
    tool = request.param(request.param.METADATA.name, "search")
    job = Mock()
    job.sid = "search.sid.123"
    job.is_done.return_value = True
    job.content = {"isDone": "1", "isFailed": "0", "resultCount": "1"}
    job.results.return_value = [{"count": "1"}]
    service = Mock(host="splunk.example", scheme="https", port=8089)
    service.jobs.create.return_value = job
    context = SplunkContext(service=service, is_connected=True)
    monkeypatch.setattr(tool, "_get_splunk_context", lambda ctx: context)
    monkeypatch.setattr(tool, "_resolve_client_config_sync", lambda ctx: None)
    monkeypatch.setattr(tool, "get_client_config_from_context", AsyncMock(return_value={}))
    ctx = SimpleNamespace(info=AsyncMock(), error=AsyncMock(), report_progress=AsyncMock())
    return SimpleNamespace(tool=tool, job=job, service=service, context=context, ctx=ctx)


def certificate_failure():
    return ssl.SSLCertVerificationError(1, "CERTIFICATE_VERIFY_FAILED: untrusted issuer")


def http_failure(status):
    return HTTPError(
        SimpleNamespace(status=status, reason="rejected", body=BytesIO(b""), headers=[])
    )


def chained_certificate_failure():
    error = RuntimeError("connection failed")
    error.__cause__ = certificate_failure()
    return error


def fail_availability(search, monkeypatch, error):
    search.context.is_connected = False
    monkeypatch.setattr(
        search.tool, "_resolve_client_config_sync", lambda ctx: {"splunk_host": "example"}
    )
    monkeypatch.setattr(splunk_client, "get_splunk_service", Mock(side_effect=error))


async def test_certificate_failure_before_dispatch(search, monkeypatch):
    fail_availability(search, monkeypatch, certificate_failure())
    result = await search.tool.execute(search.ctx, query="index=main")
    assert result["status"] == "error"
    assert "degraded mode" in result["error"]
    assert "CERTIFICATE_VERIFY_FAILED" in result["error"]
    assert result["error_code"] == "certificate_verify_failed"
    assert result["execution_stage"] == "pre_execution"
    assert result["search_started"] is False
    assert "job_id" not in result
    search.service.jobs.create.assert_not_called()


@pytest.mark.parametrize("failure", [certificate_failure(), TimeoutError("timed out")])
async def test_job_creation_failure_is_unknown(search, failure):
    search.service.jobs.create.side_effect = failure
    result = await search.tool.execute(search.ctx, query="index=main")
    assert result["execution_stage"] == "job_creation"
    assert result["search_started"] is None
    assert "job_id" not in result
    search.service.jobs.create.assert_called_once()


@pytest.mark.parametrize("stage", ["job_wait", "result_retrieval", "job_ttl"])
async def test_failure_after_creation_preserves_sid(search, monkeypatch, stage):
    if stage == "job_wait":
        if isinstance(search.tool, OneshotSearch):
            pytest.skip("Blocking create has no separate wait stage")
        search.job.is_done.side_effect = certificate_failure()
    elif stage == "result_retrieval":
        search.job.results.side_effect = certificate_failure()
    else:
        # Unexpected TTL helper errors must not lose a job already returned by create.
        module = "oneshot_search" if isinstance(search.tool, OneshotSearch) else "job_search"
        monkeypatch.setattr(
            f"src.tools.search.{module}.apply_job_ttl", Mock(side_effect=certificate_failure())
        )
    result = await search.tool.execute(search.ctx, query="index=main")
    assert result["error_code"] == "certificate_verify_failed"
    assert result["execution_stage"] == stage
    assert result["search_started"] is True
    assert result["job_id"] == search.job.sid
    search.service.jobs.create.assert_called_once()


async def test_best_effort_ttl_keeps_successful_job(search):
    search.job.set_ttl.side_effect = certificate_failure()
    result = await search.tool.execute(search.ctx, query="index=main")
    assert result["status"] == "success"
    assert result["job_id"] == search.job.sid


@pytest.mark.parametrize(
    "failure,code",
    [
        (URLError(certificate_failure()), "certificate_verify_failed"),
        (chained_certificate_failure(), "certificate_verify_failed"),
        (http_failure(401), "authentication_failed"),
        (http_failure(403), "permission_denied"),
        (http_failure(500), "connection_failed"),
        (RuntimeError("TLS certificate verification failed"), "connection_failed"),
        (socket.gaierror(socket.EAI_NONAME, "unknown host"), "dns_resolution_failed"),
        (ConnectionRefusedError(errno.ECONNREFUSED, "refused"), "connection_refused"),
        (OSError(errno.ENETUNREACH, "no route"), "network_unreachable"),
        (TimeoutError("timed out"), "connection_timeout"),
        (ssl.SSLError("handshake failed"), "tls_error"),
        (RuntimeError("unexpected failure"), "connection_failed"),
    ],
)
async def test_availability_failure_classification(search, monkeypatch, failure, code):
    fail_availability(search, monkeypatch, failure)
    result = await search.tool.execute(search.ctx, query="index=main")
    assert result["error_code"] == code
    assert result["search_started"] is False
    search.service.jobs.create.assert_not_called()


@pytest.mark.parametrize("stage", ["availability", "creation", "results", "failed_job"])
async def test_error_details_and_logs_redact_credentials(search, monkeypatch, caplog, stage):
    message = (
        "failed: splunk_token=tok-private splunk_password='private password' "
        'splunk_session_token="session-private" Authorization: Basic basic-private\n'
        "Authorization: Bearer bearer-private\nX-Splunk-Token: header-private\n"
        "https://user:url-private@splunk.example/path"
    )
    failure = RuntimeError(message)
    if stage == "availability":
        fail_availability(search, monkeypatch, failure)
    elif stage == "creation":
        search.service.jobs.create.side_effect = failure
    elif stage == "results":
        search.job.results.side_effect = failure
    else:
        search.job.content.update(isFailed="1", messages=[message])
    result = await search.tool.execute(search.ctx, query="index=main")
    emitted = json.dumps(result) + caplog.text + str(search.ctx.error.call_args_list)
    for secret in (
        "tok-private",
        "private password",
        "session-private",
        "basic-private",
        "bearer-private",
        "header-private",
        "url-private",
    ):
        assert secret not in emitted


async def test_failed_job_and_pagination_keep_sid(search):
    result = await search.tool.execute(search.ctx, query="index=main", offset=-1)
    assert result["error_code"] == "invalid_pagination"
    assert result["execution_stage"] == "result_retrieval"
    assert result["search_started"] is True
    assert result["job_id"] == search.job.sid
    search.job.content.update(isFailed="1", messages=["Search syntax error"])
    result = await search.tool.execute(search.ctx, query="index=main")
    assert result["search_started"] is True
    assert result["job_id"] == search.job.sid


@pytest.mark.parametrize(
    "stage,started", [("pre_execution", False), ("job_creation", None), ("result_retrieval", True)]
)
async def test_structured_fields_survive_real_mcp_tool_result(search, monkeypatch, stage, started):
    if stage == "pre_execution":
        fail_availability(search, monkeypatch, certificate_failure())
    elif stage == "job_creation":
        search.service.jobs.create.side_effect = certificate_failure()
    else:
        search.job.results.side_effect = certificate_failure()
    server = mcp_server_for_search(search, monkeypatch)
    async with Client(server) as client:
        result = await client.call_tool(
            search.tool.name, {"query": "index=main"}, raise_on_error=False
        )
    assert result.is_error is True
    structured = result.structured_content
    assert structured["error_code"] == "certificate_verify_failed"
    assert structured["execution_stage"] == stage
    assert structured["search_started"] is started
    if started:
        assert structured["job_id"] == search.job.sid
    assert result.content[0].text == structured["error"]


async def test_unavailable_without_known_cause(search):
    search.context.is_connected = False
    result = await search.tool.execute(search.ctx, query="index=main")
    assert result["error_code"] == "splunk_unavailable"
    assert result["execution_stage"] == "pre_execution"
    assert result["search_started"] is False
    search.service.jobs.create.assert_not_called()


def test_connection_retry_logs_redact_credentials(monkeypatch, caplog):
    monkeypatch.setattr(
        splunk_client.client,
        "connect",
        Mock(side_effect=RuntimeError("splunk_password='private password'")),
    )
    monkeypatch.setenv("SPLUNK_CONNECT_RETRY_COUNT", "1")
    with pytest.raises(RuntimeError):
        splunk_client._connect_with_retry({}, "basic")
    assert "private password" not in caplog.text


def mcp_server_for_search(search, monkeypatch):
    server = FastMCP("search error contract")
    tool_class = type(search.tool)
    monkeypatch.setattr(tool_class, "_get_splunk_context", lambda self, ctx: search.context)
    monkeypatch.setattr(
        tool_class,
        "_resolve_client_config_sync",
        lambda self, ctx: search.tool._resolve_client_config_sync(ctx),
    )
    monkeypatch.setattr(tool_class, "get_client_config_from_context", AsyncMock(return_value={}))
    wrapper = ToolLoader(server)._create_tool_wrapper(tool_class, search.tool.name)
    server.tool(name=search.tool.name)(wrapper)
    return server


@pytest.mark.parametrize(
    "stage,started", [("pre_execution", False), ("job_creation", None), ("result_retrieval", True)]
)
def test_search_error_over_production_http_app(search, monkeypatch, stage, started):
    if stage == "pre_execution":
        fail_availability(search, monkeypatch, certificate_failure())
    elif stage == "job_creation":
        search.service.jobs.create.side_effect = certificate_failure()
    else:
        search.job.results.side_effect = certificate_failure()
    server = mcp_server_for_search(search, monkeypatch)
    monkeypatch.setattr(production_server, "STATELESS_HTTP", True)
    monkeypatch.setattr(production_server, "JSON_RESPONSE", True)
    monkeypatch.setattr(production_server, "_otel_enabled", False)
    monkeypatch.setattr(production_server, "_sentry_enabled", False)
    monkeypatch.setattr(production_server, "load_plugins", lambda *args: None)
    protocol = "2026-07-28"
    with TestClient(
        production_server.create_root_app(server), base_url="http://localhost"
    ) as client:
        response = client.post(
            "/mcp",
            headers={
                "Accept": "application/json, text/event-stream",
                "Mcp-Protocol-Version": protocol,
                "Mcp-Method": "tools/call",
                "Mcp-Name": search.tool.name,
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": search.tool.name,
                    "arguments": {"query": "index=main"},
                    "_meta": {
                        PROTOCOL_VERSION_META_KEY: protocol,
                        CLIENT_CAPABILITIES_META_KEY: {},
                        CLIENT_INFO_META_KEY: {"name": "search-error-test", "version": "1"},
                    },
                },
            },
        )
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["isError"] is True
    fields = result["structuredContent"]
    assert fields["error_code"] == "certificate_verify_failed"
    assert fields["execution_stage"] == stage
    assert fields["search_started"] is started
    if started:
        assert fields["job_id"] == search.job.sid
    assert result["content"][0]["text"] == fields["error"]


@pytest.mark.parametrize("secret", ["first&second", "first;second", "first second"])
async def test_unquoted_password_is_fully_redacted(search, secret, caplog):
    search.service.jobs.create.side_effect = RuntimeError(f"splunk_password={secret}")
    result = await search.tool.execute(search.ctx, query="index=main")
    emitted = json.dumps(result) + caplog.text + str(search.ctx.error.call_args_list)
    assert "first" not in emitted
    assert "second" not in emitted
