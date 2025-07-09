#!/usr/bin/env python3
"""
Test script for SplunkTriageAgentTool using FastMCP client.

This script tests the Splunk triage agent with proper progress reporting,
timeout handling, and connection monitoring.

Usage:
    python test_agent.py "I am having some performance issues in my splunk environment, please help me troubleshoot."
    python test_agent.py --prompt "Performance issues with searches taking too long"
    python test_agent.py --help
"""

import asyncio
import argparse
import logging
import time
from typing import Any, Dict, Optional
from dataclasses import dataclass

from fastmcp import Client
from fastmcp.client.progress import ProgressHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestConfig:
    """Configuration for the test."""
    server_url: str = "http://localhost:8002/mcp/"
    timeout: float = 300.0  # 5 minutes timeout
    test_input: str = "I cant find my data in index=cca_insights"  # Default fallback
    earliest_time: str = "-24h"
    latest_time: str = "now"
    focus_index: Optional[str] = None  # Made optional since performance issues might not be index-specific
    focus_host: Optional[str] = None
    complexity_level: str = "moderate"


class ProgressTracker:
    """Tracks progress updates from the agent."""
    
    def __init__(self):
        self.progress_history = []
        self.last_progress = 0
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.timeout_threshold = 30.0  # 30 seconds without progress update
        
    async def progress_handler(
        self, 
        progress: float, 
        total: float | None, 
        message: str | None
    ) -> None:
        """Handle progress updates from the server."""
        current_time = time.time()
        elapsed = current_time - self.start_time
        since_last = current_time - self.last_update_time
        
        # Update tracking
        self.last_progress = progress
        self.last_update_time = current_time
        
        # Calculate percentage if total is provided
        if total is not None and total > 0:
            percentage = (progress / total) * 100
            progress_str = f"{percentage:.1f}%"
        else:
            progress_str = f"{progress}"
        
        # Format message
        status_msg = f"[{elapsed:.1f}s] Progress: {progress_str}"
        if message:
            status_msg += f" - {message}"
        
        logger.info(status_msg)
        
        # Store progress history
        self.progress_history.append({
            'timestamp': current_time,
            'elapsed': elapsed,
            'progress': progress,
            'total': total,
            'message': message,
            'since_last_update': since_last
        })
        
        # Check for timeout (no progress for too long)
        if since_last > self.timeout_threshold:
            logger.warning(f"⚠️  Long delay: {since_last:.1f}s since last progress update")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of progress tracking."""
        total_time = time.time() - self.start_time
        
        return {
            'total_execution_time': total_time,
            'progress_updates_count': len(self.progress_history),
            'final_progress': self.last_progress,
            'average_update_interval': total_time / max(1, len(self.progress_history)),
            'longest_gap': max(
                (update['since_last_update'] for update in self.progress_history),
                default=0
            ),
            'progress_history': self.progress_history
        }


class ConnectionMonitor:
    """Monitors connection health and timeouts."""
    
    def __init__(self, timeout: float = 300.0):
        self.timeout = timeout
        self.connection_start = None
        self.last_activity = None
        self.is_monitoring = False
        
    async def start_monitoring(self, client: Client):
        """Start monitoring connection health."""
        self.connection_start = time.time()
        self.last_activity = time.time()
        self.is_monitoring = True
        
        logger.info(f"🔗 Connection monitoring started (timeout: {self.timeout}s)")
        
        # Start background monitoring task
        asyncio.create_task(self._monitor_connection(client))
    
    async def _monitor_connection(self, client: Client):
        """Background task to monitor connection health."""
        while self.is_monitoring:
            try:
                current_time = time.time()
                
                # Check if we've exceeded timeout
                if current_time - self.connection_start > self.timeout:
                    logger.error(f"❌ Connection timeout exceeded ({self.timeout}s)")
                    break
                
                # Check if client is still connected
                if hasattr(client, 'is_connected') and not client.is_connected():
                    logger.warning("⚠️  Client connection lost")
                    break
                
                # Periodic ping to check server health
                if current_time - self.last_activity > 60:  # Ping every minute
                    try:
                        await client.ping()
                        self.last_activity = current_time
                        logger.debug("📡 Connection ping successful")
                    except Exception as e:
                        logger.warning(f"⚠️  Connection ping failed: {e}")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"❌ Connection monitoring error: {e}")
                break
    
    def stop_monitoring(self):
        """Stop connection monitoring."""
        self.is_monitoring = False
        total_time = time.time() - self.connection_start if self.connection_start else 0
        logger.info(f"🔗 Connection monitoring stopped (total time: {total_time:.1f}s)")


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Test the Splunk Triage Agent with custom prompts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test performance issues (auto-selects triage agent)
  python test_agent.py "I am having some performance issues in my splunk environment, please help me troubleshoot."
  
  # Test missing data (auto-selects reflection agent)
  python test_agent.py "I can't find my data in index=main"
  
  # Explicitly test reflection agent with dynamic coordinator
  python test_agent.py --test-type reflection --prompt "Missing data troubleshooting"
  
  # Explicitly test original triage agent
  python test_agent.py --test-type triage --prompt "Performance issues"
  
  # Explicitly test dynamic troubleshoot agent (direct to coordinator)
  python test_agent.py --test-type dynamic --prompt "Performance issues with searches"
  
  # Test with custom time range
  python test_agent.py --prompt "Performance degraded since yesterday" --earliest-time "-2d" --latest-time "now"
        """
    )
    
    parser.add_argument(
        'prompt_positional', 
        nargs='?',  # Optional positional argument
        help='Problem description to troubleshoot (can also use --prompt)'
    )
    
    parser.add_argument(
        '--prompt', '-p',
        dest='prompt_named',
        help='Problem description to troubleshoot (alternative to positional argument)'
    )
    
    parser.add_argument(
        '--server-url', '-s',
        default="http://localhost:8002/mcp/",
        help='FastMCP server URL (default: %(default)s)'
    )
    
    parser.add_argument(
        '--timeout', '-t',
        type=float,
        default=300.0,
        help='Timeout in seconds (default: %(default)s)'
    )
    
    parser.add_argument(
        '--earliest-time', '-e',
        default="-24h",
        help='Earliest time for analysis (default: %(default)s)'
    )
    
    parser.add_argument(
        '--latest-time', '-l',
        default="now",
        help='Latest time for analysis (default: %(default)s)'
    )
    
    parser.add_argument(
        '--focus-index', '-i',
        help='Specific index to focus on (optional)'
    )
    
    parser.add_argument(
        '--focus-host', '--host',
        help='Specific host to focus on (optional)'
    )
    
    parser.add_argument(
        '--complexity-level', '-c',
        choices=['simple', 'moderate', 'complex'],
        default='moderate',
        help='Analysis complexity level (default: %(default)s)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--test-type',
        choices=['triage', 'reflection', 'dynamic', 'auto'],
        default='auto',
        help='Type of test to run: triage (original), reflection (with dynamic coordinator), dynamic (direct dynamic coordinator), or auto (default: %(default)s)'
    )
    
    args = parser.parse_args()
    
    # Set verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Verbose logging enabled")
    
    # Determine the prompt to use (positional argument takes precedence)
    if args.prompt_positional:  # This is the positional argument 
        test_input = args.prompt_positional
    elif args.prompt_named:  # This is the --prompt flag
        test_input = args.prompt_named
    else:
        # Use default if no prompt provided
        test_input = "I cant find my data in index=cca_insights"
        logger.warning("No prompt provided, using default: " + test_input)
    
    return args, test_input


