#!/usr/bin/env python3
"""
Comprehensive test script for Splunk SDK functionality.

This script tests various Splunk SDK capabilities using environment credentials
and the get_splunk_service function from the MCP server.

Features tested:
- Basic connection and authentication
- Index operations and data access
- Search execution and job management
- Real-time searches
- Apps and configuration
- Users and roles
- Saved searches
- Data inputs monitoring
- Internal metrics and logs
- BaseTool integration
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


class TestResults:
    """Track and format test results."""

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
        """Print comprehensive test summary."""
        end_time = datetime.now()
        duration = end_time - self.start_time

        passed = sum(1 for r in self.results.values() if r["success"])
        total = len(self.results)

        print("\n" + "=" * 70)
        print("🏁 COMPREHENSIVE TEST SUMMARY")
        print("=" * 70)
        print(f"Duration: {duration}")
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed / total * 100):.1f}%" if total > 0 else "N/A")
        print()

        for test_name, result in self.results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{test_name:30} {status}")
            if result["details"]:
                print(f"{'':32} {result['details']}")

        print("=" * 70)

        if passed == total:
            print("🎉 All tests passed! Splunk SDK is working correctly.")
        else:
            print(f"⚠️  {total - passed} test(s) failed. Check the output above for details.")


async def test_connection(test_results: TestResults):
    """Test basic Splunk connection."""
    print("🔌 Testing Splunk Connection...")
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
        version = info["version"]
        server_name = info["serverName"]
        build = info["build"]
        license_state = info.get("licenseState", "Unknown")

        print(f"Splunk Version: {version}")
        print(f"Server Name: {server_name}")
        print(f"Build: {build}")
        print(f"License State: {license_state}")

        test_results.add_result("connection", True, f"Connected to {server_name} v{version}")
        return service

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        test_results.add_result("connection", False, str(e))
        return None


async def test_indexes(service: client.Service, test_results: TestResults):
    """Test index operations."""
    print("\n📚 Testing Index Operations...")
    print("=" * 50)

    try:
        indexes = service.indexes
        total_indexes = len(indexes)
        print(f"Total indexes: {total_indexes}")

        # List all indexes with details
        print("\nAvailable indexes:")
        accessible_indexes = 0

        for index in indexes:
            try:
                # Get index info safely
                total_events = getattr(index, "totalEventCount", "Unknown")
                earliest_time = getattr(index, "minTime", "Unknown")
                latest_time = getattr(index, "maxTime", "Unknown")
                size_mb = getattr(index, "currentDBSizeMB", "Unknown")

                print(
                    f"  - {index.name}: {total_events} events, {size_mb}MB "
                    f"({earliest_time} to {latest_time})"
                )
                accessible_indexes += 1

            except Exception as e:
                print(f"  - {index.name}: Error getting details - {e}")

        # Test accessing specific index
        main_index_details = "Not found"
        if "main" in indexes:
            try:
                main_index = indexes["main"]
                main_index_details = f"Events: {getattr(main_index, 'totalEventCount', 'Unknown')}"
                print(f"\nMain index: {main_index_details}")
            except Exception as e:
                main_index_details = f"Error: {e}"

        success = accessible_indexes > 0
        details = f"Found {accessible_indexes}/{total_indexes} accessible indexes"
        test_results.add_result("indexes", success, details)

        return success

    except Exception as e:
        print(f"❌ Index operations failed: {e}")
        test_results.add_result("indexes", False, str(e))
        return False


async def test_apps(service: client.Service, test_results: TestResults):
    """Test app operations."""
    print("\n📱 Testing App Operations...")
    print("=" * 50)

    try:
        apps = service.apps
        total_apps = len(apps)
        print(f"Total apps: {total_apps}")

        # Count app states
        enabled_apps = 0
        visible_apps = 0

        print("\nInstalled apps (showing first 10):")
        for i, app in enumerate(apps[:10]):
            try:
                visible = getattr(app, "visible", False)
                disabled = getattr(app, "disabled", False)
                version = getattr(app, "version", "Unknown")

                status = "enabled" if not disabled else "disabled"
                visibility = "visible" if visible else "hidden"

                if not disabled:
                    enabled_apps += 1
                if visible:
                    visible_apps += 1

                print(f"  {i + 1:2}. {app.name} (v{version}) - {status}, {visibility}")

            except Exception as e:
                print(f"  {i + 1:2}. {app.name}: Error getting details - {e}")

        if total_apps > 10:
            print(f"  ... and {total_apps - 10} more apps")

        success = total_apps > 0
        details = f"Found {total_apps} apps ({enabled_apps} enabled, {visible_apps} visible)"
        test_results.add_result("apps", success, details)

        return success

    except Exception as e:
        print(f"❌ App operations failed: {e}")
        test_results.add_result("apps", False, str(e))
        return False


async def test_users_and_roles(service: client.Service, test_results: TestResults):
    """Test user and role operations."""
    print("\n👥 Testing Users and Roles...")
    print("=" * 50)

    try:
        # Test users
        users = service.users
        total_users = len(users)
        print(f"Total users: {total_users}")

        print("\nUsers (showing first 5):")
        for i, user in enumerate(users[:5]):
            try:
                realname = getattr(user, "realname", "Unknown")
                roles = getattr(user, "roles", [])
                email = getattr(user, "email", "Unknown")

                print(f"  {i + 1}. {user.name} ({realname}) - Roles: {', '.join(roles)}")
                if email != "Unknown" and email:
                    print(f"     Email: {email}")
            except Exception as e:
                print(f"  {i + 1}. {user.name}: Error getting details - {e}")

        # Test roles
        roles = service.roles
        total_roles = len(roles)
        print(f"\nTotal roles: {total_roles}")

        print("\nRoles (showing first 5):")
        for i, role in enumerate(roles[:5]):
            try:
                capabilities = getattr(role, "capabilities", [])
                print(f"  {i + 1}. {role.name}: {len(capabilities)} capabilities")
            except Exception as e:
                print(f"  {i + 1}. {role.name}: Error getting details - {e}")

        success = total_users > 0 and total_roles > 0
        details = f"Found {total_users} users and {total_roles} roles"
        test_results.add_result("users_roles", success, details)

        return success

    except Exception as e:
        print(f"❌ User/Role operations failed: {e}")
        test_results.add_result("users_roles", False, str(e))
        return False


async def test_saved_searches(service: client.Service, test_results: TestResults):
    """Test saved search operations."""
    print("\n💾 Testing Saved Searches...")
    print("=" * 50)

    try:
        saved_searches = service.saved_searches
        total_searches = len(saved_searches)
        print(f"Total saved searches: {total_searches}")

        # Count scheduled vs manual
        scheduled_count = 0

        print("\nSaved searches (showing first 5):")
        for i, search in enumerate(saved_searches[:5]):
            try:
                search_query = getattr(search, "search", "Unknown")
                is_scheduled = getattr(search, "is_scheduled", False)

                if is_scheduled:
                    scheduled_count += 1

                # Truncate long searches
                if len(search_query) > 80:
                    search_query = search_query[:77] + "..."

                status = "scheduled" if is_scheduled else "manual"
                print(f"  {i + 1}. {search.name} ({status})")
                print(f"     Query: {search_query}")

            except Exception as e:
                print(f"  {i + 1}. {search.name}: Error getting details - {e}")

        success = total_searches >= 0  # Even 0 saved searches is valid
        details = f"Found {total_searches} saved searches ({scheduled_count} scheduled)"
        test_results.add_result("saved_searches", success, details)

        return success

    except Exception as e:
        print(f"❌ Saved search operations failed: {e}")
        test_results.add_result("saved_searches", False, str(e))
        return False


async def test_jobs(service: client.Service, test_results: TestResults):
    """Test job operations."""
    print("\n🔍 Testing Job Operations...")
    print("=" * 50)

    try:
        jobs = service.jobs
        job_count = len(jobs)
        print(f"Current jobs: {job_count}")

        running_jobs = 0
        completed_jobs = 0

        # List current jobs
        if job_count > 0:
            print("\nCurrent jobs (showing first 3):")
            for i, job in enumerate(jobs[:3]):
                try:
                    search_query = getattr(job, "search", "Unknown")
                    is_done = getattr(job, "is_done", False)
                    result_count = getattr(job, "resultCount", "Unknown")

                    if is_done:
                        completed_jobs += 1
                    else:
                        running_jobs += 1

                    # Truncate long searches
                    if len(search_query) > 60:
                        search_query = search_query[:57] + "..."

                    status = "completed" if is_done else "running"
                    print(f"  {i + 1}. {job.sid} ({status}) - {result_count} results")
                    print(f"     Query: {search_query}")

                except Exception as e:
                    print(f"  {i + 1}. {job.sid}: Error getting details - {e}")
        else:
            print("No current jobs found.")

        success = True  # Always succeed - even 0 jobs is valid
        details = f"Found {job_count} jobs ({running_jobs} running, {completed_jobs} completed)"
        test_results.add_result("jobs", success, details)

        return success

    except Exception as e:
        print(f"❌ Job operations failed: {e}")
        test_results.add_result("jobs", False, str(e))
        return False


async def test_search_execution(service: client.Service, test_results: TestResults):
    """Test search execution."""
    print("\n🔎 Testing Search Execution...")
    print("=" * 50)

    try:
        # Simple search
        search_query = '| makeresults | eval message="Hello from Splunk SDK test!", timestamp=now()'
        print(f"Executing search: {search_query}")

        job = service.jobs.create(search_query)
        print(f"Job created: {job.sid}")

        # Wait for job completion with timeout
        timeout = 30  # 30 seconds timeout
        elapsed = 0

        while not job.is_done() and elapsed < timeout:
            await asyncio.sleep(0.5)
            elapsed += 0.5
            job.refresh()

        if elapsed >= timeout:
            job.cancel()
            test_results.add_result("search_execution", False, "Search timed out after 30 seconds")
            return False

        result_count = int(job.resultCount)
        print(f"Job completed. Result count: {result_count}")

        # Get results
        results_found = False
        if result_count > 0:
            results_reader = results.ResultsReader(job.results())

            print("\nResults:")
            for result in results_reader:
                if isinstance(result, dict):
                    print(f"  - {result}")
                    results_found = True
                else:
                    print(f"  - Message: {result}")

        # Clean up
        job.cancel()

        success = result_count > 0 and results_found
        details = f"Executed search successfully, got {result_count} results"
        test_results.add_result("search_execution", success, details)

        return success

    except Exception as e:
        print(f"❌ Search execution failed: {e}")
        test_results.add_result("search_execution", False, str(e))
        return False


async def test_real_time_search(service: client.Service, test_results: TestResults):
    """Test real-time search capabilities."""
    print("\n⏱️ Testing Real-time Search...")
    print("=" * 50)

    try:
        # Real-time search for the last 30 seconds
        search_query = "search * earliest=-30s | head 5"
        print(f"Executing real-time search: {search_query}")

        job = service.jobs.create(
            search_query, search_mode="realtime", latest_time="rt", earliest_time="-30s"
        )

        print(f"Real-time job created: {job.sid}")

        # Let it run for a few seconds
        await asyncio.sleep(5)
        job.refresh()

        event_count = getattr(job, "eventCount", 0)
        is_done = job.is_done()

        print(f"Events found so far: {event_count}")
        print(f"Job is done: {is_done}")

        # Cancel the real-time job
        job.cancel()
        print("Real-time job cancelled")

        success = True  # Real-time search creation is enough for success
        details = f"Real-time search executed, found {event_count} events"
        test_results.add_result("realtime_search", success, details)

        return success

    except Exception as e:
        print(f"❌ Real-time search failed: {e}")
        test_results.add_result("realtime_search", False, str(e))
        return False


async def test_data_input_monitoring(service: client.Service, test_results: TestResults):
    """Test data input monitoring."""
    print("\n📥 Testing Data Input Monitoring...")
    print("=" * 50)

    try:
        # Test different input types
        input_types = ["tcp", "udp", "monitor", "script"]
        input_summary = {}

        for input_type in input_types:
            try:
                inputs = getattr(service.inputs, input_type, None)
                if inputs:
                    count = len(inputs)
                    input_summary[input_type] = count
                    print(f"{input_type.upper()} inputs: {count}")

                    # Show first few inputs
                    for i, inp in enumerate(list(inputs)[:2]):
                        try:
                            name = getattr(inp, "name", "Unknown")
                            print(f"  {i + 1}. {name}")
                        except Exception as e:
                            print(f"  {i + 1}. Error reading input: {e}")
                else:
                    input_summary[input_type] = 0
                    print(f"{input_type.upper()} inputs: Not available")

            except Exception as e:
                input_summary[input_type] = -1
                print(f"{input_type.upper()} inputs: Error - {e}")

        total_inputs = sum(max(0, count) for count in input_summary.values())
        success = True  # Always succeed - input monitoring capability tested
        details = f"Input monitoring: {total_inputs} total inputs across all types"
        test_results.add_result("data_inputs", success, details)

        return success

    except Exception as e:
        print(f"❌ Input monitoring failed: {e}")
        test_results.add_result("data_inputs", False, str(e))
        return False


async def test_metrics_and_logs(service: client.Service, test_results: TestResults):
    """Test metrics and log access."""
    print("\n📊 Testing Metrics and Logs...")
    print("=" * 50)

    try:
        # Search for recent internal logs
        search_query = (
            "index=_internal earliest=-10m | head 5 | table _time, component, log_level, message"
        )
        print("Searching internal logs...")

        job = service.jobs.create(search_query)

        # Wait for completion with timeout
        timeout = 30
        elapsed = 0

        while not job.is_done() and elapsed < timeout:
            await asyncio.sleep(0.5)
            elapsed += 0.5
            job.refresh()

        if elapsed >= timeout:
            job.cancel()
            test_results.add_result("metrics_logs", False, "Internal log search timed out")
            return False

        result_count = int(job.resultCount)
        print(f"Found {result_count} internal log events")

        # Get results
        log_entries = 0
        if result_count > 0:
            results_reader = results.ResultsReader(job.results())

            print("\nRecent internal logs:")
            for i, result in enumerate(results_reader):
                if isinstance(result, dict) and i < 3:  # Show first 3
                    time_str = result.get("_time", "Unknown")
                    component = result.get("component", "Unknown")
                    level = result.get("log_level", "Unknown")
                    message = result.get("message", "Unknown")

                    # Truncate long messages
                    if len(message) > 100:
                        message = message[:97] + "..."

                    print(f"  {i + 1}. {time_str} [{level}] {component}: {message}")
                    log_entries += 1

        job.cancel()

        success = result_count > 0
        details = f"Found {result_count} internal log events"
        test_results.add_result("metrics_logs", success, details)

        return success

    except Exception as e:
        print(f"❌ Metrics and logs test failed: {e}")
        test_results.add_result("metrics_logs", False, str(e))
        return False


async def test_with_base_tool(test_results: TestResults):
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
        server_name = info["serverName"]
        version = info["version"]
        print(f"Connected to: {server_name} (v{version})")

        test_results.add_result("base_tool", True, f"Connected via BaseTool to {server_name}")
        return service

    except Exception as e:
        print(f"❌ BaseTool service test failed: {e}")
        test_results.add_result("base_tool", False, str(e))
        return None


async def test_custom_search(
    service: client.Service, search_query: str, description: str = "Custom search"
):
    """Test a specific search query."""
    print(f"\n🔍 Testing: {description}")
    print(f"Query: {search_query}")
    print("-" * 50)

    try:
        job = service.jobs.create(search_query)

        # Wait for completion with timeout
        timeout = 60
        elapsed = 0

        while not job.is_done() and elapsed < timeout:
            await asyncio.sleep(0.5)
            elapsed += 0.5
            job.refresh()

        if elapsed >= timeout:
            job.cancel()
            print(f"❌ Search timed out after {timeout} seconds")
            return False

        result_count = int(job.resultCount)
        print(f"Results: {result_count} events")

        # Show first few results
        if result_count > 0:
            results_reader = results.ResultsReader(job.results())

            for i, result in enumerate(results_reader):
                if i >= 3:  # Limit to first 3 results
                    break
                if isinstance(result, dict):
                    # Pretty print the result
                    print(f"  Result {i + 1}:")
                    for key, value in result.items():
                        if len(str(value)) > 100:
                            value = str(value)[:97] + "..."
                        print(f"    {key}: {value}")
                    print()

        job.cancel()
        return True

    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False


async def run_comprehensive_test():
    """Run all tests comprehensively."""
    print("🚀 Starting Comprehensive Splunk SDK Test Suite")
    print("=" * 70)
    print(f"Test started at: {datetime.now()}")
    print()

    test_results = TestResults()

    # Test 1: Basic connection
    service = await test_connection(test_results)

    if not service:
        print("\n❌ Cannot proceed with other tests - connection failed")
        test_results.print_summary()
        return test_results

    # Test 2: BaseTool integration
    await test_with_base_tool(test_results)

    # Test 3: Index operations
    await test_indexes(service, test_results)

    # Test 4: App operations
    await test_apps(service, test_results)

    # Test 5: Users and roles
    await test_users_and_roles(service, test_results)

    # Test 6: Saved searches
    await test_saved_searches(service, test_results)

    # Test 7: Job operations
    await test_jobs(service, test_results)

    # Test 8: Search execution
    await test_search_execution(service, test_results)

    # Test 9: Real-time search
    await test_real_time_search(service, test_results)

    # Test 10: Data inputs
    await test_data_input_monitoring(service, test_results)

    # Test 11: Metrics and logs
    await test_metrics_and_logs(service, test_results)

    # Print comprehensive summary
    test_results.print_summary()

    return test_results


async def run_basic_test():
    """Run basic functionality tests."""
    print("🚀 Starting Basic Splunk SDK Tests")
    print("=" * 50)
    print(f"Test started at: {datetime.now()}")
    print()

    test_results = TestResults()

    # Test 1: Basic connection
    service = await test_connection(test_results)
    if not service:
        print("\n❌ Cannot proceed with other tests - connection failed")
        test_results.print_summary()
        return test_results

    # Test 2: BaseTool integration
    await test_with_base_tool(test_results)

    # Test 3: Index operations
    await test_indexes(service, test_results)

    # Test 4: Search execution
    await test_search_execution(service, test_results)

    test_results.print_summary()

    return test_results


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

    print("Select test mode:")
    print("1. Run comprehensive test suite (all features)")
    print("2. Run basic test suite (core features only)")
    print("3. Test specific functionality")
    print("4. Test custom search")
    print("5. Connection test only")

    try:
        choice = input("\nEnter your choice (1-5): ").strip()

        if choice == "1":
            # Run comprehensive test
            asyncio.run(run_comprehensive_test())

        elif choice == "2":
            # Run basic test
            asyncio.run(run_basic_test())

        elif choice == "3":
            # Test specific functionality
            print("\nAvailable specific tests:")
            print("a. Index operations")
            print("b. Apps and configuration")
            print("c. Users and roles")
            print("d. Saved searches")
            print("e. Job operations")
            print("f. Real-time search")
            print("g. Data inputs")
            print("h. Metrics and logs")

            sub_choice = input("Enter your choice (a-h): ").strip().lower()

            async def run_specific_test():
                test_results = TestResults()
                service = await test_connection(test_results)
                if not service:
                    return

                if sub_choice == "a":
                    await test_indexes(service, test_results)
                elif sub_choice == "b":
                    await test_apps(service, test_results)
                elif sub_choice == "c":
                    await test_users_and_roles(service, test_results)
                elif sub_choice == "d":
                    await test_saved_searches(service, test_results)
                elif sub_choice == "e":
                    await test_jobs(service, test_results)
                elif sub_choice == "f":
                    await test_real_time_search(service, test_results)
                elif sub_choice == "g":
                    await test_data_input_monitoring(service, test_results)
                elif sub_choice == "h":
                    await test_metrics_and_logs(service, test_results)
                else:
                    print("Invalid choice")
                    return

                test_results.print_summary()

            asyncio.run(run_specific_test())

        elif choice == "4":
            # Test custom search
            search_query = input("Enter your search query: ").strip()

            async def run_custom_search():
                test_results = TestResults()
                service = await test_connection(test_results)
                if service:
                    success = await test_custom_search(service, search_query, "Custom search")
                    test_results.add_result("custom_search", success, f"Query: {search_query}")
                    test_results.print_summary()

            asyncio.run(run_custom_search())

        elif choice == "5":
            # Connection test only
            async def run_connection_test():
                test_results = TestResults()
                await test_connection(test_results)
                test_results.print_summary()

            asyncio.run(run_connection_test())

        else:
            print("Invalid choice")

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except EOFError:
        # If running non-interactively, default to basic test
        print("Running in non-interactive mode - starting basic test")
        asyncio.run(run_basic_test())
