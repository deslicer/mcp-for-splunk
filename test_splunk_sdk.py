#!/usr/bin/env python3
"""
Comprehensive test script for Splunk SDK functionality.

This script tests various Splunk SDK capabilities using environment credentials
and the get_splunk_service function from the MCP server.
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import splunklib.results as results
from dotenv import load_dotenv
from fastmcp import Context
from splunklib import client

from src.client.splunk_client import get_splunk_config, get_splunk_service
from src.core.base import BaseTool

# Load environment variables
load_dotenv()


class SplunkSDKTester(BaseTool):
    """Test class that inherits from BaseTool to use get_splunk_service method."""

    def __init__(self):
        super().__init__("splunk_sdk_tester", "Test Splunk SDK functionality")
        self.service = None

    async def execute(self, ctx: Context, **kwargs) -> dict[str, Any]:
        """Required method from BaseTool - not used in this test"""
        pass


async def test_connection():
    """Test basic Splunk connection."""
    print("�� Testing Splunk Connection...")
    print("=" * 50)

    try:
        # Test direct connection using environment variables
        config = get_splunk_config()
        print(f"Host: {config['host']}")
        print(f"Port: {config['port']}")
        print(f"Username: {config['username']}")
        print(f"Scheme: {config['scheme']}")
        print(f"SSL Verify: {config['verify']}")

        service = get_splunk_service()
        print("✅ Connection successful!")

        # Test service info
        info = service.info
        print(f"Splunk Version: {info['version']}")
        print(f"Server Name: {info['serverName']}")
        print(f"Build: {info['build']}")
        print(f"License State: {info.get('licenseState', 'Unknown')}")

        return service

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None


async def test_indexes(service: client.Service):
    """Test index operations."""
    print("\n📚 Testing Index Operations...")
    print("=" * 50)

    try:
        indexes = service.indexes
        print(f"Total indexes: {len(indexes)}")

        # List all indexes
        print("\nAvailable indexes:")
        for index in indexes:
            try:
                # Get index info safely
                total_events = getattr(index, "totalEventCount", "Unknown")
                earliest_time = getattr(index, "minTime", "Unknown")
                latest_time = getattr(index, "maxTime", "Unknown")

                print(f"  - {index.name}: {total_events} events ({earliest_time} to {latest_time})")
            except Exception as e:
                print(f"  - {index.name}: Error getting details - {e}")

        return True

    except Exception as e:
        print(f"❌ Index operations failed: {e}")
        return False


async def test_search_execution(service: client.Service):
    """Test search execution."""
    print("\n🔎 Testing Search Execution...")
    print("=" * 50)

    try:
        # Simple search
        search_query = '| makeresults | eval message="Hello from Splunk SDK test!"'
        print(f"Executing search: {search_query}")

        job = service.jobs.create(search_query)
        print(f"Job created: {job.sid}")

        # Wait for job completion
        while not job.is_done():
            await asyncio.sleep(0.5)
            job.refresh()

        print(f"Job completed. Result count: {job.resultCount}")

        # Get results
        if int(job.resultCount) > 0:
            results_reader = results.ResultsReader(job.results())

            print("\nResults:")
            for result in results_reader:
                if isinstance(result, dict):
                    print(f"  - {result}")
                else:
                    print(f"  - Message: {result}")

        # Clean up
        job.cancel()

        return True

    except Exception as e:
        print(f"❌ Search execution failed: {e}")
        return False


async def test_with_base_tool():
    """Test using the BaseTool get_splunk_service method."""
    print("\n🔧 Testing with BaseTool get_splunk_service...")
    print("=" * 50)

    try:
        # Create a test context (mock)
        class MockLifespanContext:
            def __init__(self):
                self.is_connected = True
                self.service = None
                self.client_config = None

        class MockRequestContext:
            def __init__(self):
                self.lifespan_context = MockLifespanContext()

        class MockContext:
            def __init__(self):
                self.request_context = MockRequestContext()

        # Create tester instance
        tester = SplunkSDKTester()

        # Mock context
        ctx = MockContext()

        # Test with environment config (should work)
        service = await tester.get_splunk_service(ctx)
        print("✅ Successfully got service using BaseTool method")

        # Test basic info
        info = service.info
        print(f"Connected to: {info['serverName']} (v{info['version']})")

        return service

    except Exception as e:
        print(f"❌ BaseTool service test failed: {e}")
        return None


if __name__ == "__main__":
    # Check if .env file exists
    if not os.path.exists(".env"):
        print("❌ No .env file found. Please create one with your Splunk credentials:")
        print("SPLUNK_HOST=your_splunk_host")
        print("SPLUNK_PORT=8089")
        print("SPLUNK_USERNAME=your_username")
        print("SPLUNK_PASSWORD=your_password")
        print("SPLUNK_SCHEME=https")
        print("SPLUNK_VERIFY_SSL=false")
        sys.exit(1)

    async def run_basic_tests():
        print("🚀 Starting Basic Splunk SDK Tests")
        print("=" * 50)
        print(f"Test started at: {datetime.now()}")
        print()

        # Test 1: Basic connection
        service = await test_connection()
        if not service:
            print("\n❌ Cannot proceed with other tests - connection failed")
            return

        # Test 2: BaseTool integration
        await test_with_base_tool()

        # Test 3: Index operations
        await test_indexes(service)

        # Test 4: Search execution
        await test_search_execution(service)

        print(f"\n✅ Basic tests completed at: {datetime.now()}")

    # Run basic tests
    asyncio.run(run_basic_tests())