def create_config_from_args(args, test_input: str) -> TestConfig:
    """Create a TestConfig from parsed arguments."""
    return TestConfig(
        server_url=getattr(args, 'server_url', "http://localhost:8002/mcp/"),
        timeout=getattr(args, 'timeout', 300.0),
        test_input=test_input,
        earliest_time=getattr(args, 'earliest_time', "-24h"),
        latest_time=getattr(args, 'latest_time', "now"),
        focus_index=getattr(args, 'focus_index', None),
        focus_host=getattr(args, 'focus_host', None),
        complexity_level=getattr(args, 'complexity_level', "moderate")
    )


async def test_splunk_triage_agent(config: TestConfig):
    """Test the SplunkTriageAgentTool with comprehensive monitoring."""
    
    progress_tracker = ProgressTracker()
    connection_monitor = ConnectionMonitor(timeout=config.timeout)
    
    logger.info("="*80)
    logger.info("STARTING SPLUNK TRIAGE AGENT TEST")
    logger.info("="*80)
    logger.info(f"Server URL: {config.server_url}")
    logger.info(f"Test Input: {config.test_input}")
    logger.info(f"Timeout: {config.timeout}s")
    logger.info(f"Time Range: {config.earliest_time} to {config.latest_time}")
    logger.info(f"Focus Index: {config.focus_index}")
    logger.info("="*80)
    
    start_time = time.time()
    
    try:
        # Create client with progress handler and timeout
        client = Client(
            config.server_url,
            progress_handler=progress_tracker.progress_handler,
            timeout=config.timeout
        )
        
        logger.info("🚀 Connecting to FastMCP server...")
        
        async with client:
            # Start connection monitoring
            await connection_monitor.start_monitoring(client)
            
            # Test connection
            logger.info("📡 Testing server connection...")
            await client.ping()
            logger.info("✅ Server connection successful")
            
            # List available tools
            logger.info("🔍 Listing available tools...")
            tools = await client.list_tools()
            
            # Find the triage tool
            triage_tool = None
            for tool in tools:
                if "splunk" in tool.name.lower() and "triage" in tool.name.lower():
                    triage_tool = tool
                    break
            
            if not triage_tool:
                # Look for the specific tool name from the code
                for tool in tools:
                    if tool.name == "execute_splunk_missing_data_troubleshooting":
                        triage_tool = tool
                        break
            
            if not triage_tool:
                logger.error("❌ Splunk triage tool not found in available tools:")
                for tool in tools:
                    logger.error(f"  - {tool.name}: {tool.description}")
                return
            
            logger.info(f"✅ Found triage tool: {triage_tool.name}")
            logger.info(f"   Description: {triage_tool.description}")
            
            # Prepare tool arguments
            tool_args = {
                "problem_description": config.test_input,
                "earliest_time": config.earliest_time,
                "latest_time": config.latest_time,
                "complexity_level": config.complexity_level
            }
            
            # Add optional parameters if provided
            if config.focus_index:
                tool_args["focus_index"] = config.focus_index
            if config.focus_host:
                tool_args["focus_host"] = config.focus_host
            
            logger.info("🔧 Executing Splunk triage agent...")
            logger.info(f"   Arguments: {tool_args}")
            
            # Execute the tool with timeout and progress monitoring
            try:
                result = await client.call_tool(
                    triage_tool.name,
                    tool_args,
                    timeout=config.timeout,
                    progress_handler=progress_tracker.progress_handler
                )
                
                execution_time = time.time() - start_time
                logger.info(f"✅ Tool execution completed in {execution_time:.1f}s")
                
                # Process and display results
                await display_results(result, progress_tracker, execution_time)
                
            except asyncio.TimeoutError:
                logger.error(f"❌ Tool execution timed out after {config.timeout}s")
                raise
            except Exception as e:
                logger.error(f"❌ Tool execution failed: {e}")
                raise
            
            finally:
                connection_monitor.stop_monitoring()
    
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"❌ Test failed after {execution_time:.1f}s: {e}")
        
        # Display progress summary even on failure
        progress_summary = progress_tracker.get_summary()
        logger.info("📊 Progress Summary (despite failure):")
        logger.info(f"   Total updates: {progress_summary['progress_updates_count']}")
        logger.info(f"   Final progress: {progress_summary['final_progress']}")
        logger.info(f"   Longest gap: {progress_summary['longest_gap']:.1f}s")
        
        raise
    
    finally:
        total_time = time.time() - start_time
        logger.info("="*80)
        logger.info(f"TEST COMPLETED - Total time: {total_time:.1f}s")
        logger.info("="*80)


