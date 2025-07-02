"""
Troubleshooting prompts for Splunk diagnostics and problem resolution.

Provides structured workflows for common Splunk troubleshooting scenarios.
"""

import logging
from typing import Any

from fastmcp import Context

from ..core.base import BasePrompt, PromptMetadata

logger = logging.getLogger(__name__)


class TroubleshootInputsPrompt(BasePrompt):
    """
    Guided troubleshooting workflow for Splunk data input issues using metrics.log analysis.

    This prompt provides a comprehensive workflow to diagnose and troubleshoot data input
    problems in Splunk by analyzing metrics.log data. It follows the official Splunk
    troubleshooting methodology and guides users through systematic diagnostics.
    """

    METADATA = PromptMetadata(
        name="troubleshoot_inputs",
        description="Guided workflow for troubleshooting Splunk data input issues using metrics.log analysis",
        category="troubleshooting",
        tags=["troubleshooting", "inputs", "metrics", "diagnostics", "performance"],
        arguments=[
            {
                "name": "earliest_time",
                "description": "Start time for analysis (default: -24h)",
                "required": False,
                "type": "string"
            },
            {
                "name": "latest_time",
                "description": "End time for analysis (default: now)",
                "required": False,
                "type": "string"
            },
            {
                "name": "focus_index",
                "description": "Specific index to focus analysis on (optional)",
                "required": False,
                "type": "string"
            },
            {
                "name": "focus_host",
                "description": "Specific host to focus analysis on (optional)",
                "required": False,
                "type": "string"
            }
        ]
    )

    async def get_prompt(
        self,
        ctx: Context,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        focus_index: str | None = None,
        focus_host: str | None = None
    ) -> dict[str, Any]:
        """
        Get the troubleshoot inputs prompt with analysis workflow.

        Args:
            earliest_time: Start time for analysis (default: -24h)
            latest_time: End time for analysis (default: now)
            focus_index: Specific index to focus on (optional)
            focus_host: Specific host to focus on (optional)

        Returns:
            Dict containing the structured troubleshooting prompt
        """

        # Build focus filters
        focus_filters = []
        if focus_index:
            focus_filters.append(f'index="{focus_index}"')
        if focus_host:
            focus_filters.append(f'host="{focus_host}"')

        focus_filter_str = " AND " + " AND ".join(focus_filters) if focus_filters else ""
        focus_description = ""
        if focus_filters:
            focus_description = f"\n**Analysis Focus**: {', '.join(focus_filters)}"

        # Create the comprehensive troubleshooting workflow
        workflow_content = f"""# Splunk Input Troubleshooting Workflow

This guided workflow helps diagnose data input issues in Splunk using metrics.log analysis.{focus_description}

**Time Range**: {earliest_time} to {latest_time}

## Overview

When Splunk experiences data input problems, the metrics.log provides detailed information about:
- Data throughput per index, source, sourcetype, and host
- Processing performance and bottlenecks
- Input pipeline health and statistics

## 📋 Step-by-Step Troubleshooting Process

### Step 1: Get Troubleshooting Documentation

First, let's review the official Splunk documentation for input troubleshooting:

**Resource to retrieve:**
```json
{{
  "method": "resources/read",
  "params": {{
    "uri": "splunk-docs://latest/troubleshooting/troubleshoot-inputs"
  }}
}}
```

### Step 2: Overall Throughput Analysis

Let's examine overall data ingestion patterns to identify anomalies:

**Tool to run:**
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_filter_str} | timechart span=1h sum(kb) as totalKB | rename sum(kb) as totalKB",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

**What to look for:**
- Sudden drops in data volume
- Consistent patterns vs. unexpected spikes
- Zero throughput periods

### Step 3: Per-Index Throughput Breakdown

Analyze throughput by index to identify problematic data sources:

**Tool to run:**
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_filter_str} | stats sum(kb) as total_kb, sum(eps) as total_eps by series | sort -total_kb | head 20",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

**What to look for:**
- Indexes with unusually low throughput
- Missing indexes that should be receiving data
- Uneven distribution across indexes

### Step 4: Host-Level Analysis

Identify which hosts are contributing to input issues:

**Tool to run:**
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_host_thruput{focus_filter_str} | stats sum(kb) as total_kb, sum(eps) as total_eps by series | sort -total_kb | head 15",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

**What to look for:**
- Hosts with zero or very low throughput
- Hosts that stopped sending data abruptly
- Uneven distribution suggesting configuration issues

### Step 5: Sourcetype Analysis

Examine data by sourcetype to identify format or parsing issues:

**Tool to run:**
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_sourcetype_thruput{focus_filter_str} | stats sum(kb) as total_kb, sum(eps) as total_eps by series | sort -total_kb | head 20",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

**What to look for:**
- Sourcetypes with unexpected throughput patterns
- Missing sourcetypes that should be present
- Very high event rates with low KB (suggests parsing issues)

### Step 6: Source Path Analysis

Identify specific sources experiencing problems:

**Tool to run:**
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_source_thruput{focus_filter_str} | stats sum(kb) as total_kb, sum(eps) as total_eps by series | sort -total_kb | head 25",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

**What to look for:**
- Sources that stopped sending data
- File paths that might indicate disk issues
- Network paths that might indicate connectivity problems

### Step 7: Detailed Timeline Analysis

For any problematic sources identified above, create a detailed timeline:

**Tool to run (customize the series filter based on findings):**
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput series=\\"<problematic_index>\\"{focus_filter_str} | timechart span=15m sum(kb) as kb, sum(eps) as eps",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

### Step 8: Input Processor Performance

Check for input processing bottlenecks:

**Tool to run:**
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=queue name=indexqueue{focus_filter_str} | timechart span=5m avg(current_size_kb) as avg_queue_size_kb, max(current_size_kb) as max_queue_size_kb",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

**What to look for:**
- Consistently high queue sizes indicating processing bottlenecks
- Queue size spikes correlating with throughput drops

### Step 9: TCP Input Analysis (if applicable)

For TCP inputs, check connection and data flow:

**Tool to run:**
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=tcpin_connections{focus_filter_str} | stats latest(connections) as current_connections by host | sort -current_connections",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

## 🔍 Interpretation Guidelines

### Normal vs. Problematic Patterns

**Healthy patterns:**
- Consistent throughput with predictable daily/weekly patterns
- Even distribution across expected indexes/hosts
- Queue sizes typically under 1MB
- Connection counts stable for TCP inputs

**Warning signs:**
- Sudden throughput drops to zero
- Consistent queue buildups over 10MB
- Missing data from expected sources
- Unexpectedly low event rates compared to KB throughput

### Common Root Causes

1. **File System Issues**
   - Disk space full on monitored systems
   - File permission changes
   - File system corruption

2. **Network Issues**
   - Network connectivity problems for universal forwarders
   - Firewall changes blocking data flow
   - TCP input port issues

3. **Configuration Issues**
   - Incorrect input configurations
   - Parsing configuration problems
   - Index configuration errors

4. **Resource Constraints**
   - Indexer disk space full
   - Memory constraints causing processing delays
   - CPU bottlenecks

## 💡 Next Steps

Based on your analysis results:

1. **For throughput issues**: Focus on the specific indexes, hosts, or sources showing problems
2. **For parsing issues**: Examine sourcetype configurations and sample events
3. **For performance issues**: Check system resources and queue performance
4. **For missing data**: Verify forwarder connectivity and input configurations

## 📚 Additional Resources

- Use the SPL reference resource for advanced search techniques
- Check the Splunk health resource for system-wide status
- Review configuration resources for input settings

**Remember**: Always correlate metrics.log findings with the actual missing or problematic data to confirm root causes.
"""

        return {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": workflow_content
                }
            ]
        }
