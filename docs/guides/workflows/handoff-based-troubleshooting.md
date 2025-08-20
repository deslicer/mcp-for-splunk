# Deprecated: Handoff-Based Troubleshooting

This legacy document described a handoff-based agent orchestration approach. The current system consolidates on the workflow tools for creating, validating, discovering, and executing workflows.

Use these instead:

- `workflow_requirements` — schema, validation rules, best practices
- `workflow_builder` — create/edit/validate/process workflows (with templates)
- `list_workflows` — discover core and contrib workflows
- `workflow_runner` — execute workflows by ID with progress and optional summarization

Quick execution example:

```python
from src.tools.workflows.workflow_runner import WorkflowRunnerTool

runner = WorkflowRunnerTool("workflow_runner", "workflows")
await runner.execute(
    ctx=ctx,
    workflow_id="performance_analysis",
    earliest_time="-24h",
    latest_time="now"
)
```

Prerequisites (set in `.env`):

```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=4000
```

See `workflows-overview.md`, `README.md` (this folder), and `workflow_runner_guide.md` for the current guidance.
