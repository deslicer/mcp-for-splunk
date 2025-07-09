#!/usr/bin/env python3
"""
FastMCP Client Test for Parallel Execution System

This script tests the parallel agent execution system using FastMCP client
connecting to the HTTP server running in Docker container mcp-server-dev.

Server URL: http://localhost:8002/mcp/
"""

import asyncio
import json
import time
from typing import Dict, Any
import logging

# Configure logging to show all progress and messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from fastmcp import Client
    print("✅ FastMCP imported successfully")
except ImportError as e:
    print(f"❌ FastMCP import failed: {e}")
    print("Please install FastMCP: pip install fastmcp")
    exit(1)

class TestLogger:
    """Logger for capturing all client interactions."""
    
    def __init__(self):
        self.logs = []
        self.progress_updates = []
        self.responses = []
    
    async def log_handler(self, message):
        """Handle server log messages."""
        log_entry = {
            "timestamp": time.time(),
            "type": "server_log",
            "level": getattr(message, 'level', 'INFO'),
            "message": str(message),
            "data": getattr(message, 'data', None)
        }
        self.logs.append(log_entry)
        logger.info(f"🔍 Server Log [{log_entry['level']}]: {log_entry['message']}")
        
        if log_entry['data']:
            logger.info(f"   Data: {log_entry['data']}")
    
    async def progress_handler(self, progress: float, total: float | None, message: str | None):
        """Monitor progress of long-running operations."""
        progress_entry = {
            "timestamp": time.time(),
            "type": "progress",
            "progress": progress,
            "total": total,
            "message": message,
            "percentage": (progress / total * 100) if total and total > 0 else 0
        }
        self.progress_updates.append(progress_entry)
        
        if total:
            logger.info(f"📊 Progress: {progress}/{total} ({progress_entry['percentage']:.1f}%) - {message}")
        else:
            logger.info(f"📊 Progress: {progress} - {message}")
    
    def log_response(self, operation: str, result: Any, execution_time: float):
        """Log operation responses."""
        response_entry = {
            "timestamp": time.time(),
            "type": "response",
            "operation": operation,
            "execution_time": execution_time,
            "result_type": type(result).__name__,
            "result_size": len(str(result)) if result else 0,
            "success": True
        }
        self.responses.append(response_entry)
        logger.info(f"✅ {operation} completed in {execution_time:.2f}s")
        logger.info(f"   Result type: {response_entry['result_type']}, Size: {response_entry['result_size']} chars")
    
    def log_error(self, operation: str, error: Exception, execution_time: float):
        """Log operation errors."""
        error_entry = {
            "timestamp": time.time(),
            "type": "error",
            "operation": operation,
            "execution_time": execution_time,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "success": False
        }
        self.responses.append(error_entry)
        logger.error(f"❌ {operation} failed in {execution_time:.2f}s: {error}")
    
    def print_summary(self):
        """Print a summary of all captured interactions."""
        print("\n" + "="*80)
        print("TEST EXECUTION SUMMARY")
        print("="*80)
        
        print(f"\n📋 Server Logs: {len(self.logs)} entries")
        for log in self.logs[-5:]:  # Show last 5 logs
            print(f"   [{log['level']}] {log['message']}")
        
        print(f"\n📊 Progress Updates: {len(self.progress_updates)} entries")
        for progress in self.progress_updates[-5:]:  # Show last 5 progress updates
            if progress['total']:
                print(f"   {progress['percentage']:.1f}% - {progress['message']}")
            else:
                print(f"   {progress['progress']} - {progress['message']}")
        
        print(f"\n🔄 Operations: {len(self.responses)} total")
        successful = len([r for r in self.responses if r['success']])
        failed = len([r for r in self.responses if not r['success']])
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        
        total_time = sum(r['execution_time'] for r in self.responses)
        print(f"   ⏱️  Total execution time: {total_time:.2f}s")

async def test_server_connectivity(client: Client, test_logger: TestLogger):
    """Test basic server connectivity."""
    print("\n" + "="*60)
    print("TESTING SERVER CONNECTIVITY")
    print("="*60)
    
    start_time = time.time()
    try:
        await client.ping()
        execution_time = time.time() - start_time
        test_logger.log_response("ping", "success", execution_time)
        print("✅ Server ping successful")
        return True
    except Exception as e:
        execution_time = time.time() - start_time
        test_logger.log_error("ping", e, execution_time)
        print(f"❌ Server ping failed: {e}")
        return False

async def test_list_tools(client: Client, test_logger: TestLogger):
    """Test listing available tools."""
    print("\n" + "="*60)
    print("TESTING TOOL DISCOVERY")
    print("="*60)
    
    start_time = time.time()
    try:
        tools = await client.list_tools()
        execution_time = time.time() - start_time
        test_logger.log_response("list_tools", tools, execution_time)
        
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description[:100]}...")
        
        # Look for our dynamic troubleshoot agent
        dynamic_tool = next((t for t in tools if 'dynamic_troubleshoot' in t.name), None)
        if dynamic_tool:
            print(f"\n🎯 Found parallel execution tool: {dynamic_tool.name}")
            print(f"   Description: {dynamic_tool.description[:200]}...")
            return dynamic_tool
        else:
            print("⚠️  Dynamic troubleshoot agent not found")
            return None
            
    except Exception as e:
        execution_time = time.time() - start_time
        test_logger.log_error("list_tools", e, execution_time)
        print(f"❌ Failed to list tools: {e}")
        return None

