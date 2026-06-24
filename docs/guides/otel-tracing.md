# OpenTelemetry Tracing for MCP Server

This guide explains how to enable OpenTelemetry (OTel) distributed tracing so the MCP Server for Splunk participates in end-to-end traces. When enabled, the server exports spans to any OpenTelemetry-compatible backend (Jaeger, Tempo, Grafana, Splunk Observability, etc.), continues an incoming W3C trace (`traceparent`), and emits child spans for outbound HTTP calls.

> **🔧 OTel is Optional**: The MCP server runs normally without it. Tracing activates **only** when the `[otel]` extra is installed *and* `OTEL_EXPORTER_OTLP_ENDPOINT` is set. Otherwise there is zero overhead.

## 🚀 Quick Start

### 1. Install the OTel extra

```bash
pip install mcp-server-for-splunk[otel]
```

This pulls in the OTel SDK, the OTLP/HTTP exporter, and the Starlette, httpx, and logging instrumentations.

### 2. Configure environment

Add to your `.env` file:

```bash
# Required: enables tracing when set
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318

# Recommended (defaults shown)
OTEL_SERVICE_NAME=splunk-mcp
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_TRACES_SAMPLER=parentbased_always_on
DEPLOYMENT_ENVIRONMENT=development
```

### 3. Start the server

```bash
uv run python src/server.py
```

You'll see in the logs:

```
INFO - OpenTelemetry initialized (service=splunk-mcp, env=development, endpoint=http://otel-collector:4318)
INFO - OpenTelemetry tracing and JSON logging enabled
INFO - OpenTelemetry tool span middleware added
INFO - Starlette OTel instrumentation enabled
INFO - httpx OTel instrumentation enabled
```

## 🔧 What gets traced

| Span | Source | Notes |
|------|--------|-------|
| HTTP server span | Starlette instrumentation | Extracts the W3C `traceparent` on `/mcp`, continuing the upstream trace |
| `mcp.tool.{name}` | `OtelToolSpanMiddleware` | One span per tool call, carrying the `mcp.tool.name` attribute |
| httpx client spans | httpx instrumentation | Child spans for outbound REST calls |

> **Note on Splunk REST:** the Splunk SDK (`splunklib`) uses `urllib`, not `httpx`, so its calls are not captured by the httpx instrumentation. httpx child spans appear for other outbound HTTP traffic. Native `splunklib` span capture is tracked separately.

## 📋 Configuration reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | _(unset)_ | OTLP/HTTP collector base URL. **Enables tracing when set.** |
| `OTEL_SERVICE_NAME` | `splunk-mcp` | Stable service name reported to your tracing backend |
| `OTEL_SERVICE_VERSION` | package version | `service.version` resource attribute |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` | OTLP wire protocol |
| `OTEL_TRACES_SAMPLER` | `parentbased_always_on` | Honors the upstream sampling decision |
| `OTEL_TRACES_SAMPLER_ARG` | `1.0` | Ratio when using a `traceidratio` sampler |
| `DEPLOYMENT_ENVIRONMENT` | `development` | `deployment.environment` resource attribute (commonly used to filter traces by environment) |

The OTLP/HTTP exporter reads standard OTel environment variables (`OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, etc.) directly.

## 🔗 Logs ↔ traces

When tracing is enabled, log records are reformatted as single-line JSON carrying `otelTraceID`, `otelSpanID`, and `otelServiceName`, so logs and traces share the same identifiers in your backend:

```json
{"timestamp": "2026-06-23T17:07:46.645Z", "level": "INFO", "logger": "src.server", "message": "...", "otelTraceID": "9b...", "otelSpanID": "1a...", "otelServiceName": "splunk-mcp"}
```

## 🔒 Security

Credential values are denied from spans and logs: `Authorization`, `X-Splunk-Token`, `X-Splunk-Password`, and generic `token` / `password` / `api_key` / `secret` patterns are masked as `***`. Tool arguments are never attached to spans.

## 🔭 Distributed tracing conventions

For consistent end-to-end traces across services, the defaults follow common OTel conventions: W3C context propagation, `parentbased_always_on` sampling (so a service honors the caller's sampling decision), a stable service name, and a `deployment.environment` resource attribute. Override any of these via the standard `OTEL_*` environment variables to match your own topology.
