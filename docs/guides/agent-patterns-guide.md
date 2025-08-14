# OpenAI Agent Patterns for Splunk Troubleshooting

This guide explains how we've implemented three powerful OpenAI agent patterns to transform your Splunk troubleshooting workflows from complex monolithic prompts into intelligent, collaborative agent systems.

## Overview

Based on our analysis of your troubleshooting prompts, we've identified that your workflows exhibit sophisticated multi-phase diagnostic patterns that are perfect for the OpenAI agents SDK. We've implemented three key patterns:

1. **Hierarchical Triage + Specialist Handoff** - Intelligent routing to domain experts
2. **Parallel Multi-Component Analysis** - Simultaneous analysis across system components
3. **Iterative Reflection + Self-Improvement** - Continuous refinement and validation

## Pattern 1: Hierarchical Triage + Specialist Handoff

### What It Solves
Your current troubleshooting prompts require different expertise for different problem types. Instead of one massive prompt trying to handle everything, this pattern routes problems to specialized agents.

### How It Works
```
User Problem → Triage Agent → Specialist Agent → Solution
```

**Triage Agent** analyzes the problem and routes to:
- **Inputs Specialist** - Data ingestion, forwarder connectivity, parsing issues
- **Performance Specialist** - System resources, search performance, capacity planning
- **Indexing Specialist** - Indexing delays, bucket management, storage optimization
- **General Specialist** - Overall health, configuration validation, cross-component issues

### Implementation Highlights

```python
# Triage agent with intelligent routing
triage_agent = Agent(
    name="Splunk Diagnostic Triage Agent",
    instructions=prompt_with_handoff_instructions("""
    You are a Splunk expert triage agent. Route problems based on:

    🔍 Input/Ingestion Issues → Handoff to Splunk Inputs Specialist
    ⚡ Performance Issues → Handoff to Splunk Performance Specialist
    📊 Indexing Issues → Handoff to Splunk Indexing Specialist
    🏥 General/Health Issues → Handoff to Splunk General Specialist
    """),
    handoffs=[inputs_specialist, performance_specialist, indexing_specialist, general_specialist]
)
```

### Best Use Cases
- **Routine troubleshooting** with clear problem categories
- **Scalable support workflows** where different expertise is needed
- **Training and knowledge transfer** with specialist domain focus
- **Efficient resource allocation** routing problems to right experts

### Example Scenarios
- "Data missing from web servers" → Routes to **Inputs Specialist**
- "Searches running slowly, high CPU" → Routes to **Performance Specialist**
- "Indexing delays, bucket issues" → Routes to **Indexing Specialist**

## Pattern 2: Parallel Multi-Component Analysis

### What It Solves
Your complex troubleshooting workflows analyze multiple system components. Instead of sequential analysis, this pattern runs specialist agents in parallel for comprehensive system assessment.

### How It Works
```
Problem → Orchestrator → [Infrastructure Agent, Application Agent, Data Agent, Security Agent, Network Agent] → Synthesis
```

**Parallel Specialists:**
- **Infrastructure Agent** - CPU, memory, disk I/O, system resources
- **Application Agent** - Search performance, dashboards, user experience
- **Data Ingestion Agent** - Volume trends, source/sourcetype analysis, forwarder health
- **Security Agent** - Authentication, access patterns, security events
- **Network Agent** - Connectivity, transmission rates, network performance

### Implementation Highlights

```python
# Execute multiple agents in parallel with controlled concurrency
async def _execute_parallel_analysis(self, components, max_parallel=3):
    semaphore = asyncio.Semaphore(max_parallel)

    async def run_component_analysis(component):
        async with semaphore:
            return await self._run_single_component_analysis(component)

    tasks = [run_component_analysis(comp) for comp in components]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Best Use Cases
- **Comprehensive system health checks** across all components
- **Complex multi-faceted problems** requiring different perspectives
- **Time-sensitive analysis** where speed is critical
- **Capacity planning and optimization** assessments

### Analysis Scopes
- **Performance Scope** - Infrastructure + Application + Data Ingestion
- **Security Scope** - Security + Network + Infrastructure
- **Comprehensive Scope** - All components analyzed simultaneously

## Pattern 3: Iterative Reflection + Self-Improvement

### What It Solves
Your troubleshooting workflows involve complex reasoning that benefits from self-critique and iterative improvement. This pattern implements a reflection cycle where agents improve their analysis through multiple iterations.

### How It Works
```
Problem → Analyst → Critic → Improvement → Validator → Synthesizer → Final Analysis
    ↑                                                                        ↓
    └─────────────────── Iteration Cycle ──────────────────────────────────┘
