# Workflow Runner Guide

## Overview
The workflow runner tool executes any available workflow by ID with progress reporting, context control, and optional AI summarization.

## Key Features
- Progress reporting via `ctx.report_progress()` and periodic updates
- Dependency-aware parallel task execution
- Detailed execution metrics and optional summarization

## Prerequisites

- Set OpenAI env vars in `.env` (copy from `env.example`):

```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=4000
```

- Ensure OpenAI dependencies are available:

```bash
uv add openai
uv add openai-agents
```

## Usage Example
```python
await workflow_runner.execute(
    ctx=context,
    workflow_id="missing_data_troubleshooting",
    problem_description="Data missing in main index",
    earliest_time="-24h",
    latest_time="now",
    focus_index="main",
    complexity_level="moderate",
    enable_summarization=True,
)
```

## Best Practices
- Use appropriate time windows and focus parameters to narrow scope
- For long runs, rely on progress reporting built into the tool
- Enable summarization for executive-ready summaries and recommendations
