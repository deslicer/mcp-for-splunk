#!/usr/bin/env python3
"""
Demonstration script showing how to use the Splunk Triage Agent test suite.

This script demonstrates the complete workflow from validation to testing.
"""

import asyncio
import os
import sys
import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_banner(title: str):
    """Print a banner with the given title."""
    logger.info("="*80)
    logger.info(f"{title:^80}")
    logger.info("="*80)

def print_step(step_num: int, title: str):
    """Print a step header."""
    logger.info(f"\n🔹 Step {step_num}: {title}")
    logger.info("-" * 50)

async def demo_validation():
    """Demonstrate the validation process."""
    print_step(1, "Environment Validation")
    
    logger.info("First, let's validate that the environment is properly configured...")
    logger.info("This will check:")
    logger.info("  - Environment variables")
    logger.info("  - Python dependencies")
    logger.info("  - File structure")
    logger.info("  - Server connection")
    
    # Import and run validation
    try:
        from validate_setup import main as validate_main
        logger.info("\n🚀 Running validation...")
        await validate_main()
        return True
    except SystemExit as e:
        if e.code == 0:
            return True
        else:
            logger.error("❌ Validation failed. Please fix the issues and try again.")
            return False
    except Exception as e:
        logger.error(f"❌ Validation error: {e}")
        return False

async def demo_basic_test():
    """Demonstrate a basic test run."""
    print_step(2, "Basic Test Run")
    
    logger.info("Now let's run a basic test with the default scenario...")
    logger.info("This will test the 'missing data' scenario with comprehensive monitoring.")
    
    try:
        from test_agent import test_splunk_triage_agent
        
        logger.info("\n🚀 Running basic test...")
        await test_splunk_triage_agent()
        logger.info("✅ Basic test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Basic test failed: {e}")
        return False

async def demo_scenario_tests():
    """Demonstrate different test scenarios."""
    print_step(3, "Scenario Tests")
    
    logger.info("Let's demonstrate different test scenarios...")
    
    scenarios = [
        ("missing_data", "Missing data troubleshooting"),
        ("performance", "Performance issue analysis"),
        ("inputs", "Input/ingestion troubleshooting")
    ]
    
    results = {}
    
    for scenario_name, description in scenarios:
        logger.info(f"\n🎯 Testing scenario: {scenario_name}")
        logger.info(f"   Description: {description}")
        
        try:
            # Import the runner
            from run_test import run_test_scenario, get_test_scenarios
            
            # Get the scenario config
            scenario_configs = get_test_scenarios()
            if scenario_name in scenario_configs:
                config = scenario_configs[scenario_name]
                config.server_url = os.getenv('MCP_SERVER_URL', 'http://localhost:8000')
                
                logger.info(f"   Problem: {config.test_input}")
                logger.info(f"   Complexity: {config.complexity_level}")
                
                # Run the scenario (with shorter timeout for demo)
                config.timeout = 60.0  # 1 minute for demo
                
                success = await run_test_scenario(scenario_name, config)
                results[scenario_name] = success
                
                if success:
                    logger.info(f"✅ Scenario '{scenario_name}' passed")
                else:
                    logger.warning(f"⚠️  Scenario '{scenario_name}' failed")
            else:
                logger.error(f"❌ Scenario '{scenario_name}' not found")
                results[scenario_name] = False
                
        except Exception as e:
            logger.error(f"❌ Scenario '{scenario_name}' error: {e}")
            results[scenario_name] = False
    
    # Summary
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    logger.info(f"\n📊 Scenario Test Summary:")
    for name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"   {name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} scenarios passed")
    return passed == total

def demo_monitoring_features():
    """Demonstrate monitoring features."""
    print_step(4, "Monitoring Features")
    
    logger.info("The test suite includes comprehensive monitoring features:")
    logger.info("")
    
    logger.info("🔍 Progress Monitoring:")
    logger.info("  - Real-time progress updates from the agent")
    logger.info("  - Timeout detection (warns if no updates for 30+ seconds)")
    logger.info("  - Progress history tracking")
    logger.info("  - Gap analysis between updates")
    logger.info("")
    
    logger.info("🔗 Connection Monitoring:")
    logger.info("  - Health checks with periodic server pings")
    logger.info("  - Configurable timeout management")
    logger.info("  - Connection loss detection")
    logger.info("  - Background monitoring (non-blocking)")
    logger.info("")
    
    logger.info("📊 Result Analysis:")
    logger.info("  - Structured data display")
    logger.info("  - Step-by-step workflow summary")
    logger.info("  - Tool execution tracking")
    logger.info("  - Detailed timing analysis")
    logger.info("")
    
    logger.info("Example progress output:")
    logger.info("  [5.2s] Progress: 10.0% - Starting Splunk triage analysis")
    logger.info("  [12.8s] Progress: 40.0% - Agent analysis in progress")
    logger.info("  [25.1s] Progress: 70.0% - Specialist: Step 3: Checking permissions")
    logger.info("  [45.6s] Progress: 90.0% - Specialist: Step 8: Analyzing scheduled search")
    logger.info("  [52.3s] Progress: 100.0% - Analysis complete")

