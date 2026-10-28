"""Check the built wheel outside the checkout, including real MCP tool calls."""

import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def main() -> None:
    wheel = Path(sys.argv[1]).resolve()
    probe = Path(__file__).with_name("_installed_wheel_probe.py").resolve()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        installed = root / "installed"
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            assert not any(
                name.startswith("src/") for name in names
            ), "The wheel must not install a top-level src package"
            assert "mcp_server_for_splunk/server.py" in names
            assert "mcp_server_for_splunk/bundled_docs/dashboard_studio_cheatsheet.md" in names
            archive.extractall(installed)
        if len(sys.argv) > 2:
            with zipfile.ZipFile(Path(sys.argv[2]).resolve()) as archive:
                archive.extractall(installed)
        # An unrelated distribution is allowed to own the generic src name.
        collision = installed / "src"
        collision.mkdir()
        (collision / "__init__.py").write_text(
            "raise RuntimeError('The MCP wheel imported another distribution src package')\n"
        )
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": directory,
            "PYTHONPATH": str(installed),
            "PYTHONDONTWRITEBYTECODE": "1",
            "FASTMCP_ENV_FILE": os.devnull,
            "PYTHON_DOTENV_DISABLED": "1",
            "MCP_DISABLE_PLUGINS": "true",
            "MCP_DEFAULT_TOOLSETS": "splunk,itsi",
            "SPLUNK_CONNECT_RETRY_COUNT": "1",
            "SPLUNK_CONNECT_RETRY_BASE_DELAY": "0",
        }
        if len(sys.argv) > 2:
            subprocess.run(
                [
                    sys.executable,
                    "-P",
                    "-c",
                    (
                        "import mcp_itsi.config.headers; import sys; "
                        "assert 'mcp_server_for_splunk' not in sys.modules; "
                        "assert 'src' not in sys.modules"
                    ),
                ],
                cwd=root,
                env=env,
                check=True,
                timeout=30,
            )
            env["MCP_DISABLE_PLUGINS"] = "false"
        subprocess.run(
            [sys.executable, "-P", str(probe), str(installed)],
            cwd=root,
            env=env,
            check=True,
            timeout=60,
        )
        assert not (installed / "logs").exists(), "Do not write logs into site-packages"
    print("Wheel namespace, bundled assets, entry point, and MCP search smoke checks passed")


if __name__ == "__main__":
    main()
