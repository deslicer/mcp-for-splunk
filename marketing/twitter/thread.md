1/ Introducing MCP for Splunk by Deslicer — a Model Context Protocol server that connects LLMs to Splunk for secure, repeatable, AI‑assisted ops. Turn manual, tribal troubleshooting into sharable automations.
Repo: https://github.com/deslicer/mcp-for-splunk

2/ One server, many Splunk instances. Client‑scoped headers let a single MCP endpoint serve multiple tenants/environments without restarts. Platform teams: ship one service; users pick targets via headers.

3/ Agentic AI workflows, not one‑off prompts. Define step‑by‑step runbooks as chains of tasks; each task can call one or many built‑in tools (search, admin, config, etc.), with its own instructions and inputs. Reuse. Share. Standardize.

4/ Example: missing data triage. Our `missing_data_troubleshooting.json` codifies Splunk’s official inputs troubleshooting guide into a multi‑step agent workflow — consistent every time.
Docs reference: https://help.splunk.com/en/splunk-enterprise/administer/troubleshoot/10.0/splunk-enterprise-log-files/troubleshoot-inputs-with-metrics.log

5/ Embedded Splunk resources. The server ships splunk‑aware docs/resources so LLMs answer with better context and fewer hallucinations.

6/ Rich tool surface: search (oneshot/jobs/saved searches), metadata discovery, health, admin (apps/users/config), workflows — designed for enterprise day‑2 use.

7/ Free and open source. Built by the community, for the community — and it will always remain FOSS. Contributions welcome.

8/ Why this vs alternatives? We lean into enterprise realities: multi‑client isolation, agentic workflows, and embedded Splunk context.
Comparator: https://github.com/splunk/splunk-mcp-server2

9/ Try it, contribute, or bring your team to our .conf25 Boston workshop (DEV1666).
deslicer.com • https://github.com/deslicer/mcp-for-splunk • https://conf.splunk.com/sessions/catalog.html?search=dev1666#/

10/ Thanks to the Splunk community — we’re excited to give back and keep building together.

