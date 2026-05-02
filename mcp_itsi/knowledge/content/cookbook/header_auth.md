# Header-based authentication recipe

The ITSI MCP server is intentionally compatible with the parent
`mcp-for-splunk` server: it accepts the same `X-Splunk-*` headers and
adds three optional `X-ITSI-*` headers for namespace overrides.

## Required headers

| Header              | Description                                                          |
|---------------------|----------------------------------------------------------------------|
| `X-Splunk-Host`     | Splunk(d) host name or IP. **Required** if not set via env.          |
| `X-Splunk-Username` | Username. **Required** with password when not using a token or session token. |
| `X-Splunk-Password` | Password. Same pairing rule as username.                           |
| `X-Splunk-Token`    | Splunk bearer / access token (alternative to user / password).     |
| `X-Splunk-Session-Token` | Existing splunkd session token (sends `Authorization: Splunk …`). |
| `auth_token`        | Optional alias for the bearer token value.                           |

## Optional headers

| Header                | Default      | Description                                          |
|-----------------------|--------------|------------------------------------------------------|
| `X-Splunk-Port`       | `8089`       | splunkd management port.                             |
| `X-Splunk-Scheme`     | `https`      | Scheme for splunkd.                                  |
| `X-Splunk-Verify-SSL` | `false`      | Set `true` in production with a valid cert.          |
| `X-ITSI-App`          | `SA-ITOA`    | Splunk app namespace.                                |
| `X-ITSI-User-NS`      | `nobody`     | User namespace (`/servicesNS/<user>/...`).           |
| `X-ITSI-API-Version`  | `vLatest`    | ITSI API version.                                    |
| `X-Session-ID`        | (none)       | Optional client-defined session id for log tagging.  |

## Example: streamable-http MCP client

```json
{
  "mcpServers": {
    "splunk-itsi": {
      "url": "http://localhost:8004/mcp/",
      "headers": {
        "X-Splunk-Host": "so1",
        "X-Splunk-Port": "8089",
        "X-Splunk-Username": "admin",
        "X-Splunk-Password": "Chang3d!",
        "X-Splunk-Scheme": "https",
        "X-Splunk-Verify-SSL": "false",
        "X-Session-ID": "itsi-dev-session"
      }
    }
  }
}
```

## Example: token-based auth

```json
{
  "mcpServers": {
    "splunk-itsi-prod": {
      "url": "https://itsi-mcp.example.com/mcp/",
      "headers": {
        "X-Splunk-Host": "splunk.prod.example.com",
        "X-Splunk-Token": "<long-lived-token>",
        "X-Splunk-Verify-SSL": "true"
      }
    }
  }
}
```

## Falling back to environment variables

If no headers are sent, the server uses environment variables (helpful for
single-tenant local development):

```bash
SPLUNK_HOST=localhost
SPLUNK_PORT=8089
SPLUNK_USERNAME=admin
SPLUNK_PASSWORD=Chang3d!
SPLUNK_VERIFY_SSL=false
ITSI_APP=SA-ITOA
ITSI_USER_NS=nobody
```

When running as a plugin inside `mcp-for-splunk`, the parent server's
header handling is reused — you don't need to send credentials twice.
