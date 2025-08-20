## Deprecated: Legacy OpenAI Agent Integration

This document described a legacy agent-centric integration that is no longer the recommended path.

Use the workflow tools instead:

- `workflow_requirements`: schema, validation rules, best practices
- `workflow_builder`: create/edit/validate/process workflows
- `list_workflows`: discover core and contrib workflows
- `workflow_runner`: execute a workflow by ID

Quick start:

```python
from src.tools.workflows.list_workflows import create_list_workflows_tool
from src.tools.workflows.workflow_runner import WorkflowRunnerTool

lister = create_list_workflows_tool()
await lister.execute(ctx, format_type="summary")

runner = WorkflowRunnerTool("workflow_runner", "workflows")
await runner.execute(ctx, workflow_id="missing_data_troubleshooting", earliest_time="-24h", latest_time="now")
```

Prerequisites (set in `.env`):

```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=4000
```

For a consolidated overview, see `workflows-overview.md` and `README.md` in this folder.
