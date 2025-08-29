"""
Stop MCP Server (local and Docker) utility.

Stops:
- Local MCP server started via FastMCP (uses PID file if available, else pkill -f)
- Docker deployment via docker compose / docker-compose (runs `down`)
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


# Colors
BLUE = "\033[0;34m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
RESET = "\033[0m"


def info(msg: str) -> None:
    print(f"{BLUE}[INFO]{RESET} {msg}")


def success(msg: str) -> None:
    print(f"{GREEN}[SUCCESS]{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}[WARNING]{RESET} {msg}")


def error(msg: str) -> None:
    print(f"{RED}[ERROR]{RESET} {msg}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="stop-mcp",
        description="Stop MCP server processes running locally and/or via Docker compose.",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Stop only local FastMCP processes (skip Docker)",
    )
    parser.add_argument(
        "--docker-only",
        action="store_true",
        help="Stop only Docker services (skip local)",
    )
    return parser.parse_args(argv)


def compose_cmd() -> list[str] | None:
    if shutil.which("docker") is not None:
        code = subprocess.run(["docker", "compose", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode
        if code == 0:
            return ["docker", "compose"]
    if shutil.which("docker-compose") is not None:
        return ["docker-compose"]
    return None


def stop_docker() -> int:
    # Ensure we're at repo root (same logic as other CLIs)
    base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    os.chdir(base_dir)

    cmd = compose_cmd()
    if not cmd:
        warn("docker-compose or docker compose not found; skipping Docker stop.")
        return 0
    # Check if anything is running first
    ps_quiet = cmd + ["ps", "-q"]
    try:
        out = subprocess.run(ps_quiet, capture_output=True, text=True, check=False)
        running_ids = [l for l in out.stdout.strip().splitlines() if l.strip()]
    except FileNotFoundError:
        running_ids = []

    if not running_ids:
        info("No Docker MCP services appear to be running (compose ps is empty).")
        return 0

    info(f"Stopping Docker services (found {len(running_ids)} running container(s))...")
    full = cmd + ["down"]
    try:
        rc = subprocess.run(full, check=False).returncode
        if rc == 0:
            # Verify after stopping
            out2 = subprocess.run(ps_quiet, capture_output=True, text=True, check=False)
            remaining = [l for l in out2.stdout.strip().splitlines() if l.strip()]
            if remaining:
                warn(f"Some Docker containers may still be running: {len(remaining)}")
            else:
                success("Docker services stopped.")
        else:
            error("Failed to stop some Docker services.")
        return rc
    except FileNotFoundError:
        warn("Docker is not available; skipping Docker stop.")
        return 0


def stop_local() -> int:
    base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    os.chdir(base_dir)

    # Stop by PID file if present
    pid_file = base_dir / ".mcp_local_server.pid"
    inspector_pid_file = base_dir / ".inspector_pid"  # legacy from shell script

    # Detect pre-state
    initial_pids: set[int] = set()
    # From pidfile
    if pid_file.exists():
        try:
            p_str = pid_file.read_text(encoding="utf-8").strip()
            p = int(p_str)
            initial_pids.add(p)
        except (OSError, ValueError):
            pass
    # From pgrep
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
            info(f"Stopping local MCP Server (PID {pid})...")
            os.kill(pid, signal.SIGTERM)
            # Wait briefly for termination
            for _ in range(10):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.3)
                except ProcessLookupError:
                    break
            else:
                warn("Process did not exit after SIGTERM; sending SIGKILL...")
                os.kill(pid, signal.SIGKILL)
            pid_file.unlink(missing_ok=True)
            success("Local MCP Server stopped.")
        except (OSError, ValueError) as e:
            warn(f"Could not stop PID from file: {e}")

    # Stop inspector if present
    if inspector_pid_file.exists():
        try:
            ipid_str = inspector_pid_file.read_text(encoding="utf-8").strip()
            ipid = int(ipid_str)
            info(f"Stopping MCP Inspector (PID {ipid})...")
            os.kill(ipid, signal.SIGTERM)
            inspector_pid_file.unlink(missing_ok=True)
            success("MCP Inspector stop signal sent.")
        except (OSError, ValueError) as e:
            warn(f"Could not stop inspector PID from file: {e}")

    # Additional inspector stop fallbacks (port-based / name-based)
    # If port 6274 is listening, try to identify and kill the owning PID
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        port_open = s.connect_ex(("127.0.0.1", 6274)) == 0
        s.close()
    except OSError:
        port_open = False

    if port_open:
        # lsof method when available
        if shutil.which("lsof"):
            out = subprocess.run(["lsof", "-t", "-i", ":6274"], capture_output=True, text=True, check=False)
            pids = [line.strip() for line in out.stdout.splitlines() if line.strip()]
            for pid_str in pids:
                try:
                    pid = int(pid_str)
                    info(f"Stopping MCP Inspector (port 6274) PID {pid}...")
                    os.kill(pid, signal.SIGTERM)
                    success("MCP Inspector stop signal sent.")
                except (ValueError, OSError):
                    continue
        else:
            # Fallback to name-based termination
            if shutil.which("pkill"):
                info("Trying pkill -f '@modelcontextprotocol/inspector'...")
                subprocess.run(["pkill", "-f", "@modelcontextprotocol/inspector"], check=False)
            elif shutil.which("pgrep") and shutil.which("kill"):
                out = subprocess.run(["pgrep", "-f", "@modelcontextprotocol/inspector"], capture_output=True, text=True, check=False)
                if out.returncode == 0 and out.stdout:
                    for line in out.stdout.strip().splitlines():
                        try:
                            pid = int(line.strip())
                            info(f"Killing Inspector PID {pid} matching '@modelcontextprotocol/inspector'...")
                            os.kill(pid, signal.SIGTERM)
                        except (ValueError, OSError):
                            continue

    # Fall back to pkill if processes still running
    for pat in patterns:
        if shutil.which("pkill") is not None:
            info(f"Trying pkill -f '{pat}'...")
            subprocess.run(["pkill", "-f", pat], check=False)
        else:
            # Fallback: pgrep + kill
            if shutil.which("pgrep") and shutil.which("kill"):
                out = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True, check=False)
                if out.returncode == 0 and out.stdout:
                    for line in out.stdout.strip().splitlines():
                        try:
                            pid = int(line.strip())
                            info(f"Killing PID {pid} matching '{pat}'...")
                            os.kill(pid, signal.SIGTERM)
                        except (ValueError, OSError):
                            continue

    # Verify post-state
    remaining_pids: set[int] = set()
    # Check pidfile pid if still present and alive
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

    initially_running = len(initial_pids)
    now_running = len(remaining_pids)
    stopped_count = max(0, initially_running - now_running)

    if initially_running == 0:
        info("No local MCP processes found.")
        return 0

    if stopped_count > 0:
        success(f"Stopped {stopped_count} local MCP process(es).")
    if now_running > 0:
        warn(f"{now_running} MCP process(es) may still be running: {', '.join(map(str, sorted(remaining_pids)))})")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.local_only and args.docker_only:
        error("Cannot use --local-only and --docker-only together.")
        return 1

    rc_local = 0
    rc_docker = 0

    if not args.docker_only:
        rc_local = stop_local()

    if not args.local_only:
        rc_docker = stop_docker()

    # Prefer non-zero if any failed
    return rc_local or rc_docker


if __name__ == "__main__":
    sys.exit(main())