async def display_results(result, progress_tracker: ProgressTracker, execution_time: float):
    """Display the results of the triage agent execution."""
    
    logger.info("="*80)
    logger.info("TRIAGE AGENT RESULTS")
    logger.info("="*80)
    
    # Display structured data if available
    if hasattr(result, 'data') and result.data:
        logger.info("📋 Structured Results:")
        
        if isinstance(result.data, dict):
            for key, value in result.data.items():
                if key == 'step_summary' and isinstance(value, dict):
                    logger.info(f"   {key}:")
                    display_step_summary(value)
                elif key == 'execution_times' and isinstance(value, dict):
                    logger.info(f"   {key}:")
                    for time_key, time_value in value.items():
                        logger.info(f"     {time_key}: {time_value:.2f}s")
                else:
                    logger.info(f"   {key}: {value}")
        else:
            logger.info(f"   Data: {result.data}")
    
    # Display content blocks
    if hasattr(result, 'content') and result.content:
        logger.info("📄 Content Results:")
        for i, content in enumerate(result.content):
            if hasattr(content, 'text'):
                logger.info(f"   Content {i+1}: {content.text[:500]}...")
            elif hasattr(content, 'data'):
                logger.info(f"   Binary Content {i+1}: {len(content.data)} bytes")
    
    # Display progress summary
    progress_summary = progress_tracker.get_summary()
    logger.info("📊 Progress Summary:")
    logger.info(f"   Total execution time: {execution_time:.1f}s")
    logger.info(f"   Progress updates: {progress_summary['progress_updates_count']}")
    logger.info(f"   Final progress: {progress_summary['final_progress']}")
    logger.info(f"   Average update interval: {progress_summary['average_update_interval']:.1f}s")
    logger.info(f"   Longest gap between updates: {progress_summary['longest_gap']:.1f}s")
    
    # Check for timeout concerns
    if progress_summary['longest_gap'] > 30:
        logger.warning(f"⚠️  Long gap detected: {progress_summary['longest_gap']:.1f}s without progress")
    
    if progress_summary['progress_updates_count'] == 0:
        logger.warning("⚠️  No progress updates received - check progress reporting implementation")


