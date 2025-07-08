"""
Splunk Agent Patterns Demo

This demo showcases the three OpenAI agent patterns implemented for Splunk troubleshooting:
1. Hierarchical Triage + Specialist Handoff Pattern
2. Parallel Multi-Component Analysis Pattern  
3. Iterative Reflection + Self-Improvement Pattern

Each pattern demonstrates different approaches to complex troubleshooting workflows.
"""

import asyncio
import os
import logging
import json
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock FastMCP context for demo
class MockContext:
    """Mock context for demonstration purposes."""
    
    async def info(self, message: str):
        print(f"ℹ️  {message}")
    
    async def error(self, message: str):
        print(f"❌ {message}")


async def demo_triage_pattern():
    """Demonstrate the hierarchical triage + specialist handoff pattern."""
    print("\n" + "="*80)
    print("🔍 DEMO 1: Hierarchical Triage + Specialist Handoff Pattern")
    print("="*80)
    
    try:
        from src.tools.agents.splunk_triage_agent import SplunkTriageAgentTool
        
        # Initialize the triage agent
        triage_agent = SplunkTriageAgentTool("execute_splunk_triage_agent", "agents")
        
        # Test scenarios for different specialist routing
        test_scenarios = [
            {
                "name": "Data Ingestion Issue",
                "description": "We're missing data from our web servers. The logs show that data was being sent but it's not appearing in our main index. Universal forwarders seem to be connected but throughput has dropped significantly.",
                "expected_specialist": "Inputs Specialist"
            },
            {
                "name": "Performance Problem", 
                "description": "Searches are running very slowly and users are complaining about dashboard load times. CPU usage is high and we're seeing search concurrency warnings in the logs.",
                "expected_specialist": "Performance Specialist"
            },
            {
                "name": "Indexing Delay",
                "description": "There's a significant delay between when events occur and when they become searchable. The indexing queues show high latency and bucket management seems inefficient.",
                "expected_specialist": "Indexing Specialist"
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n📋 Testing Scenario: {scenario['name']}")
            print(f"Problem: {scenario['description']}")
            print(f"Expected Routing: {scenario['expected_specialist']}")
            
            # Execute triage agent
            result = await triage_agent.execute(
                ctx=MockContext(),
                problem_description=scenario['description'],
                earliest_time="-4h",
                latest_time="now",
                complexity_level="moderate"
            )
            
            if result['status'] == 'success':
                print(f"✅ Routed to: {result['last_agent']}")
                print(f"📊 Execution Summary:")
                print(f"   - Items processed: {result['execution_items']}")
                print(f"   - Conversation length: {result['conversation_length']}")
                print(f"   - Agent response preview: {result['agent_response'][:200]}...")
            else:
                print(f"❌ Error: {result['error']}")
    
    except ImportError as e:
        print(f"⚠️  Triage agent pattern not available: {e}")
        print("   Install OpenAI agents SDK: pip install openai-agents")
    except Exception as e:
        print(f"❌ Demo error: {e}")


async def demo_parallel_pattern():
    """Demonstrate the parallel multi-component analysis pattern."""
    print("\n" + "="*80)
    print("⚡ DEMO 2: Parallel Multi-Component Analysis Pattern")
    print("="*80)
    
    try:
        from src.tools.agents.parallel_analysis_agent import ParallelAnalysisAgentTool
        
        # Initialize the parallel analysis agent
        parallel_agent = ParallelAnalysisAgentTool("execute_parallel_analysis_agent", "agents")
        
        # Test different analysis scopes
        test_scopes = [
            {
                "scope": "performance",
                "description": "Focus on performance-related components",
                "expected_components": ["infrastructure", "application", "data_ingestion"]
            },
            {
                "scope": "security", 
                "description": "Focus on security-related components",
                "expected_components": ["security", "network", "infrastructure"]
            },
            {
                "scope": "comprehensive",
                "description": "Analyze all system components",
                "expected_components": ["infrastructure", "application", "data_ingestion", "security", "network"]
            }
        ]
        
        for test_scope in test_scopes:
            print(f"\n📊 Testing Analysis Scope: {test_scope['scope']}")
            print(f"Description: {test_scope['description']}")
            print(f"Expected Components: {', '.join(test_scope['expected_components'])}")
            
            # Execute parallel analysis
            result = await parallel_agent.execute(
                ctx=MockContext(),
                analysis_scope=test_scope['scope'],
                earliest_time="-2h",
                latest_time="now",
                max_parallel_agents=2,  # Limit for demo
                timeout_minutes=5       # Short timeout for demo
            )
            
            if result['status'] == 'success':
                print(f"✅ Analysis completed successfully")
                print(f"📈 Execution Summary:")
                print(f"   - Components analyzed: {result['execution_summary']['total_components']}")
                print(f"   - Successful analyses: {result['execution_summary']['successful_analyses']}")
                print(f"   - Failed analyses: {result['execution_summary']['failed_analyses']}")
                print(f"   - Timeout analyses: {result['execution_summary']['timeout_analyses']}")
                
                # Show component results summary
                print(f"\n🔍 Component Results:")
                for comp_name, comp_result in result['component_results'].items():
                    status_emoji = "✅" if comp_result['status'] == 'success' else "❌"
                    print(f"   {status_emoji} {comp_name}: {comp_result['status']} ({comp_result['execution_time']:.2f}s)")
                
                print(f"\n📋 Synthesis Preview: {result['synthesized_analysis'][:300]}...")
            else:
                print(f"❌ Error: {result['error']}")
    
    except ImportError as e:
        print(f"⚠️  Parallel analysis pattern not available: {e}")
        print("   Install OpenAI agents SDK: pip install openai-agents")
    except Exception as e:
        print(f"❌ Demo error: {e}")


async def demo_reflection_pattern():
    """Demonstrate the iterative reflection + self-improvement pattern."""
    print("\n" + "="*80)
    print("🔄 DEMO 3: Iterative Reflection + Self-Improvement Pattern")
    print("="*80)
    
    try:
        from src.tools.agents.reflection_agent import ReflectionAgentTool
        
        # Initialize the reflection agent
        reflection_agent = ReflectionAgentTool("execute_reflection_agent", "agents")
        
        # Test problem for iterative improvement
        test_problem = """
        Our Splunk environment is experiencing intermittent issues that are difficult to pinpoint. 
        Users report that sometimes searches are slow, sometimes data appears to be missing, and 
        occasionally the system seems unresponsive. The issues don't follow a clear pattern and 
        seem to affect different components at different times. We need a thorough analysis that 
        can identify root causes and provide confidence in the findings.
        """
        
        print(f"🔍 Testing Iterative Analysis Problem:")
        print(f"Problem: {test_problem.strip()}")
        
        # Execute reflection-based analysis
        result = await reflection_agent.execute(
            ctx=MockContext(),
            problem_description=test_problem,
            earliest_time="-6h",
            latest_time="now",
            max_reflection_cycles=2,  # Limit for demo
            confidence_threshold=0.75,
            enable_deep_validation=True
        )
        
        if result['status'] == 'success':
            print(f"✅ Reflection analysis completed successfully")
            print(f"🔄 Reflection Summary:")
            print(f"   - Total cycles: {result['metrics']['total_cycles']}")
            print(f"   - Improvement iterations: {result['metrics']['improvement_iterations']}")
            print(f"   - Final confidence: {result['metrics']['final_confidence']:.2f}")
            print(f"   - Critical issues identified: {result['metrics']['critical_issues_identified']}")
            print(f"   - Actionable recommendations: {result['metrics']['actionable_recommendations']}")
            
            # Show reflection cycles
            print(f"\n📈 Reflection Cycles:")
            for cycle in result['reflection_cycles']:
                print(f"   Cycle {cycle['cycle_number']}: {cycle['phase']} (confidence: {cycle['confidence_score']:.2f})")
                if cycle['critique_points']:
                    print(f"     Critique: {cycle['critique_points'][0][:100]}...")
                if cycle['improvements']:
                    print(f"     Improvement: {cycle['improvements'][0][:100]}...")
            
            print(f"\n📋 Final Analysis Preview: {result['final_analysis'][:300]}...")
            print(f"\n🔍 Validation Preview: {result['validation_results'][:200] if result['validation_results'] else 'No validation performed'}...")
            print(f"\n📊 Synthesis Preview: {result['synthesis'][:300]}...")
        else:
            print(f"❌ Error: {result['error']}")
    
    except ImportError as e:
        print(f"⚠️  Reflection pattern not available: {e}")
        print("   Install OpenAI agents SDK: pip install openai-agents")
    except Exception as e:
        print(f"❌ Demo error: {e}")


async def demo_pattern_comparison():
    """Compare the different agent patterns and their use cases."""
    print("\n" + "="*80)
    print("📊 PATTERN COMPARISON & RECOMMENDATIONS")
    print("="*80)
    
    patterns = [
        {
            "name": "Hierarchical Triage + Specialist Handoff",
            "best_for": [
                "Clear, categorizable problems",
                "Domain-specific expertise required",
                "Efficient routing of different issue types",
                "Scalable troubleshooting workflows"
            ],
            "when_to_use": "When you have well-defined problem categories and specialized knowledge domains",
            "example": "Data ingestion issues → Inputs Specialist, Performance issues → Performance Specialist"
        },
        {
            "name": "Parallel Multi-Component Analysis", 
            "best_for": [
                "Complex system-wide issues",
                "Time-sensitive comprehensive analysis",
                "Multi-faceted problems requiring different perspectives",
                "Capacity planning and health assessments"
            ],
            "when_to_use": "When you need comprehensive analysis across multiple system components simultaneously",
            "example": "System health check analyzing infrastructure, security, performance, and data flow in parallel"
        },
        {
            "name": "Iterative Reflection + Self-Improvement",
            "best_for": [
                "Ambiguous or complex problems",
                "High-stakes analysis requiring confidence",
                "Learning and improving analysis quality",
                "Problems requiring multiple perspectives"
            ],
            "when_to_use": "When problem complexity requires iterative refinement and high confidence in findings",
            "example": "Intermittent system issues requiring careful analysis, critique, and validation"
        }
    ]
    
    for pattern in patterns:
        print(f"\n🎯 {pattern['name']}")
        print(f"   Best for:")
        for use_case in pattern['best_for']:
            print(f"     • {use_case}")
        print(f"   When to use: {pattern['when_to_use']}")
        print(f"   Example: {pattern['example']}")
    
    print(f"\n💡 SELECTION GUIDELINES:")
    print(f"   1. Use TRIAGE pattern for routine, categorizable issues")
    print(f"   2. Use PARALLEL pattern for comprehensive system analysis")  
    print(f"   3. Use REFLECTION pattern for complex, ambiguous problems")
    print(f"   4. Combine patterns for complex scenarios (e.g., Triage → Parallel → Reflection)")


async def main():
    """Run all agent pattern demonstrations."""
    print("🚀 Splunk Agent Patterns Demonstration")
    print("This demo showcases OpenAI agent patterns for Splunk troubleshooting")
    
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  OPENAI_API_KEY environment variable not set")
        print("   The demos will show the pattern structure but won't execute actual agents")
        print("   Set OPENAI_API_KEY to run full demonstrations")
    
    # Run pattern demonstrations
    await demo_triage_pattern()
    await demo_parallel_pattern()
    await demo_reflection_pattern()
    await demo_pattern_comparison()
    
    print("\n" + "="*80)
    print("✅ Agent Patterns Demo Complete!")
    print("="*80)
    print("\nNext Steps:")
    print("1. Install OpenAI agents SDK: pip install openai-agents")
    print("2. Set OPENAI_API_KEY environment variable")
    print("3. Configure Splunk connection in your .env file")
    print("4. Run individual patterns based on your troubleshooting needs")
    print("\nFor production use, integrate these patterns into your MCP server configuration.")


if __name__ == "__main__":
    asyncio.run(main()) 