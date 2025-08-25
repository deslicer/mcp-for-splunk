# Workflows Guide

### Overview

Workflows automate Splunk troubleshooting and validation using JSON-defined tasks executed in dependency-aware parallel phases. You create, validate, discover, and run workflows using these tools:

- `workflow_requirements`: requirements and schema
- `workflow_builder`: create/edit/validate/process workflows
- `list_workflows`: discover available core and contrib workflows
- `workflow_runner`: execute a workflow by ID

### Prerequisites (must-do)

- Set OpenAI environment variables in your `.env` (copy from `env.example`):

```bash
# OpenAI Agent Settings
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=4000
```

- Ensure OpenAI Agents SDK is installed (used by the runner for execution and tracing):

```bash
uv add openai
uv add openai-agents
```

### Where workflows live

- Core: `src/tools/workflows/core/`
- Contrib (your custom workflows): `contrib/workflows/<category>/<workflow_id>.json`

### Core workflows

- `missing_data_troubleshooting`: Systematic 10-step missing data analysis. Follows Splunk’s guidance for inputs and metrics troubleshooting; see [I can't find my data!](https://help.splunk.com/en/splunk-enterprise/administer/troubleshoot/10.0/splunk-web-and-search-problems/i-cant-find-my-data).
- `performance_analysis`: Parallel performance diagnostics (resources, search performance, scheduling).

### Discover workflows (📚)

```python
from src.tools.workflows.list_workflows import create_list_workflows_tool

lister = create_list_workflows_tool()
result = await lister.execute(ctx, format_type="summary")
```

### Run workflows (🚀)

```python
from src.tools.workflows.workflow_runner import WorkflowRunnerTool

runner = WorkflowRunnerTool("workflow_runner", "workflows")
result = await runner.execute(
    ctx=ctx,
    workflow_id="missing_data_troubleshooting",  # or performance_analysis
    earliest_time="-24h",
    latest_time="now",
    focus_index="main",
    complexity_level="moderate",
    enable_summarization=True,
)
```

The runner reports progress regularly and returns structured results with execution metrics and optional AI summaries.

### Create workflows (🔧)

Use `workflow_builder` to generate templates or validate/process finished JSON.

Minimal JSON structure:

```json
{
  "workflow_id": "simple_health_check",
  "name": "Simple Health Check",
  "description": "Basic Splunk health verification workflow",
  "tasks": [
    {
      "task_id": "server_health_check",
      "name": "Server Health Check",
      "description": "Check Splunk server health and connectivity",
      "instructions": "Execute health check using get_splunk_health tool and summarize findings.",
      "required_tools": ["get_splunk_health"],
      "dependencies": [],
      "context_requirements": []
    }
  ]
}
```

Save contrib workflows at `contrib/workflows/<category>/<workflow_id>.json`.

### Validate (✅)

- Get JSON Schemas from `workflow_requirements` with `format_type="schema"`.
- The contrib loader validates during discovery; errors are surfaced in logs and via `list_workflows` output.

### Benefits (why workflows)

- **Consistency**: Repeatable procedures using the same tools your team uses every day
- **Speed**: Parallel phases produce 3–5x faster diagnostics vs sequential steps
- **Coverage**: No missed checks; encode best practices (e.g., missing data 10-step flow)
- **Automation**: Run routine tasks on a schedule or ad hoc with rich summaries

### Quick start (2 minutes)

1. Copy `.env.example` to `.env`, set `OPENAI_API_KEY` and optional model settings
2. Start the server (Docker recommended): `docker compose up -d`
3. Discover workflows with `list_workflows`
4. Run `missing_data_troubleshooting` with `workflow_runner`

Example:

```python
from src.tools.workflows.list_workflows import create_list_workflows_tool
from src.tools.workflows.workflow_runner import WorkflowRunnerTool

lister = create_list_workflows_tool()
await lister.execute(ctx, format_type="summary")

runner = WorkflowRunnerTool("workflow_runner", "workflows")
await runner.execute(ctx, workflow_id="performance_analysis", earliest_time="-24h", latest_time="now")
```

### More resources (📚)

- `workflows-overview.md`: concepts and lifecycle
- `workflow_runner_guide.md`: parameters, progress, and results
- Splunk reference for missing data analysis: [Troubleshoot inputs with metrics.log](https://help.splunk.com/en/splunk-enterprise/administer/troubleshoot/10.0/splunk-enterprise-log-files/troubleshoot-inputs-with-metrics.log)