def display_step_summary(step_summary: Dict[str, Any]):
    """Display the step summary in a formatted way."""
    
    if 'workflow_overview' in step_summary:
        overview = step_summary['workflow_overview']
        logger.info(f"     Workflow Overview:")
        logger.info(f"       Initial triage: {overview.get('initial_triage', 'N/A')}")
        logger.info(f"       Specialist assigned: {overview.get('specialist_assigned', 'N/A')}")
        logger.info(f"       Conversation turns: {overview.get('total_conversation_turns', 0)}")
    
    if 'execution_summary' in step_summary:
        summary = step_summary['execution_summary']
        logger.info(f"     Execution Summary:")
        logger.info(f"       Tools used: {summary.get('tools_used', 0)}")
        logger.info(f"       Diagnostic steps: {summary.get('diagnostic_steps_performed', 0)}")
        logger.info(f"       Key findings: {summary.get('key_findings_identified', 0)}")
        logger.info(f"       Recommendations: {summary.get('recommendations_provided', 0)}")
        logger.info(f"       Routing successful: {summary.get('routing_successful', False)}")
    
    if 'tools_executed' in step_summary:
        tools = step_summary['tools_executed']
        if tools:
            logger.info(f"     Tools Executed ({len(tools)}):")
            for tool in tools[:5]:  # Show first 5 tools
                logger.info(f"       - {tool.get('tool', 'Unknown')}: {tool.get('description', 'N/A')}")
            if len(tools) > 5:
                logger.info(f"       ... and {len(tools) - 5} more")


