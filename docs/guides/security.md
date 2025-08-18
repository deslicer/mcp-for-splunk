# Security Guide

This guide summarizes security best practices for deploying and operating the MCP Server for Splunk.

## Scope

- Transport security (HTTP vs stdio)
- Credential handling and secrets
- Least-privilege Splunk access
- Multi-tenant isolation
- Logging/auditing and hardening

## Transport Security

- Prefer HTTPS for HTTP transport behind a reverse proxy (e.g., Traefik).
- Terminate TLS at the edge and limit inbound ports to required services.
- For local development, stdio is acceptable; avoid exposing dev HTTP to untrusted networks.

## Credentials and Secrets

- Do not hardcode Splunk credentials in code or commit them to VCS.
- For Docker:
  - Use Docker secrets for `SPLUNK_PASSWORD` and other sensitive values.
  - Mount secrets and read via `_FILE` environment variables when possible.
- For Kubernetes:
  - Store credentials in Kubernetes Secrets; mount as env or files.
- Never log passwords/tokens; scrub sensitive values from logs.

## Least‑Privilege Access

- Create a dedicated Splunk service account with only required roles for targeted tools.
- Separate roles for admin tools vs read-only search tools.
- Restrict index access to only what is needed.

## Multi‑Tenant Isolation

- Prefer client-provided Splunk credentials per request for isolation.
- Validate and sanitize all client-provided connection parameters.
- Enforce request scoping: clients should not see each other's config or data.

## Logging and Auditing

- Enable structured logs and include request IDs and client identifiers where appropriate.
- Avoid logging request bodies containing credentials.
- Consider centralizing logs with Fluentd/ELK and monitoring for security anomalies.

## Hardening Checklist

- HTTPS enabled for HTTP transport
- Secrets managed via Docker/Kubernetes
- Service account with least-privilege roles
- Logs scrub sensitive values
- Requests validated and scoped per client

## References

- Deployment hardening: `docs/guides/deployment/`
- Example secrets usage: Docker/Kubernetes snippets in deployment guide
- Windows specifics: `docs/WINDOWS_GUIDE.md`
