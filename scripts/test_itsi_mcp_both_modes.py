"""Run the full ITSI MCP integration suite against both deployment modes.

This driver:

1. Starts the standalone ``mcp-itsi-server`` on port 8084.
2. Runs the smoke + deep + CRUD scripts against it.
3. Stops the standalone server.
4. Starts the parent ``mcp-for-splunk`` server on port 8085 with the
   ITSI plugin auto-loading via the ``mcp_splunk.plugins.itsi`` entry
   point.
5. Runs the same smoke + deep + CRUD scripts against the parent.
6. Runs the plugin-isolation test against the parent.
7. Stops the parent server.

Each phase prints a header and the script exits non-zero if any
sub-script fails. It is idempotent: the round-trip scripts
auto-cleanup, so repeated runs don't pollute the target ITSI cluster.

Required environment (same as the individual scripts):

    ITSI_HOST, ITSI_USERNAME, ITSI_PASSWORD,
    optional: ITSI_PORT, ITSI_SCHEME, ITSI_VERIFY_SSL
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f"Server at {host}:{port} did not become reachable in {timeout}s")


@contextmanager
def _spawn(cmd: list[str], env: dict[str, str], log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = log_path.open("w")
    proc = subprocess.Popen(
        cmd, env=env, stdout=log, stderr=subprocess.STDOUT, cwd=str(ROOT), preexec_fn=os.setsid
    )
    try:
        yield proc
    finally:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGINT)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
        log.close()


def _run(label: str, cmd: list[str], env: dict[str, str]) -> int:
    print(f"\n--- {label} ---", flush=True)
    print("$", " ".join(cmd), flush=True)
    return subprocess.call(cmd, env=env, cwd=str(ROOT))


def _required_env() -> dict[str, str]:
    base = os.environ.copy()
    for key in ("ITSI_HOST", "ITSI_USERNAME", "ITSI_PASSWORD"):
        if key not in base:
            raise SystemExit(f"missing required env var: {key}")
    return base


def _phase(env: dict[str, str], label: str, url: str, run_isolation: bool) -> int:
    env = {**env, "MCP_ITSI_URL": url}
    failures = 0
    failures += _run(f"{label}: smoke", [sys.executable, str(SCRIPTS / "test_itsi_mcp.py")], env)
    failures += _run(
        f"{label}: deep round-trips",
        [sys.executable, str(SCRIPTS / "test_itsi_mcp_deep.py")],
        env,
    )
    failures += _run(
        f"{label}: CRUD round-trips",
        [sys.executable, str(SCRIPTS / "test_itsi_mcp_crud.py")],
        env,
    )
    if run_isolation:
        failures += _run(
            f"{label}: plugin isolation",
            [sys.executable, str(SCRIPTS / "test_itsi_plugin_isolation.py")],
            env,
        )
    return failures


def main() -> int:
    env = _required_env()
    log_dir = ROOT / "logs" / "test_both_modes"
    failures = 0

    standalone_env = {
        **env,
        "MCP_ITSI_SERVER_HOST": "127.0.0.1",
        "MCP_ITSI_SERVER_PORT": "8084",
        "MCP_ITSI_TRANSPORT": "http",
        "MCP_ITSI_LOG_LEVEL": "INFO",
    }
    print("\n========== STANDALONE MODE ==========", flush=True)
    with _spawn(
        ["uv", "run", "mcp-itsi-server", "--host", "127.0.0.1", "--port", "8084"],
        env=standalone_env,
        log_path=log_dir / "standalone.log",
    ):
        _wait_for_port("127.0.0.1", 8084, timeout=20)
        failures += _phase(env, "standalone", "http://127.0.0.1:8084/mcp", run_isolation=False)

    parent_env = {
        **env,
        "SPLUNK_HOST": env["ITSI_HOST"],
        "SPLUNK_PORT": env.get("ITSI_PORT", "8089"),
        "SPLUNK_SCHEME": env.get("ITSI_SCHEME", "https"),
        "SPLUNK_USERNAME": env["ITSI_USERNAME"],
        "SPLUNK_PASSWORD": env["ITSI_PASSWORD"],
        "SPLUNK_VERIFY_SSL": env.get("ITSI_VERIFY_SSL", "false"),
        "MCP_SERVER_HOST": "127.0.0.1",
        "MCP_SERVER_PORT": "8085",
        "MCP_LOG_LEVEL": "INFO",
        "MCP_STATELESS_HTTP": "true",
        "MCP_JSON_RESPONSE": "true",
        "MCP_AUTH_DISABLED": "true",
        "PHOENIX_ENABLED": "false",
    }
    print("\n========== PLUGIN MODE (mcp-for-splunk + itsi plugin) ==========", flush=True)
    with _spawn(
        [
            "uv",
            "run",
            "python",
            "src/server.py",
            "--host",
            "127.0.0.1",
            "--port",
            "8085",
        ],
        env=parent_env,
        log_path=log_dir / "plugin.log",
    ):
        _wait_for_port("127.0.0.1", 8085, timeout=60)
        failures += _phase(env, "plugin", "http://127.0.0.1:8085/mcp", run_isolation=True)

    print(f"\n--- TOTAL FAILURES: {failures} ---")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