async def test_reflection_agent(config: TestConfig):
    """Test the ReflectionAgentTool with comprehensive monitoring."""
    
    progress_tracker = ProgressTracker()
    connection_monitor = ConnectionMonitor(timeout=config.timeout)
    
    logger.info("="*80)
    logger.info("STARTING REFLECTION AGENT TEST")
    logger.info("="*80)
    logger.info(f"Server URL: {config.server_url}")
    logger.info(f"Test Input: {config.test_input}")
    logger.info(f"Timeout: {config.timeout}s")
    logger.info(f"Time Range: {config.earliest_time} to {config.latest_time}")
    logger.info("="*80)
    
    start_time = time.time()
    
    try:
        # Create client with progress handler and timeout
        client = Client(
            config.server_url,
            progress_handler=progress_tracker.progress_handler,
            timeout=config.timeout
        )
        
        logger.info("🚀 Connecting to FastMCP server...")
        
        async with client:
            # Start connection monitoring
            await connection_monitor.start_monitoring(client)
            
            # Test connection
            logger.info("📡 Testing server connection...")
            await client.ping()
            logger.info("✅ Server connection successful")
            
            # List available tools
            logger.info("🔍 Listing available tools...")
            tools = await client.list_tools()
            
            # Find the reflection tool
            reflection_tool = None
            for tool in tools:
                if tool.name == "execute_reflection_agent":
                    reflection_tool = tool
                    break
            
            if not reflection_tool:
                logger.error("❌ Reflection agent tool not found in available tools:")
                for tool in tools:
                    logger.error(f"  - {tool.name}: {tool.description}")
                return
            
            logger.info(f"✅ Found reflection tool: {reflection_tool.name}")
            logger.info(f"   Description: {reflection_tool.description}")
            
            # Prepare tool arguments for reflection agent
            tool_args = {
                "problem_description": config.test_input,
                "earliest_time": config.earliest_time,
                "latest_time": config.latest_time,
                "max_iterations": 2,  # Limit iterations for testing
                "improvement_threshold": 0.1,
                "enable_validation": True,
                "focus_areas": ["accuracy", "completeness", "actionability"]
            }
            
            logger.info("🔧 Executing Reflection agent...")
            logger.info(f"   Arguments: {tool_args}")
            
            # Execute the tool with timeout and progress monitoring
            try:
                result = await client.call_tool(
                    reflection_tool.name,
                    tool_args,
                    timeout=config.timeout,
                    progress_handler=progress_tracker.progress_handler
                )
                
                execution_time = time.time() - start_time
                logger.info(f"✅ Reflection agent execution completed in {execution_time:.1f}s")
                
                # Process and display results
                await display_reflection_results(result, progress_tracker, execution_time)
                
            except asyncio.TimeoutError:
                logger.error(f"❌ Reflection agent execution timed out after {config.timeout}s")
                raise
            except Exception as e:
                logger.error(f"❌ Reflection agent execution failed: {e}")
                raise
            
            finally:
                connection_monitor.stop_monitoring()
    
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"❌ Reflection agent test failed after {execution_time:.1f}s: {e}")
        
        # Display progress summary even on failure
        progress_summary = progress_tracker.get_summary()
        logger.info("📊 Progress Summary (despite failure):")
        logger.info(f"   Total updates: {progress_summary['progress_updates_count']}")
        logger.info(f"   Final progress: {progress_summary['final_progress']}")
        logger.info(f"   Longest gap: {progress_summary['longest_gap']:.1f}s")
        
        raise
    
    finally:
        total_time = time.time() - start_time
        logger.info("="*80)
        logger.info(f"REFLECTION AGENT TEST COMPLETED - Total time: {total_time:.1f}s")
        logger.info("="*80)


async def display_reflection_results(result, progress_tracker: ProgressTracker, execution_time: float):
    """Display the results of the reflection agent execution."""
    
    logger.info("="*80)
    logger.info("REFLECTION AGENT RESULTS")
    logger.info("="*80)
    
    # Display structured data if available
    if hasattr(result, 'data') and result.data:
        logger.info("📋 Structured Results:")
        
        if isinstance(result.data, dict):
            # Display reflection-specific results
            if "iteration_results" in result.data:
                iterations = result.data["iteration_results"]
                logger.info(f"   📈 Reflection Iterations: {len(iterations)}")
                for iteration in iterations:
                    logger.info(f"     Iteration {iteration['iteration_number']}:")
                    logger.info(f"       - Improvement Score: {iteration['improvement_score']:.3f}")
                    logger.info(f"       - Execution Time: {iteration['execution_time']:.2f}s")
                    logger.info(f"       - Gaps Identified: {len(iteration['identified_gaps'])}")
                    if iteration['identified_gaps']:
                        logger.info(f"       - Key Gap: {iteration['identified_gaps'][0]}")
            
            if "final_synthesis" in result.data:
                synthesis = result.data["final_synthesis"]
                logger.info(f"   🎯 Final Synthesis: {synthesis[:200]}...")
            
            if "performance_metrics" in result.data:
                metrics = result.data["performance_metrics"]
                logger.info(f"   📊 Performance Metrics:")
                logger.info(f"     - Iterations Completed: {metrics.get('iterations_completed', 0)}")
                logger.info(f"     - Final Improvement Score: {metrics.get('final_improvement_score', 0):.3f}")
                logger.info(f"     - Total Gaps Identified: {metrics.get('total_gaps_identified', 0)}")
                logger.info(f"     - Convergence Achieved: {metrics.get('convergence_achieved', False)}")
            
            # Display other data
            for key, value in result.data.items():
                if key not in ["iteration_results", "final_synthesis", "performance_metrics"]:
                    if isinstance(value, dict) and "execution_time" in value:
                        logger.info(f"   {key}:")
                        for time_key, time_value in value.items():
                            if "time" in time_key.lower():
                                logger.info(f"     {time_key}: {time_value:.2f}s")
                            else:
                                logger.info(f"     {time_key}: {time_value}")
                    else:
                        logger.info(f"   {key}: {value}")
        else:
            logger.info(f"   Data: {result.data}")
    
    # Display content blocks
    if hasattr(result, 'content') and result.content:
        logger.info("📄 Content Results:")
        for i, content in enumerate(result.content):
            if hasattr(content, 'text'):
                logger.info(f"   Content {i+1}: {content.text[:500]}...")
            elif hasattr(content, 'data'):
                logger.info(f"   Binary Content {i+1}: {len(content.data)} bytes")
    
    # Display progress summary
    progress_summary = progress_tracker.get_summary()
    logger.info("📊 Progress Summary:")
    logger.info(f"   Total execution time: {execution_time:.1f}s")
    logger.info(f"   Progress updates: {progress_summary['progress_updates_count']}")
    logger.info(f"   Final progress: {progress_summary['final_progress']}")
    logger.info(f"   Average update interval: {progress_summary['average_update_interval']:.1f}s")
    logger.info(f"   Longest gap between updates: {progress_summary['longest_gap']:.1f}s")
    
    # Check for timeout concerns
    if progress_summary['longest_gap'] > 60:
        logger.warning(f"⚠️  Long gap detected: {progress_summary['longest_gap']:.1f}s without progress")
    
    if progress_summary['progress_updates_count'] == 0:
        logger.warning("⚠️  No progress updates received - check progress reporting implementation")


