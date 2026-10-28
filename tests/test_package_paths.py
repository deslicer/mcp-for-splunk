"""Source launches retain contrib discovery with a proper src package layout."""

import os
import subprocess
import sys
from pathlib import Path

from mcp_server_for_splunk.cli.paths import source_checkout


def test_source_checkout_location():
    assert source_checkout() == Path(__file__).resolve().parents[1]


def test_source_server_keeps_contrib_importable(tmp_path):
    root = Path(__file__).resolve().parents[1]
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_path),
        "PYTHONPATH": str(root / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "FASTMCP_ENV_FILE": os.devnull,
        "PYTHON_DOTENV_DISABLED": "1",
        "MCP_DISABLE_PLUGINS": "true",
    }
    subprocess.run(
        [
            sys.executable,
            "-P",
            "-c",
            (
                "import mcp_server_for_splunk.server; import contrib.tools; "
                "from pathlib import Path; "
                f"assert Path(contrib.tools.__file__).is_relative_to(Path({str(root)!r}))"
            ),
        ],
        cwd=tmp_path,
        env=env,
        check=True,
        timeout=30,
    )


def test_contributor_entrypoints_work_without_repo_on_initial_path(tmp_path):
    root = Path(__file__).resolve().parents[1]
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_path),
        "PYTHONPATH": str(root / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    script = """
import sys
from unittest.mock import patch
from mcp_server_for_splunk.cli.contrib import generate_tool, validate_tools
sys.argv = ['validate-tools', '--help']
assert validate_tools() == 0
with patch('builtins.input', side_effect=KeyboardInterrupt):
    try:
        generate_tool()
    except SystemExit as exc:
        assert exc.code in (0, 1)
"""
    subprocess.run(
        [sys.executable, "-P", "-c", script],
        cwd=tmp_path,
        env=env,
        check=True,
        timeout=30,
    )
