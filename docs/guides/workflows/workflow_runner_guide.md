# Workflow Runner Guide

## Overview
The workflow runner tool allows execution of any available workflow with progress reporting to prevent timeouts.

## Key Features
- Progress reporting via `ctx.report_progress()`
- Automatic updates every <60s for long operations
- Detailed execution metrics

## Usage Example
```python
await workflow_runner.execute(
    ctx=context,
    workflow_id="missing_data_troubleshooting",
    problem_description="Data missing in main index"
)
```

## Best Practices
- For workflows >60s, ensure frequent progress reports
- Monitor execution_time in results
- Use enable_summarization for comprehensive analysis