async def test_parallel_execution_basic(client: Client, test_logger: TestLogger, tool_name: str):
    """Test basic parallel execution with health check workflow."""
    print("\n" + "="*60)
    print("TESTING BASIC PARALLEL EXECUTION (Health Check)")
    print("="*60)
    
    start_time = time.time()
    try:
        # Test with health check workflow (simplest)
        result = await client.call_tool(tool_name, {
            "problem_description": "Quick health check to verify system is working",
            "workflow_type": "health_check",
            "complexity_level": "basic"
        })
        
        execution_time = time.time() - start_time
        test_logger.log_response("parallel_execution_health_check", result, execution_time)
        
        print(f"✅ Health check completed in {execution_time:.2f}s")
        
        # Parse and display results
        if hasattr(result, 'data') and result.data:
            data = result.data if isinstance(result.data, dict) else json.loads(result.data)
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Workflow: {data.get('detected_workflow_type', 'unknown')}")
            
            if 'execution_metadata' in data:
                metadata = data['execution_metadata']
                print(f"   Total time: {metadata.get('total_execution_time', 0):.2f}s")
                print(f"   Parallel execution: {metadata.get('parallel_execution', False)}")
                print(f"   Tracing enabled: {metadata.get('tracing_enabled', False)}")
            
            if 'summarization' in data:
                summarization = data['summarization']
                print(f"   Summarization time: {summarization.get('execution_time', 0):.2f}s")
                print(f"   Analysis length: {summarization.get('output_length', 0)} chars")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        test_logger.log_error("parallel_execution_health_check", e, execution_time)
        print(f"❌ Health check failed: {e}")
        return None

async def test_parallel_execution_missing_data(client: Client, test_logger: TestLogger, tool_name: str):
    """Test parallel execution with missing data workflow (complex)."""
    print("\n" + "="*60)
    print("TESTING COMPLEX PARALLEL EXECUTION (Missing Data)")
    print("="*60)
    
    start_time = time.time()
    try:
        # Test with missing data workflow (most complex)
        result = await client.call_tool(tool_name, {
            "problem_description": "My dashboard shows no data for the security index in the last 24 hours. Users are reporting they can't see any events that should be there.",
            "earliest_time": "-24h",
            "latest_time": "now",
            "focus_index": "security",
            "workflow_type": "missing_data",
            "complexity_level": "moderate"
        })
        
        execution_time = time.time() - start_time
        test_logger.log_response("parallel_execution_missing_data", result, execution_time)
        
        print(f"✅ Missing data analysis completed in {execution_time:.2f}s")
        
        # Parse and display detailed results
        if hasattr(result, 'data') and result.data:
            data = result.data if isinstance(result.data, dict) else json.loads(result.data)
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Detected workflow: {data.get('detected_workflow_type', 'unknown')}")
            
            # Show workflow execution details
            if 'workflow_execution' in data:
                workflow = data['workflow_execution']
                print(f"   Workflow ID: {workflow.get('workflow_id', 'unknown')}")
                print(f"   Total tasks: {workflow.get('total_tasks', 0)}")
                print(f"   Successful tasks: {workflow.get('successful_tasks', 0)}")
                print(f"   Failed tasks: {workflow.get('failed_tasks', 0)}")
                print(f"   Execution phases: {workflow.get('execution_phases', 0)}")
                print(f"   Parallel efficiency: {workflow.get('parallel_efficiency', 0):.1%}")
            
            # Show execution metadata
            if 'execution_metadata' in data:
                metadata = data['execution_metadata']
                print(f"   Total execution time: {metadata.get('total_execution_time', 0):.2f}s")
                print(f"   Workflow execution time: {metadata.get('workflow_execution_time', 0):.2f}s")
                print(f"   Summarization time: {metadata.get('summarization_execution_time', 0):.2f}s")
            
            # Show task results summary
            if 'task_results' in data:
                task_results = data['task_results']
                print(f"   Task results: {len(task_results)} tasks")
                for task_id, task_result in list(task_results.items())[:3]:  # Show first 3
                    status = task_result.get('status', 'unknown')
                    findings = len(task_result.get('findings', []))
                    recommendations = len(task_result.get('recommendations', []))
                    print(f"     {task_id}: {status} ({findings} findings, {recommendations} recommendations)")
            
            # Show summarization results
            if 'summarization' in data:
                summarization = data['summarization']
                print(f"   Summarization analysis: {summarization.get('output_length', 0)} chars")
                if 'full_result' in summarization:
                    full_result = summarization['full_result']
                    if isinstance(full_result, dict):
                        print(f"   Executive summary available: {bool(full_result.get('executive_summary'))}")
                        print(f"   Action items: {len(full_result.get('action_items', []))}")
                        print(f"   Recommendations: {len(full_result.get('priority_recommendations', []))}")
                        print(f"   Severity: {full_result.get('severity_assessment', 'unknown')}")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        test_logger.log_error("parallel_execution_missing_data", e, execution_time)
        print(f"❌ Missing data analysis failed: {e}")
        return None

