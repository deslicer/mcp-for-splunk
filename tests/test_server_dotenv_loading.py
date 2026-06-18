"""Tests for .env loading before MCP client config extraction."""

import os
import subprocess
import sys
from pathlib import Path


def _run_server_env_probe(cwd: Path, extra_env: dict[str, str] | None = None) -> dict[str, str]:
    """Import server startup path in an isolated subprocess."""
    env = os.environ.copy()
    project_root = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = str(project_root)
    for key in (
        "MCP_SPLUNK_HOST",
        "MCP_SPLUNK_TOKEN",
        "MCP_LOG_LEVEL",
        "SPLUNK_HOST",
        "SPLUNK_USERNAME",
        "SPLUNK_PASSWORD",
        "SPLUNK_TOKEN",
    ):
        env.pop(key, None)
    if extra_env:
        env.update(extra_env)

    script = """
import json
import os
from src.server import LOG_LEVEL_NAME, extract_client_config_from_env

print(json.dumps({
    "log_level": LOG_LEVEL_NAME,
    "config": extract_client_config_from_env(),
    "mcp_log_level_env": os.getenv("MCP_LOG_LEVEL"),
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    import json

    return json.loads(result.stdout.strip())


def test_load_dotenv_before_extract_client_config(tmp_path: Path):
    """MCP_SPLUNK_* values from a cwd .env file must be visible at startup."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "MCP_SPLUNK_HOST=splunk.example.com",
                "MCP_SPLUNK_TOKEN=test-bearer-token",
                "MCP_LOG_LEVEL=WARNING",
            ]
        )
    )

    probe = _run_server_env_probe(tmp_path)

    assert probe["config"] is not None
    assert probe["config"]["splunk_host"] == "splunk.example.com"
    assert probe["config"]["splunk_token"] == "test-bearer-token"
    assert probe["log_level"] == "WARNING"
    assert probe["mcp_log_level_env"] == "WARNING"
