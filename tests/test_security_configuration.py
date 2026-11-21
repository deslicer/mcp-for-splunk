"""Regression coverage for credential-safe setup and late Sentry initialization."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_server_for_splunk.cli.build_and_run import prompt_splunk_config
from mcp_server_for_splunk.cli.splunk_host_input import normalize_splunk_host
from mcp_server_for_splunk.core.sentry import (
    config,
    context,
    decorators,
    http_middleware,
    mcp_middleware,
)


@pytest.mark.parametrize(
    "value",
    [
        "https://user:secret@host:8089",
        "user:secret@host",
        "https://host/path/secret",
        "https://host?token=secret",
        "https://host#secret",
        "https://host:invalid",
        "https://host\\\\@other",
        "https://ho\nst",
        "https://user%40host",
    ],
)
def test_rejects_sensitive_or_invalid_host_without_echo(value):
    with pytest.raises(ValueError) as error:
        normalize_splunk_host(value)
    assert value not in str(error.value)
    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("splunk.example.com", "splunk.example.com"),
        ("https://splunk.example.com:8089/", "splunk.example.com:8089"),
        ("https://[::1]:8089", "[::1]:8089"),
    ],
)
def test_accepts_host_and_origin(value, expected):
    assert normalize_splunk_host(value) == expected


@pytest.mark.parametrize("from_env", [True, False])
def test_setup_never_displays_or_saves_url_credentials(tmp_path, monkeypatch, capsys, from_env):
    monkeypatch.chdir(tmp_path)
    bad_host = "https://user:unique-secret@host:8089"
    env = tmp_path / ".env"
    original = f"SPLUNK_HOST={'host' if not from_env else bad_host}\nSPLUNK_PASSWORD=other-secret\n"
    env.write_text(original)
    monkeypatch.setattr("builtins.input", lambda _: bad_host)
    assert prompt_splunk_config(False) is False
    assert "unique-secret" not in capsys.readouterr().out
    assert env.read_text() == original


@pytest.mark.parametrize("consumer", [context, decorators, http_middleware, mcp_middleware])
def test_consumers_observe_late_initialization(consumer, monkeypatch):
    monkeypatch.setattr(config, "_sentry_initialized", False)
    assert consumer.is_sentry_initialized() is False
    monkeypatch.setattr(config, "_sentry_initialized", True)
    assert consumer.is_sentry_initialized() is True


def test_span_starts_after_initialization(monkeypatch):
    import sys

    span = Mock()
    sdk = SimpleNamespace(start_span=Mock(return_value=nullcontext(span)))
    monkeypatch.setitem(sys.modules, "sentry_sdk", sdk)
    monkeypatch.setattr(config, "_sentry_initialized", False)
    with context.mcp_span("test", "before"):
        pass
    sdk.start_span.assert_not_called()
    monkeypatch.setattr(config, "_sentry_initialized", True)
    with context.mcp_span("test", "after"):
        pass
    sdk.start_span.assert_called_once()


def test_init_publishes_state_only_after_success(monkeypatch):
    sdk = pytest.importorskip("sentry_sdk")
    monkeypatch.setattr(config, "_sentry_initialized", False)
    monkeypatch.setattr(config, "_sentry_sdk_available", True)
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.com/1")
    initialize = Mock(side_effect=RuntimeError("initialization failed"))
    monkeypatch.setattr(sdk, "init", initialize)
    assert config.init_sentry() is False
    assert context.is_sentry_initialized() is False
    initialize.side_effect = None
    assert config.init_sentry() is True
    assert context.is_sentry_initialized() is True
    assert config.init_sentry() is True
    assert initialize.call_count == 2


def test_password_is_saved_but_never_displayed(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    env = tmp_path / ".env"
    env.write_text("SPLUNK_HOST=host\nSPLUNK_USERNAME=admin\nSPLUNK_PASSWORD=old-secret\n")
    for key in ("SPLUNK_HOST", "SPLUNK_PORT", "SPLUNK_USERNAME", "SPLUNK_PASSWORD"):
        monkeypatch.setenv(key, "")
    answers = iter(["", "", "", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda _: "new-secret")
    assert prompt_splunk_config(False) is True
    output = capsys.readouterr().out
    assert "new-secret" not in output
    assert "old-secret" not in output
    assert "new-secret" in env.read_text()
