"""
Troubleshooting prompts for Splunk diagnostics and problem resolution.

Provides structured workflows for common Splunk troubleshooting scenarios
following multi-agent patterns and MCP best practices.
"""

import logging
from typing import Any

from fastmcp import Context

from ..core.base import BasePrompt, PromptMetadata

logger = logging.getLogger(__name__)


class TroubleshootInputsPrompt(BasePrompt):
    """
    Guided troubleshooting workflow for Splunk data input issues.

    This prompt implements a sophisticated multi-step diagnostic process using metrics.log
    analysis following Anthropic's research patterns. It provides structured delegation
    of tasks, parallel analysis capabilities, and comprehensive validation workflows.
    """

    METADATA = PromptMetadata(
        name="troubleshoot_inputs",
        description="workflow for systematic Splunk data input troubleshooting using metrics.log analysis with parallel execution and validation",
        category="troubleshooting",
        tags=["troubleshooting", "inputs", "metrics", "diagnostics", "performance", "multi-agent"],
        arguments=[
            {
                "name": "earliest_time",
                "description": "Start time for analysis (ISO format or relative like -24h, -7d)",
                "required": False,
                "type": "string"
            },
            {
                "name": "latest_time",
                "description": "End time for analysis (ISO format or relative like now, -1h)",
                "required": False,
                "type": "string"
            },
            {
                "name": "focus_index",
                "description": "Specific index to focus analysis on (optional for targeted investigation)",
                "required": False,
                "type": "string"
            },
            {
                "name": "focus_host",
                "description": "Specific host to focus analysis on (optional for targeted investigation)",
                "required": False,
                "type": "string"
            },
            {
                "name": "complexity_level",
                "description": "Analysis complexity: simple, moderate, comprehensive (determines parallel execution strategy)",
                "required": False,
                "type": "string"
            },
            {
                "name": "include_performance_analysis",
                "description": "Include detailed performance bottleneck analysis (impacts execution time)",
                "required": False,
                "type": "boolean"
            }
        ]
    )

    async def get_prompt(
        self,
        ctx: Context,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        focus_index: str | None = None,
        focus_host: str | None = None,
        complexity_level: str = "moderate",
        include_performance_analysis: bool = True
    ) -> dict[str, Any]:
        """
        Generate a comprehensive multi-agent troubleshooting workflow.

        Args:
            earliest_time: Start time for analysis
            latest_time: End time for analysis
            focus_index: Specific index to focus on
            focus_host: Specific host to focus on
            complexity_level: Analysis complexity level
            include_performance_analysis: Include performance analysis

        Returns:
            Dict containing the structured multi-agent troubleshooting workflow
        """

        # Validate and process arguments
        complexity_level = self._validate_complexity_level(complexity_level)
        parallel_strategy = self._determine_parallel_strategy(complexity_level)

        # Build focus filters and context
        focus_context = self._build_focus_context(focus_index, focus_host)

        # Generate the comprehensive workflow
        workflow_content = self._generate_workflow_content(
            earliest_time=earliest_time,
            latest_time=latest_time,
            focus_context=focus_context,
            parallel_strategy=parallel_strategy,
            include_performance_analysis=include_performance_analysis
        )

        return {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": workflow_content
                }
            ]
        }

    def _validate_complexity_level(self, level: str) -> str:
        """Validate and normalize complexity level."""
        valid_levels = ["simple", "moderate", "comprehensive"]
        normalized = level.lower() if level else "moderate"
        return normalized if normalized in valid_levels else "moderate"

    def _determine_parallel_strategy(self, complexity_level: str) -> dict[str, Any]:
        """Determine parallel execution strategy based on complexity."""
        strategies = {
            "simple": {
                "parallel_searches": 2,
                "analysis_depth": "basic",
                "validation_level": "standard"
            },
            "moderate": {
                "parallel_searches": 4,
                "analysis_depth": "detailed",
                "validation_level": "enhanced"
            },
            "comprehensive": {
                "parallel_searches": 6,
                "analysis_depth": "deep",
                "validation_level": "thorough"
            }
        }
        return strategies.get(complexity_level, strategies["moderate"])

    def _build_focus_context(self, focus_index: str | None, focus_host: str | None) -> dict[str, Any]:
        """Build focused analysis context."""
        context = {
            "filters": [],
            "filter_string": "",
            "description": "",
            "scope": "general"
        }

        if focus_index:
            context["filters"].append(f'index="{focus_index}"')
            context["scope"] = "index-focused"

        if focus_host:
            context["filters"].append(f'host="{focus_host}"')
            context["scope"] = "host-focused" if not focus_index else "index-host-focused"

        if context["filters"]:
            context["filter_string"] = " AND " + " AND ".join(context["filters"])
            context["description"] = f"\n**🎯 Analysis Focus**: {', '.join(context['filters'])}"

        return context

    def _generate_workflow_content(
        self,
        earliest_time: str,
        latest_time: str,
        focus_context: dict[str, Any],
        parallel_strategy: dict[str, Any],
        include_performance_analysis: bool
    ) -> str:
        """Generate the complete workflow content."""

        return f"""# 🔍 Advanced Splunk Input Troubleshooting Workflow

**Multi-Agent Diagnostic System** | **Metrics.log Analysis Framework**{focus_context['description']}

**📊 Analysis Parameters**:
- **Time Range**: `{earliest_time}` to `{latest_time}`
- **Complexity Level**: `{parallel_strategy['analysis_depth'].title()}`
- **Parallel Execution**: `{parallel_strategy['parallel_searches']} concurrent searches`
- **Validation Level**: `{parallel_strategy['validation_level'].title()}`

---

## 🎯 Executive Summary & Strategy

This workflow implements a **systematic multi-agent approach** to Splunk input troubleshooting, following proven diagnostic patterns. The process uses **parallel execution** and **structured delegation** to efficiently identify and resolve data ingestion issues.

### 🔄 OODA Loop Methodology
Each analysis phase follows the **Observe-Orient-Decide-Act** loop:
- **Observe**: Gather metrics and data points
- **Orient**: Contextualize findings within system knowledge  
- **Decide**: Determine next diagnostic steps
- **Act**: Execute targeted investigations

---

## 📚 Phase 0: Knowledge Acquisition & Context Building

### Step 0.1: Retrieve Documentation Context
**🎯 Objective**: Establish foundational knowledge for troubleshooting process

**🔧 Resource Retrieval**:
```json
{{
  "method": "resources/read",
  "params": {{
    "uri": "splunk-docs://latest/troubleshooting/troubleshoot-inputs"
  }}
}}
```

**🧠 Context Integration**: This documentation provides the authoritative framework for our analysis.

---

## 🚀 Phase 1: Parallel Initial Assessment

### Concurrent Analysis Block A (Execute Simultaneously)

#### Step 1.1: Overall System Health Overview
**🎯 Objective**: Establish baseline system throughput patterns

**🔧 Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['filter_string']} | timechart span=1h sum(kb) as totalKB sum(eps) as totalEPS | eval throughput_trend=if(totalKB>lag(totalKB), \"increasing\", \"decreasing\")",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

#### Step 1.2: Index-Level Distribution Analysis  
**🎯 Objective**: Identify problematic indexes and distribution anomalies

**🔧 Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search", 
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['filter_string']} | stats sum(kb) as total_kb sum(eps) as total_eps avg(kb) as avg_kb by series | eval efficiency_ratio=total_eps/total_kb | eval health_indicator=case(efficiency_ratio>50 AND efficiency_ratio>2, \"optimal\", efficiency_ratio>10 AND efficiency_ratio>1, \"good\", efficiency_ratio>1, \"suboptimal\", 1=1, \"critical\") | sort -total_kb | head 25",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

### Concurrent Analysis Block B (Execute Simultaneously)

#### Step 1.3: Host Performance Matrix
**🎯 Objective**: Map host-level contribution and identify silent failures

**🔧 Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_host_thruput{focus_context['filter_string']} | stats sum(kb) as total_kb sum(eps) as total_eps count as measurement_count first(_time) as first_seen last(_time) as last_seen by series | eval data_gap_hours=round((last_seen-first_seen)/3600,2) | eval avg_kb_per_hour=round(total_kb/(data_gap_hours+1),2) | sort -total_kb | head 20",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

#### Step 1.4: Sourcetype Parsing Efficiency Analysis
**🎯 Objective**: Detect parsing issues and format problems

**🔧 Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_sourcetype_thruput{focus_context['filter_string']} | stats sum(kb) as total_kb sum(eps) as total_eps by series | eval parse_efficiency=if(total_kb>0, total_eps/total_kb, 0) | eval efficiency_category=case(parse_efficiency>50, \"high_event_density\", parse_efficiency>10, \"normal\", parse_efficiency>1, \"low_density\", 1=1, \"parsing_issues\") | sort -total_kb | head 20",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

---

## 🕵️ Phase 2: Deep Diagnostic Investigation

### Step 2.1: Timeline Pattern Analysis
**🎯 Objective**: Identify temporal patterns and correlation with system events

**🔧 Search Query** (Execute for top problematic sources identified in Phase 1):
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['filter_string']} | timechart span=15m sum(kb) as kb sum(eps) as eps | eval kb_change=kb-lag(kb) | eval eps_change=eps-lag(eps) | eval anomaly_score=abs(kb_change)+abs(eps_change) | where anomaly_score>percentile(anomaly_score,90)",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

### Step 2.2: Source Path Forensics
**🎯 Objective**: Investigate specific file paths and network sources

**🔧 Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_source_thruput{focus_context['filter_string']} | stats sum(kb) as total_kb sum(eps) as total_eps count as measurements by series | eval source_type=case(match(series, \"tcp:\"), \"network\", match(series, \"udp:\"), \"network\", match(series, \"^/\"), \"file_system\", match(series, \"[A-Z]:\"), \"windows_file\", 1=1, \"other\") | eval reliability_score=measurements/24 | sort -total_kb | head 30",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

{self._generate_performance_analysis_section(include_performance_analysis, focus_context, earliest_time, latest_time) if include_performance_analysis else ""}

---

## 🔬 Phase 3: Advanced Analysis & Correlation

### Step 3.1: Cross-Component Correlation Analysis
**🎯 Objective**: Identify system-wide patterns and dependencies

**🔧 Multi-Component Search**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* (group=per_index_thruput OR group=queue OR group=tcpin_connections){focus_context['filter_string']} | stats count by group _time span=5m | chart sum(count) over _time by group | fillnull value=0",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

### Step 3.2: Error Pattern Investigation
**🎯 Objective**: Correlate throughput issues with error conditions

**🔧 Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal (source=*splunkd.log* OR source=*metrics.log*) (ERROR OR WARN OR \"connection*\" OR \"failed*\" OR \"timeout*\"){focus_context['filter_string']} | bucket _time span=15m | stats count by _time log_level component | where count>5",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

---

## 📊 Phase 4: Comprehensive Validation & Synthesis

### Step 4.1: Data Quality Validation
**🎯 Objective**: Verify findings consistency and identify data gaps

**🔧 Validation Queries** (Execute in parallel):

1. **Measurement Consistency Check**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['filter_string']} | stats dc(_time) as time_points sum(kb) as total_data by series | where time_points<expected_measurements OR total_data=0 | sort -expected_measurements",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

2. **Cross-Reference Validation**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "| union [search index=_internal source=*metrics.log* group=per_index_thruput{focus_context['filter_string']} | stats sum(kb) as metrics_kb by series] [search index=* {focus_context['filter_string']} | eval series=index | stats count as event_count by series] | stats values(*) as * by series | eval data_consistency=if(isnull(metrics_kb) OR isnull(event_count), \"MISMATCH\", \"OK\")",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

---

## 📋 Interpretation Framework & Decision Matrix

### 🟢 Healthy System Indicators
- **Throughput Stability**: Consistent patterns with predictable variations (±20%)
- **Distribution Balance**: Even load across expected indexes and hosts
- **Processing Efficiency**: Queue sizes consistently under 1MB
- **Network Stability**: TCP connections stable for network inputs
- **Error Rate**: <1% of total events showing parsing or ingestion errors

### 🟡 Warning Conditions  
- **Moderate Throughput Drops**: 20-50% reduction from baseline
- **Queue Buildup**: 1-10MB sustained queue sizes
- **Partial Host Loss**: <30% of expected hosts reporting
- **Parse Efficiency Issues**: Events/KB ratios outside expected ranges
- **Intermittent Connectivity**: Sporadic connection drops

### 🔴 Critical Issues
- **Complete Data Loss**: Zero throughput from expected sources
- **System Overload**: Queue sizes >10MB sustained
- **Massive Host Loss**: >30% of hosts not reporting
- **Network Failures**: TCP input connection counts dropping to zero
- **Parse Failures**: Extremely low events per KB indicating severe parsing issues

---

## 🛠️ Diagnostic Decision Tree

### Based on your analysis results:

#### **Throughput Pattern Issues** → Focus on:
1. **Time-based analysis** for identifying when problems started
2. **Correlation with system events** (restarts, configuration changes)
3. **Infrastructure monitoring** (disk space, network connectivity)

#### **Host-Level Problems** → Investigate:
1. **Universal Forwarder connectivity** and configuration
2. **Network path validation** between forwarders and indexers  
3. **Host-specific resource constraints** (CPU, memory, disk)

#### **Parse/Format Issues** → Examine:
1. **Sourcetype configurations** and props.conf settings
2. **Sample raw events** for format changes
3. **Transform configurations** and parsing rules

#### **Performance Bottlenecks** → Check:
1. **Indexer resource utilization** (CPU, memory, I/O)
2. **Queue management** and processing capacity
3. **Network bandwidth** and latency issues

---

## 🔍 Advanced Troubleshooting Techniques

### Multi-Dimensional Analysis
Use the **correlation analysis** from Phase 3 to identify:
- **Temporal relationships** between different component failures
- **Cascade effects** where one system impacts another
- **Resource competition** patterns during peak load periods

### Root Cause Validation
For each identified issue:
1. **Reproduce conditions** that trigger the problem
2. **Isolate variables** by testing individual components
3. **Verify fixes** through controlled testing before full deployment

### Preventive Monitoring
Establish **baseline thresholds** from healthy system analysis:
- Set alerts for deviations beyond normal variance
- Create dashboards for ongoing monitoring
- Implement automated health checks

---

## 📚 Additional Resources & Follow-Up Actions

### Next Steps Based on Findings:
1. **For Infrastructure Issues**: Review system resources and capacity planning
2. **For Configuration Issues**: Validate input and parsing configurations
3. **For Network Issues**: Perform network diagnostics and connectivity tests
4. **For Performance Issues**: Analyze resource utilization and optimization opportunities

### Documentation References:
- **SPL Reference**: Use for advanced search optimization
- **Splunk Health Resource**: Check system-wide status and recommendations  
- **Configuration Resources**: Review input and parsing settings
- **Performance Tuning Guide**: Optimize system performance based on findings

---

## ⚡ Quality Assurance & Validation Checklist

Before concluding your analysis:
- [ ] **Data Completeness**: Verified all expected time periods have metrics
- [ ] **Cross-Validation**: Confirmed findings across multiple data sources
- [ ] **Pattern Consistency**: Ensured observed patterns align with system knowledge
- [ ] **Impact Assessment**: Quantified the scope and severity of identified issues  
- [ ] **Action Plan**: Developed specific, actionable next steps
- [ ] **Risk Evaluation**: Assessed potential impacts of recommended changes

**Remember**: This multi-agent approach provides comprehensive analysis but requires careful interpretation. Always validate findings through multiple perspectives and cross-reference with additional system data sources.
"""

    def _generate_performance_analysis_section(self, include_performance: bool, focus_context: dict[str, Any], earliest_time: str, latest_time: str) -> str:
        """Generate performance analysis section when requested."""
        if not include_performance:
            return ""

        return f"""
---

## ⚡ Phase 2.5: Performance Bottleneck Deep Dive

### Step 2.5.1: Queue Performance Analysis
**🎯 Objective**: Identify processing bottlenecks and resource constraints

**🔧 Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=queue{focus_context['filter_string']} | timechart span=5m avg(current_size_kb) as avg_queue_size max(current_size_kb) as max_queue_size avg(cntr_1_lookahead) as avg_lookahead by name | where avg_queue_size>100 OR max_queue_size>1000",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

### Step 2.5.2: Processing Pipeline Efficiency
**🎯 Objective**: Analyze data flow through processing pipeline

**🔧 Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=pipeline{focus_context['filter_string']} | timechart span=10m avg(cpu_seconds) as avg_cpu avg(executes) as avg_executes by processor | eval efficiency=avg_executes/avg_cpu",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

### Step 2.5.3: Network Input Performance Analysis  
**🎯 Objective**: Assess TCP/UDP input performance and connection health

**🔧 Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=tcpin_connections{focus_context['filter_string']} | timechart span=10m avg(connections) as avg_connections max(connections) as max_connections avg(kb) as avg_kb_received | eval connection_efficiency=avg_kb_received/avg_connections",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```
"""


