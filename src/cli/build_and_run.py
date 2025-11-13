"""
Python CLI replacement for scripts/build_and_run.sh.

Step 1: Provide CLI skeleton with argument parsing, colored output, and
environment checks (uv, Docker). Subsequent steps will implement each shell
feature (local setup, Splunk config, server run, Docker mode, stop, etc.).
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ANSI colors
COLOR_RED = "\033[0;31m"
COLOR_GREEN = "\033[0;32m"
COLOR_YELLOW = "\033[1;33m"
COLOR_BLUE = "\033[0;34m"
COLOR_PURPLE = "\033[0;35m"
COLOR_RESET = "\033[0m"


def print_status(message: str) -> None:
    print(f"{COLOR_BLUE}[INFO]{COLOR_RESET} {message}")


def print_success(message: str) -> None:
    print(f"{COLOR_GREEN}[SUCCESS]{COLOR_RESET} {message}")


def print_warning(message: str) -> None:
    print(f"{COLOR_YELLOW}[WARNING]{COLOR_RESET} {message}")


def print_error(message: str) -> None:
    print(f"{COLOR_RED}[ERROR]{COLOR_RESET} {message}")


def print_local(message: str) -> None:
    print(f"{COLOR_PURPLE}[LOCAL]{COLOR_RESET} {message}")


@dataclass
class CliArgs:
    force_docker: bool
    force_local: bool
    stop: bool
    restart: bool
    detached: bool
    no_inspector: bool
    local_only: bool
    docker_only: bool
    test: bool
    detailed: bool
    setup: bool


def parse_args(argv: list[str] | None = None) -> CliArgs:
    parser = argparse.ArgumentParser(
        prog="build-and-run",
        description=(
            "Build and run MCP Server for Splunk. Either via Docker (full stack) "
            "or local mode (FastMCP server only)."
        ),
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Force Docker deployment (skip prompt)",
        dest="force_docker",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Force local deployment (skip prompt)",
        dest="force_local",
    )
    parser.add_argument(
        "--stop", action="store_true", help="Stop Docker services and clean up", dest="stop"
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help=(
            "Stop any running MCP processes/services, then start local server detached using current .env (no prompts)"
        ),
        dest="restart",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="With --stop: stop only local FastMCP processes (skip Docker)",
        dest="local_only",
    )
    parser.add_argument(
        "--docker-only",
        action="store_true",
        help="With --stop: stop only Docker services (skip local)",
        dest="docker_only",
    )
    parser.add_argument(
        "--detached",
        "-d",
        action="store_true",
        help="Run local server in background (detached). Use with --local or interactive local mode",
        dest="detached",
    )
    parser.add_argument(
        "--no-inspector",
        action="store_true",
        help="Do not auto-start MCP Inspector in local mode",
        dest="no_inspector",
    )
    parser.add_argument(
        "--test",
        "-t",
        action="store_true",
        help="Run MCP server test (standalone or after starting)",
        dest="test",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed output in test (use with --test)",
        dest="detailed",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Force Splunk credential setup prompt (even if .env is configured)",
        dest="setup",
    )

    ns = parser.parse_args(argv)
    return CliArgs(
        force_docker=ns.force_docker,
        force_local=ns.force_local,
        stop=ns.stop,
        restart=ns.restart,
        detached=ns.detached,
        no_inspector=ns.no_inspector,
        local_only=ns.local_only,
        docker_only=ns.docker_only,
        test=ns.test,
        detailed=ns.detailed,
        setup=ns.setup,
    )


def check_uv_available() -> bool:
    return shutil.which("uv") is not None


def check_docker_available() -> bool:
    return shutil.which("docker") is not None


def check_compose_available() -> tuple[bool, list[str]]:
    """Return whether a compose command is available and the base command list.

    Prefers `docker compose`, falls back to `docker-compose`.
    """
    if shutil.which("docker") is not None:
        # Verify `docker compose` subcommand works
        code = subprocess.run(
            ["docker", "compose", "version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        if code == 0:
            return True, ["docker", "compose"]
    if shutil.which("docker-compose") is not None:
        return True, ["docker-compose"]
    return False, []


def show_intro() -> None:
    print("🚀 Building and Running MCP Server for Splunk")
    print("=============================================")
    print()
    print("📚 Need help with prerequisites? See: docs/getting-started/installation.md")
    print()


def interactive_choice() -> str:
    print_status("Both Docker and local development options are available.")
    print("Choose deployment method:")
    print("  1) Docker (full stack with Splunk, Traefik, MCP Inspector)")
    print("  2) Local (FastMCP server only, lighter weight)")
    print()
    choice = input("Enter your choice (1 or 2, default: 1): ").strip() or "1"
    if choice not in {"1", "2"}:
        print_warning("Invalid choice. Using Docker deployment (default).")
        return "docker"
    return "docker" if choice == "1" else "local"


def not_implemented_yet(topic: str) -> int:
    print_error(f"{topic} is not implemented yet in the Python CLI.")
    print_status("We'll implement this functionality in the next steps.")
    return 2


def run_cmd(cmd: list[str], cwd: str | None = None) -> int:
    try:
        print_local(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, check=False)
        return result.returncode
    except FileNotFoundError:
        print_error(f"Command not found: {cmd[0]}")
        return 127


def ensure_logs_dir() -> None:
    logs_dir = Path("logs")
    if not logs_dir.exists():
        print_local("Creating logs directory...")
        logs_dir.mkdir(parents=True, exist_ok=True)


def install_uv_if_missing() -> bool:
    """Attempt to install uv if missing. Returns True if available after attempt."""
    if check_uv_available():
        return True
    print_warning("uv not found. Attempting to install uv...")
    installer = None
    if shutil.which("curl"):
        installer = ["bash", "-lc", "curl -LsSf https://astral.sh/uv/install.sh | sh"]
    elif shutil.which("wget"):
        installer = ["bash", "-lc", "wget -qO- https://astral.sh/uv/install.sh | sh"]
    if installer is None:
        print_error("Neither curl nor wget found. Please install uv manually: pip install uv")
        return False

    code = subprocess.run(installer, check=False).returncode
    # try update PATH for current process
    os.environ["PATH"] = f"{os.path.expanduser('~')}/.cargo/bin:" + os.environ.get("PATH", "")
    if code == 0 and check_uv_available():
        print_success("uv installed successfully!")
        return True
    print_error("Failed to install uv. Please install manually: https://astral.sh/uv")
    return False


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        print_warning("No .env file found. Using system environment variables only.")
        # Show minimal info if present
        sys_host = os.environ.get("SPLUNK_HOST") or os.environ.get("MCP_SPLUNK_HOST")
        if sys_host:
            print_status("📋 System Environment Splunk Configuration:")
            print(f"   🌐 Host: {sys_host}")
        return

    print_local("Loading environment variables from .env file...")
    with env_path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            # Strip quotes
            value = value.strip().strip('"').strip("'")
            os.environ[key] = value

    print_success("Environment variables loaded from .env file!")

    # Show summary (mask passwords)
    print()
    print_status("📋 Splunk Configuration Summary:")
    print(f"   🌐 Host: {os.environ.get('SPLUNK_HOST', 'Not set')}")
    print(f"   🔌 Port: {os.environ.get('SPLUNK_PORT', '8089 (default)')}")
    print(f"   👤 User: {os.environ.get('SPLUNK_USERNAME', 'Not set')}")
    pw = os.environ.get("SPLUNK_PASSWORD")
    pw_display = f"***{pw[-3:]}" if pw else "Not set"
    print(f"   🔐 Pass: {pw_display}")
    print(f"   🔒 SSL:  {os.environ.get('SPLUNK_VERIFY_SSL', 'Not set')}")


def update_env_file(env_path: Path, updates: dict[str, str]) -> None:
    # Create if missing
    if not env_path.exists():
        env_path.write_text("", encoding="utf-8")

    # Read current lines
    with env_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    # Normalize: ensure last line ends with \n to prevent concatenation on append
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    keys = set(updates.keys())
    new_lines: list[str] = []
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            new_lines.append(line)
            continue
        if "=" not in line:
            new_lines.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in keys:
            val = updates[key]
            new_lines.append(f"{key}='{val}'\n")
            keys.remove(key)
        else:
            new_lines.append(line)

    # Append any remaining keys
    for k in keys:
        new_lines.append(f"{k}='{updates[k]}'\n")

    with env_path.open("w", encoding="utf-8") as f:
        f.writelines(new_lines)


def prompt_splunk_config(is_docker_mode: bool) -> bool:
    env_path = Path(".env")

    # Ensure .env exists (seed from env.example if present)
    if not env_path.exists():
        example = Path("env.example")
        if example.exists():
            print_local("Creating .env file from env.example...")
            env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            print_success(".env file created from env.example")
        else:
            print_error("env.example not found. Cannot create .env file.")
            return False

    # Read current values
    current: dict[str, str] = {}
    with env_path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            current[k] = v

    cur_host = current.get("SPLUNK_HOST", "")
    cur_port = current.get("SPLUNK_PORT", "8089")
    cur_user = current.get("SPLUNK_USERNAME", "admin")
    cur_pass = current.get("SPLUNK_PASSWORD", "")

    print()
    print_status("🔧 Splunk Configuration Setup")
    print("==================================")
    print()
    print("Current Splunk configuration:")
    print(f"  Host: {cur_host or 'Not set'}")
    print(f"  Port: {cur_port or '8089'}")
    print(f"  Username: {cur_user or 'admin'}")
    print(f"  Password: {'***' if cur_pass else 'Not set'}")
    print()

    docker_defaults_restored = False
    if is_docker_mode and cur_host and cur_host != "so1":
        print("🚢 Docker Mode Detected:")
        print(f"   Current SPLUNK_HOST ({cur_host}) is different from Docker default (so1)")
        print("   This will use external Splunk instead of the included Docker container")
        print()
        restore = input(
            "Restore Docker defaults (so1) to include Splunk container? (y/N): "
        ).strip()
        if restore.lower() == "y":
            cur_host = "so1"
            cur_port = "8089"
            cur_user = "admin"
            cur_pass = "Chang3d!"
            docker_defaults_restored = True
            print_success(
                "Restored Docker defaults: SPLUNK_HOST=so1, SPLUNK_PORT=8089, SPLUNK_USERNAME=admin, SPLUNK_PASSWORD=Chang3d!"
            )
            print()

    if docker_defaults_restored:
        final_host, final_port, final_user, final_pass = cur_host, cur_port, cur_user, cur_pass
        print_local("Using restored Docker defaults, skipping user input prompts...")
    else:
        # Helper to prompt with enforcement
        def prompt_value(
            label: str,
            current: str,
            display_current: str | None = None,
            default: str | None = None,
            required: bool = True,
            secure_mode: bool = False,
        ) -> str:
            import getpass

            value = current
            display = display_current if display_current is not None else current
            while True:
                if current:
                    p = f"Enter {label} (press Enter to keep current: {display}): "
                else:
                    p = f"Enter {label} (required, current: Not set): "
                if secure_mode:
                    new = getpass.getpass(p)
                else:
                    new = input(p).strip()
                if new:
                    value = new
                elif current:
                    if secure_mode and current:  # Confirm keep for secure fields
                        confirm = input("Keep current value? (y/N): ").strip().lower()
                        if confirm != "y":
                            continue
                    value = current
                elif default:
                    value = default
                if required and not value:
                    print_error(f"{label} is required. Please provide a value.")
                    continue
                return value

        final_host = prompt_value("Splunk host/URL", cur_host)
        final_port = prompt_value("Splunk port", cur_port, default="8089", required=False)
        final_user = prompt_value("Splunk username", cur_user, default="admin")
        try:
            final_pass = prompt_value(
                "Splunk password",
                cur_pass,
                display_current="***" if cur_pass else "",
                required=True,
                secure_mode=True,
            )
        except KeyboardInterrupt:
            print()
            final_pass = cur_pass

        # Strip protocol if URL provided
        if final_host.startswith("http://") or final_host.startswith("https://"):
            final_host = final_host.split("://", 1)[1]
            print_local(f"Extracted hostname from URL: {final_host}")
            print_local(
                "Note: SSL verification setting unchanged (preserves private CA configuration)"
            )

    # Validate
    if not final_host:
        print_error("SPLUNK_HOST is required. Please provide a value.")
        return False
    if not final_user:
        print_error("SPLUNK_USERNAME is required. Please provide a value.")
        return False
    if not final_pass:
        print_error("SPLUNK_PASSWORD is required. Please provide a value.")
        return False

    # Determine whether changes are needed
    has_changes = docker_defaults_restored or any(
        [
            final_host != cur_host,
            final_port != cur_port,
            final_user != cur_user,
            final_pass != cur_pass,
        ]
    )

    print()
    print("Final Splunk configuration:")
    print(f"  Host: {final_host}")
    print(f"  Port: {final_port}")
    print(f"  Username: {final_user}")
    print("  Password: ***")
    print()

    # Note: final_pass contains the actual password value (not masked);
    # the display_current is only for prompt masking, actual value is preserved/updated
    if has_changes:
        if docker_defaults_restored:
            print_status("Automatically updating .env file with restored Docker defaults...")
            update_env_file(
                env_path,
                {
                    "SPLUNK_HOST": final_host,
                    "SPLUNK_PORT": final_port,
                    "SPLUNK_USERNAME": final_user,
                    "SPLUNK_PASSWORD": final_pass,
                },
            )
            print_success(".env file updated successfully with Docker defaults!")
        else:
            confirm = input("Update .env file with these settings? (y/N): ").strip().lower()
            if confirm == "y":
                update_env_file(
                    env_path,
                    {
                        "SPLUNK_HOST": final_host,
                        "SPLUNK_PORT": final_port,
                        "SPLUNK_USERNAME": final_user,
                        "SPLUNK_PASSWORD": final_pass,
                    },
                )
                print_success(".env file updated successfully!")
            else:
                print_warning("Configuration update cancelled. Using existing values.")

    # Export for current session
    os.environ["SPLUNK_HOST"] = final_host
    os.environ["SPLUNK_PORT"] = final_port
    os.environ["SPLUNK_USERNAME"] = final_user
    os.environ["SPLUNK_PASSWORD"] = final_pass
    print_success("Splunk configuration loaded for current session.")
    return True


def setup_local_env(force_setup: bool = False) -> int:
    print_local("Setting up local development environment...")

    if not install_uv_if_missing():
        return 1

    # Create or sync venv
    venv_cfg = Path(".venv/pyvenv.cfg")
    uv_lock = Path("uv.lock")
    pyproject = Path("pyproject.toml")

    if (
        (not venv_cfg.exists())
        or (uv_lock.exists() and uv_lock.stat().st_mtime > venv_cfg.stat().st_mtime)
        or (pyproject.stat().st_mtime > venv_cfg.stat().st_mtime)
    ):
        print_local("Creating/updating virtual environment and installing dependencies...")
        code = run_cmd(["uv", "sync", "--dev"])
        if code != 0:
            return code
    else:
        print_local("Virtual environment is up to date.")

    # Ensure .env exists
    env_path = Path(".env")
    was_existing = env_path.exists()
    if not was_existing:
        print_warning(".env file not found. Creating from env.example...")
        example = Path("env.example")
        if example.exists():
            env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            print_warning("Created .env file from env.example.")
            print_status("Prompting for Splunk configuration to customize...")
        else:
            print_warning("env.example not found. Proceeding without .env.")

    # Check if prompting is needed
    if not force_setup and was_existing:
        # Read current .env to check key vars
        current: dict[str, str] = {}
        if env_path.exists():
            with env_path.open("r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    v = v.strip().strip('"').strip("'")
                    current[k] = v

        has_host = bool(current.get("SPLUNK_HOST", "").strip())
        has_user = bool(current.get("SPLUNK_USERNAME", "").strip())
        has_pass = bool(current.get("SPLUNK_PASSWORD", "").strip())

        if has_host and has_user and has_pass:
            print_status("Splunk configuration in .env looks complete. Skipping setup prompt.")
            load_env_file(env_path)
            print_success("Local environment setup complete!")
            return 0

    # Prompt and load configuration if needed or forced
    if not prompt_splunk_config(is_docker_mode=False):
        return 1
    load_env_file(env_path)

    print_success("Local environment setup complete!")
    return 0


def find_available_port(start_port: int, attempts: int = 10) -> int:
    import socket

    port = start_port
    for _ in range(attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            result = s.connect_ex(("127.0.0.1", port))
            if result != 0:  # non-zero means connection failed => likely free
                return port
        port += 1
        print_local(f"Port {port - 1} is in use, trying next port...")
    print_warning(f"Could not find an available port after {attempts} attempts")
    return start_port


def is_port_listening(port: int) -> bool:
    import socket

    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def print_access_points(mcp_port: int) -> None:
    print()
    print_status("📋 Access Points:")
    print(f"   🔌 MCP Server (HTTP):  http://localhost:{mcp_port}")
    print(f"   🔌 MCP Server API:     http://localhost:{mcp_port}/mcp/")
    print(f"   🩺 MCP Health Dashboard: http://localhost:{mcp_port}")


def start_mcp_inspector(mcp_port: int) -> bool:
    """Start MCP Inspector (Node 22+ required). Returns True if available/running."""
    # If already running on 6274, reuse
    if is_port_listening(6274):
        print_warning("MCP Inspector appears to already be running on port 6274")
        print_success("Using existing MCP Inspector instance")
        return True

    if shutil.which("node") is None or shutil.which("npx") is None:
        print_warning("Node.js/npx not found. MCP Inspector will not be available.")
        return False

    # Check Node version
    out = subprocess.run(["node", "--version"], capture_output=True, text=True, check=False)
    version = out.stdout.strip().lstrip("v")
    try:
        major = int(version.split(".")[0]) if version else 0
    except ValueError:
        major = 0

    if major < 22:
        print_warning(
            f"Node.js v{version or 'unknown'} detected, but MCP Inspector requires Node.js 22+."
        )
        return False

    print_local("Node.js v22+ detected. Starting MCP Inspector...")

    ensure_logs_dir()
    inspector_url = f"http://localhost:{mcp_port}/mcp/"
    env = os.environ.copy()
    env["DANGEROUSLY_OMIT_AUTH"] = "true"
    env["MCP_AUTO_OPEN_ENABLED"] = "false"

    cmd = [
        "npx",
        "--yes",
        "@modelcontextprotocol/inspector@0.16.5",
        "--transport",
        "streamable-http",
        "--server-url",
        inspector_url,
    ]

    log_file = Path("logs/inspector.log")
    try:
        with log_file.open("w", encoding="utf-8") as lf:
            proc = subprocess.Popen(cmd, stdout=lf, stderr=lf, env=env)
    except FileNotFoundError:
        print_warning("Failed to start MCP Inspector (npx not available).")
        return False

    # Wait for readiness
    attempts = 0
    max_attempts = 10
    ready = False
    import time

    try:
        import httpx  # lightweight dependency already in project

        while attempts < max_attempts:
            try:
                r = httpx.get("http://localhost:6274", timeout=2.0)
                if r.status_code < 500:
                    ready = True
                    break
            except httpx.HTTPError:
                pass
            attempts += 1
            time.sleep(1)
    except ImportError:
        # Fallback: port check
        while attempts < max_attempts and not is_port_listening(6274):
            attempts += 1
            time.sleep(1)
        ready = is_port_listening(6274)

    # Persist PID for stop_mcp
    Path(".inspector_pid").write_text(str(proc.pid), encoding="utf-8")

    if ready:
        print_success("MCP Inspector started successfully on port 6274 and is accessible!")
        return True
    else:
        print_warning("MCP Inspector may not be fully ready yet. Check logs: logs/inspector.log")
        return False


def run_local_server(
    detached: bool = False,
    skip_inspector: bool = False,
    run_test: bool = False,
    detailed: bool = False,
) -> int:
    # Ensure any existing local processes are stopped first
    print_status("Checking for and stopping any existing local MCP processes...")
    stop_local_processes()

    print_local("Starting MCP server locally with FastMCP CLI...")

    if not install_uv_if_missing():
        return 1

    ensure_logs_dir()

    preferred_port_str = os.environ.get("MCP_SERVER_PORT", "8003")
    try:
        preferred_port = int(preferred_port_str)
    except ValueError:
        preferred_port = 8003

    print_local(f"Preferred port from MCP_SERVER_PORT: {preferred_port}")
    mcp_port = find_available_port(preferred_port)
    if mcp_port != preferred_port:
        print_warning(f"Port {preferred_port} is in use. Using port {mcp_port} instead.")
    else:
        print_local(f"Using port {mcp_port} for MCP server.")

    log_file = Path("logs/mcp_splunk_server.log")
    # Preflight: ensure fastmcp is importable; if not, install
    test_code = subprocess.run(
        ["uv", "run", "python", "-c", "import fastmcp; print('ok')"],
        capture_output=True,
        text=True,
        check=False,
    )
    if test_code.returncode != 0:
        print_local("FastMCP import failed. Installing fastmcp...")
        add_code = run_cmd(["uv", "add", "fastmcp"])
        if add_code != 0:
            print_warning(
                "Failed to add fastmcp via uv; continuing, it may already be present via sync."
            )
        run_cmd(["uv", "sync", "--dev"])  # best-effort
    cmd = [
        "uv",
        "run",
        "fastmcp",
        "run",
        "src/server.py",
        "--transport",
        "http",
        "--port",
        str(mcp_port),
    ]
    print_local(f"Command: {' '.join(cmd)}")

    # Start server
    # Ensure local defaults for HTTP stateless mode and JSON responses for compatibility
    child_env = os.environ.copy()
    child_env.setdefault("MCP_STATELESS_HTTP", "true")
    child_env.setdefault("MCP_JSON_RESPONSE", "true")
    print_local(
        f"Setting env for local run: MCP_STATELESS_HTTP={child_env.get('MCP_STATELESS_HTTP')}, MCP_JSON_RESPONSE={child_env.get('MCP_JSON_RESPONSE')}"
    )
    with log_file.open("w", encoding="utf-8") as lf:
        proc = subprocess.Popen(cmd, stdout=lf, stderr=lf, start_new_session=True, env=child_env)

    # Always write PID file for monitoring/testing
    pid_file = Path(".mcp_local_server.pid")
    pid_file.write_text(str(proc.pid), encoding="utf-8")
    print_local(f"Server PID: {proc.pid} (written to {pid_file})")

    print_local("Waiting for MCP server to start...")
    import time

    time.sleep(3)

    if proc.poll() is not None:
        print_error("MCP server failed to start. Check the logs:")
        if log_file.exists():
            print_error("=== MCP Server Log (last 50 lines) ===")
            try:
                lines = log_file.read_text(encoding="utf-8").splitlines()[-50:]
                for line in lines:
                    print_error(line)
            except (OSError, UnicodeDecodeError):
                print_error("(failed to read log file)")
        # Cleanup PID on early failure
        pid_file.unlink(missing_ok=True)
        return 1

    # Check port listening up to 5 attempts
    attempts = 0
    max_attempts = 5
    server_listening = False
    while attempts < max_attempts:
        if is_port_listening(mcp_port):
            server_listening = True
            break
        time.sleep(2)
        attempts += 1
        print_local(f"Port check attempt {attempts}/{max_attempts}...")

    if not server_listening:
        print_error(f"MCP server is not listening on port {mcp_port}")
        print_error(f"Server process ID: {proc.pid}")
        if log_file.exists():
            print_error("=== MCP Server Log (last 20 lines) ===")
            try:
                lines = log_file.read_text(encoding="utf-8").splitlines()[-20:]
                for line in lines:
                    print_error(line)
            except (OSError, UnicodeDecodeError):
                print_error("(failed to read log file)")
        # Try foreground restart for debugging
        if proc.poll() is None:
            proc.terminate()
        print_error("Attempting to run server in foreground for debugging...")
        # Cleanup PID on failure
        pid_file.unlink(missing_ok=True)
        return run_cmd(cmd)

    print_success(f"MCP server is listening on port {mcp_port}!")
    print_status("🎉 Local MCP Server Ready!")
    print_access_points(mcp_port)

    print()
    print_status("📊 Log Files:")
    print("   📄 MCP Server:    logs/mcp_splunk_server.log")

    # Start MCP Inspector (best-effort)
    started_inspector = False
    if skip_inspector:
        print_warning("Skipping MCP Inspector auto-start (flag --no-inspector).")
    else:
        started_inspector = start_mcp_inspector(mcp_port)
        if started_inspector:
            print("   📊 MCP Inspector:     http://localhost:6274")
            print("   📄 MCP Inspector: logs/inspector.log")

    # Detached mode: exit after start
    if detached:
        print()
        print_success(f"✅ Local server is running detached (PID {proc.pid}).")
        print_access_points(mcp_port)
        if started_inspector:
            print("   📊 MCP Inspector:     http://localhost:6274")
        print()
        print_status("🛑 To stop the server:")
        print("   uv run mcp-server --stop")

        if run_test:
            print_status("Running MCP server test...")
            test_cmd = ["uv", "run", "python", "src/cli/test_mcp_server.py"]
            if detailed:
                test_cmd.append("--detailed")
            run_cmd(test_cmd)

        return 0  # Exit main script immediately after starting detached and optional test

    print()
    print_status("🛑 To stop the server: press Ctrl+C")
    print_local("Monitoring server; press Ctrl+C to stop.")
    # Always re-print access points as the final lines for easy copy/paste
    print_access_points(mcp_port)

    try:
        while proc.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        print_local("Stopping MCP Server...")
        if proc.poll() is None:
            proc.terminate()
            # Wait for up to 10 seconds for graceful shutdown
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print_warning("Process did not exit gracefully; sending SIGKILL...")
                proc.kill()
        # Ensure inspector and pid artifacts are cleaned up on Ctrl+C
        try:
            stop_local_processes()
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
        # Cleanup PID file
        pid_file.unlink(missing_ok=True)
        return 0

    # Handle natural process exit (e.g., crash or manual kill)
    print_error("MCP server process exited unexpectedly.")
    if log_file.exists():
        print_error("=== Recent server logs (last 10 lines) ===")
        try:
            lines = log_file.read_text(encoding="utf-8").splitlines()[-10:]
            for line in lines:
                print_error(line)
        except (OSError, UnicodeDecodeError):
            print_error("(failed to read log file)")
    # Cleanup
    try:
        stop_local_processes()
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    # Cleanup PID file
    pid_file.unlink(missing_ok=True)
    return proc.returncode or 1


def stop_docker_services() -> int:
    print_status("Stopping Docker services for this project (compose files only)...")
    available, base_cmd = check_compose_available()
    if not available:
        print_warning("docker-compose or docker compose not found; skipping Docker stop.")
        return 0

    # Limit scope strictly to known compose files in this repo
    compose_files = [
        "docker-compose-dev.yml",
        "docker-compose.yml",
        "docker-compose-splunk.yml",
    ]

    any_found = False
    overall_rc = 0

    service_map: dict[str, list[str]] = {
        "docker-compose-dev.yml": ["traefik", "mcp-inspector", "mcp-server-dev"],
        "docker-compose.yml": ["traefik", "mcp-inspector", "mcp-server", "so1"],
        "docker-compose-splunk.yml": ["so1"],
    }

    for cf in compose_files:
        if not Path(cf).exists():
            continue
        any_found = True
        # Discover running services for this compose file only
        ps_services_cmd = base_cmd + ["-f", cf, "ps", "--services", "--filter", "status=running"]
        try:
            out = subprocess.run(ps_services_cmd, capture_output=True, text=True, check=False)
            running_services = [line for line in out.stdout.strip().splitlines() if line.strip()]
        except FileNotFoundError:
            running_services = []

        if not running_services:
            print_status(f"No running containers for {cf}. Skipping 'down'.")
            continue

        # Restrict to known/expected services for this project, intersection with running
        expected = set(service_map.get(cf, []))
        targets = [s for s in running_services if s in expected]
        if not targets:
            print_status(
                f"{cf}: Running services not recognized as project services: {running_services or '[]'}"
            )
            continue

        print_status(f"Stopping services in {cf}: {', '.join(targets)}")
        rc = run_cmd(base_cmd + ["-f", cf, "stop", *targets])
        if rc != 0:
            print_error(f"Failed to stop one or more services for {cf}.")
            overall_rc = rc
            continue

        # Verify after stopping targets
        out2 = subprocess.run(ps_services_cmd, capture_output=True, text=True, check=False)
        remaining_services = [line for line in out2.stdout.strip().splitlines() if line.strip()]
        remaining_expected = [s for s in remaining_services if s in expected]
        if remaining_expected:
            print_warning(
                f"{cf}: Some project services still running: {', '.join(remaining_expected)}"
            )
        else:
            print_success(f"{cf}: Project services stopped.")

    if not any_found:
        print_status("No compose files found to stop (nothing to do).")

    return overall_rc


def stop_local_processes() -> int:
    base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    os.chdir(base_dir)

    # Stop by PID file if present
    pid_file = base_dir / ".mcp_local_server.pid"
    inspector_pid_file = base_dir / ".inspector_pid"

    # Detect initial processes
    initial_pids: set[int] = set()
    if pid_file.exists():
        try:
            p_str = pid_file.read_text(encoding="utf-8").strip()
            p = int(p_str)
            initial_pids.add(p)
        except (OSError, ValueError):
            pass

    patterns = [
        "fastmcp run src/server.py",
        "fastmcp run",
    ]
    for pat in patterns:
        if shutil.which("pgrep") is not None:
            out = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True, check=False)
            if out.returncode == 0 and out.stdout:
                for line in out.stdout.strip().splitlines():
                    try:
                        initial_pids.add(int(line.strip()))
                    except ValueError:
                        continue

    if pid_file.exists():
        try:
            pid_str = pid_file.read_text(encoding="utf-8").strip()
            pid = int(pid_str)
            print_status(f"Stopping local MCP Server (PID {pid})...")
            os.kill(pid, signal.SIGTERM)
            # Wait briefly for termination
            for _ in range(10):
                try:
                    os.kill(pid, 0)
                    import time as _t

                    _t.sleep(0.3)
                except ProcessLookupError:
                    break
            else:
                print_warning("Process did not exit after SIGTERM; sending SIGKILL...")
                os.kill(pid, signal.SIGKILL)
            pid_file.unlink(missing_ok=True)
            print_success("Local MCP Server stopped.")
        except (OSError, ValueError) as e:
            print_warning(f"Could not stop PID from file: {e}")

    # Stop inspector if present
    if inspector_pid_file.exists():
        try:
            ipid_str = inspector_pid_file.read_text(encoding="utf-8").strip()
            ipid = int(ipid_str)
            print_status(f"Stopping MCP Inspector (PID {ipid})...")
            os.kill(ipid, signal.SIGTERM)
            # Wait briefly for inspector termination
            for _ in range(10):
                try:
                    os.kill(ipid, 0)
                    import time as _t

                    _t.sleep(0.3)
                except ProcessLookupError:
                    break
            else:
                print_warning("Inspector did not exit after SIGTERM; sending SIGKILL...")
                os.kill(ipid, signal.SIGKILL)
            inspector_pid_file.unlink(missing_ok=True)
            print_success("MCP Inspector stopped.")
        except (OSError, ValueError) as e:
            # If the process is already gone or PID invalid, still remove stale pid file
            print_warning(f"Could not stop inspector PID from file: {e}")
            inspector_pid_file.unlink(missing_ok=True)
            print_status("Removed stale .inspector_pid file.")

    # Additional inspector stop attempts for port 6274
    try:
        import socket as _socket

        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        s.settimeout(0.2)
        port_open = s.connect_ex(("127.0.0.1", 6274)) == 0
        s.close()
    except OSError:
        port_open = False

    if port_open:
        if shutil.which("lsof"):
            out = subprocess.run(
                ["lsof", "-t", "-i", ":6274"], capture_output=True, text=True, check=False
            )
            pids = [line.strip() for line in out.stdout.splitlines() if line.strip()]
            for pid_str in pids:
                try:
                    pid = int(pid_str)
                    print_status(f"Stopping MCP Inspector (port 6274) PID {pid}...")
                    os.kill(pid, signal.SIGTERM)
                    print_success("MCP Inspector stop signal sent.")
                except (ValueError, OSError):
                    continue
        else:
            if shutil.which("fuser"):
                print_status("Using fuser to kill processes on port 6274...")
                subprocess.run(["fuser", "-k", "6274/tcp"], check=False)
            elif shutil.which("pkill"):
                print_status("Trying pkill -f '@modelcontextprotocol/inspector'...")
                subprocess.run(["pkill", "-f", "@modelcontextprotocol/inspector"], check=False)
            elif shutil.which("pgrep") and shutil.which("kill"):
                out = subprocess.run(
                    ["pgrep", "-f", "@modelcontextprotocol/inspector"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if out.returncode == 0 and out.stdout:
                    for line in out.stdout.strip().splitlines():
                        try:
                            pid = int(line.strip())
                            print_status(
                                f"Killing Inspector PID {pid} matching '@modelcontextprotocol/inspector'..."
                            )
                            os.kill(pid, signal.SIGTERM)
                        except (ValueError, OSError):
                            continue

        # After attempting to stop inspector by port/name, remove stale pid file if present
        inspector_pid_file.unlink(missing_ok=True)

    # Fall back to pkill for fastmcp patterns
    for pat in patterns:
        if shutil.which("pkill") is not None:
            print_status(f"Trying pkill -f '{pat}'...")
            subprocess.run(["pkill", "-f", pat], check=False)
        else:
            if shutil.which("pgrep") and shutil.which("kill"):
                out = subprocess.run(
                    ["pgrep", "-f", pat], capture_output=True, text=True, check=False
                )
                if out.returncode == 0 and out.stdout:
                    for line in out.stdout.strip().splitlines():
                        try:
                            pid = int(line.strip())
                            print_status(f"Killing PID {pid} matching '{pat}'...")
                            os.kill(pid, signal.SIGTERM)
                        except (ValueError, OSError):
                            continue

    # Small grace period to allow processes to exit cleanly before verification
    try:
        import time as _t

        _t.sleep(0.5)
    except (ImportError, RuntimeError, OSError):
        pass

    # Verify post-state
    remaining_pids: set[int] = set()
    if pid_file.exists():
        try:
            p_str = pid_file.read_text(encoding="utf-8").strip()
            p = int(p_str)
            remaining_pids.add(p)
        except (OSError, ValueError):
            pass
    for pat in patterns:
        if shutil.which("pgrep") is not None:
            out = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True, check=False)
            if out.returncode == 0 and out.stdout:
                for line in out.stdout.strip().splitlines():
                    try:
                        remaining_pids.add(int(line.strip()))
                    except ValueError:
                        continue

    # Confirm candidates are truly alive (avoid false positives from zombie/exited processes)
    alive_remaining: set[int] = set()
    for pid in list(remaining_pids):
        try:
            os.kill(pid, 0)  # raises ProcessLookupError if not running
            alive_remaining.add(pid)
        except ProcessLookupError:
            continue
        except PermissionError:
            # If we lack permission, assume it's alive to be safe
            alive_remaining.add(pid)

    initially_running = len(initial_pids)
    now_running = len(alive_remaining)
    stopped_count = max(0, initially_running - now_running)

    if initially_running == 0:
        print_status("No local MCP processes found.")
        return 0

    if stopped_count > 0:
        print_success(f"Stopped {stopped_count} local MCP process(es).")
    if now_running > 0:
        print_warning(
            f"{now_running} MCP process(es) may still be running: {', '.join(map(str, sorted(alive_remaining)))}"
        )
    return 0


def run_docker_setup(run_test: bool = False) -> int:
    print_status("Using Docker deployment mode...")

    # Ensure compose available
    available, base_cmd = check_compose_available()
    if not available:
        print_error("docker-compose or docker compose not found. Please install or use local mode.")
        print_error("To install docker-compose: https://docs.docker.com/compose/install/")
        return 1

    # If uv exists (install if missing), ensure uv.lock is up to date
    if install_uv_if_missing():
        print_status("uv detected. Ensuring uv.lock is up to date for Docker build...")
        uv_lock = Path("uv.lock")
        pyproject = Path("pyproject.toml")
        if (not uv_lock.exists()) or (pyproject.stat().st_mtime > uv_lock.stat().st_mtime):
            print_status("Updating uv.lock file...")
            code = run_cmd(["uv", "sync", "--dev"])
            if code != 0:
                return code
            print_success("uv.lock updated successfully!")
        else:
            print_status("uv.lock is already up to date.")
    else:
        print_warning("uv not found. Docker will use existing uv.lock file (if present).")

    # Ensure .env exists
    env_path = Path(".env")
    if not env_path.exists():
        print_warning(".env file not found. Creating from env.example...")
        example = Path("env.example")
        if example.exists():
            env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            print_warning(
                "Created .env file. You may want to edit it with your Splunk configuration."
            )
        else:
            print_warning("env.example not found. Proceeding without .env.")

    # Prompt for Splunk configuration with Docker mode enabled
    prompt_splunk_config(is_docker_mode=True)
    load_env_file(env_path)

    # Choose mode
    print()
    print_status("Choose Docker deployment mode:")
    print("  1) Production (default) - Optimized for performance, no hot reload")
    print("  2) Development - Hot reload enabled, enhanced debugging")
    print()
    docker_choice = input("Enter your choice (1 or 2, default: 1): ").strip() or "1"
    docker_mode = "prod" if docker_choice == "1" else "dev"
    service_name = "mcp-server" if docker_mode == "prod" else "mcp-server-dev"

    # Compose command with file selection
    compose_cmd = base_cmd[:]
    if docker_mode == "dev":
        compose_cmd += ["-f", "docker-compose-dev.yml"]

    # Build
    print_status("Building Docker image...")
    code = run_cmd(compose_cmd + ["build", service_name])
    if code != 0:
        print_error("Failed to build Docker image")
        return code
    print_success("Docker image built successfully!")

    # Up
    print_status("Starting services with docker compose...")
    code = run_cmd(compose_cmd + ["up", "-d"])
    if code != 0:
        print_error("Failed to start services")
        return code
    print_success("Services started successfully!")

    # Brief wait and status
    import time

    time.sleep(5)
    print_status("Checking service status...")
    run_cmd(compose_cmd + ["ps"])  # best-effort

    # Show service URLs
    print()
    print_success("🎉 Docker setup complete!")
    print()
    print_status("📋 Service URLs:")
    print("   🔧 Traefik Dashboard: http://localhost:8080")
    if os.environ.get("SPLUNK_HOST", "") in ("", "so1"):
        print("   🌐 Splunk Web UI:     http://localhost:9000 (admin/Chang3d!)")
    else:
        print(f"   🌐 External Splunk:   {os.environ.get('SPLUNK_HOST')}")
    print(
        f"   🔌 MCP Server:        http://localhost:{os.environ.get('MCP_SERVER_PORT', '8001')}/mcp/"
    )
    print(
        f"   🩺 MCP Health Dashboard: http://localhost:{os.environ.get('MCP_SERVER_PORT', '8001')}"
    )
    print("   📊 MCP Inspector:     http://localhost:6274")
    print()
    print_status("🔍 To check logs:")
    print("   " + " ".join(compose_cmd + ["logs", "-f", service_name]))
    print("   " + " ".join(compose_cmd + ["logs", "-f", "mcp-inspector"]))
    print()
    print_status("🛑 To stop all services:")
    print("   " + " ".join(compose_cmd + ["down"]))

    if docker_mode == "dev":
        print()
        print_status("🚀 Development Mode Features:")
        print("   • Hot reload enabled - changes sync automatically")
        print("   • Enhanced debugging and logging")
        print("   • Use: " + " ".join(compose_cmd + ["logs", "-f", service_name]))

    if run_test:
        print_status("Running MCP server test...")
        test_cmd = ["uv", "run", "python", "src/cli/test_mcp_server.py", "--detailed"]
        run_cmd(test_cmd)

    return 0


def main(argv: list[str] | None = None) -> int:
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    show_intro()

    args = parse_args(argv)

    docker_available = check_docker_available()
    uv_available = check_uv_available()

    if docker_available:
        print_success("Docker is available and may be running.")
    else:
        print_warning("Docker is not available.")

    if uv_available:
        print_success("uv package manager is available.")
    else:
        print_warning("uv package manager is not available.")

    # Handle standalone --test first (no startup)
    if args.test and not (args.force_docker or args.force_local or args.restart or args.stop):
        print_status("Running standalone MCP server test...")
        test_cmd = ["uv", "run", "python", "src/cli/test_mcp_server.py"]
        if args.detailed:
            test_cmd.append("--detailed")
        return run_cmd(test_cmd)

    # Handle forced modes first
    if args.stop:
        if args.local_only and args.docker_only:
            print_error("Cannot use --local-only and --docker-only together.")
            return 1

        rc_local = 0
        rc_docker = 0

        if not args.docker_only:
            rc_local = stop_local_processes()
        if not args.local_only:
            rc_docker = stop_docker_services()

        # Prefer non-zero if any failed
        return rc_local or rc_docker

    if args.restart:
        # Stop everything, then start local server in detached mode using existing .env strictly
        print_status("Restart requested: stopping running services/processes first...")
        rc_local = stop_local_processes()
        rc_docker = stop_docker_services()
        if rc_local or rc_docker:
            print_warning("Some components may not have stopped cleanly; continuing with restart.")

        # Ensure uv available for local run
        if not check_uv_available() and not install_uv_if_missing():
            print_error("uv package manager is required for local restart.")
            return 1

        # Strictly use current .env without prompts
        env_path = Path(".env")
        if not env_path.exists():
            print_error(".env file is required for --restart. Please create it first.")
            return 1
        print_local("Loading existing .env without prompting...")
        load_env_file(env_path)

        # Start local server detached and skip inspector only if user requested via flag
        return run_local_server(
            detached=True,
            skip_inspector=args.no_inspector,
            run_test=args.test,
            detailed=args.detailed,
        )

    if args.force_docker and args.force_local:
        print_error("Cannot force both --docker and --local. Choose one.")
        return 1

    if args.force_docker:
        if not docker_available:
            print_error("Docker deployment requested but Docker is not available.")
            print_error("Please start Docker or install Docker first.")
            return 1
        print_status("Forcing Docker deployment as requested...")
        return run_docker_setup(run_test=args.test)

    if args.force_local:
        if not uv_available:
            print_error("Local deployment requested but uv package manager is not available.")
            print_error("Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh")
            return 1
        print_status("Forcing local deployment as requested...")
        code = setup_local_env(force_setup=args.setup)
        if code != 0:
            return code
        return run_local_server(
            detached=args.detached,
            skip_inspector=args.no_inspector,
            run_test=args.test,
            detailed=args.detailed,
        )

    # Interactive mode selection
    if docker_available and uv_available:
        selected = interactive_choice()
        if selected == "docker":
            return run_docker_setup(run_test=args.test)
        else:
            code = setup_local_env(force_setup=args.setup)
            if code != 0:
                return code
            # If not explicitly detached by flag, ask interactively
            local_detached = args.detached
            if not local_detached:
                ans = (
                    input("Run local server detached (background)? (y/N): ").strip() or "n"
                ).lower()
                local_detached = ans == "y"
            return run_local_server(
                detached=local_detached,
                skip_inspector=args.no_inspector,
                run_test=args.test,
                detailed=args.detailed,
            )

    if docker_available:
        print_status("Only Docker is available. Using Docker deployment...")
        return run_docker_setup(run_test=args.test)

    if uv_available:
        print_status("Only local development is available. Setting up local mode...")
        code = setup_local_env(force_setup=args.setup)
        if code != 0:
            return code
        # If not explicitly detached by flag, ask interactively
        local_detached = args.detached
        if not local_detached:
            ans = (input("Run local server detached (background)? (y/N): ").strip() or "n").lower()
            local_detached = ans == "y"
        return run_local_server(
            detached=local_detached,
            skip_inspector=args.no_inspector,
            run_test=args.test,
            detailed=args.detailed,
        )

    print_error("Neither Docker nor uv package manager are available.")
    print_error("Please install one of the following:")
    print_error("1. Docker: https://docs.docker.com/get-docker/")
    print_error("2. uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
    print()
    print_error("📚 For detailed installation instructions, see:")
    print_error("   docs/getting-started/installation.md")
    print_error("")
    print_error("🔧 You can also run our prerequisite checker to see what's missing:")
    print_error("   ./scripts/check-prerequisites.sh")
    return 1


if __name__ == "__main__":
    sys.exit(main())