```

**Reflection Agents:**
- **Analyst Agent** - Performs initial/iterative analysis with reasoning
- **Critic Agent** - Reviews analysis, identifies gaps and weaknesses
- **Validator Agent** - Cross-checks findings with independent verification
- **Synthesizer Agent** - Consolidates insights into final recommendations

### Implementation Highlights

```python
# Reflection cycle with confidence tracking
for cycle_num in range(1, max_reflection_cycles + 1):
    # Phase 1: Analysis
    analysis_result = await self._execute_analysis_phase(current_analysis)

    # Phase 2: Self-Critique
    critique_result = await self._execute_critique_phase(analysis_result)

    # Phase 3: Improvement
    if cycle_num < max_reflection_cycles:
        improvement_result = await self._execute_improvement_phase(analysis_result, critique_result)
        current_analysis = improvement_result

    # Check confidence threshold
    if confidence_score >= confidence_threshold:
        break
```

### Best Use Cases
- **Ambiguous or complex problems** without clear root causes
- **High-stakes analysis** requiring high confidence levels
- **Learning and improvement** of troubleshooting quality over time
- **Complex reasoning** requiring multiple perspectives and validation

### Reflection Metrics
- **Confidence Scoring** - Track analysis reliability across iterations
- **Improvement Tracking** - Monitor how analysis quality improves
- **Validation Success** - Measure accuracy of findings through verification

## Mapping Your Current Prompts to Agent Patterns

### Your Existing Workflow Patterns → Agent Patterns

| Your Current Approach | Recommended Agent Pattern | Why It Fits |
|----------------------|---------------------------|-------------|
| **Multi-phase diagnostic workflows** | Hierarchical Triage | Clear phase separation maps to specialist handoffs |
| **Parallel execution capabilities** | Parallel Analysis | Multiple concurrent searches become parallel agents |
| **Agent role delegation** | All Patterns | Specialist roles become dedicated agents |
| **Cross-component correlation** | Parallel + Reflection | Synthesis across components with iterative improvement |
| **Complex decision matrices** | Triage + Reflection | Decision trees for routing + confidence validation |

### Example: Performance Troubleshooting Transformation

**Before (Monolithic Prompt):**
```
Your current TroubleshootPerformancePrompt with 4-5 phases, multiple steps,
parallel searches, and complex decision logic all in one large prompt.
```

**After (Agent Pattern):**
```python
# Option 1: Triage Pattern
problem → triage_agent → performance_specialist → detailed_analysis

# Option 2: Parallel Pattern
problem → [infrastructure_agent, application_agent, data_agent] → synthesis

# Option 3: Reflection Pattern
problem → analyst → critic → improvement → validator → final_analysis
```

## Usage Examples

### Quick Start: Triage Pattern
```python
from src.tools.agents import SplunkTriageAgentTool

triage_agent = SplunkTriageAgentTool("execute_splunk_triage_agent", "agents")

result = await triage_agent.execute(
    ctx=ctx,
    problem_description="Searches are slow and CPU usage is high",
    earliest_time="-4h",
    latest_time="now"
)
# → Routes to Performance Specialist automatically
```

### Comprehensive Analysis: Parallel Pattern
```python
from src.tools.agents import ParallelAnalysisAgentTool

parallel_agent = ParallelAnalysisAgentTool("execute_parallel_analysis_agent", "agents")

