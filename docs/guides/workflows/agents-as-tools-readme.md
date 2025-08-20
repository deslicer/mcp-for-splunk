## Deprecated: Agents-as-Tools

This document described a legacy agent-oriented approach. The project now uses workflow tools as the entry point for creation and execution.

Use these instead:

- `workflow_requirements`: schema and best practices
- `workflow_builder`: create/edit/validate/process workflows (templates available: minimal, security, performance, data_quality, parallel, sequential)
- `list_workflows`: discover core and contrib workflows
- `workflow_runner`: execute workflows by ID with context and optional summarization

Quick execution example:

```python
from src.tools.workflows.workflow_runner import WorkflowRunnerTool

runner = WorkflowRunnerTool("workflow_runner", "workflows")
await runner.execute(
    ctx=ctx,
    workflow_id="missing_data_troubleshooting",
    earliest_time="-24h",
    latest_time="now",
    focus_index="main",
)
```

Prerequisites (set in `.env`):

```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=4000
```

See `workflows-overview.md`, `README.md` (this folder), and `workflow_runner_guide.md` for the current flow.