class TroubleshootInputsPromptMultiAgent(BasePrompt):
    """
    Advanced multi-agent troubleshooting workflow for Splunk data input issues.

    This prompt implements sophisticated multi-step diagnostic processes using metrics.log
    analysis following Anthropic's research patterns and MCP best practices. It provides
    structured delegation of tasks, parallel analysis capabilities, and comprehensive
    validation workflows with enhanced security and efficiency considerations.
    """

    METADATA = PromptMetadata(
        name="troubleshoot_inputs_multi_agent",
        description="Advanced multi-agent workflow for Splunk input troubleshooting with parallel execution, validation, and research-based patterns",
        category="troubleshooting",
        tags=["troubleshooting", "inputs", "metrics", "multi-agent", "parallel", "validation", "research"],
        arguments=[
            {
                "name": "earliest_time",
                "description": "Start time for analysis (ISO format or relative like -24h, -7d)",
                "required": False,
                "type": "string"
            },
            {
                "name": "latest_time",
                "description": "End time for analysis (ISO format or relative like now, -1h)",
                "required": False,
                "type": "string"
            },
            {
                "name": "focus_index",
                "description": "Specific index to focus analysis on (optional for targeted investigation)",
                "required": False,
                "type": "string"
            },
            {
                "name": "focus_host",
                "description": "Specific host to focus analysis on (optional for targeted investigation)",
                "required": False,
                "type": "string"
            },
            {
                "name": "complexity_level",
                "description": "Analysis complexity: simple, moderate, comprehensive, expert (determines parallel execution strategy)",
                "required": False,
                "type": "string"
            },
            {
                "name": "include_performance_analysis",
                "description": "Include detailed performance bottleneck analysis (impacts execution time)",
                "required": False,
                "type": "boolean"
            },
            {
                "name": "enable_cross_validation",
                "description": "Enable cross-validation of findings across multiple data sources",
                "required": False,
                "type": "boolean"
            },
            {
                "name": "analysis_mode",
                "description": "Analysis mode: diagnostic, preventive, forensic (determines investigation approach)",
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
        focus_host: str | None = None,
        complexity_level: str = "moderate",
        include_performance_analysis: bool = True,
        enable_cross_validation: bool = True,
        analysis_mode: str = "diagnostic"
    ) -> dict[str, Any]:
        """
        Generate an advanced multi-agent troubleshooting workflow.

        This method creates a comprehensive diagnostic framework following
        research-based multi-agent patterns with enhanced validation and
        security considerations.

        Args:
            earliest_time: Start time for analysis
            latest_time: End time for analysis
            focus_index: Specific index to focus on
            focus_host: Specific host to focus on
            complexity_level: Analysis complexity level
            include_performance_analysis: Include performance analysis
            enable_cross_validation: Enable cross-validation
            analysis_mode: Investigation approach mode

        Returns:
            Dict containing the structured multi-agent troubleshooting workflow
        """

        # Validate and process arguments with enhanced validation
        complexity_level = self._validate_complexity_level_enhanced(complexity_level)
        analysis_mode = self._validate_analysis_mode(analysis_mode)

        # Determine execution strategy based on complexity and mode
        execution_strategy = self._determine_execution_strategy(complexity_level, analysis_mode)

        # Build enhanced focus context with validation
        focus_context = self._build_enhanced_focus_context(focus_index, focus_host)

        # Generate the advanced workflow content
        workflow_content = self._generate_advanced_workflow_content(
            earliest_time=earliest_time,
            latest_time=latest_time,
            focus_context=focus_context,
            execution_strategy=execution_strategy,
            include_performance_analysis=include_performance_analysis,
            enable_cross_validation=enable_cross_validation,
            analysis_mode=analysis_mode
        )

        return {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": workflow_content
                }
            ]
        }

    def _validate_complexity_level_enhanced(self, level: str) -> str:
        """Validate and normalize complexity level with enhanced options."""
        valid_levels = ["simple", "moderate", "comprehensive", "expert"]
        normalized = level.lower() if level else "moderate"
        return normalized if normalized in valid_levels else "moderate"

    def _validate_analysis_mode(self, mode: str) -> str:
        """Validate and normalize analysis mode."""
        valid_modes = ["diagnostic", "preventive", "forensic"]
        normalized = mode.lower() if mode else "diagnostic"
        return normalized if normalized in valid_modes else "diagnostic"

    def _determine_execution_strategy(self, complexity_level: str, analysis_mode: str) -> dict[str, Any]:
        """Determine advanced execution strategy based on complexity and mode."""
        base_strategies = {
            "simple": {"parallel_searches": 3, "analysis_depth": "basic", "validation_level": "standard"},
            "moderate": {"parallel_searches": 5, "analysis_depth": "detailed", "validation_level": "enhanced"},
            "comprehensive": {"parallel_searches": 8, "analysis_depth": "deep", "validation_level": "thorough"},
            "expert": {"parallel_searches": 12, "analysis_depth": "expert", "validation_level": "comprehensive"}
        }

        mode_modifiers = {
            "diagnostic": {"focus": "problem_identification", "timeline": "recent", "validation": "standard"},
            "preventive": {"focus": "pattern_analysis", "timeline": "extended", "validation": "predictive"},
            "forensic": {"focus": "root_cause_analysis", "timeline": "comprehensive", "validation": "exhaustive"}
        }

        strategy = base_strategies.get(complexity_level, base_strategies["moderate"]).copy()
        strategy.update(mode_modifiers.get(analysis_mode, mode_modifiers["diagnostic"]))

        return strategy

    def _build_enhanced_focus_context(self, focus_index: str | None, focus_host: str | None) -> dict[str, Any]:
        """Build enhanced focused analysis context with validation."""
        context = {
            "filters": [],
            "filter_string": "",
            "description": "",
            "scope": "general",
            "security_considerations": [],
            "validation_queries": []
        }

        # Enhanced input validation and sanitization
        if focus_index:
            # Basic validation for index names (alphanumeric, underscore, hyphen)
            if focus_index.replace('_', '').replace('-', '').isalnum():
                context["filters"].append(f'index="{focus_index}"')
                context["scope"] = "index-focused"
                context["security_considerations"].append("Index scope validation required")

        if focus_host:
            # Basic validation for hostnames
            if focus_host.replace('.', '').replace('-', '').replace('_', '').isalnum():
                context["filters"].append(f'host="{focus_host}"')
                context["scope"] = "host-focused" if not focus_index else "index-host-focused"
                context["security_considerations"].append("Host scope validation required")

        if context["filters"]:
            context["filter_string"] = " AND " + " AND ".join(context["filters"])
            context["description"] = f"\n**🎯 Enhanced Analysis Focus**: {', '.join(context['filters'])}"

        return context

    def _generate_advanced_workflow_content(
        self,
        earliest_time: str,
        latest_time: str,
        focus_context: dict[str, Any],
        execution_strategy: dict[str, Any],
        include_performance_analysis: bool,
        enable_cross_validation: bool,
        analysis_mode: str
    ) -> str:
        """Generate the complete advanced workflow content."""

        security_section = self._generate_security_section(focus_context)
        validation_section = self._generate_validation_section(enable_cross_validation)
        mode_specific_section = self._generate_mode_specific_section(analysis_mode, earliest_time, latest_time, focus_context)

        return f"""# 🔬 Advanced Multi-Agent Splunk Input Troubleshooting Workflow

**Research-Based Diagnostic System** | **Enhanced Metrics.log Analysis Framework**{focus_context['description']}

**📊 Advanced Analysis Parameters**:
- **Time Range**: `{earliest_time}` to `{latest_time}`
- **Complexity Level**: `{execution_strategy['analysis_depth'].title()}`
- **Analysis Mode**: `{analysis_mode.title()}`
- **Parallel Execution**: `{execution_strategy['parallel_searches']} concurrent searches`
- **Validation Level**: `{execution_strategy['validation_level'].title()}`
- **Security Considerations**: `{len(focus_context['security_considerations'])} active`

---

## 🎯 Executive Summary & Multi-Agent Strategy

This workflow implements an **advanced multi-agent approach** to Splunk input troubleshooting, incorporating research-based patterns from Anthropic's multi-agent systems. The process leverages **hierarchical task delegation**, **parallel execution**, and **comprehensive validation** to efficiently identify and resolve complex data ingestion issues.

### 🧠 Research-Based Agent Architecture
Following proven multi-agent patterns:
- **Lead Agent**: Orchestrates overall investigation strategy
- **Specialist Agents**: Execute domain-specific analysis (performance, network, parsing)
- **Validation Agent**: Cross-validates findings across multiple data sources
- **Synthesis Agent**: Integrates findings into actionable recommendations

### 🔄 Enhanced OODA Loop with Feedback Mechanisms
- **Observe**: Multi-dimensional data gathering with parallel execution
- **Orient**: Context-aware analysis with domain expertise
- **Decide**: Evidence-based decision making with confidence scoring
- **Act**: Validated action recommendations with risk assessment

{security_section}

---

## 📚 Phase 0: Enhanced Knowledge Acquisition & Context Building

### Step 0.1: Multi-Source Documentation Retrieval
**🎯 Objective**: Establish comprehensive knowledge foundation

**🔧 Primary Resource Retrieval**:
```json
{{
  "method": "resources/read",
  "params": {{
    "uri": "splunk-docs://latest/troubleshooting/troubleshoot-inputs"
  }}
}}
```

**🔧 Supplementary Knowledge Sources**:
```json
{{
  "method": "resources/read",
  "params": {{
    "uri": "splunk-docs://latest/performance/performance-troubleshooting"
  }}
}}
```

### Step 0.2: System Context Assessment
**🎯 Objective**: Establish current system baseline and health status

**🔧 System Health Check**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "| rest /services/server/info | eval health_status=case(isnotnull(splunk_server), \"online\", 1=1, \"unknown\") | table splunk_server, version, server_roles, health_status",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

---

## 🚀 Phase 1: Hierarchical Parallel Initial Assessment

### Agent Delegation Block Alpha (Lead Analysis - Execute Simultaneously)

#### Step 1.1: System-Wide Throughput Baseline Establishment
**🎯 Objective**: Establish comprehensive system throughput patterns with trend analysis
**👤 Agent**: Lead Diagnostic Agent

**🔧 Enhanced Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['filter_string']} | timechart span=1h sum(kb) as totalKB sum(eps) as totalEPS | eval throughput_trend=case(totalKB>lag(totalKB)*1.1, \"increasing\", totalKB<lag(totalKB)*0.9, \"decreasing\", 1=1, \"stable\") | eval anomaly_score=abs((totalKB-lag(totalKB))/lag(totalKB))*100 | eval health_indicator=case(anomaly_score>50, \"critical\", anomaly_score>20, \"warning\", 1=1, \"healthy\")",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

#### Step 1.2: Advanced Index Distribution Matrix
**🎯 Objective**: Multi-dimensional index analysis with efficiency scoring
**👤 Agent**: Data Distribution Specialist

**🔧 Enhanced Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['filter_string']} | stats sum(kb) as total_kb sum(eps) as total_eps avg(kb) as avg_kb stdev(kb) as stdev_kb by series | eval efficiency_ratio=total_eps/total_kb | eval consistency_score=if(stdev_kb>0, avg_kb/stdev_kb, 0) | eval health_category=case(efficiency_ratio>50 AND consistency_score>2, \"optimal\", efficiency_ratio>10 AND consistency_score>1, \"good\", efficiency_ratio>1, \"suboptimal\", 1=1, \"critical\") | sort -total_kb | head 30",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

### Agent Delegation Block Beta (Specialist Analysis - Execute Simultaneously)

#### Step 1.3: Host Reliability and Performance Matrix
**🎯 Objective**: Comprehensive host-level analysis with reliability scoring
**👤 Agent**: Infrastructure Performance Specialist

**🔧 Enhanced Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_host_thruput{focus_context['filter_string']} | stats sum(kb) as total_kb sum(eps) as total_eps count as measurement_count first(_time) as first_seen last(_time) as last_seen dc(date_hour) as active_hours by series | eval expected_hours=round((last_seen-first_seen)/3600,0) | eval reliability_ratio=active_hours/expected_hours | eval avg_kb_per_hour=round(total_kb/active_hours,2) | eval performance_category=case(reliability_ratio>0.95 AND avg_kb_per_hour>100, \"high_performance\", reliability_ratio>0.8, \"stable\", reliability_ratio>0.5, \"intermittent\", 1=1, \"critical\") | sort -total_kb | head 25",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

#### Step 1.4: Advanced Sourcetype Parsing Intelligence
**🎯 Objective**: Deep parsing efficiency analysis with anomaly detection
**👤 Agent**: Data Parsing Specialist

**🔧 Enhanced Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_sourcetype_thruput{focus_context['filter_string']} | stats sum(kb) as total_kb sum(eps) as total_eps count as measurements avg(eps) as avg_eps by series | eval parse_efficiency=if(total_kb>0, total_eps/total_kb, 0) | eval efficiency_z_score=(parse_efficiency-avg(parse_efficiency))/stdev(parse_efficiency) | eval efficiency_category=case(parse_efficiency>50, \"high_event_density\", parse_efficiency>10, \"normal\", parse_efficiency>1, \"low_density\", efficiency_z_score<-2, \"parsing_anomaly\", 1=1, \"parsing_failure\") | eval confidence_score=case(measurements>20, \"high\", measurements>5, \"medium\", 1=1, \"low\") | sort -total_kb | head 25",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

{mode_specific_section}

{self._generate_advanced_performance_section(include_performance_analysis, focus_context, earliest_time, latest_time) if include_performance_analysis else ""}

---

## 🔬 Phase 3: Multi-Agent Correlation & Cross-Analysis

### Step 3.1: System-Wide Dependency Mapping
**🎯 Objective**: Identify inter-component dependencies and cascade effects
**👤 Agent**: System Architecture Analyst

**🔧 Multi-Dimensional Correlation Search**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* (group=per_index_thruput OR group=queue OR group=tcpin_connections OR group=resource_usage){focus_context['filter_string']} | eval metric_type=case(group=\"per_index_thruput\", \"throughput\", group=\"queue\", \"processing\", group=\"tcpin_connections\", \"network\", group=\"resource_usage\", \"system\") | bucket _time span=10m | stats avg(kb) as avg_value count as measurements by _time metric_type | eval normalized_value=avg_value/max(avg_value) | chart values(normalized_value) over _time by metric_type",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

### Step 3.2: Advanced Error Correlation & Pattern Analysis
**🎯 Objective**: Multi-source error correlation with temporal analysis
**👤 Agent**: Error Pattern Analyst

**🔧 Enhanced Error Investigation**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal (source=*splunkd.log* OR source=*metrics.log*) (ERROR OR WARN OR \"connection*\" OR \"failed*\" OR \"timeout*\" OR \"unable*\" OR \"denied*\"){focus_context['filter_string']} | rex field=_raw \"(?<error_pattern>\\\\b(?:ERROR|WARN|failed|timeout|unable|denied)\\\\s+\\\\w+)\" | bucket _time span=15m | stats count as error_count values(source) as error_sources dc(host) as affected_hosts by _time error_pattern component | where error_count>threshold_value | eval severity=case(error_count>100, \"critical\", error_count>20, \"high\", error_count>5, \"medium\", 1=1, \"low\")",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

{validation_section}

---

## 📊 Phase 5: Advanced Synthesis & Decision Framework

### Multi-Agent Consensus Building
**🎯 Objective**: Synthesize findings across all specialist agents

**Decision Matrix Framework**:
1. **Confidence Scoring**: Each finding includes confidence metrics
2. **Cross-Validation**: Findings validated across multiple data sources  
3. **Risk Assessment**: Impact and probability scoring for each issue
4. **Priority Ranking**: Evidence-based priority assignment

### Advanced Health Indicators & Thresholds

#### 🟢 Optimal System Performance
- **Throughput Stability**: CV < 0.2 (Coefficient of Variation)
- **Processing Efficiency**: Queue depths < 1MB sustained
- **Network Reliability**: Connection stability > 99%
- **Error Rate**: < 0.1% of total events
- **Resource Utilization**: CPU < 80%, Memory < 85%

#### 🟡 Performance Degradation Indicators
- **Moderate Throughput Variance**: 0.2 < CV < 0.5
- **Processing Delays**: 1MB < Queue depths < 10MB
- **Network Instability**: 95% < Connection stability < 99%
- **Elevated Error Rate**: 0.1% < Error rate < 1%
- **Resource Pressure**: CPU 80-90%, Memory 85-95%

#### 🔴 Critical System Issues
- **High Throughput Volatility**: CV > 0.5
- **Processing Bottlenecks**: Queue depths > 10MB sustained
- **Network Failures**: Connection stability < 95%
- **Critical Error Rate**: Error rate > 1%
- **Resource Exhaustion**: CPU > 90%, Memory > 95%

---

## 🛠️ Advanced Diagnostic Decision Tree & Action Framework

### Evidence-Based Decision Making
Each recommendation includes:
- **Evidence Score**: Quantitative support for the finding
- **Confidence Interval**: Statistical confidence in the assessment
- **Risk Level**: Potential impact if left unaddressed
- **Effort Estimate**: Resources required for resolution

### Automated Prioritization Algorithm
1. **Severity Score** = (Impact × Probability × Confidence)
2. **Effort-Adjusted Priority** = Severity Score / Effort Estimate
3. **Business Impact Weighting** = Priority × Business_Critical_Factor

---

## 📚 Enhanced Resources & Continuous Improvement

### Feedback Loop Integration
- **Outcome Tracking**: Monitor resolution effectiveness
- **Pattern Learning**: Update diagnostic patterns based on results
- **Threshold Optimization**: Refine alerting thresholds from historical data

### Advanced Documentation Integration
- **Dynamic Resource Linking**: Context-aware documentation suggestions
- **Knowledge Base Updates**: Contribute findings to organizational knowledge
- **Best Practices Evolution**: Continuous improvement of diagnostic processes

---

## ⚡ Comprehensive Quality Assurance Framework

### Multi-Layer Validation Protocol
- [ ] **Data Integrity**: Verified data completeness and consistency
- [ ] **Cross-Source Validation**: Confirmed findings across multiple metrics
- [ ] **Statistical Significance**: Ensured findings meet confidence thresholds
- [ ] **Temporal Consistency**: Validated patterns across time dimensions
- [ ] **Agent Consensus**: Achieved agreement among specialist agents
- [ ] **Risk Assessment**: Quantified potential impacts and probabilities
- [ ] **Action Validation**: Verified recommended actions against best practices
- [ ] **Security Review**: Confirmed analysis adheres to security guidelines

**Multi-Agent Coordination**: This advanced framework provides comprehensive analysis through coordinated specialist agents. Always validate critical findings through multiple agents and cross-reference with authoritative data sources before implementing recommendations.
"""

    def _generate_security_section(self, focus_context: dict[str, Any]) -> str:
        """Generate security considerations section."""
        if not focus_context.get('security_considerations'):
            return ""

        return f"""
---

## 🔒 Security & Compliance Considerations

### Input Validation & Sanitization
- **Query Parameter Validation**: All user inputs validated against allowlists
- **Injection Prevention**: Search queries use parameterized construction
- **Scope Limitation**: Analysis restricted to authorized data sources
- **Audit Trail**: All analysis activities logged for compliance

### Data Access Controls
- **Principle of Least Privilege**: Queries limited to necessary data scope
- **Sensitive Data Protection**: No exposure of authentication credentials
- **Compliance Framework**: Adheres to organizational security policies

**Active Security Measures**: {len(focus_context['security_considerations'])} security validations applied
"""

    def _generate_validation_section(self, enable_cross_validation: bool) -> str:
        """Generate cross-validation section if enabled."""
        if not enable_cross_validation:
            return ""

        return """
---

## ✅ Phase 4: Advanced Cross-Validation & Verification

### Multi-Source Data Consistency Verification
**🎯 Objective**: Validate findings across independent data sources
**👤 Agent**: Validation Specialist

#### Step 4.1: Metric Consistency Cross-Check
```json
{
  "method": "tools/call",
  "params": {
    "name": "run_splunk_search",
    "arguments": {
      "query": "| multisearch [search index=_internal source=*metrics.log* group=per_index_thruput | stats sum(kb) as metrics_kb by series | eval source_type=\"metrics\"] [search index=* | eval series=index | stats count as event_count by series | eval source_type=\"events\"] | stats values(*) as * by series | eval consistency_ratio=if(isnull(metrics_kb) OR isnull(event_count), 0, if(metrics_kb>0, event_count/(metrics_kb*10), 0)) | eval validation_status=case(consistency_ratio>0.5 AND consistency_ratio<2, \"VALIDATED\", isnull(metrics_kb), \"MISSING_METRICS\", isnull(event_count), \"MISSING_EVENTS\", 1=1, \"INCONSISTENT\")",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }
  }
}
```

#### Step 4.2: Temporal Consistency Validation
```json
{
  "method": "tools/call",
  "params": {
    "name": "run_splunk_search",
    "arguments": {
      "query": "index=_internal source=*metrics.log* group=per_index_thruput | bucket _time span=1h | stats count as measurement_count sum(kb) as hourly_kb by _time series | eventstats avg(measurement_count) as expected_measurements | eval completeness_ratio=measurement_count/expected_measurements | eval temporal_health=case(completeness_ratio>0.9, \"COMPLETE\", completeness_ratio>0.7, \"PARTIAL\", 1=1, \"INCOMPLETE\")",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }
  }
}
```
"""

    def _generate_mode_specific_section(self, analysis_mode: str, earliest_time: str, latest_time: str, focus_context: dict[str, Any]) -> str:
        """Generate mode-specific analysis section."""
        if analysis_mode == "forensic":
            return f"""
---

## 🔍 Phase 2: Forensic Deep Dive Investigation

### Step 2.1: Historical Pattern Forensics
**🎯 Objective**: Comprehensive historical analysis for root cause identification
**👤 Agent**: Forensic Analyst

**🔧 Extended Timeline Analysis**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['filter_string']} | bucket _time span=1h | stats sum(kb) as hourly_kb sum(eps) as hourly_eps by _time series | eventstats avg(hourly_kb) as baseline_kb stdev(hourly_kb) as stdev_kb by series | eval z_score=(hourly_kb-baseline_kb)/stdev_kb | eval anomaly_type=case(z_score>3, \"extreme_high\", z_score>2, \"high\", z_score<-3, \"extreme_low\", z_score<-2, \"low\", 1=1, \"normal\") | where anomaly_type!=\"normal\"",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```
"""
        elif analysis_mode == "preventive":
            return f"""
---

## 📈 Phase 2: Predictive Pattern Analysis

### Step 2.1: Trend Analysis & Capacity Forecasting
**🎯 Objective**: Identify growth patterns and predict future capacity needs
**👤 Agent**: Predictive Analytics Specialist

**🔧 Trend Analysis Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['filter_string']} | bucket _time span=1d | stats sum(kb) as daily_kb by _time series | sort _time | streamstats window=7 avg(daily_kb) as moving_avg by series | eval growth_rate=((daily_kb-lag(daily_kb,7))/lag(daily_kb,7))*100 | eval trend_classification=case(growth_rate>10, \"rapid_growth\", growth_rate>5, \"steady_growth\", growth_rate>-5, \"stable\", growth_rate>-10, \"declining\", 1=1, \"rapid_decline\")",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```
"""
        else:  # diagnostic mode
            return f"""
---

## 🕵️ Phase 2: Targeted Diagnostic Investigation

### Step 2.1: Real-Time Pattern Analysis
**🎯 Objective**: Identify current system issues and immediate concerns
**👤 Agent**: Diagnostic Specialist

**🔧 Current State Analysis**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['filter_string']} | timechart span=15m sum(kb) as kb sum(eps) as eps | eval kb_change=kb-lag(kb) | eval eps_change=eps-lag(eps) | eval change_magnitude=sqrt(pow(kb_change,2)+pow(eps_change,2)) | eval issue_severity=case(change_magnitude>percentile(change_magnitude,95), \"critical\", change_magnitude>percentile(change_magnitude,80), \"high\", change_magnitude>percentile(change_magnitude,60), \"medium\", 1=1, \"low\")",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```
"""

    def _generate_advanced_performance_section(self, include_performance: bool, focus_context: dict[str, Any], earliest_time: str, latest_time: str) -> str:
        """Generate advanced performance analysis section."""
        if not include_performance:
            return ""

        return f"""
---

## ⚡ Phase 2.5: Advanced Performance Intelligence

### Step 2.5.1: Intelligent Queue Analysis with Bottleneck Detection
**🎯 Objective**: Advanced queue performance analysis with predictive bottleneck identification
**👤 Agent**: Performance Optimization Specialist

**🔧 Enhanced Queue Analysis**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=queue{focus_context['filter_string']} | timechart span=5m avg(current_size_kb) as avg_queue_size max(current_size_kb) as max_queue_size avg(cntr_1_lookahead) as avg_lookahead stdev(current_size_kb) as queue_volatility by name | eval bottleneck_score=(avg_queue_size*queue_volatility)/1000 | eval performance_category=case(bottleneck_score>10, \"critical_bottleneck\", bottleneck_score>5, \"performance_risk\", bottleneck_score>1, \"monitoring_required\", 1=1, \"optimal\") | where performance_category!=\"optimal\"",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

### Step 2.5.2: Resource Utilization Efficiency Matrix
**🎯 Objective**: Multi-dimensional resource analysis with efficiency scoring
**👤 Agent**: Resource Optimization Specialist

**🔧 Resource Efficiency Analysis**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=resource_usage{focus_context['filter_string']} | timechart span=10m avg(cpu_user_pct) as avg_cpu avg(mem_used) as avg_memory max(fd_used) as max_fd | eval resource_efficiency=100-((avg_cpu+avg_memory/1024)/2) | eval efficiency_trend=resource_efficiency-lag(resource_efficiency) | eval performance_status=case(resource_efficiency>80, \"optimal\", resource_efficiency>60, \"good\", resource_efficiency>40, \"degraded\", 1=1, \"critical\") | eval trend_direction=case(efficiency_trend>5, \"improving\", efficiency_trend<-5, \"degrading\", 1=1, \"stable\")",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

### Step 2.5.3: Network Performance Intelligence
**🎯 Objective**: Advanced network input analysis with connection health scoring
**👤 Agent**: Network Performance Specialist

**🔧 Network Intelligence Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=tcpin_connections{focus_context['filter_string']} | timechart span=10m avg(connections) as avg_connections max(connections) as max_connections min(connections) as min_connections avg(kb) as avg_kb_received | eval connection_stability=(min_connections/max_connections)*100 | eval throughput_per_connection=avg_kb_received/avg_connections | eval network_health_score=(connection_stability*throughput_per_connection)/100 | eval network_status=case(network_health_score>50, \"excellent\", network_health_score>25, \"good\", network_health_score>10, \"fair\", 1=1, \"poor\")",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```
"""


