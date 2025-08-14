#!/usr/bin/env python3
"""
Simple runner script for testing the Splunk Triage Agent.

This script provides different test scenarios and configurations.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import the test
sys.path.insert(0, str(Path(__file__).parent))

from test_agent import TestConfig, logger, test_splunk_triage_agent


def get_test_scenarios():
    """Get different test scenarios."""
    return {
        "missing_data": TestConfig(
            test_input="I cant find my data in index=cca_insights",
            focus_index="cca_insights",
            complexity_level="moderate",
        ),
        "performance": TestConfig(
            test_input="My searches are running very slowly and timing out", complexity_level="high"
        ),
        "inputs": TestConfig(
            test_input="No new data is being ingested from my forwarders",
            complexity_level="moderate",
        ),
        "indexing": TestConfig(
            test_input="There are delays in data indexing and high latency", complexity_level="high"
        ),
        "general": TestConfig(
            test_input="I'm experiencing various issues with my Splunk environment",
            complexity_level="moderate",
        ),
    }


async def run_test_scenario(scenario_name: str, config: TestConfig):
    """Run a specific test scenario."""

    logger.info(f"🎯 Running test scenario: {scenario_name.upper()}")
    logger.info(f"   Problem: {config.test_input}")
    logger.info(f"   Complexity: {config.complexity_level}")

    # Temporarily modify the global test config
    original_config = TestConfig()

    # Update the test_agent module's config
    import test_agent

    test_agent.TestConfig.__dict__.update(config.__dict__)

    try:
        await test_splunk_triage_agent()
        logger.info(f"✅ Scenario '{scenario_name}' completed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Scenario '{scenario_name}' failed: {e}")
        return False


async def main():
    """Main function to run tests."""

    # Check if server URL is provided
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
    logger.info(f"Using server URL: {server_url}")

    # Get command line arguments
    if len(sys.argv) > 1:
        scenario = sys.argv[1].lower()
    else:
        scenario = "missing_data"  # Default scenario

    scenarios = get_test_scenarios()

    if scenario == "all":
        # Run all scenarios
        logger.info("🚀 Running all test scenarios...")
        results = {}

        for name, config in scenarios.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"SCENARIO: {name.upper()}")
            logger.info(f"{'='*60}")

            config.server_url = server_url
            success = await run_test_scenario(name, config)
            results[name] = success

            if not success:
                logger.warning(f"⚠️  Scenario '{name}' failed, continuing with next...")

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("FINAL RESULTS SUMMARY")
        logger.info("=" * 60)

        passed = sum(1 for success in results.values() if success)
        total = len(results)

        for name, success in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            logger.info(f"   {name}: {status}")

        logger.info(f"\nOverall: {passed}/{total} scenarios passed")

        if passed == total:
            logger.info("🎉 All scenarios passed!")
        else:
            logger.warning(f"⚠️  {total - passed} scenarios failed")
            sys.exit(1)

    elif scenario in scenarios:
        # Run specific scenario
        config = scenarios[scenario]
        config.server_url = server_url

        success = await run_test_scenario(scenario, config)

        if success:
            logger.info("🎉 Test scenario completed successfully!")
        else:
            logger.error("💥 Test scenario failed!")
            sys.exit(1)

    else:
        logger.error(f"❌ Unknown scenario: {scenario}")
        logger.info("Available scenarios:")
        for name, config in scenarios.items():
            logger.info(f"  - {name}: {config.test_input}")
        logger.info("  - all: Run all scenarios")
        sys.exit(1)


def print_usage():
    """Print usage information."""
    print("Usage: python run_test.py [scenario]")
    print()
    print("Available scenarios:")
    scenarios = get_test_scenarios()
    for name, config in scenarios.items():
        print(f"  {name:12} - {config.test_input}")
    print("  all          - Run all scenarios")
    print()
    print("Environment variables:")
    print("  MCP_SERVER_URL - Server URL (default: http://localhost:8000)")
    print()
    print("Examples:")
    print("  python run_test.py missing_data")
    print("  python run_test.py performance")
    print("  python run_test.py all")
    print("  MCP_SERVER_URL=http://localhost:8001 python run_test.py inputs")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print_usage()
        sys.exit(0)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Test runner failed: {e}")
        sys.exit(1)
