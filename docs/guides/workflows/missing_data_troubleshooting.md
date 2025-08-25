# Missing Data Troubleshooting Workflow

Automate Splunk's "I can't find my data" investigation with a single, repeatable workflow. This turns Splunk guidance into an executable procedure that delivers consistent, auditable results.

- **Workflow file**: `src/tools/workflows/core/missing_data_troubleshooting.json`
- **Reference**: [I can't find my data!](https://help.splunk.com/en/splunk-enterprise/administer/troubleshoot/10.0/splunk-web-and-search-problems/i-cant-find-my-data)
- **Overview docs**: See `docs/guides/workflows/README.md`

## A Real-World Example: Automating Splunk's "I Can't Find My Data" Troubleshooting

Picture this all-too-common Splunk scenario: your security team alerts you that logs seem to be vanishing from a critical index—maybe due to forwarder dropouts, misconfigured permissions, or subtle time range mismatches. What used to involve hours of manual debugging, cross-referencing docs, and inconsistent approaches across engineers can now be streamlined into a single, automated process with MCP for Splunk.

Our `workflows/core/missing_data_troubleshooting.json` takes Splunk's official "I can't find my data" troubleshooting guide and converts it into a fully executable, 10-task workflow. This JSON-defined automation lets AI agents orchestrate the entire diagnostic process systematically, pulling in required tools like `run_splunk_search` and `me` (for user info), resolving dependencies automatically, and even running parallel checks where possible. The result is a structured executive summary with recommendations, ensuring every run is consistent, auditable, and faster than manual efforts.

### What the workflow does

- **Task 1: Splunk License & Edition Verification** – Checks if you're on Splunk Free (with its limitations) and verifies license state via a REST search.
- **Task 2: Index Verification** – Confirms data landed in the right indexes (for example, `main`, `os`) and tests accessibility.
- **Task 3: Permissions & Access Control** – Analyzes user roles and index access restrictions to spot permission blocks.
- **Task 4: Time Range Issues** – Examines indexing lags and time windows, including future‑timestamped events.
- **Task 5: Forwarder Connectivity** – Validates connections, queues, and recent host activity.
- **Task 6: Search Head Configuration** – Verifies distributed search peers and cluster status.
- **Task 7: License Violations** – Detects usage overages that might block searches (dependent on Task 1).
- **Task 8: Scheduled Search Issues** – Reviews scheduler logs for failures or performance bottlenecks.
- **Task 9: Search Query Validation** – Scans for syntax errors, logic flaws, or parser issues in recent searches.
- **Task 10: Field Extraction Issues** – Tests regex patterns and extraction configs for sourcetypes.

Each task includes detailed instructions for the LLM, required tools, dependencies (to enable parallel execution where safe), and context requirements (like `focus_index` or `earliest_time`). This setup not only follows Splunk's guide to the letter but enhances it with automation—agents handle the heavy lifting and summarize findings into actionable insights.

### Why use a workflow over individual tools?

- **Using tools (manual approach)**: You query the AI to check search capabilities, then forwarders, then configs—analyzing results step‑by‑step. It's flexible but time‑consuming and prone to human error.
- **Using workflows (automated approach)**: A single user prompt triggers the full 10‑step process. The AI agent executes the workflow, spawns sub‑agents for tasks like license verification or index checks, and feeds results into a summarizer for a cohesive report.

## Where to find it

- JSON definition: `../../src/tools/workflows/core/missing_data_troubleshooting.json`
- Workflow docs hub: `./README.md`