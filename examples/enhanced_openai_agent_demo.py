#!/usr/bin/env python3
"""
Enhanced OpenAI Agent Demo

This demo showcases the enhanced OpenAI agent capabilities including:
- Resource integration and automatic fetching
- Workflow parsing and structured execution
- Access to MCP tools and documentation
- Systematic troubleshooting methodology

Run this script to see how the agent processes complex workflows.
"""

import asyncio
import logging
import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.tools.agents import OpenAIAgentTool, WorkflowParser
from fastmcp import Context

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_enhanced_agent():
    """Demonstrate the enhanced OpenAI agent capabilities."""
    
    print("🚀 Enhanced OpenAI Agent Demo")
    print("=" * 50)
    
    # Check if OpenAI API key is available
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable is required")
        print("Please set it in your .env file or environment")
        return
    
    try:
        # Create a mock context for demonstration
        class MockContext(Context):
            def __init__(self):
                self.messages = []
            
            async def info(self, message: str):
                print(f"ℹ️  {message}")
                self.messages.append(("info", message))
            
            async def error(self, message: str):
                print(f"❌ {message}")
                self.messages.append(("error", message))
        
        ctx = MockContext()
        
        # Initialize the enhanced agent
        print("\n1. Initializing Enhanced OpenAI Agent...")
        agent = OpenAIAgentTool("execute_openai_agent", "agents")
        
        # Demonstrate workflow parsing
        print("\n2. Demonstrating Workflow Parsing...")
        sample_workflow = """
# 🚀 Splunk Performance Diagnostic Workflow

## Executive Summary & Methodology
This workflow implements Splunk's official performance troubleshooting methodology using advanced diagnostic patterns.

### 🔄 Diagnostic Philosophy
Following **Observe-Orient-Decide-Act (OODA)** methodology for systematic analysis.

## Phase 1: Initial Assessment
### Step 1.1: System-Wide Throughput Analysis
**🎯 Objective**: Establish comprehensive system throughput patterns

```json
{
  "method": "tools/call",
  "params": {
    "name": "run_splunk_search",
    "arguments": {
      "query": "index=_internal source=*metrics.log* group=per_index_thruput | timechart span=1h sum(kb) as totalKB",
      "earliest_time": "-24h",
      "latest_time": "now"
    }
  }
}
```

### Step 1.2: Resource Documentation Review
**🎯 Objective**: Get relevant documentation

```json
{
  "method": "resources/read",
  "params": {
    "uri": "splunk-docs://latest/troubleshooting/performance"
  }
}
```

## 🎯 Diagnostic Decision Matrix

### 🟢 Healthy Performance Indicators
- **Indexing Delay**: Consistent <30 seconds average
- **Queue Sizes**: Consistently under 1MB
- **Throughput Stability**: Variance within ±15%

### 🟡 Performance Warning Conditions  
- **Moderate Delays**: 30-60 seconds average delay
- **Queue Buildup**: 1-10MB sustained queue sizes
- **Throughput Degradation**: 15-30% reduction

### 🔴 Critical Performance Issues
- **High Delays**: >60 seconds sustained
- **Queue Overflow**: >10MB sustained
- **Severe Degradation**: >30% throughput loss

## 🛠️ Targeted Remediation Strategies

### **Indexing Delay Issues** → Investigate:
1. **Disk I/O Performance**: Check storage bottlenecks
2. **Resource Allocation**: Verify CPU and memory
3. **Network Latency**: Check forwarder connections

### **Queue Buildup Problems** → Focus on:
1. **Pipeline Tuning**: Adjust queue sizes
2. **Load Balancing**: Distribute search load
3. **Resource Scaling**: Consider scaling options
"""
        
        parser = WorkflowParser()
        parsed = parser.parse_workflow(sample_workflow)
        
        print(f"   ✅ Parsed workflow: '{parsed.title}'")
        print(f"   📊 Found {len(parsed.phases)} phases with {sum(len(p.steps) for p in parsed.phases)} total steps")
        print(f"   🎯 Decision matrix categories: {list(parsed.decision_matrix.get('indicators', {}).keys())}")
        print(f"   🛠️  Remediation strategies: {list(parsed.remediation_strategies.keys())}")
        
        # Demonstrate structured prompt generation
        print("\n3. Generating Structured Prompt...")
        structured_prompt = parser.generate_structured_prompt(parsed)
        print(f"   ✅ Generated structured prompt ({len(structured_prompt)} characters)")
        print(f"   📝 Preview: {structured_prompt[:200]}...")
        
        # Demonstrate agent execution (mock)
        print("\n4. Demonstrating Agent Execution...")
        print("   🤖 Agent would execute with:")
        print("   - Structured workflow understanding")
        print("   - Resource fetching capabilities") 
        print("   - Tool integration")
        print("   - Decision matrix guidance")
        print("   - Remediation strategy references")
        
        # Show what the agent context would contain
        print("\n5. Agent Context Preview...")
        
        # Mock some context data
        mock_tools = [
            {"function": {"name": "run_splunk_search", "description": "Execute Splunk search queries"}},
            {"function": {"name": "list_indexes", "description": "List available Splunk indexes"}},
            {"function": {"name": "get_splunk_health", "description": "Check Splunk server health"}}
        ]
        
        mock_resources = [
            {"uri": "splunk-docs://troubleshooting", "category": "documentation"},
            {"uri": "splunk://config/props", "category": "configuration"}
        ]
        
        print(f"   🔧 Available tools: {len(mock_tools)} (run_splunk_search, list_indexes, etc.)")
        print(f"   📚 Available resources: {len(mock_resources)} (docs, configs)")
        print(f"   🎯 Workflow structure: {len(parsed.phases)} phases, {sum(len(p.steps) for p in parsed.phases)} steps")
        
        # Example of what an enhanced prompt would look like
        print("\n6. Enhanced Prompt Structure Preview...")
        enhanced_preview = f"""
# Splunk Troubleshooting Expert Agent

## Your Mission: {parsed.title}
{parsed.description[:100]}...

## Methodology  
{parsed.methodology[:100]}...

## Structured Workflow ({len(parsed.phases)} phases, {sum(len(p.steps) for p in parsed.phases)} steps)
[Detailed phase and step breakdown...]

## Available Resources and Context
### 📚 Referenced Documentation
[Resource content would be fetched and included...]

### 🔧 Available Tools ({len(mock_tools)} tools)
[Tool descriptions and capabilities...]

## Execution Guidelines
1. Follow the Structured Workflow
2. Use Referenced Documentation  
3. Execute Tools Strategically
4. Apply Decision Matrix
5. Implement Remediation Strategies

Begin your systematic analysis now...
"""
        
        print(f"   📄 Enhanced prompt preview ({len(enhanced_preview)} characters):")
        print(f"   {enhanced_preview[:300]}...")
        
        print("\n✅ Enhanced OpenAI Agent Demo Complete!")
        print("\n🎯 Key Enhancements:")
        print("   • Resource integration and automatic fetching")
        print("   • Workflow parsing and structured execution")
        print("   • Decision matrix guidance")
        print("   • Remediation strategy references")
        print("   • Systematic OODA methodology")
        print("   • Enhanced context with tools and documentation")
        
        print("\n🚀 To use the enhanced agent:")
        print("   1. Set OPENAI_API_KEY in your environment")
        print("   2. Use the execute_openai_agent tool with any component")
        print("   3. The agent will automatically parse workflows and fetch resources")
        print("   4. Get structured, evidence-based troubleshooting analysis")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"❌ Demo failed: {e}")


if __name__ == "__main__":
    asyncio.run(demo_enhanced_agent()) 