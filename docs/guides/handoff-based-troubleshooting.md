# Handoff-Based Dynamic Troubleshooting with OpenAI Agents SDK

This guide explains the enhanced handoff-based troubleshooting architecture that leverages the OpenAI Agents SDK for intelligent agent coordination and comprehensive tracing.

## 🎯 Overview

The handoff-based dynamic troubleshooting agent provides a sophisticated orchestration system that uses specialized micro-agents to diagnose and resolve Splunk issues. Unlike traditional parallel execution, this approach uses the OpenAI Agents SDK handoff pattern for intelligent routing and maintains context throughout the entire diagnostic process.

## 🏗️ Architecture

### Core Components

1. **🎯 Orchestrating Agent**: Central coordinator that analyzes problems and hands off to specialists
2. **🔍 Specialized Micro-Agents**: Individual agents for specific diagnostic tasks
3. **📊 Comprehensive Tracing**: End-to-end visibility using OpenAI Agents SDK
4. **🔍 Context Inspection**: Optimization insights and efficiency scoring

### Handoff Flow

```
User Problem → Orchestrating Agent → Specialist Selection → Handoffs → Result Synthesis
```

## 🤖 Specialized Micro-Agents

### Missing Data Specialists

- **📄 License Verification Agent**: License status, edition limitations, violations
- **📂 Index Verification Agent**: Index accessibility and configuration
- **🔐 Permissions Agent**: User roles and role-based access control
- **⏰ Time Range Agent**: Data availability and timestamp issues
- **🔗 Forwarder Connectivity Agent**: Connection status and data flow
- **🔍 Search Head Configuration Agent**: Distributed search and cluster health

### Performance Analysis Specialists

- **💻 System Resource Agent**: CPU, memory, disk usage analysis
- **⚡ Search Concurrency Agent**: Search performance and concurrency limits
- **📊 Indexing Performance Agent**: Pipeline performance and throughput

### Health Check Specialists

- **🌐 Connectivity Agent**: Server connectivity and service availability
- **📈 Data Availability Agent**: Recent ingestion and basic data checks

## 🔄 Handoff Pattern Benefits

### Intelligent Routing
- **Problem Analysis**: Orchestrator analyzes symptoms to determine appropriate specialists
- **Dynamic Selection**: Automatically engages relevant agents based on issue type
- **Context Preservation**: Maintains diagnostic context across all handoffs

### Comprehensive Tracing
- **OpenAI Agents SDK Integration**: Native trace support with the agents framework
- **Agent Interaction Tracking**: Visibility into which specialists are engaged
- **Performance Metrics**: Execution times and engagement statistics
- **Turn Analysis**: Detailed view of conversation flows

### Context Optimization
- **Input Analysis**: Tracks what context is sent to agents
- **Efficiency Scoring**: Calculates context efficiency (0-1 scale)
- **Optimization Recommendations**: Suggests improvements for better performance

## 📊 Context Inspection

The system provides detailed insights into context being sent to agents:

### Metrics Tracked
- **Input Length**: Total characters in orchestration input
- **Problem Description Ratio**: Proportion of input that is problem description
- **Context Specificity**: Score based on focus areas provided
- **Efficiency Score**: Overall context optimization rating

### Optimization Recommendations
- Input length optimization (500-5000 characters ideal)
- Context specificity improvements
- Time range refinements
- Complexity level adjustments

## 🚀 Usage Examples

### Missing Data Analysis
```python
result = await agent.execute(
    ctx=ctx,
    problem_description="Dashboard shows no data for last 2 hours",
    earliest_time="-4h",
    latest_time="now",
    focus_index="security",
    workflow_type="auto"  # Auto-detects missing data issue
)
```

### Performance Analysis
```python
result = await agent.execute(
    ctx=ctx,
    problem_description="Searches running very slowly since yesterday",
    earliest_time="-24h",
    latest_time="now",
    complexity_level="advanced",
    workflow_type="performance"  # Forces performance workflow
)
```

## 📋 Result Structure

The handoff-based agent returns comprehensive results:

```python
{
    "status": "success",
    "coordinator_type": "handoff_based_missing_data",
    "orchestration_analysis": "Detailed analysis from orchestrator",
    "workflow_execution": {
        "workflow_id": "handoff_missing_data",
        "execution_method": "handoff_orchestration",
        "turns_executed": 15,
        "agents_engaged": 6
    },
    "handoff_metadata": {
        "orchestrating_agent": "Splunk Troubleshooting Orchestrator",
        "available_specialists": ["License Verification Agent", ...],
        "handoff_approach": "Intelligent routing based on problem analysis"
    },
    "context_inspection": {
        "orchestration_input": {
            "total_length": 2847,
            "problem_description_length": 245
        },
        "context_optimization": {
            "context_efficiency_score": 0.85,
            "recommendations": ["Context appears well-optimized"]
        }
    }
}
```

