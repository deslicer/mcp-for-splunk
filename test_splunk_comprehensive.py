#!/usr/bin/env python3
"""Comprehensive Splunk SDK test suite."""

import asyncio
import os
import sys
from datetime import datetime
from typing import Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv
from fastmcp import Context
from splunklib import client

from src.client.splunk_client import get_splunk_config, get_splunk_service
from src.core.base import BaseTool

load_dotenv()


class SplunkSDKTester(BaseTool):
    def __init__(self):
        super().__init__("splunk_sdk_tester", "Test Splunk SDK functionality")

    async def execute(self, ctx: Context, **kwargs) -> dict[str, Any]:
        pass


class TestResults:
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()

    def add_result(self, test_name: str, success: bool, details: str = ""):
        self.results[test_name] = {
            "success": success,
            "details": details,
            "timestamp": datetime.now(),
        }

    def print_summary(self):
        end_time = datetime.now()
        duration = end_time - self.start_time

        passed = sum(1 for r in self.results.values() if r["success"])
        total = len(self.results)

        print("\n" + "=" * 70)
        print("🏁 TEST SUMMARY")
        print("=" * 70)
        print(f"Duration: {duration}")
        print(f"Tests: {passed}/{total} passed")
        print()

        for test_name, result in self.results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{test_name:25} {status}")
            if result["details"]:
                print(f"{'':27} {result['details']}")


async def test_connection(test_results: TestResults):
    """Test basic Splunk connection."""
    print("🔌 Testing Connection...")
    try:
        config = get_splunk_config()
        print(f"Connecting to {config['host']}:{config['port']}")

        service = get_splunk_service()
        info = service.info

        print(f"✅ Connected to {info['serverName']} v{info['version']}")
        test_results.add_result("connection", True, f"{info['serverName']} v{info['version']}")
        return service

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        test_results.add_result("connection", False, str(e))
        return None


async def test_indexes(service: client.Service, test_results: TestResults):
    """Test index operations."""
    print("\n📚 Testing Indexes...")
    try:
        indexes = service.indexes
        print(f"Found {len(indexes)} indexes")

        for i, index in enumerate(list(indexes)[:5]):
            events = getattr(index, "totalEventCount", "Unknown")
            print(f"  {i + 1}. {index.name}: {events} events")

        test_results.add_result("indexes", True, f"Found {len(indexes)} indexes")
        return True
    except Exception as e:
        test_results.add_result("indexes", False, str(e))
        return False


async def test_search(service: client.Service, test_results: TestResults):
    """Test search execution."""
    print("\n🔎 Testing Search...")
    try:
        query = '| makeresults | eval message="SDK Test"'
        job = service.jobs.create(query)

        while not job.is_done():
            await asyncio.sleep(0.5)
            job.refresh()

        print(f"✅ Search completed: {job.resultCount} results")
        job.cancel()

        test_results.add_result("search", True, f"{job.resultCount} results")
        return True
    except Exception as e:
        test_results.add_result("search", False, str(e))
        return False


async def test_base_tool(test_results: TestResults):
    """Test BaseTool integration."""
    print("\n🔧 Testing BaseTool...")
    try:

        class MockContext:
            def __init__(self):
                self.request_context = type(
                    "obj",
                    (object,),
                    {
                        "lifespan_context": type(
                            "obj",
                            (object,),
                            {"is_connected": True, "service": None, "client_config": None},
                        )()
                    },
                )()

        tester = SplunkSDKTester()
        ctx = MockContext()

        service = await tester.get_splunk_service(ctx)
        info = service.info

        print(f"✅ BaseTool connection to {info['serverName']}")
        test_results.add_result("base_tool", True, f"Connected to {info['serverName']}")
        return True
    except Exception as e:
        test_results.add_result("base_tool", False, str(e))
        return False


async def run_tests():
    """Run all tests."""
    print("🚀 Splunk SDK Test Suite")
    print("=" * 50)

    test_results = TestResults()

    # Run tests
    service = await test_connection(test_results)
    if service:
        await test_base_tool(test_results)
        await test_indexes(service, test_results)
        await test_search(service, test_results)

    test_results.print_summary()


if __name__ == "__main__":
    if not os.path.exists(".env"):
        print("❌ Create .env file with Splunk credentials")
        sys.exit(1)

    asyncio.run(run_tests())
