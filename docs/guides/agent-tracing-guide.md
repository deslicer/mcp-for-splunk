# Agent Tracing Guide

This guide explains how to use the comprehensive tracing capabilities built into the MCP Server for Splunk's dynamic troubleshooting agent system. The tracing implementation follows the [OpenAI Agents SDK tracing documentation](https://openai.github.io/openai-agents-python/tracing/) and provides full observability from the top-level troubleshooting agent down to individual micro-agent tool calls.

## Overview

The tracing system provides end-to-end visibility into:

- **Top-level troubleshooting workflows** - Problem analysis, workflow selection, and orchestration
- **Workflow execution** - Dependency analysis, parallel task execution phases, and result synthesis  
- **Individual micro-agents** - Task execution, instruction building, and tool calls
- **Splunk tool interactions** - Search queries, health checks, and data retrieval operations

## Architecture

The tracing follows a hierarchical structure:

```
🔍 Splunk Dynamic Troubleshooting Trace
├── 📋 Diagnostic Context Creation
├── 🤖 Workflow Type Detection  
├── ⚡ Workflow Execution (Missing Data/Performance/Health Check)
│   ├── 🔍 Workflow Definition Lookup
│   ├── 📊 Dependency Analysis
│   ├── 🏃 Execution Phase 1
│   │   ├── 🤖 Micro Agent Task: license_verification
│   │   │   ├── 📝 Instruction Building
│   │   │   ├── 🔧 OpenAI Agent Execution
│   │   │   └── 🔍 Splunk Search Tool Calls
│   │   └── 🤖 Micro Agent Task: index_verification
│   │       ├── 📝 Instruction Building  
│   │       ├── 🔧 OpenAI Agent Execution
│   │       └── 🔍 Splunk Tool Calls
│   ├── 🏃 Execution Phase 2 (dependent tasks)
│   └── 📊 Workflow Result Synthesis
└── 🧠 Orchestration Analysis
```

## Prerequisites

### Required Dependencies

```bash
# Install OpenAI Agents SDK with tracing support
pip install openai-agents

# Ensure your environment has the OpenAI API key
export OPENAI_API_KEY="your-openai-api-key"
```

### Environment Variables

The tracing system respects standard OpenAI Agents SDK environment variables:

```bash
# Enable/disable tracing globally
export OPENAI_AGENTS_DISABLE_TRACING=0  # 0 = enabled, 1 = disabled

# Configure sensitive data logging
export OPENAI_AGENTS_DONT_LOG_MODEL_DATA=0    # 0 = log model data, 1 = don't log
export OPENAI_AGENTS_DONT_LOG_TOOL_DATA=0     # 0 = log tool data, 1 = don't log

# OpenAI API configuration for tracing backend
export OPENAI_ORG_ID="your-org-id"           # Optional
export OPENAI_PROJECT_ID="your-project-id"   # Optional
```

## Using the Tracing System

### Basic Usage

The tracing is automatically enabled when you use the `dynamic_troubleshoot` tool:

```python
# Example usage - tracing happens automatically
result = await dynamic_troubleshoot_tool.execute(
    ctx=context,
    problem_description="My dashboard shows no data for the last 2 hours",
    earliest_time="-24h",
    latest_time="now",
    workflow_type="auto"
)
```

### Trace Information in Results

The enhanced results include comprehensive tracing metadata:

```python
{
    "status": "success",
    "tracing_info": {
        "trace_available": True,
        "workflow_traced": True,
        "orchestration_traced": True,
        "trace_name": "Splunk Dynamic Troubleshooting: My dashboard shows no data...",
        "trace_metadata": {
            "problem_description": "My dashboard shows no data for the last 2 hours",
            "time_range": "-24h to now",
            "workflow_type": "auto",
            "tool_name": "dynamic_troubleshoot_agent"
        }
    },
    "execution_metadata": {
        "tracing_enabled": True,
        "workflow_execution_time": 45.2,
        "orchestration_execution_time": 12.8
    }
}
```