class TroubleshootPerformancePrompt(BasePrompt):
    """
    Specialized prompt for Splunk performance analysis and optimization.
    
    Focuses on system resource utilization, processing efficiency, and 
    capacity planning based on metrics analysis.
    """

    METADATA = PromptMetadata(
        name="troubleshoot_performance",
        description="Comprehensive Splunk performance analysis and optimization workflow",
        category="troubleshooting",
        tags=["performance", "optimization", "capacity", "monitoring"],
        arguments=[
            {
                "name": "earliest_time",
                "description": "Start time for performance analysis",
                "required": False,
                "type": "string"
            },
            {
                "name": "latest_time",
                "description": "End time for performance analysis",
                "required": False,
                "type": "string"
            },
            {
                "name": "analysis_type",
                "description": "Type of performance analysis: resource, throughput, capacity",
                "required": False,
                "type": "string"
            }
        ]
    )

    async def get_prompt(
        self,
        ctx: Context,
        earliest_time: str = "-7d",
        latest_time: str = "now",
        analysis_type: str = "comprehensive"
    ) -> dict[str, Any]:
        """Generate performance analysis workflow."""

        workflow_content = f"""# 🚀 Splunk Performance Analysis & Optimization

**Time Range**: {earliest_time} to {latest_time}
**Analysis Type**: {analysis_type.title()}

## 📊 Resource Utilization Analysis

### System Resource Monitoring
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=resource_usage | timechart span=1h avg(cpu_user_pct) as avg_cpu avg(mem_used) as avg_memory max(fd_used) as max_file_descriptors",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

## 🔄 Throughput Optimization

### Processing Pipeline Analysis
```json
{{
  "method": "tools/call", 
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=pipeline | stats avg(cpu_seconds) as avg_cpu_time sum(executes) as total_executions by processor | eval efficiency_ratio=total_executions/avg_cpu_time | sort -efficiency_ratio",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

## 📈 Capacity Planning Recommendations

Based on your analysis results, this workflow provides:
- Resource utilization patterns and recommendations
- Throughput bottleneck identification
- Capacity planning guidance for scaling decisions

Refer to Splunk performance documentation for detailed optimization strategies.
"""

        return {
            "role": "assistant",
            "content": [{"type": "text", "text": workflow_content}]
        }