result = await parallel_agent.execute(
    ctx=ctx,
    analysis_scope="comprehensive",
    earliest_time="-24h",
    latest_time="now",
    max_parallel_agents=3
)
# → Analyzes infrastructure, application, data, security, network in parallel
```

### Deep Analysis: Reflection Pattern
```python
from src.tools.agents import ReflectionAgentTool

reflection_agent = ReflectionAgentTool("execute_reflection_agent", "agents")

result = await reflection_agent.execute(
    ctx=ctx,
    problem_description="Intermittent issues across multiple components",
    max_reflection_cycles=3,
    confidence_threshold=0.8,
    enable_deep_validation=True
)
# → Iteratively improves analysis until high confidence achieved
```

## Pattern Selection Guide

### Decision Matrix

| Problem Characteristics | Recommended Pattern | Reasoning |
|-------------------------|-------------------|-----------|
| **Clear issue category** (inputs, performance, etc.) | Triage | Efficient routing to right specialist |
| **System-wide assessment** needed | Parallel | Comprehensive coverage across components |
| **Ambiguous/complex** problem | Reflection | Iterative refinement and validation |
| **Time-sensitive** analysis | Parallel | Fastest comprehensive coverage |
| **High-stakes** decision | Reflection | Maximum confidence through validation |
| **Routine troubleshooting** | Triage | Scalable and efficient |
| **Learning/training** scenario | Reflection | Shows reasoning and improvement process |

### Combining Patterns

For complex scenarios, combine patterns:

```python
# Complex workflow: Triage → Parallel → Reflection
1. Triage determines it's a performance issue
2. Parallel analysis across performance-related components
3. Reflection validates and refines findings
```

## Integration with Your Current System

### Replacing Existing Prompts

Your current prompts can be gradually replaced:

1. **Start with Triage** - Replace your routing logic with triage agent
2. **Add Parallel** - Replace complex multi-component analysis
3. **Enhance with Reflection** - Add to critical/complex scenarios

### Maintaining Compatibility

The agent patterns integrate with your existing MCP tools:

```python
# Agents use your existing Splunk tools
@function_tool
async def run_splunk_search(query: str) -> str:
    search_tool = tool_registry.get_tool("run_oneshot_search")
    return await search_tool.execute(ctx, query=query)
```

## Performance and Scalability

### Efficiency Gains

| Pattern | Speed | Resource Usage | Scalability |
|---------|-------|----------------|-------------|
| **Triage** | Fast | Low | High - routes efficiently |
| **Parallel** | Fast | Medium | High - controlled concurrency |
| **Reflection** | Slower | Higher | Medium - iterative process |

### Best Practices

1. **Use Triage for 80% of routine issues** - Most efficient
2. **Reserve Parallel for comprehensive analysis** - When you need full picture
3. **Apply Reflection to complex/critical issues** - When quality matters most
4. **Set appropriate timeouts** - Prevent runaway processes
5. **Monitor agent performance** - Track success rates and execution times

## Next Steps

1. **Install Dependencies**
   ```bash
   pip install openai-agents
   ```

2. **Set Environment Variables**
   ```bash
   export OPENAI_API_KEY="your-key-here"
   ```

3. **Run the Demo**
   ```bash
   python examples/splunk_agent_patterns_demo.py
   ```

4. **Start with Triage Pattern** - Replace your most common troubleshooting workflows

5. **Gradually Expand** - Add parallel and reflection patterns for complex scenarios

6. **Monitor and Optimize** - Track which patterns work best for your use cases

## Resources

- **Demo Script**: `examples/splunk_agent_patterns_demo.py`
- **Agent Implementations**: `src/tools/agents/`
- **OpenAI Agents Documentation**: https://openai.github.io/openai-agents-python/
- **Pattern Examples**: https://github.com/openai/openai-agents-python/tree/main/examples/agent_patterns

The agent patterns transform your complex troubleshooting prompts into intelligent, collaborative systems that can route problems efficiently, analyze comprehensively in parallel, and continuously improve through reflection. This represents a significant evolution from monolithic prompts to sophisticated agent orchestration.
