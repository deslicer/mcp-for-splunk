# Troubleshooting

Quick fixes for common setup and usage issues.

## Connection Issues

- Verify Splunk host/port and credentials
- For self-signed certs, set `SPLUNK_VERIFY_SSL=false` in development
- Test connectivity: `curl -k https://<splunk-host>:8089/services/server/info`

## MCP Inspector

- Open `http://localhost:6274`
- Set URL to `http://localhost:8001/mcp/` (Docker) or `http://localhost:8002/mcp/` (dev compose)
- If Connect fails, check server logs and port mappings

## Tools Not Visible

- Ensure tool files are in `src/tools/` or `contrib/tools/`
- Confirm classes inherit the correct base classes and include metadata
- Restart server after adding new tools

## Docker Environment

- Check container logs: `docker compose logs -f mcp-server`
- Verify required services are healthy (Traefik, Splunk if enabled)
- Confirm license if running the `so1` Splunk container

## Windows Notes

- Use PowerShell scripts under `scripts/`
- If execution policy blocks scripts: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`

## Next Steps

- Installation: `docs/getting-started/installation.md`
- Tests: `docs/tests.md` and `docs/guides/TESTING.md`
- Deployment: `docs/guides/deployment/`
