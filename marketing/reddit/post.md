Title: MCP for Splunk — agentic workflows, one server for many tenants, community‑first FOSS

If you’re exploring MCP servers to connect LLMs to Splunk, Deslicer’s MCP for Splunk focuses on enterprise realities:

- One server, many Splunk instances: client‑scoped headers = multi‑tenant without restarts
- Agentic AI workflows: chain tasks that call built‑in tools (search/admin/config/etc.) with per‑task instructions/inputs
- Example: `missing_data_troubleshooting.json` codifies Splunk’s official inputs troubleshooting into a repeatable workflow
  Ref: https://help.splunk.com/en/splunk-enterprise/administer/troubleshoot/10.0/splunk-enterprise-log-files/troubleshoot-inputs-with-metrics.log
- Embedded Splunk resources so LLMs answer with better context, fewer hallucinations
- FOSS: free forever, built by the community, for the community

Compare with Splunk’s reference server: both useful, but we emphasize multi‑client isolation + agentic workflows + embedded docs.
Repo: https://github.com/deslicer/mcp-for-splunk
Workshop @ .conf25 Boston (DEV1666): https://conf.splunk.com/sessions/catalog.html?search=dev1666#/
Site: deslicer.com

We’ve worked hard to make this public — feedback and contributions welcome.