async def test_parallel_execution_performance(client: Client, test_logger: TestLogger, tool_name: str):
    """Test parallel execution with performance workflow."""
    print("\n" + "="*60)
    print("TESTING PARALLEL EXECUTION (Performance Analysis)")
    print("="*60)
    
    start_time = time.time()
    try:
        # Test with performance workflow
        result = await client.call_tool(tool_name, {
            "problem_description": "Search performance has been degraded since yesterday. Users are experiencing slow search responses and timeouts.",
            "earliest_time": "-48h",
            "latest_time": "now",
            "workflow_type": "performance",
            "complexity_level": "advanced"
        })
        
        execution_time = time.time() - start_time
        test_logger.log_response("parallel_execution_performance", result, execution_time)
        
        print(f"✅ Performance analysis completed in {execution_time:.2f}s")
        
        # Display key results
        if hasattr(result, 'data') and result.data:
            data = result.data if isinstance(result.data, dict) else json.loads(result.data)
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Workflow: {data.get('detected_workflow_type', 'unknown')}")
            
            if 'parallel_metadata' in data:
                parallel_meta = data['parallel_metadata']
                print(f"   Execution method: {parallel_meta.get('execution_method', 'unknown')}")
                print(f"   Dependency graph: {len(parallel_meta.get('dependency_graph', {})) if parallel_meta.get('dependency_graph') else 0} tasks")
                print(f"   Execution phases: {len(parallel_meta.get('execution_order', [])) if parallel_meta.get('execution_order') else 0}")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        test_logger.log_error("parallel_execution_performance", e, execution_time)
        print(f"❌ Performance analysis failed: {e}")
        return None

async def run_comprehensive_test():
    """Run comprehensive test of the parallel execution system."""
    print("🚀 STARTING FASTMCP CLIENT TEST FOR PARALLEL EXECUTION SYSTEM")
    print("="*80)
    print(f"Server URL: http://localhost:8002/mcp/")
    print(f"Test started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Initialize test logger
    test_logger = TestLogger()
    
    # Create client with logging handlers
    client = Client(
        "http://localhost:8002/mcp/",
        log_handler=test_logger.log_handler,
        progress_handler=test_logger.progress_handler,
        timeout=120.0  # Extended timeout for complex operations
    )
    
    test_results = {}
    total_start_time = time.time()
    
    try:
        async with client:
            logger.info("🔗 Connected to MCP server")
            print(f"✅ Connected to server: {client.is_connected()}")
            
            # Test 1: Server Connectivity
            connectivity_result = await test_server_connectivity(client, test_logger)
            test_results['connectivity'] = connectivity_result
            
            if not connectivity_result:
                print("❌ Cannot proceed without server connectivity")
                return False
            
            # Test 2: Tool Discovery
            dynamic_tool = await test_list_tools(client, test_logger)
            test_results['tool_discovery'] = dynamic_tool is not None
            
            if not dynamic_tool:
                print("❌ Cannot test parallel execution without the dynamic troubleshoot tool")
                return False
            
            tool_name = dynamic_tool.name
            print(f"🎯 Using tool: {tool_name}")
            
            # Test 3: Basic Parallel Execution (Health Check)
            health_result = await test_parallel_execution_basic(client, test_logger, tool_name)
            test_results['health_check'] = health_result is not None
            
            # Test 4: Complex Parallel Execution (Missing Data)
            missing_data_result = await test_parallel_execution_missing_data(client, test_logger, tool_name)
            test_results['missing_data'] = missing_data_result is not None
            
            # Test 5: Performance Analysis
            performance_result = await test_parallel_execution_performance(client, test_logger, tool_name)
            test_results['performance'] = performance_result is not None
            
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        test_results['execution_error'] = str(e)
        return False
    
    finally:
        total_execution_time = time.time() - total_start_time
        
        # Print comprehensive summary
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST RESULTS")
        print("="*80)
        
        passed = sum(1 for result in test_results.values() if result is True)
        total = len([k for k in test_results.keys() if k != 'execution_error'])
        
        print(f"📊 Test Results: {passed}/{total} passed ({passed/total*100:.1f}%)")
        print(f"⏱️  Total execution time: {total_execution_time:.2f} seconds")
        
        for test_name, result in test_results.items():
            if test_name == 'execution_error':
                continue
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name:<20}: {status}")
        
        if 'execution_error' in test_results:
            print(f"❌ Execution Error: {test_results['execution_error']}")
        
        # Print detailed interaction summary
        test_logger.print_summary()
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! Parallel execution system is working perfectly via FastMCP HTTP client.")
            return True
        else:
            print(f"\n⚠️  {total - passed} tests failed. Please review the results above.")
            return False

if __name__ == "__main__":
    try:
        success = asyncio.run(run_comprehensive_test())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        logger.exception("Full error details:")
        exit(1) 