def demo_usage_examples():
    """Show usage examples."""
    print_step(5, "Usage Examples")
    
    logger.info("Here are some common usage patterns:")
    logger.info("")
    
    logger.info("🚀 Basic Usage:")
    logger.info("  python validate_setup.py          # Validate environment")
    logger.info("  python test_agent.py              # Run default test")
    logger.info("  python run_test.py missing_data   # Run specific scenario")
    logger.info("")
    
    logger.info("🎯 Scenario Testing:")
    logger.info("  python run_test.py performance    # Test performance issues")
    logger.info("  python run_test.py inputs         # Test input problems")
    logger.info("  python run_test.py indexing       # Test indexing issues")
    logger.info("  python run_test.py general        # Test general problems")
    logger.info("  python run_test.py all            # Run all scenarios")
    logger.info("")
    
    logger.info("🔧 Configuration:")
    logger.info("  MCP_SERVER_URL=http://localhost:8001 python test_agent.py")
    logger.info("  export TEST_TIMEOUT=600           # 10 minute timeout")
    logger.info("")
    
    logger.info("📋 Getting Help:")
    logger.info("  python run_test.py --help         # Show usage information")
    logger.info("  cat TEST_README.md                # Read full documentation")

async def main():
    """Main demonstration function."""
    print_banner("SPLUNK TRIAGE AGENT TEST SUITE DEMONSTRATION")
    
    logger.info("This demonstration will show you how to use the test suite")
    logger.info("to validate and test the Splunk Triage Agent with proper")
    logger.info("progress reporting and timeout handling.")
    logger.info("")
    
    # Check if this is a full demo or just information
    if len(sys.argv) > 1 and sys.argv[1] == "--info-only":
        logger.info("ℹ️  Running in information-only mode (no actual tests)")
        demo_monitoring_features()
        demo_usage_examples()
        
        logger.info("\n🎉 Demo completed! To run actual tests:")
        logger.info("  python demo_test.py")
        return
    
    # Full demo with actual tests
    logger.info("🚀 Starting full demonstration with actual tests...")
    logger.info("Note: This requires a running MCP server and proper environment setup.")
    logger.info("")
    
    try:
        # Step 1: Validation
        validation_success = await demo_validation()
        if not validation_success:
            logger.error("❌ Validation failed. Cannot continue with tests.")
            logger.info("💡 Try running: python validate_setup.py")
            return
        
        # Step 2: Basic test
        basic_test_success = await demo_basic_test()
        if not basic_test_success:
            logger.warning("⚠️  Basic test failed, but continuing with demonstration...")
        
        # Step 3: Scenario tests (optional, may be skipped if basic test failed)
        if basic_test_success:
            scenario_success = await demo_scenario_tests()
            if not scenario_success:
                logger.warning("⚠️  Some scenario tests failed")
        
        # Step 4 & 5: Information
        demo_monitoring_features()
        demo_usage_examples()
        
        # Final summary
        print_banner("DEMONSTRATION COMPLETE")
        logger.info("🎉 Test suite demonstration completed!")
        logger.info("")
        logger.info("You can now use the test suite to validate your")
        logger.info("Splunk Triage Agent implementation with:")
        logger.info("  - Comprehensive progress monitoring")
        logger.info("  - Connection timeout handling")
        logger.info("  - Detailed result analysis")
        logger.info("")
        logger.info("For more information, see TEST_README.md")
        
    except KeyboardInterrupt:
        logger.info("🛑 Demonstration interrupted by user")
    except Exception as e:
        logger.error(f"💥 Demonstration failed: {e}")
        logger.info("💡 For troubleshooting, see TEST_README.md")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Demonstration interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Demonstration error: {e}")
        sys.exit(1) 