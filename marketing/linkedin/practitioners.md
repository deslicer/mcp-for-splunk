## From Manual Troubleshooting to Agentic AI Workflows in Splunk (Practitioners)

MCP for Splunk by Deslicer helps you bottle your best Splunk runbooks into reusable agentic workflows.

### What changes day‑to‑day
- One server, many Splunk instances: Per‑client headers isolate sessions so a single MCP endpoint serves multiple tenants (dev/test/prod or different orgs) with no restarts.
- Agentic workflows: Chain tasks; each task calls one or many built‑in tools (search/admin/config/etc.) with its own instructions and inputs. Parallelize and standardize.
- Embedded Splunk context: Built‑in docs/resources give LLMs more accurate guidance.

### Concrete example
`workflows/core/missing_data_troubleshooting.json` turns Splunk’s official inputs troubleshooting guide into a step‑by‑step workflow your agents can run consistently.
Ref: https://help.splunk.com/en/splunk-enterprise/administer/troubleshoot/10.0/splunk-enterprise-log-files/troubleshoot-inputs-with-metrics.log

### Simple view
```text
[LLM or agent]
      │  MCP (tools + workflows)
      ▼
   Splunk A   Splunk B   Splunk C
  (headers)   (headers)  (headers)
```

### Why this vs alternatives
Other servers (e.g., Splunk’s reference) are useful starters. This one leans into enterprise realities: multi‑client isolation, workflow chaining, and embedded Splunk resources — less glue code, more repeatability.
Comparator: https://github.com/splunk/splunk-mcp-server2

### Call to action
- Website: deslicer.com
- Repo: https://github.com/deslicer/mcp-for-splunk (free and open source — built by the community, for the community)
- Join our .conf25 Boston workshop (DEV1666): https://conf.splunk.com/sessions/catalog.html?search=dev1666#/

We worked hard to bring this to the community — contributions and feedback very welcome.