async def test_dynamic_troubleshoot_agent(config: TestConfig):
    """Test the DynamicTroubleshootAgentTool with comprehensive monitoring."""
    
    progress_tracker = ProgressTracker()
    connection_monitor = ConnectionMonitor(timeout=config.timeout)
    
    logger.info("="*80)
    logger.info("STARTING DYNAMIC TROUBLESHOOT AGENT TEST")
    logger.info("="*80)
    logger.info(f"Server URL: {config.server_url}")
    logger.info(f"Test Input: {config.test_input}")
    logger.info(f"Timeout: {config.timeout}s")
    logger.info(f"Time Range: {config.earliest_time} to {config.latest_time}")
    logger.info(f"Focus Index: {config.focus_index}")
    logger.info("="*80)
    
    start_time = time.time()
    
    try:
        # Create client with progress handler and timeout
        client = Client(
            config.server_url,
            progress_handler=progress_tracker.progress_handler,
            timeout=config.timeout
        )
        
        logger.info("🚀 Connecting to FastMCP server...")
        
        async with client:
            # Start connection monitoring
            await connection_monitor.start_monitoring(client)
            
            # Test connection
            logger.info("📡 Testing server connection...")
            await client.ping()
            logger.info("✅ Server connection successful")
            
            # List available tools
            logger.info("🔍 Listing available tools...")
            tools = await client.list_tools()
            
            # Find the dynamic troubleshoot tool
            dynamic_tool = None
            for tool in tools:
                if tool.name == "dynamic_troubleshoot":
                    dynamic_tool = tool
                    break
            
            if not dynamic_tool:
                logger.error("❌ Dynamic troubleshoot tool not found in available tools:")
                for tool in tools:
                    logger.error(f"  - {tool.name}: {tool.description}")
                return
            
            logger.info(f"✅ Found dynamic troubleshoot tool: {dynamic_tool.name}")
            logger.info(f"   Description: {dynamic_tool.description}")
            
            # Prepare tool arguments for dynamic troubleshoot agent
            tool_args = {
                "problem_description": config.test_input,
                "earliest_time": config.earliest_time,
                "latest_time": config.latest_time,
                "complexity_level": config.complexity_level,
                "workflow_type": "auto"  # Let it auto-detect the workflow type
            }
            
            # Add optional parameters if provided
            if config.focus_index:
                tool_args["focus_index"] = config.focus_index
            if config.focus_host:
                tool_args["focus_host"] = config.focus_host
            
            logger.info("🔧 Executing Dynamic troubleshoot agent...")
            logger.info(f"   Arguments: {tool_args}")
            
            # Execute the tool with timeout and progress monitoring
            try:
                result = await client.call_tool(
                    dynamic_tool.name,
                    tool_args,
                    timeout=config.timeout,
                    progress_handler=progress_tracker.progress_handler
                )
                
                execution_time = time.time() - start_time
                logger.info(f"✅ Dynamic troubleshoot agent execution completed in {execution_time:.1f}s")
                
                # Process and display results
                await display_dynamic_results(result, progress_tracker, execution_time)
                
            except asyncio.TimeoutError:
                logger.error(f"❌ Dynamic troubleshoot agent execution timed out after {config.timeout}s")
                raise
            except Exception as e:
                logger.error(f"❌ Dynamic troubleshoot agent execution failed: {e}")
                raise
            
            finally:
                connection_monitor.stop_monitoring()
    
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"❌ Dynamic troubleshoot agent test failed after {execution_time:.1f}s: {e}")
        
        # Display progress summary even on failure
        progress_summary = progress_tracker.get_summary()
        logger.info("📊 Progress Summary (despite failure):")
        logger.info(f"   Total updates: {progress_summary['progress_updates_count']}")
        logger.info(f"   Final progress: {progress_summary['final_progress']}")
        logger.info(f"   Longest gap: {progress_summary['longest_gap']:.1f}s")
        
        raise
    
    finally:
        total_time = time.time() - start_time
        logger.info("="*80)
        logger.info(f"DYNAMIC TROUBLESHOOT AGENT TEST COMPLETED - Total time: {total_time:.1f}s")
        logger.info("="*80)


