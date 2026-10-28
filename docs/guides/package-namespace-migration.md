# Python package namespace migration

The server now installs as `mcp_server_for_splunk`. Earlier wheels installed a
generic `src` package, which collided with other Python distributions. No `src`
compatibility package is installed because it would preserve that collision.

The PyPI distribution name remains `mcp-server-for-splunk`. MCP tool names,
resource URIs, HTTP paths, and Splunk configuration headers remain the same.

## Imports and launch commands

Update Python integrations and plugins:

```python
from mcp_server_for_splunk.server import mcp, create_root_app
from mcp_server_for_splunk.core.base import BaseTool
```

Replace `from src...` imports and string-based module references such as
`src.server` with `mcp_server_for_splunk.server`. Importing the package alone no
longer initializes the server; importing its `server` module does.

For an installed wheel, run from a writable application directory:

```bash
mcp-server --local --host 127.0.0.1 --port 8001
mcp-server --transport stdio
```

HTTP host/port defaults also honor `MCP_SERVER_HOST` and `MCP_SERVER_PORT`.
Logs are written beneath the working directory, outside site-packages.

For a source checkout, reinstall the editable package after updating:

```bash
uv sync --extra dev
uv run mcp-server --local
uv run python -m mcp_server_for_splunk.server --host 127.0.0.1 --port 8001
```

The checkout keeps its development CLI, including Docker, Inspector, setup,
detached runs, and stop commands. Those checkout-management options are not
available in an installed wheel. Custom file launchers must use
`src/mcp_server_for_splunk/server.py` instead of the old `src/server.py` path.

## ITSI and downstream plugins

The `[itsi]` extra requires `mcp-itsi-server>=0.2.0`. Earlier ITSI wheels import
the old `src` namespace. The companion package now handles its own header
classification and no longer imports the parent server for that operation.

Publish the compatible ITSI release before publishing the parent release.
Rebuild Docker images together with their dependencies. Auth wrappers and other
plugins that import the parent directly must update their imports when adopting
the new parent release.

## Distribution verification

```bash
uv build --all-packages --wheel
uv run --locked python scripts/check_wheel.py dist/mcp_server_for_splunk-*.whl dist/mcp_itsi_server-*.whl
```

This check extracts the wheels outside the checkout, adds an unrelated `src`
package, and verifies imports, bundled documentation/workflows, ITSI discovery,
and the console entry point. A real MCP client calls the installed search tools
against a mocked Splunk backend and connects to an HTTP server launched by the
installed CLI. It does not claim live Splunk or production deployment coverage.
