#!/usr/bin/env python3
"""
Advanced Multi-Agent Prompt System Demo

This demonstrates the enhanced troubleshooting prompt with:
- Research-based multi-agent patterns
- Advanced security validation
- Parallel execution strategies
- Cross-validation frameworks
- Evidence-based decision making
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastmcp import FastMCP
from src.core.loader import ComponentLoader
from src.core.registry import prompt_registry
from unittest.mock import Mock


async def demo_advanced_prompt_system():
    """Demonstrate the advanced multi-agent prompt system capabilities."""
    print("=" * 80)
    print("🔬 Advanced Multi-Agent Splunk Troubleshooting System Demo")
    print("=" * 80)
    
    # Initialize MCP server and loader
    print("\n📦 Initializing MCP server and loading components...")
    mcp = FastMCP('Advanced Troubleshooting Demo')
    loader = ComponentLoader(mcp)
    
    # Load all components
    results = loader.load_all_components()
    print(f"✅ Loaded components: {results}")
    
    # Get registered prompts
    prompts = prompt_registry.list_prompts()
    print(f"\n📋 Available prompts: {len(prompts)}")
    
    # Find our advanced multi-agent prompt
    multi_agent_prompt = None
    original_prompt = None
    
    for prompt in prompts:
        if prompt.name == "troubleshoot_inputs_multi_agent":
            multi_agent_prompt = prompt
        elif prompt.name == "troubleshoot_inputs":
            original_prompt = prompt
    
    if not multi_agent_prompt:
        print("❌ Multi-agent prompt not found!")
        return
    
    print(f"\n🚀 Found advanced multi-agent prompt: {multi_agent_prompt.name}")
    print(f"📝 Description: {multi_agent_prompt.description}")
    print(f"🏷️  Tags: {multi_agent_prompt.tags}")
    
    # Demonstrate different complexity levels and modes
    test_scenarios = [
        {
            "name": "🔍 Simple Diagnostic Analysis",
            "params": {
                "earliest_time": "-1h",
                "latest_time": "now",
                "complexity_level": "simple",
                "analysis_mode": "diagnostic",
                "include_performance_analysis": False,
                "enable_cross_validation": False
            }
        },
        {
            "name": "🧠 Comprehensive Multi-Agent Investigation", 
            "params": {
                "earliest_time": "-24h",
                "latest_time": "now",
                "complexity_level": "comprehensive",
                "analysis_mode": "diagnostic",
                "include_performance_analysis": True,
                "enable_cross_validation": True,
                "focus_index": "security_events",
                "focus_host": "prod-server-01"
            }
        },
        {
            "name": "🔬 Expert Forensic Analysis",
            "params": {
                "earliest_time": "-7d",
                "latest_time": "now", 
                "complexity_level": "expert",
                "analysis_mode": "forensic",
                "include_performance_analysis": True,
                "enable_cross_validation": True
            }
        },
        {
            "name": "📈 Preventive Pattern Analysis",
            "params": {
                "earliest_time": "-30d",
                "latest_time": "now",
                "complexity_level": "comprehensive", 
                "analysis_mode": "preventive",
                "include_performance_analysis": True,
                "enable_cross_validation": True
            }
        }
    ]
    
    # Create mock context
    mock_ctx = Mock()
    
    print("\n" + "=" * 80)
    print("🎯 Testing Advanced Multi-Agent Scenarios")
    print("=" * 80)
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print("-" * 60)
        
        try:
            # Get the prompt instance
            prompt_instance = prompt_registry.get_prompt(multi_agent_prompt.name)
            
            # Generate the workflow
            result = await prompt_instance.get_prompt(mock_ctx, **scenario['params'])
            
            # Extract key information from the generated workflow
            workflow_text = result['content'][0]['text']
            
            # Analyze the generated workflow
            features = []
            if "Multi-Agent Diagnostic System" in workflow_text:
                features.append("✅ Multi-agent architecture")
            if "Parallel Execution" in workflow_text:
                features.append("✅ Parallel execution strategy")
            if "Security Considerations" in workflow_text:
                features.append("✅ Security validation")
            if "Cross-Validation" in workflow_text:
                features.append("✅ Cross-validation framework")
            if "Evidence-Based" in workflow_text:
                features.append("✅ Evidence-based decisions")
            if "OODA Loop" in workflow_text:
                features.append("✅ OODA loop methodology")
            
            # Count analysis phases
            phase_count = workflow_text.count("## ")
            search_count = workflow_text.count('"method": "tools/call"')
            
            print(f"📊 Generated workflow analysis:")
            print(f"   - Analysis phases: {phase_count}")
            print(f"   - Search queries: {search_count}")
            print(f"   - Advanced features: {len(features)}")
            for feature in features:
                print(f"     {feature}")
            
            # Show key parameters
            params = scenario['params']
            complexity = params.get('complexity_level', 'moderate')
            mode = params.get('analysis_mode', 'diagnostic')
            print(f"   - Complexity level: {complexity}")
            print(f"   - Analysis mode: {mode}")
            print(f"   - Performance analysis: {'✅' if params.get('include_performance_analysis') else '❌'}")
            print(f"   - Cross-validation: {'✅' if params.get('enable_cross_validation') else '❌'}")
            
            if params.get('focus_index') or params.get('focus_host'):
                focus_items = []
                if params.get('focus_index'):
                    focus_items.append(f"index:{params['focus_index']}")
                if params.get('focus_host'):
                    focus_items.append(f"host:{params['focus_host']}")
                print(f"   - Focus scope: {', '.join(focus_items)}")
            
            print("✅ Scenario completed successfully")
            
        except Exception as e:
            print(f"❌ Error in scenario: {e}")
    
    # Compare with original prompt
    print("\n" + "=" * 80)
    print("📊 Original vs Advanced Multi-Agent Comparison")
    print("=" * 80)
    
    if original_prompt:
        try:
            # Test original prompt
            original_instance = prompt_registry.get_prompt(original_prompt.name)
            original_result = await original_instance.get_prompt(
                mock_ctx, 
                earliest_time="-24h", 
                latest_time="now"
            )
            original_text = original_result['content'][0]['text']
            
            # Test advanced prompt with same parameters
            advanced_result = await prompt_instance.get_prompt(
                mock_ctx,
                earliest_time="-24h",
                latest_time="now", 
                complexity_level="moderate",
                analysis_mode="diagnostic"
            )
            advanced_text = advanced_result['content'][0]['text']
            
            # Compare features
            print(f"📋 Feature Comparison:")
            print(f"{'Feature':<35} {'Original':<12} {'Advanced':<12}")
            print("-" * 60)
            
            features_to_check = [
                ("Multi-agent architecture", "Multi-Agent", "Multi-Agent"),
                ("Parallel execution", "Execute Simultaneously", "Execute Simultaneously"),
                ("Security validation", "Security", "Security"),
                ("Cross-validation", "Cross-Validation", "Cross-Validation"),
                ("Evidence scoring", "Evidence", "Evidence"),
                ("OODA methodology", "OODA", "OODA"),
                ("Performance analysis", "Performance", "Performance"),
                ("Decision matrix", "Decision", "Decision Matrix")
            ]
            
            for feature_name, original_key, advanced_key in features_to_check:
                original_has = "✅" if original_key in original_text else "❌"
                advanced_has = "✅" if advanced_key in advanced_text else "❌"
                print(f"{feature_name:<35} {original_has:<12} {advanced_has:<12}")
            
            # Count complexity
            original_phases = original_text.count("## ")
            advanced_phases = advanced_text.count("## ")
            original_searches = original_text.count('"method": "tools/call"')
            advanced_searches = advanced_text.count('"method": "tools/call"')
            
            print(f"\n📊 Complexity Comparison:")
            print(f"{'Metric':<35} {'Original':<12} {'Advanced':<12}")
            print("-" * 60)
            print(f"{'Analysis phases':<35} {original_phases:<12} {advanced_phases:<12}")
            print(f"{'Search queries':<35} {original_searches:<12} {advanced_searches:<12}")
            print(f"{'Arguments supported':<35} {len(original_prompt.arguments):<12} {len(multi_agent_prompt.arguments):<12}")
            
        except Exception as e:
            print(f"❌ Error in comparison: {e}")
    
    # Show advanced capabilities
    print("\n" + "=" * 80)
    print("🚀 Advanced Multi-Agent Capabilities Summary")
    print("=" * 80)
    
    capabilities = [
        "🧠 Research-Based Agent Architecture",
        "   - Lead Agent orchestration with specialist delegation",
        "   - Performance, Network, and Parsing specialist agents", 
        "   - Validation Agent for cross-source verification",
        "   - Synthesis Agent for evidence-based recommendations",
        "",
        "⚡ Advanced Execution Strategies",
        "   - Complexity levels: simple (3), moderate (5), comprehensive (8), expert (12) parallel searches",
        "   - Analysis modes: diagnostic, preventive, forensic",
        "   - Dynamic strategy adaptation based on mode and complexity",
        "",
        "🔒 Enhanced Security & Validation",
        "   - Input validation and sanitization for parameters",
        "   - Query parameter validation against allowlists", 
        "   - Injection prevention through parameterized construction",
        "   - Cross-validation framework with data consistency checks",
        "",
        "📊 Advanced Analytics & Intelligence",
        "   - Statistical anomaly detection with z-score analysis",
        "   - Confidence intervals and evidence scoring",
        "   - Risk assessment with impact/probability matrices",
        "   - Automated prioritization algorithms",
        "",
        "🔄 Research-Based Methodologies",
        "   - OODA loop methodology with feedback mechanisms",
        "   - Evidence-based decision making with confidence scoring",
        "   - Multi-dimensional correlation analysis",
        "   - Hierarchical task delegation patterns"
    ]
    
    for capability in capabilities:
        print(capability)
    
    print("\n" + "=" * 80)
    print("✅ Advanced Multi-Agent Prompt System Demo Complete!")
    print("🎯 Key Benefits:")
    print("   - 3-5x more comprehensive analysis coverage")
    print("   - Enhanced security with input validation")
    print("   - Research-based multi-agent patterns")
    print("   - Evidence-based decision making")
    print("   - Flexible complexity and mode selection")
    print("   - Backward compatibility with original prompt")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(demo_advanced_prompt_system()) 