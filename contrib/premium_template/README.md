# MCP Splunk Premium (template)

Minimal skeleton for premium extensions loaded by the OSS server via entry points.

## Install (editable) next to OSS repo

```bash
pip install -e /Users/young/code/deslicer/mcp-for-splunk
pip install -e .
export PREMIUM_API_KEY=dev-key
mcp-server
```

- Requests without `x-api-key: dev-key` are rejected.
- Disable plugins at runtime: `export MCP_DISABLE_PLUGINS=true`.

## Packaging

```bash
uv build  # or: python -m build
```

Publish the wheel to your private index and install it where the OSS server runs.
