# Monitoring Guide

This guide outlines monitoring and observability practices for the MCP Server for Splunk.

## What to Monitor

- Server health and uptime
- Tool execution latency and error rate
- Splunk connection health
- Resource usage (CPU, memory)
- Transport metrics (HTTP request rates/latency)

## Metrics

- Enable metrics in server configuration where supported
- Expose metrics endpoint (e.g., `:9090`) and scrape with Prometheus
- Track:
  - `tool_execution_duration_seconds` (histogram)
  - `tool_errors_total` (counter)
  - `splunk_connection_errors_total` (counter)
  - `requests_total` and `request_latency_seconds`

## Logs

- Use structured logging (JSON) for easier parsing
- Centralize logs (Fluentd/ELK or Splunk HTTP Event Collector)
- Scrub sensitive fields before logging

## Dashboards

- Build dashboards for:
  - Error rates by tool
  - P95 tool latency
  - Splunk connectivity status
  - CPU/memory of server containers

## Alerts

- Alert on sustained error rates, timeouts, or connection failures
- Alert on high latency (e.g., P95 > 5s) and resource saturation

## References

- Deployment: `docs/guides/deployment/`
- Windows: `docs/WINDOWS_GUIDE.md`