class TroubleshootIndexingPerformancePrompt(BasePrompt):
    """
    Systematic indexing performance troubleshooting workflow for Splunk.

    This prompt implements a comprehensive diagnostic process for identifying and triaging
    indexing performance issues based on Splunk's official troubleshooting methodology.
    It follows multi-agent patterns with structured analysis phases, parallel execution,
    and comprehensive validation workflows.

    References:
    - Splunk Enterprise troubleshooting documentation  
    - Platform instrumentation logs and searches
    - Indexing performance metrics and analysis
    """

    METADATA = PromptMetadata(
        name="troubleshoot_indexing_performance",
        description="Comprehensive workflow for identifying and triaging Splunk indexing performance issues using platform instrumentation and metrics analysis",
        category="troubleshooting",
        tags=["troubleshooting", "indexing", "performance", "metrics", "platform-instrumentation", "multi-agent"],
        arguments=[
            {
                "name": "earliest_time",
                "description": "Start time for analysis (ISO format or relative like -24h, -7d)",
                "required": False,
                "type": "string"
            },
            {
                "name": "latest_time", 
                "description": "End time for analysis (ISO format or relative like now, -1h)",
                "required": False,
                "type": "string"
            },
            {
                "name": "focus_index",
                "description": "Specific index to focus analysis on (optional for targeted investigation)",
                "required": False,
                "type": "string"
            },
            {
                "name": "focus_host",
                "description": "Specific indexer host to focus analysis on (optional for targeted investigation)",
                "required": False,
                "type": "string"
            },
            {
                "name": "analysis_depth",
                "description": "Analysis depth: quick, standard, comprehensive (determines scope and execution time)",
                "required": False,
                "type": "string"
            },
            {
                "name": "include_delay_analysis",
                "description": "Include indexing delay and latency analysis (may increase execution time)",
                "required": False,
                "type": "boolean"
            },
            {
                "name": "include_platform_instrumentation",
                "description": "Include platform instrumentation logs and searches analysis",
                "required": False,
                "type": "boolean"
            }
        ]
    )

    async def get_prompt(
        self,
        ctx: Context,
        earliest_time: str = "-24h",
        latest_time: str = "now", 
        focus_index: str | None = None,
        focus_host: str | None = None,
        analysis_depth: str = "standard",
        include_delay_analysis: bool = True,
        include_platform_instrumentation: bool = True
    ) -> dict[str, Any]:
        """
        Generate a comprehensive indexing performance troubleshooting workflow.

        Args:
            earliest_time: Start time for analysis
            latest_time: End time for analysis
            focus_index: Specific index to focus on
            focus_host: Specific indexer host to focus on
            analysis_depth: Analysis depth level
            include_delay_analysis: Include delay analysis
            include_platform_instrumentation: Include platform instrumentation analysis

        Returns:
            Dict containing the structured indexing performance troubleshooting workflow
        """

        # Validate and process arguments
        analysis_depth = self._validate_analysis_depth(analysis_depth)
        execution_strategy = self._determine_execution_strategy(analysis_depth)

        # Build focus filters and context
        focus_context = self._build_focus_context(focus_index, focus_host)

        # Generate the comprehensive workflow
        workflow_content = self._generate_indexing_workflow_content(
            earliest_time=earliest_time,
            latest_time=latest_time,
            focus_context=focus_context,
            execution_strategy=execution_strategy,
            include_delay_analysis=include_delay_analysis,
            include_platform_instrumentation=include_platform_instrumentation
        )

        return {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": workflow_content
                }
            ]
        }

    def _validate_analysis_depth(self, depth: str) -> str:
        """Validate and normalize analysis depth."""
        valid_depths = ["quick", "standard", "comprehensive"]
        normalized = depth.lower() if depth else "standard"
        return normalized if normalized in valid_depths else "standard"

    def _determine_execution_strategy(self, analysis_depth: str) -> dict[str, Any]:
        """Determine execution strategy based on analysis depth."""
        strategies = {
            "quick": {
                "parallel_searches": 3,
                "analysis_phases": ["basic_metrics", "error_detection"],
                "validation_level": "basic"
            },
            "standard": {
                "parallel_searches": 5,
                "analysis_phases": ["basic_metrics", "error_detection", "performance_analysis", "correlation"],
                "validation_level": "standard"
            },
            "comprehensive": {
                "parallel_searches": 8,
                "analysis_phases": ["basic_metrics", "error_detection", "performance_analysis", "correlation", "deep_analysis", "prediction"],
                "validation_level": "thorough"
            }
        }
        return strategies.get(analysis_depth, strategies["standard"])

    def _build_focus_context(self, focus_index: str | None, focus_host: str | None) -> dict[str, Any]:
        """Build focused analysis context."""
        context = {
            "filters": [],
            "search_filter": "",
            "description": "",
            "scope": "general"
        }

        if focus_index:
            context["filters"].append(f'index="{focus_index}"')
            context["scope"] = "index-focused"

        if focus_host:
            context["filters"].append(f'host="{focus_host}"')
            context["scope"] = "host-focused" if not focus_index else "index-host-focused"

        if context["filters"]:
            context["search_filter"] = " AND " + " AND ".join(context["filters"])
            context["description"] = f"\n**🎯 Analysis Focus**: {', '.join(context['filters'])}"

        return context

    def _generate_indexing_workflow_content(
        self,
        earliest_time: str,
        latest_time: str,
        focus_context: dict[str, Any],
        execution_strategy: dict[str, Any],
        include_delay_analysis: bool,
        include_platform_instrumentation: bool
    ) -> str:
        """Generate the complete indexing performance workflow content."""

        return f"""# 🚀 Splunk Indexing Performance Diagnostic Workflow

**Advanced Indexing Performance Analysis** | **Platform Instrumentation Framework**{focus_context['description']}

**📊 Analysis Configuration**:
- **Time Range**: `{earliest_time}` to `{latest_time}`
- **Analysis Depth**: `{execution_strategy['parallel_searches']} parallel searches`
- **Analysis Phases**: `{', '.join(execution_strategy['analysis_phases'])}`
- **Validation Level**: `{execution_strategy['validation_level'].title()}`

---

## 🎯 Executive Summary & Methodology

This workflow implements **Splunk's official indexing performance troubleshooting methodology** using advanced multi-agent diagnostic patterns. The process systematically identifies and triages indexing bottlenecks, delays, and performance degradation through structured analysis of platform instrumentation data.

### 🔄 Diagnostic Philosophy
Following **Observe-Orient-Decide-Act (OODA)** methodology:
- **Observe**: Collect indexing metrics and platform instrumentation data
- **Orient**: Contextualize findings within system architecture and baselines
- **Decide**: Prioritize issues by impact and determine investigation paths
- **Act**: Execute targeted remediation strategies

---

## 📚 Phase 0: Enhanced Knowledge Acquisition & Context Building

### Step 0.1: Multi-Source Documentation Retrieval
**🎯 Objective**: Establish comprehensive knowledge foundation

**🔧 Primary Resource Retrieval**:
```json
{{
  "method": "resources/read",
  "params": {{
    "uri": "splunk-docs://latest/troubleshooting/indexing-performance"
  }}
}}
```

### Step 0.2: System Context Assessment
**🎯 Objective**: Establish current system baseline and health status

**🔧 System Information Gathering**:

1. **Available Indexes**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "list_indexes",
    "arguments": {{}}
  }}
}}
```

2. **Available Sourcetypes**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "list_sourcetypes", 
    "arguments": {{}}
  }}
}}
```

3. **Documentation Discovery**:
```json
{{
  "method": "resources/read",
  "params": {{
    "uri": "splunk-docs://discovery"
  }}
}}
```

---

## 🚀 Phase 1: Hierarchical Parallel Initial Assessment

### Agent Delegation Block Alpha (Lead Analysis - Execute Simultaneously)

#### Step 1.1: System-Wide Throughput Baseline Establishment
**🎯 Objective**: Establish comprehensive system throughput patterns with trend analysis
**👤 Agent**: Lead Diagnostic Agent

**🔧 Enhanced Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['search_filter']} | timechart span=1h sum(kb) as totalKB sum(eps) as totalEPS | eval throughput_trend=case(totalKB>lag(totalKB)*1.1, \"increasing\", totalKB<lag(totalKB)*0.9, \"decreasing\", 1=1, \"stable\") | eval anomaly_score=abs((totalKB-lag(totalKB))/lag(totalKB))*100 | eval health_indicator=case(anomaly_score>50, \"critical\", anomaly_score>20, \"warning\", 1=1, \"healthy\")",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

#### Step 1.2: Advanced Index Distribution Matrix
**🎯 Objective**: Multi-dimensional index analysis with efficiency scoring
**👤 Agent**: Data Distribution Specialist

**🔧 Enhanced Search Query**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['search_filter']} | stats sum(kb) as total_kb sum(eps) as total_eps avg(kb) as avg_kb stdev(kb) as stdev_kb by series | eval efficiency_ratio=total_eps/total_kb | eval consistency_score=if(stdev_kb>0, avg_kb/stdev_kb, 0) | eval health_category=case(efficiency_ratio>50 AND consistency_score>2, \"optimal\", efficiency_ratio>10 AND consistency_score>1, \"good\", efficiency_ratio>1, \"suboptimal\", 1=1, \"critical\") | sort -total_kb | head 30",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

### Agent Delegation Block Beta (Specialist Analysis - Execute Simultaneously)

#### Step 1.3: Indexer Host Performance Assessment
**🎯 Objective**: Evaluate per-host indexing capacity and identify bottlenecks

**🔧 Host Performance Analysis**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_host_thruput{focus_context['search_filter']} | stats sum(kb) as total_kb sum(eps) as total_eps avg(avg_age) as avg_indexing_delay count as measurement_count by series | eval kb_per_measurement=round(total_kb/measurement_count,2) | eval processing_efficiency=case(avg_indexing_delay<30, \"efficient\", avg_indexing_delay<60, \"normal\", avg_indexing_delay<120, \"slow\", 1=1, \"bottleneck\") | sort -total_kb | head 15",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

#### Step 1.4: Queue and Pipeline Performance Monitoring
**🎯 Objective**: Detect processing pipeline congestion and queue buildup

**🔧 Pipeline Monitoring Search**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=queue{focus_context['search_filter']} | stats avg(current_size) as avg_queue_size max(current_size) as max_queue_size min(current_size) as min_queue_size by series | eval queue_category=case(max_queue_size<1024, \"healthy\", max_queue_size<10240, \"moderate\", max_queue_size<102400, \"high\", 1=1, \"critical\") | eval queue_variance=max_queue_size-min_queue_size | sort -max_queue_size",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

---

## 🔍 Phase 2: Performance Bottleneck Investigation

### Step 2.1: Indexing Delay Pattern Analysis
**🎯 Objective**: Identify patterns in indexing delays and correlate with system events

**🔧 Delay Timeline Analysis**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['search_filter']} | eval delay_bucket=case(avg_age<10, \"<10s\", avg_age<30, \"10-30s\", avg_age<60, \"30-60s\", avg_age<120, \"1-2min\", avg_age<300, \"2-5min\", 1=1, \">5min\") | timechart span=30m count by delay_bucket | fillnull value=0",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

{self._generate_delay_analysis_section(include_delay_analysis, focus_context, earliest_time, latest_time) if include_delay_analysis else ""}

### Step 2.2: Resource Utilization Correlation
**🎯 Objective**: Correlate indexing performance with system resource usage

**🔧 Resource Correlation Search**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* (group=per_index_thruput OR group=resource_usage){focus_context['search_filter']} | eval metric_type=case(group=\"per_index_thruput\", \"throughput\", group=\"resource_usage\", \"resources\", 1=1, \"other\") | timechart span=10m sum(eval(if(metric_type=\"throughput\", kb, 0))) as total_kb avg(eval(if(metric_type=\"resources\", data, null()))) as resource_usage | eval correlation_score=correlation(total_kb, resource_usage)",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

---

## 🕵️ Phase 3: Advanced Diagnostic Analysis

### Step 3.1: Cross-Component Impact Analysis
**🎯 Objective**: Analyze interdependencies between indexing components

**🔧 Component Correlation Matrix**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* (group=per_index_thruput OR group=queue OR group=tcpin_connections OR group=searchconcurrency){focus_context['search_filter']} | eval component=case(group=\"per_index_thruput\", \"indexing\", group=\"queue\", \"processing\", group=\"tcpin_connections\", \"input\", group=\"searchconcurrency\", \"search\", 1=1, \"other\") | timechart span=5m sum(eval(if(component=\"indexing\", kb, 0))) as indexing_kb count(eval(if(component=\"processing\", 1, null()))) as processing_activity count(eval(if(component=\"input\", 1, null()))) as input_connections count(eval(if(component=\"search\", 1, null()))) as search_activity",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

### Step 3.2: Error and Warning Pattern Detection
**🎯 Objective**: Correlate performance issues with error conditions and warnings

**🔧 Error Correlation Search**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal (source=*splunkd.log* OR source=*metrics.log*) (ERROR OR WARN OR \"timeout\" OR \"failed\" OR \"blocked\" OR \"queue full\" OR \"max size\"){focus_context['search_filter']} | rex field=_raw \"(?<error_type>ERROR|WARN).*?(?<error_component>IndexProcessor|TcpInputProcessor|IndexerService|BucketMover)\" | bucket _time span=10m | stats count by _time error_type error_component | where count>threshold_value",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

### Step 3.3: Saved Search Performance Impact
**🎯 Objective**: Analyze impact of saved searches on indexing performance

**🔧 List and Analyze Saved Searches**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "list_saved_searches",
    "arguments": {{
      "owner": null,
      "app": null,
      "sharing": null,
      "include_disabled": false
    }}
  }}
}}
```

**🔧 Search Concurrency Impact Analysis**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=searchconcurrency{focus_context['search_filter']} | timechart span=10m avg(active_hist_searches) as avg_active_searches avg(active_realtime_searches) as avg_realtime_searches | join _time [search index=_internal source=*metrics.log* group=per_index_thruput{focus_context['search_filter']} | timechart span=10m avg(avg_age) as avg_indexing_delay] | eval search_impact_score=case(avg_active_searches>10 AND avg_indexing_delay>60, \"high_impact\", avg_active_searches>5 AND avg_indexing_delay>30, \"moderate_impact\", 1=1, \"low_impact\")",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

---

## 📊 Phase 4: Validation & Impact Assessment

### Step 4.1: Performance Threshold Validation
**🎯 Objective**: Validate findings against established performance thresholds

**🔧 Threshold Compliance Check**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['search_filter']} | stats avg(avg_age) as avg_delay max(max_age) as max_delay sum(kb) as total_kb sum(eps) as total_eps by series | eval delay_threshold_status=case(avg_delay<30, \"PASS\", avg_delay<60, \"WARNING\", avg_delay<120, \"CRITICAL\", 1=1, \"SEVERE\") | eval throughput_efficiency=total_eps/total_kb | eval efficiency_threshold_status=case(throughput_efficiency>20, \"EXCELLENT\", throughput_efficiency>10, \"GOOD\", throughput_efficiency>5, \"ACCEPTABLE\", 1=1, \"POOR\")",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

### Step 4.2: Baseline Comparison Analysis
**🎯 Objective**: Compare current performance against historical baselines

**🔧 Historical Baseline Comparison**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "| union [search index=_internal source=*metrics.log* group=per_index_thruput{focus_context['search_filter']} earliest={earliest_time} latest={latest_time} | stats avg(avg_age) as current_avg_delay sum(kb) as current_total_kb by series] [search index=_internal source=*metrics.log* group=per_index_thruput{focus_context['search_filter']} earliest=-7d@d latest=-1d@d | stats avg(avg_age) as baseline_avg_delay sum(kb) as baseline_total_kb by series] | stats values(*) as * by series | eval delay_change_pct=round(((current_avg_delay-baseline_avg_delay)/baseline_avg_delay)*100,2) | eval throughput_change_pct=round(((current_total_kb-baseline_total_kb)/baseline_total_kb)*100,2) | eval performance_trend=case(delay_change_pct<-10, \"improving\", delay_change_pct>10, \"degrading\", 1=1, \"stable\")",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

---

## 🎯 Diagnostic Decision Matrix & Triage Framework

### 🟢 Healthy Performance Indicators
- **Indexing Delay**: Consistent <30 seconds average, <120 seconds maximum
- **Queue Sizes**: Consistently under 1MB across all processing queues
- **Throughput Stability**: Variance within ±15% of baseline rates
- **Resource Utilization**: CPU <70%, Memory <80%, Disk I/O within normal ranges
- **Error Rate**: <0.1% of processing events show errors or warnings

### 🟡 Performance Warning Conditions
- **Moderate Delays**: 30-60 seconds average delay, occasional spikes to 300 seconds
- **Queue Buildup**: 1-10MB sustained queue sizes in processing pipelines
- **Throughput Degradation**: 15-30% reduction from baseline throughput
- **Resource Pressure**: CPU 70-85%, Memory 80-90%, elevated disk latency
- **Intermittent Errors**: 0.1-1% error rate in processing or ingestion

### 🔴 Critical Performance Issues
- **High Throughput Volatility**: CV > 0.5
- **Processing Bottlenecks**: Queue depths > 10MB sustained
- **Network Failures**: Connection stability < 95%
- **Critical Error Rate**: Error rate > 1%
- **Resource Exhaustion**: CPU > 90%, Memory > 95%

---

## 🛠️ Targeted Remediation Strategies

### **Indexing Delay Issues** → Investigate:
1. **Disk I/O Performance**: Check for storage bottlenecks and disk latency
2. **Indexer Resource Allocation**: Verify CPU and memory allocation adequacy
3. **Hot/Warm Bucket Management**: Analyze bucket rolling and size configurations
4. **Network Latency**: Check forwarder-to-indexer network performance

### **Queue Buildup Problems** → Focus on:
1. **Processing Pipeline Tuning**: Adjust queue sizes and processing threads
2. **Search Load Balancing**: Distribute search load across search heads
3. **Batch Size Optimization**: Tune batch processing parameters
4. **Resource Scaling**: Consider horizontal or vertical scaling

### **Throughput Degradation** → Examine:
1. **Input Source Health**: Verify all expected data sources are active
2. **Network Connectivity**: Check for network issues affecting data flow
3. **Parsing Configuration**: Optimize props.conf and transforms.conf settings
4. **Indexer Clustering**: Verify cluster health and replication factor

### **Resource Exhaustion** → Address:
1. **Capacity Planning**: Evaluate need for additional indexer resources
2. **Search Scheduling**: Optimize saved search schedules and resource usage
3. **Data Retention**: Review data retention policies and storage efficiency
4. **System Optimization**: Fine-tune Splunk configuration parameters

---

## 📈 Continuous Monitoring Recommendations

### Automated Health Checks
Implement continuous monitoring using these key searches:

1. **Real-time Delay Monitoring**:
   - Alert when average delay >60 seconds for 10+ minutes
   - Dashboard showing delay trends by index and host

2. **Queue Size Monitoring**:
   - Alert when queue sizes >5MB sustained for 5+ minutes
   - Track processing pipeline health metrics

3. **Throughput Baseline Monitoring**:
   - Alert when throughput drops >20% below baseline
   - Monitor daily/weekly throughput patterns

### Performance Trending
- Establish monthly performance baselines
- Track capacity utilization trends
- Monitor search concurrency impact on indexing
- Correlate performance with infrastructure changes

---

## 🔍 Advanced Analysis Techniques

### Multi-Dimensional Correlation
Use correlation analysis to identify relationships between:
- **Search activity patterns** and indexing performance
- **Infrastructure metrics** and throughput degradation  
- **Data source changes** and processing efficiency
- **Time-based patterns** and resource utilization

### Predictive Analysis
Implement trend analysis to predict:
- **Capacity requirements** based on growth patterns
- **Performance degradation** before it impacts users
- **Resource exhaustion** timelines for proactive scaling
- **Optimal maintenance windows** based on usage patterns

### Root Cause Investigation
For identified issues, implement systematic root cause analysis:
1. **Timeline correlation** with system events and changes
2. **Component isolation** testing to identify specific bottlenecks
3. **Load testing** to validate capacity limits and breaking points
4. **Configuration validation** against best practices and recommendations

---

*This workflow provides comprehensive visibility into Splunk indexing performance with actionable insights for optimization and troubleshooting.*
"""

    def _generate_delay_analysis_section(
        self, 
        include_delay: bool, 
        focus_context: dict[str, Any], 
        earliest_time: str, 
        latest_time: str
    ) -> str:
        """Generate indexing delay analysis section."""
        if not include_delay:
            return ""
            
        return f"""

### Step 2.1a: Advanced Indexing Delay Analysis
**🎯 Objective**: Deep analysis of indexing delays and temporal patterns

**🔧 Delay Distribution Analysis**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['search_filter']} | eval delay_bucket=case(avg_age<10, \"<10s\", avg_age<30, \"10-30s\", avg_age<60, \"30-60s\", avg_age<120, \"1-2min\", avg_age<300, \"2-5min\", 1=1, \">5min\") | timechart span=30m count by delay_bucket | fillnull value=0",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

**🔧 Delay Hotspot Identification**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['search_filter']} | where avg_age>60 | stats count as delay_incidents sum(kb) as delayed_data_kb avg(avg_age) as avg_delay_duration by series _time span=1h | where delay_incidents>5 | sort -delayed_data_kb",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```

**🔧 Delay Root Cause Correlation**:
```json
{{
  "method": "tools/call",
  "params": {{
    "name": "run_splunk_search",
    "arguments": {{
      "query": "index=_internal source=*metrics.log* group=per_index_thruput{focus_context['search_filter']} | join _time [search index=_internal source=*metrics.log* group=queue | timechart span=1h avg(current_size) as avg_queue_size] | where avg_age>60 | eval delay_category=case(avg_queue_size>10240, \"queue_bottleneck\", avg_age>300, \"severe_delay\", 1=1, \"moderate_delay\") | stats count by delay_category | sort -count",
      "earliest_time": "{earliest_time}",
      "latest_time": "{latest_time}"
    }}
  }}
}}
```
"""

    def _generate_platform_instrumentation_section(self, include_platform: bool) -> str:
        """Generate platform instrumentation analysis section."""
        if not include_platform:
            return ""
            
        return """

### Step 0.2a: Platform Instrumentation Documentation
**🎯 Objective**: Understand platform instrumentation for performance analysis

**🔧 Platform Instrumentation Resources**:

1. **Platform Instrumentation Logs**:
```json
{
  "method": "resources/read",
  "params": {
    "uri": "splunk-docs://latest/troubleshooting/platform-instrumentation-logs"
  }
}
```

2. **Platform Instrumentation Searches**:
```json
{
  "method": "resources/read",
  "params": {
    "uri": "splunk-docs://latest/troubleshooting/platform-instrumentation-searches"
  }
}
```

**🧠 Context Integration**: Platform instrumentation provides detailed insight into indexing pipeline performance and resource utilization.
"""