## Trace Structure and Spans

### Top-Level Trace

Each troubleshooting session creates a main trace with:

- **Name**: `"Splunk Dynamic Troubleshooting: {problem_description}"`
- **Metadata**: Problem details, time range, workflow type, complexity level
- **Duration**: Full end-to-end execution time

### Workflow-Level Spans

#### Diagnostic Context Creation
- **Span**: `diagnostic_context_creation`
- **Attributes**: Time range, focus index/host, complexity level
- **Purpose**: Track context setup and validation

#### Workflow Type Detection  
- **Span**: `workflow_type_detection`
- **Attributes**: Requested vs detected workflow, auto-detection usage
- **Purpose**: Track problem analysis and routing decisions

#### Workflow Execution
- **Span**: `workflow_execution_{workflow_type}`
- **Attributes**: Workflow type, problem description, status, task count
- **Purpose**: Track overall workflow orchestration

### Micro-Agent Level Spans

#### Task Execution
- **Span**: `micro_agent_task_{task_id}`
- **Attributes**: Agent name, task details, tools, dependencies, context
- **Purpose**: Track individual task execution within workflows

#### Instruction Building
- **Span**: `instruction_building`  
- **Attributes**: Dependencies, context injection, instruction length
- **Purpose**: Track dynamic instruction generation

#### Agent Execution
- **Span**: `openai_agent_execution` or `fallback_execution`
- **Attributes**: Model, temperature, turns, execution method
- **Purpose**: Track AI agent reasoning and decision making

### Tool-Level Spans

#### Splunk Tool Calls
- **Spans**: `splunk_search_{task_id}`, `splunk_oneshot_search_{task_id}`, etc.
- **Attributes**: Tool name, query, parameters, success, results
- **Purpose**: Track individual Splunk API interactions

Example tool span attributes:
```python
{
    "tool_name": "run_splunk_search",
    "query": "index=_internal earliest=-24h | stats count",
    "earliest_time": "-24h", 
    "latest_time": "now",
    "agent_name": "DynamicAgent_license_verification",
    "task_id": "license_verification",
    "tool_success": True,
    "result_length": 1024
}
```

## Viewing Traces

### OpenAI Traces Dashboard

Traces are automatically sent to OpenAI's traces dashboard when using a valid API key:

1. Visit the [OpenAI Platform](https://platform.openai.com)
2. Navigate to "Traces" in the sidebar
3. Find your troubleshooting traces by name or time
4. Drill down into spans for detailed execution flow

### Custom Trace Processors

You can add custom trace processors to send traces to other observability platforms:

```python
from agents import add_trace_processor
from your_observability_platform import CustomTraceProcessor

# Add additional trace processor
add_trace_processor(CustomTraceProcessor(
    endpoint="https://your-platform.com/traces",
    api_key="your-platform-key"
))
```

### Supported External Platforms

The OpenAI Agents SDK supports many observability platforms:

- **Weights & Biases**
- **Arize Phoenix** 
- **MLflow**
- **Braintrust**
- **LangSmith**
- **Langfuse**
- **Langtrace**
- **And many more...**

See the [external processors list](https://openai.github.io/openai-agents-python/tracing/#external-tracing-processors-list) for details.

## Troubleshooting

### Tracing Not Working

1. **Check OpenAI Agents SDK Installation**:
   ```bash
   pip show openai-agents
   ```

2. **Verify API Key**:
   ```bash
   echo $OPENAI_API_KEY
   ```

3. **Check Environment Variables**:
   ```bash
   echo $OPENAI_AGENTS_DISABLE_TRACING  # Should be 0 or unset
   ```

4. **Review Logs**:
   ```python
   # Enable verbose logging
   from agents import enable_verbose_stdout_logging
   enable_verbose_stdout_logging()
   ```

### Common Issues

#### No Traces Appearing
- Ensure `OPENAI_API_KEY` is set and valid
- Check that `OPENAI_AGENTS_DISABLE_TRACING` is not set to `1`
- Verify network connectivity to OpenAI's tracing endpoint

#### Sensitive Data in Traces
- Set `OPENAI_AGENTS_DONT_LOG_MODEL_DATA=1` to exclude LLM inputs/outputs
- Set `OPENAI_AGENTS_DONT_LOG_TOOL_DATA=1` to exclude tool inputs/outputs
- Review span attributes for any sensitive information

#### Performance Impact
- Tracing has minimal performance overhead (~1-5ms per span)
- For high-volume scenarios, consider sampling or selective tracing
- Use `trace_include_sensitive_data=False` in RunConfig to reduce payload size

## Advanced Configuration

### Custom Trace Metadata

You can add custom metadata to traces by modifying the trace creation:

```python
# In dynamic_troubleshoot_agent.py
trace_metadata = {
    "problem_description": problem_description,
    "user_id": ctx.user_id,  # Add user context
    "environment": "production",  # Add environment info
    "custom_field": "custom_value"
}
```

### Selective Tracing

Enable tracing only for specific scenarios:

```python
# Only trace complex workflows
if complexity_level == "advanced":
    with trace(workflow_name=trace_name, metadata=trace_metadata):
        return await self._execute_with_tracing(...)
else:
    return await self._execute_with_tracing(...)
```

### Trace Sampling

For high-volume environments, implement sampling:

```python
import random

# Sample 10% of traces
if random.random() < 0.1:
    with trace(workflow_name=trace_name, metadata=trace_metadata):
        return await self._execute_with_tracing(...)
```

## Best Practices

### Span Naming
- Use descriptive, hierarchical names: `workflow_execution_missing_data`
- Include identifiers for correlation: `micro_agent_task_{task_id}`
- Keep names consistent across similar operations

### Attribute Usage
- Add relevant business context: problem type, user info, environment
- Include performance metrics: execution time, result counts
- Capture error details: error messages, types, stack traces
- Use consistent attribute names across spans

### Security Considerations
- Never include passwords, API keys, or PII in span attributes
- Truncate long queries or data for readability: `query[:200]`
- Use environment variables to control sensitive data logging
- Review trace data before enabling in production

### Performance Optimization
- Minimize span creation overhead by checking availability first
- Use batch operations where possible
- Consider async span creation for high-throughput scenarios
- Monitor trace payload sizes and optimize as needed

## Integration Examples

### LangSmith Integration

```python
from langsmith.wrappers import OpenAIAgentsTracingProcessor
from agents import set_trace_processors

# Send traces to both OpenAI and LangSmith
set_trace_processors([
    OpenAIAgentsTracingProcessor(),  # Default OpenAI processor
    LangSmithTracingProcessor(
        project_name="splunk-troubleshooting",
        api_key=os.getenv("LANGSMITH_API_KEY")
    )
])
```

### Custom Analytics

```python
class CustomAnalyticsProcessor:
    def export(self, items):
        for item in items:
            if hasattr(item, 'metadata') and 'problem_description' in item.metadata:
                # Send to custom analytics platform
                self.analytics_client.track_troubleshooting_session(
                    problem=item.metadata['problem_description'],
                    duration=item.execution_time,
                    success=item.status == 'success'
                )

add_trace_processor(CustomAnalyticsProcessor())
```

## Conclusion

The comprehensive tracing system provides unprecedented visibility into the dynamic troubleshooting agent workflows. By following the OpenAI Agents SDK patterns, you get:

- **Full observability** from top-level workflows to individual tool calls
- **Rich metadata** for debugging and optimization
- **Integration flexibility** with multiple observability platforms
- **Performance insights** for workflow optimization
- **Error tracking** for reliability improvements

Use this tracing data to understand agent behavior, optimize performance, debug issues, and improve the overall troubleshooting experience. 