async def display_dynamic_results(result, progress_tracker: ProgressTracker, execution_time: float):
    """Display the results of the dynamic troubleshoot agent execution."""
    
    logger.info("="*80)
    logger.info("DYNAMIC TROUBLESHOOT AGENT RESULTS")
    logger.info("="*80)
    
    # Display structured data if available
    if hasattr(result, 'data') and result.data:
        logger.info("📋 Structured Results:")
        
        if isinstance(result.data, dict):
            # Display dynamic troubleshoot-specific results
            if "detected_workflow_type" in result.data:
                logger.info(f"   🎯 Detected Workflow: {result.data['detected_workflow_type']}")
            
            if "requested_workflow_type" in result.data:
                logger.info(f"   🎛️  Requested Workflow: {result.data['requested_workflow_type']}")
            
            if "workflow_execution" in result.data:
                workflow = result.data["workflow_execution"]
                logger.info(f"   🔄 Workflow Execution:")
                logger.info(f"     - Workflow ID: {workflow.get('workflow_id', 'Unknown')}")
                logger.info(f"     - Overall Status: {workflow.get('overall_status', 'Unknown')}")
                logger.info(f"     - Execution Time: {workflow.get('execution_time', 0):.2f}s")
                logger.info(f"     - Parallel Efficiency: {workflow.get('parallel_efficiency', 0):.1%}")
                logger.info(f"     - Execution Phases: {workflow.get('execution_phases', 0)}")
                logger.info(f"     - Total Tasks: {workflow.get('total_tasks', 0)}")
            
            if "task_results" in result.data:
                tasks = result.data["task_results"]
                logger.info(f"   📋 Task Results ({len(tasks)} tasks):")
                for task in tasks:
                    status_emoji = {"healthy": "✅", "warning": "⚠️", "error": "❌"}.get(task.get('status', 'unknown'), "❓")
                    logger.info(f"     {status_emoji} {task.get('task', 'Unknown Task')}: {task.get('status', 'unknown')}")
                    if task.get('findings'):
                        logger.info(f"       Findings: {len(task['findings'])} items")
                        if task['findings']:
                            logger.info(f"       Key Finding: {task['findings'][0][:100]}...")
                    if task.get('recommendations'):
                        logger.info(f"       Recommendations: {len(task['recommendations'])} items")
            
            if "performance_metrics" in result.data:
                metrics = result.data["performance_metrics"]
                logger.info(f"   📊 Performance Metrics:")
                logger.info(f"     - Total Execution Time: {metrics.get('total_execution_time', 0):.2f}s")
                logger.info(f"     - Workflow Execution Time: {metrics.get('workflow_execution_time', 0):.2f}s")
                logger.info(f"     - Tasks Completed: {metrics.get('tasks_completed', 0)}")
                logger.info(f"     - Successful Tasks: {metrics.get('successful_tasks', 0)}")
                logger.info(f"     - Failed Tasks: {metrics.get('failed_tasks', 0)}")
                logger.info(f"     - Parallel Phases: {metrics.get('parallel_phases', 0)}")
            
            if "summary" in result.data:
                summary = result.data["summary"]
                logger.info(f"   📝 Workflow Summary:")
                if isinstance(summary, dict):
                    for key, value in summary.items():
                        logger.info(f"     - {key}: {value}")
                else:
                    logger.info(f"     {summary}")
            
            # Display other data
            for key, value in result.data.items():
                if key not in ["detected_workflow_type", "requested_workflow_type", "workflow_execution", "task_results", "performance_metrics", "summary"]:
                    if isinstance(value, dict) and "execution_time" in value:
                        logger.info(f"   {key}:")
                        for time_key, time_value in value.items():
                            if "time" in time_key.lower():
                                logger.info(f"     {time_key}: {time_value:.2f}s")
                            else:
                                logger.info(f"     {time_key}: {time_value}")
                    else:
                        logger.info(f"   {key}: {value}")
        else:
            logger.info(f"   Data: {result.data}")
    
    # Display content blocks
    if hasattr(result, 'content') and result.content:
        logger.info("📄 Content Results:")
        for i, content in enumerate(result.content):
            if hasattr(content, 'text'):
                logger.info(f"   Content {i+1}: {content.text[:500]}...")
            elif hasattr(content, 'data'):
                logger.info(f"   Binary Content {i+1}: {len(content.data)} bytes")
    
    # Display progress summary
    progress_summary = progress_tracker.get_summary()
    logger.info("📊 Progress Summary:")
    logger.info(f"   Total execution time: {execution_time:.1f}s")
    logger.info(f"   Progress updates: {progress_summary['progress_updates_count']}")
    logger.info(f"   Final progress: {progress_summary['final_progress']}")
    logger.info(f"   Average update interval: {progress_summary['average_update_interval']:.1f}s")
    logger.info(f"   Longest gap between updates: {progress_summary['longest_gap']:.1f}s")
    
    # Check for timeout concerns
    if progress_summary['longest_gap'] > 30:
        logger.warning(f"⚠️  Long gap detected: {progress_summary['longest_gap']:.1f}s without progress")
    
    if progress_summary['progress_updates_count'] == 0:
        logger.warning("⚠️  No progress updates received - check progress reporting implementation")