## 🔧 Configuration

### Environment Variables
```bash
# Required
OPENAI_API_KEY=your_openai_api_key

# Optional
OPENAI_MODEL=gpt-4o                    # Default model
OPENAI_TEMPERATURE=0.7                 # Default temperature
OPENAI_MAX_TOKENS=4000                 # Default max tokens
OPENAI_MAX_RETRIES=3                   # Retry configuration
```

### Agent Configuration
```python
config = AgentConfig(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o",
    temperature=0.7,
    max_tokens=4000
)
```

## 📈 Performance Characteristics

### Execution Patterns
- **Sequential Handoffs**: Agents are engaged based on problem analysis
- **Context Preservation**: Diagnostic context maintained across handoffs
- **Intelligent Coordination**: Orchestrator synthesizes all specialist findings

### Tracing Overhead
- **Minimal Impact**: OpenAI Agents SDK tracing is lightweight
- **Rich Insights**: Comprehensive visibility into agent interactions
- **Debugging Support**: Detailed traces for troubleshooting

## 🔍 Context Validation

### What Context is Sent to Agents

The system tracks and optimizes context sent to specialist agents:

1. **Problem Description**: User's issue description
2. **Diagnostic Context**: Time ranges, focus areas, complexity level
3. **Specialist Instructions**: Role-specific guidance and available tools
4. **Handoff Strategy**: Workflow-specific engagement patterns

### Context Efficiency Factors

- **Problem Description Ratio**: 20-40% of total input (optimal)
- **Context Specificity**: Focus areas and targeted parameters
- **Input Length**: 500-5000 characters (optimal range)
- **Tool Availability**: Relevant tools for each specialist

## 🎯 Best Practices

### Problem Descriptions
- **Be Specific**: Include error messages, symptoms, and affected components
- **Provide Context**: Time when issue started, scope of impact
- **Include Environment**: Distributed setup, forwarder details, user roles

### Parameter Optimization
- **Use Focus Areas**: Specify `focus_index` and `focus_host` when applicable
- **Appropriate Time Ranges**: Use specific ranges for time-bounded issues
- **Complexity Levels**: 
  - `basic`: Quick checks and connectivity
  - `moderate`: Standard diagnostic workflow
  - `advanced`: Comprehensive analysis with detailed metrics

### Workflow Selection
- **Auto-Detection**: Let the system analyze and route automatically
- **Forced Workflows**: Use specific types when you know the issue category
- **Missing Data**: For data visibility and access issues
- **Performance**: For search speed and resource problems
- **Health Check**: For basic connectivity and availability

## 🔄 Migration from Workflow Manager

### Key Differences
- **Handoffs vs Parallel**: Sequential specialist engagement vs parallel task execution
- **Context Preservation**: Maintained across handoffs vs task-specific contexts
- **Tracing Integration**: Native OpenAI Agents SDK vs custom tracing
- **Intelligent Routing**: Problem-based specialist selection vs predefined workflows

### Migration Benefits
- **Better Tracing**: End-to-end visibility of agent interactions
- **Context Optimization**: Insights into what context is being sent
- **Flexible Routing**: Dynamic specialist selection based on problem analysis
- **Simplified Architecture**: Fewer moving parts with OpenAI Agents SDK

## 🚀 Getting Started

1. **Install Dependencies**:
   ```bash
   pip install openai-agents
   ```

2. **Set Environment Variables**:
   ```bash
   export OPENAI_API_KEY=your_api_key
   ```

3. **Run Test Script**:
   ```bash
   python examples/test_handoff_troubleshooting.py
   ```

4. **Integrate with MCP Server**:
   ```python
   from src.tools.agents.dynamic_troubleshoot_agent import DynamicTroubleshootAgentTool
   
   agent = DynamicTroubleshootAgentTool("dynamic_troubleshoot", "troubleshooting")
   ```

## 📊 Monitoring and Debugging

### Context Inspection Logs
```
AGENT CONTEXT INSPECTION
Total orchestration input length: 2847 characters
Available specialists: 8
Context efficiency score: 0.85
Specialist agents:
  - License Verification Agent
  - Index Verification Agent
  - Permissions Agent
  - ...
```

### Tracing Output
- **OpenAI Agents SDK Traces**: Native integration with agents framework
- **Handoff Tracking**: Which specialists are engaged and when
- **Performance Metrics**: Execution times and turn counts
- **Context Flow**: How diagnostic context flows between agents

This handoff-based approach provides superior traceability, context optimization, and intelligent routing compared to traditional parallel execution patterns. 