async def main():
    """Main test function."""
    try:
        # Parse command-line arguments
        args, test_input = parse_arguments()
        
        # Create configuration from arguments
        config = create_config_from_args(args, test_input)
        
        # Log the configuration being used
        logger.info("🔧 Configuration:")
        logger.info(f"   Prompt: {test_input}")
        logger.info(f"   Server URL: {config.server_url}")
        logger.info(f"   Timeout: {config.timeout}s")
        logger.info(f"   Time Range: {config.earliest_time} to {config.latest_time}")
        if config.focus_index:
            logger.info(f"   Focus Index: {config.focus_index}")
        if config.focus_host:
            logger.info(f"   Focus Host: {config.focus_host}")
        logger.info(f"   Complexity Level: {config.complexity_level}")
        
        # Determine which test to run based on command line argument
        test_type = getattr(args, 'test_type', 'auto')
        
        if test_type == 'reflection':
            logger.info("🧠 Running Reflection Agent test (explicit selection)")
            await test_reflection_agent(config)
        elif test_type == 'triage':
            logger.info("🔍 Running Splunk Triage Agent test (explicit selection)")
            await test_splunk_triage_agent(config)
        elif test_type == 'dynamic':
            logger.info("🤖 Running Dynamic Troubleshoot Agent test (explicit selection)")
            await test_dynamic_troubleshoot_agent(config)
        else:  # auto
            logger.info("\n🤖 Auto-selecting test based on input content:")
            logger.info("   Available: Triage Agent (original) | Reflection Agent (with dynamic coordinator) | Dynamic Troubleshoot Agent")
            
            # For automated testing, default to reflection agent if input suggests missing data
            if "missing" in test_input.lower() or "data" in test_input.lower() or "find" in test_input.lower():
                logger.info("🧠 Auto-selected: Reflection Agent (missing data detected)")
                await test_reflection_agent(config)
            else:
                logger.info("🔍 Auto-selected: Splunk Triage Agent")
                await test_splunk_triage_agent(config)
        
        logger.info("🎉 Test completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"💥 Test failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 