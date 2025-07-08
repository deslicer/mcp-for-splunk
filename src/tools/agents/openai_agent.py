"""
OpenAI Agent tool for executing troubleshooting workflows.

This tool integrates with the OpenAI Python library to execute AI agents that can
perform troubleshooting tasks using the available MCP tools and prompts.
"""

import os
import asyncio
import logging
import json
import re
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from fastmcp import Context
from openai import OpenAI

from ...core.base import BaseTool, ToolMetadata
from ...core.registry import tool_registry, prompt_registry, resource_registry
from ...prompts.troubleshooting import (
    TroubleshootPerformancePrompt,
    TroubleshootInputsPrompt,
    TroubleshootIndexingPerformancePrompt,
    TroubleshootInputsPromptMultiAgent
)
from .workflow_parser import WorkflowParser, ParsedWorkflow

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for the OpenAI Agent."""
    api_key: str
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4000


@dataclass
class WorkflowStep:
    """Represents a workflow step with tool calls."""
    step_id: str
    title: str
    objective: str
    tool_calls: List[Dict[str, Any]]
    resource_calls: List[Dict[str, Any]]
    parallel_execution: bool = False
    agent_role: Optional[str] = None


@dataclass
class WorkflowExecution:
    """Tracks workflow execution state."""
    total_steps: int
    completed_steps: int
    failed_steps: int
    step_results: Dict[str, Any]
    tool_call_results: Dict[str, Any]
    resource_results: Dict[str, Any]


class OpenAIAgentTool(BaseTool):
    """
    Tool that executes OpenAI agents for troubleshooting Splunk issues.
    
    This tool implements a structured 6-step workflow:
    1. Initialize tools and resources 
    2. Fetch prompt
    3. Define steps (sequential or parallel)
    4. Fetch required resources for each step
    5. Execute agent with initial prompt and resources
    6. Verify tool calls and results
    """

    METADATA = ToolMetadata(
        name="execute_openai_agent",
        description="Execute an OpenAI agent for troubleshooting Splunk issues with structured workflows and tool call execution",
        category="agents"
    )

    def __init__(self, name: str, category: str):
        super().__init__(name, category)
        self.config = self._load_config()
        self.client = OpenAI(api_key=self.config.api_key)
        self.workflow_parser = WorkflowParser()
        
        # Map of available prompt types and components
        self.prompt_map = {
            "troubleshooting": {
                "performance": TroubleshootPerformancePrompt,
                "inputs": TroubleshootInputsPrompt,
                "indexing": TroubleshootIndexingPerformancePrompt,
                "inputs_multi": TroubleshootInputsPromptMultiAgent
            }
        }

    def _load_config(self) -> AgentConfig:
        """Load OpenAI configuration from environment variables."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        return AgentConfig(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
        )

    # STEP 1: Initialize Tools and Resources
    async def _initialize_tools_and_resources(self, ctx: Context) -> Dict[str, Any]:
        """Step 1: Initialize and inventory available tools and resources."""
        await ctx.info("🔧 Step 1: Initializing tools and resources...")
        
        # Get available tools
        tool_metadata_list = tool_registry.list_tools()
        available_tools = []
        
        for metadata in tool_metadata_list:
            if metadata.name == self.METADATA.name:
                continue  # Skip self
                
            tool_info = {
                "name": metadata.name,
                "description": metadata.description,
                "category": metadata.category
            }
            available_tools.append(tool_info)
        
        logger.info(f"Initialized {len(available_tools)} available tools")
        
        # Get available resources
        resource_metadata_list = resource_registry.list_resources()
        available_resources = []
        
        for metadata in resource_metadata_list:
            resource_info = {
                "uri": metadata.uri,
                "name": metadata.name,
                "description": metadata.description,
                "category": metadata.category
            }
            available_resources.append(resource_info)
        
        logger.info(f"Initialized {len(available_resources)} available resources")
        
        initialization_result = {
            "tools": available_tools,
            "resources": available_resources,
            "tool_count": len(available_tools),
            "resource_count": len(available_resources)
        }
        
        await ctx.info(f"✅ Initialized {len(available_tools)} tools and {len(available_resources)} resources")
        return initialization_result

    # STEP 2: Fetch Prompt
    async def _fetch_prompt(
        self, 
        ctx: Context, 
        prompt_type: str, 
        component: str, 
        **kwargs
    ) -> str:
        """Step 2: Fetch the appropriate prompt content."""
        await ctx.info(f"📝 Step 2: Fetching prompt for {prompt_type} - {component}...")
        
        try:
            if prompt_type in self.prompt_map and component in self.prompt_map[prompt_type]:
                prompt_class = self.prompt_map[prompt_type][component]
                prompt_instance = prompt_class(
                    name=f"troubleshoot_{component}",
                    description=f"Troubleshooting prompt for {component}"
                )
                
                # Filter kwargs based on component type to match method signatures
                filtered_kwargs = self._filter_kwargs_for_component(component, kwargs)
                
                # Get the prompt content
                result = await prompt_instance.get_prompt(ctx, **filtered_kwargs)
                
                # Extract text content from the prompt result
                if isinstance(result, dict) and "content" in result:
                    content_parts = result["content"]
                    if isinstance(content_parts, list):
                        text_parts = [
                            part.get("text", "") for part in content_parts 
                            if part.get("type") == "text"
                        ]
                        prompt_content = "\n".join(text_parts)
                    else:
                        prompt_content = str(content_parts)
                else:
                    prompt_content = str(result)
                
                logger.info(f"Successfully fetched prompt: {len(prompt_content)} characters")
                await ctx.info(f"✅ Fetched prompt: {len(prompt_content)} characters")
                return prompt_content
            
            else:
                raise ValueError(f"Unknown prompt type '{prompt_type}' or component '{component}'")
                
        except Exception as e:
            logger.error(f"Failed to fetch prompt: {e}")
            await ctx.error(f"Failed to fetch prompt: {e}")
            raise

    def _filter_kwargs_for_component(self, component: str, kwargs: dict) -> dict:
        """Filter kwargs to match the expected parameters for each component."""
        
        # Define parameter mappings for each component
        component_params = {
            "performance": [
                "earliest_time", "latest_time", "analysis_type"
            ],
            "inputs": [
                "earliest_time", "latest_time", "focus_index", "focus_host", 
                "complexity_level", "include_performance_analysis"
            ],
            "inputs_multi": [
                "earliest_time", "latest_time", "focus_index", "focus_host",
                "complexity_level", "include_performance_analysis", 
                "enable_cross_validation", "analysis_mode"
            ],
            "indexing": [
                "earliest_time", "latest_time", "focus_index", "focus_host",
                "analysis_depth", "include_delay_analysis", 
                "include_platform_instrumentation"
            ]
        }
        
        # Get allowed parameters for this component
        allowed_params = component_params.get(component, [])
        
        # Filter kwargs to only include allowed parameters
        filtered = {}
        for param in allowed_params:
            if param in kwargs:
                filtered[param] = kwargs[param]
        
        logger.info(f"Filtered kwargs for component '{component}': {list(filtered.keys())}")
        return filtered

    # STEP 3: Define Steps (Sequential or Parallel)
    async def _define_workflow_steps(self, ctx: Context, prompt_content: str) -> List[WorkflowStep]:
        """Step 3: Parse prompt and define workflow steps with tool calls."""
        await ctx.info("🗺️ Step 3: Defining workflow steps and execution strategy...")
        
        # Parse the workflow from prompt
        parsed_workflow = self.workflow_parser.parse_workflow(prompt_content)
        
        # Extract tool calls from the prompt content
        tool_calls = self._extract_tool_calls_from_prompt(prompt_content)
        resource_calls = self._extract_resource_calls_from_prompt(prompt_content)
        
        logger.info(f"Extracted {len(tool_calls)} tool calls and {len(resource_calls)} resource calls from prompt")
        
        workflow_steps = []
        step_counter = 1
        
        for phase in parsed_workflow.phases:
            for step in phase.steps:
                # Find tool calls that belong to this step
                step_tool_calls = []
                step_resource_calls = []
                
                # Match tool calls to steps based on proximity in text
                for tool_call in tool_calls:
                    if self._is_tool_call_in_step(tool_call, step, prompt_content):
                        step_tool_calls.append(tool_call)
                
                for resource_call in resource_calls:
                    if self._is_resource_call_in_step(resource_call, step, prompt_content):
                        step_resource_calls.append(resource_call)
                
                workflow_step = WorkflowStep(
                    step_id=f"step_{step_counter}",
                    title=step.title,
                    objective=step.objective,
                    tool_calls=step_tool_calls,
                    resource_calls=step_resource_calls,
                    parallel_execution=step.parallel_execution,
                    agent_role=step.agent_role
                )
                
                workflow_steps.append(workflow_step)
                step_counter += 1
        
        # If no structured steps found, create steps from tool calls
        if not workflow_steps and tool_calls:
            await ctx.info("No structured steps found, creating steps from tool calls...")
            
            for i, tool_call in enumerate(tool_calls[:10]):  # Limit to 10 calls
                workflow_step = WorkflowStep(
                    step_id=f"tool_step_{i+1}",
                    title=f"Execute {tool_call.get('tool_name', 'Unknown Tool')}",
                    objective=f"Execute tool call: {tool_call.get('tool_name', 'Unknown')}",
                    tool_calls=[tool_call],
                    resource_calls=[],
                    parallel_execution=False
                )
                workflow_steps.append(workflow_step)
        
        logger.info(f"Defined {len(workflow_steps)} workflow steps")
        await ctx.info(f"✅ Defined {len(workflow_steps)} workflow steps")
        
        # Log step details
        for step in workflow_steps:
            logger.info(f"Step {step.step_id}: {step.title} - {len(step.tool_calls)} tool calls, {len(step.resource_calls)} resource calls")
        
        return workflow_steps

    def _extract_tool_calls_from_prompt(self, prompt_content: str) -> List[Dict[str, Any]]:
        """Extract tool calls from JSON blocks in the prompt."""
        tool_calls = []
        
        # Find JSON blocks with tool calls
        json_pattern = r'```json\s*\n(.*?)\n```'
        json_matches = re.findall(json_pattern, prompt_content, re.DOTALL)
        
        for json_str in json_matches:
            try:
                call_data = json.loads(json_str)
                if isinstance(call_data, dict) and call_data.get("method") == "tools/call":
                    params = call_data.get("params", {})
                    tool_calls.append({
                        "tool_name": params.get("name"),
                        "arguments": params.get("arguments", {}),
                        "raw_json": call_data
                    })
            except json.JSONDecodeError:
                logger.debug(f"Failed to parse JSON: {json_str[:100]}...")
        
        return tool_calls

    def _extract_resource_calls_from_prompt(self, prompt_content: str) -> List[Dict[str, Any]]:
        """Extract resource calls from JSON blocks in the prompt."""
        resource_calls = []
        
        # Find JSON blocks with resource calls
        json_pattern = r'```json\s*\n(.*?)\n```'
        json_matches = re.findall(json_pattern, prompt_content, re.DOTALL)
        
        for json_str in json_matches:
            try:
                call_data = json.loads(json_str)
                if isinstance(call_data, dict) and call_data.get("method") == "resources/read":
                    params = call_data.get("params", {})
                    resource_calls.append({
                        "uri": params.get("uri"),
                        "raw_json": call_data
                    })
            except json.JSONDecodeError:
                logger.debug(f"Failed to parse JSON: {json_str[:100]}...")
        
        return resource_calls

    def _is_tool_call_in_step(self, tool_call: Dict[str, Any], step: Any, prompt_content: str) -> bool:
        """Determine if a tool call belongs to a specific step."""
        # Simple heuristic: check if tool call appears near step title in prompt
        step_title = step.title
        tool_name = tool_call.get("tool_name", "")
        
        # Find positions in text
        step_pos = prompt_content.find(step_title)
        tool_pos = prompt_content.find(tool_name)
        
        if step_pos == -1 or tool_pos == -1:
            return False
        
        # If tool call is within 1000 characters of step title, consider it part of the step
        return abs(step_pos - tool_pos) < 1000

    def _is_resource_call_in_step(self, resource_call: Dict[str, Any], step: Any, prompt_content: str) -> bool:
        """Determine if a resource call belongs to a specific step."""
        # Similar heuristic for resource calls
        step_title = step.title
        resource_uri = resource_call.get("uri", "")
        
        step_pos = prompt_content.find(step_title)
        resource_pos = prompt_content.find(resource_uri)
        
        if step_pos == -1 or resource_pos == -1:
            return False
        
        return abs(step_pos - resource_pos) < 1000

    # STEP 4: Fetch Required Resources
    async def _fetch_required_resources(
        self, 
        ctx: Context, 
        workflow_steps: List[WorkflowStep]
    ) -> Dict[str, str]:
        """Step 4: Fetch all required resources for workflow steps."""
        await ctx.info("📚 Step 4: Fetching required resources...")
        
        resource_content = {}
        unique_uris = set()
        
        # Collect all unique resource URIs
        for step in workflow_steps:
            for resource_call in step.resource_calls:
                uri = resource_call.get("uri")
                if uri:
                    unique_uris.add(uri)
        
        logger.info(f"Fetching {len(unique_uris)} unique resources")
        
        # Fetch each resource
        for uri in unique_uris:
            try:
                await ctx.info(f"Fetching resource: {uri}")
                content = await self._fetch_resource_content(ctx, uri)
                resource_content[uri] = content
                logger.info(f"Successfully fetched resource: {uri} ({len(content)} chars)")
            except Exception as e:
                logger.error(f"Failed to fetch resource {uri}: {e}")
                resource_content[uri] = f"Error fetching resource: {str(e)}"
        
        await ctx.info(f"✅ Fetched {len(resource_content)} resources")
        return resource_content

    async def _fetch_resource_content(self, ctx: Context, uri: str) -> str:
        """Fetch content from a specific MCP resource."""
        try:
            resource = resource_registry.get_resource(uri)
            if resource:
                content = await resource.get_content(ctx)
                return content
            else:
                return f"Resource not found: {uri}"
        except Exception as e:
            logger.error(f"Error fetching resource {uri}: {e}")
            return f"Error fetching resource {uri}: {str(e)}"

    # STEP 5: Execute Agent with Initial Prompt and Resources
    async def _execute_agent_with_context(
        self, 
        ctx: Context, 
        prompt_content: str,
        workflow_steps: List[WorkflowStep],
        resource_content: Dict[str, str],
        initialization_result: Dict[str, Any]
    ) -> str:
        """Step 5: Execute the OpenAI agent with comprehensive context."""
        await ctx.info("🤖 Step 5: Executing OpenAI agent with context...")
        
        # Create enhanced system prompt
        enhanced_prompt = await self._create_enhanced_system_prompt(
            prompt_content, workflow_steps, resource_content, initialization_result
        )
        
        logger.info(f"Created enhanced prompt: {len(enhanced_prompt)} characters")
        
        try:
            messages = [
                {
                    "role": "system", 
                    "content": enhanced_prompt
                },
                {
                    "role": "user",
                    "content": "Please begin the troubleshooting analysis using the structured workflow, available tools, and documentation resources provided. Execute the workflow step by step and provide comprehensive analysis with actionable recommendations."
                }
            ]
            
            await ctx.info("Sending request to OpenAI...")
            
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content
                logger.info(f"Received OpenAI response: {len(content) if content else 0} characters")
                await ctx.info("✅ Received response from OpenAI agent")
                return content or "Agent completed but returned no content."
            
            return "Agent execution failed - no response received."
            
        except Exception as e:
            error_msg = f"OpenAI agent execution failed: {str(e)}"
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise RuntimeError(error_msg)

    async def _create_enhanced_system_prompt(
        self, 
        original_prompt: str, 
        workflow_steps: List[WorkflowStep],
        resource_content: Dict[str, str],
        initialization_result: Dict[str, Any]
    ) -> str:
        """Create an enhanced system prompt with workflow and resource context."""
        
        enhanced_prompt = f"""# Splunk Troubleshooting Expert Agent

You are an advanced Splunk troubleshooting expert with access to comprehensive tools and documentation resources.

## Workflow Overview
You have a structured workflow with {len(workflow_steps)} steps to execute:

"""
        
        # Add workflow steps
        for i, step in enumerate(workflow_steps, 1):
            enhanced_prompt += f"""
### Step {i}: {step.title}
**Objective**: {step.objective}
**Tool Calls**: {len(step.tool_calls)} available
**Resource Calls**: {len(step.resource_calls)} available
**Execution**: {'Parallel' if step.parallel_execution else 'Sequential'}
"""
            if step.agent_role:
                enhanced_prompt += f"**Agent Role**: {step.agent_role}\n"

        # Add available tools
        enhanced_prompt += f"""

## Available Tools ({initialization_result['tool_count']} tools)
You have access to the following Splunk MCP tools:
"""
        
        for tool in initialization_result['tools'][:10]:  # Limit to 10 for brevity
            enhanced_prompt += f"- **{tool['name']}**: {tool['description'][:80]}...\n"
        
        if len(initialization_result['tools']) > 10:
            enhanced_prompt += f"- ... and {len(initialization_result['tools']) - 10} more tools\n"

        # Add resource content
        enhanced_prompt += f"""

## Referenced Documentation ({len(resource_content)} documents)
"""
        
        for uri, content in list(resource_content.items())[:3]:  # Limit to 3 resources
            enhanced_prompt += f"""
### Resource: {uri}
```
{content[:1000]}{'...' if len(content) > 1000 else ''}
```
"""

        enhanced_prompt += f"""

## Execution Guidelines

1. **Follow the Structured Workflow**: Execute the steps systematically as defined above
2. **Use Available Tools**: Leverage the MCP tools to gather data and perform analysis
3. **Reference Documentation**: Use the provided documentation content when making recommendations
4. **Provide Evidence**: Support your findings with data from tool executions
5. **Be Systematic**: Follow a methodical approach to troubleshooting

## Original Workflow Instructions
{original_prompt[:2000]}{'...' if len(original_prompt) > 2000 else ''}

Begin your systematic analysis now, following the structured workflow defined above.
"""
        
        return enhanced_prompt

    # STEP 6: Verify Tool Calls and Results
    async def _verify_and_execute_tool_calls(
        self, 
        ctx: Context, 
        workflow_steps: List[WorkflowStep]
    ) -> WorkflowExecution:
        """Step 6: Verify and execute tool calls from the workflow."""
        await ctx.info("🔍 Step 6: Verifying and executing tool calls...")
        
        execution = WorkflowExecution(
            total_steps=len(workflow_steps),
            completed_steps=0,
            failed_steps=0,
            step_results={},
            tool_call_results={},
            resource_results={}
        )
        
        for step in workflow_steps:
            step_id = step.step_id
            await ctx.info(f"Executing step: {step.title}")
            logger.info(f"Executing step {step_id}: {step.title}")
            
            step_results = {
                "tool_calls_executed": 0,
                "tool_calls_failed": 0,
                "tool_results": {}
            }
            
            # Execute tool calls for this step
            for tool_call in step.tool_calls:
                tool_name = tool_call.get("tool_name")
                arguments = tool_call.get("arguments", {})
                
                try:
                    await ctx.info(f"Executing tool: {tool_name}")
                    logger.info(f"Executing tool call: {tool_name} with args: {arguments}")
                    
                    # Get the tool from registry
                    tool = tool_registry.get_tool(tool_name)
                    if tool:
                        # Execute the tool
                        result = await tool.execute(ctx, **arguments)
                        step_results["tool_results"][tool_name] = result
                        step_results["tool_calls_executed"] += 1
                        
                        logger.info(f"Tool {tool_name} executed successfully")
                        await ctx.info(f"✅ Tool {tool_name} completed")
                    else:
                        error_msg = f"Tool {tool_name} not found in registry"
                        logger.error(error_msg)
                        step_results["tool_results"][tool_name] = {"error": error_msg}
                        step_results["tool_calls_failed"] += 1
                        
                except Exception as e:
                    error_msg = f"Tool {tool_name} execution failed: {str(e)}"
                    logger.error(error_msg)
                    await ctx.error(f"❌ Tool {tool_name} failed: {str(e)}")
                    step_results["tool_results"][tool_name] = {"error": error_msg}
                    step_results["tool_calls_failed"] += 1
            
            # Update execution tracking
            execution.step_results[step_id] = step_results
            
            if step_results["tool_calls_failed"] == 0:
                execution.completed_steps += 1
                await ctx.info(f"✅ Step {step.title} completed successfully")
            else:
                execution.failed_steps += 1
                await ctx.info(f"⚠️ Step {step.title} completed with {step_results['tool_calls_failed']} failures")
        
        logger.info(f"Workflow execution completed: {execution.completed_steps}/{execution.total_steps} steps successful")
        await ctx.info(f"✅ Workflow execution completed: {execution.completed_steps}/{execution.total_steps} steps successful")
        
        return execution

    async def execute(
        self,
        ctx: Context,
        agent_type: str = "troubleshooting",
        component: str = "performance",
        earliest_time: str = "-24h",
        latest_time: str = "now",
        focus_index: str | None = None,
        focus_host: str | None = None,
        complexity_level: str = "moderate",
        include_performance_analysis: bool = True,
        enable_cross_validation: bool = True,
        analysis_mode: str = "diagnostic",
        analysis_type: str = "comprehensive",
        analysis_depth: str = "standard",
        include_delay_analysis: bool = True,
        include_platform_instrumentation: bool = True
    ) -> Dict[str, Any]:
        """
        Execute an OpenAI agent for troubleshooting Splunk issues using structured 6-step workflow.
        
        Args:
            ctx: FastMCP context for progress updates and resource access
            agent_type: Type of agent to execute (default: "troubleshooting")
            component: Component to focus on (default: "performance")
            earliest_time: Start time for analysis (default: "-24h")
            latest_time: End time for analysis (default: "now")
            focus_index: Specific index to focus analysis on (optional)
            focus_host: Specific host to focus analysis on (optional)
            complexity_level: Analysis complexity level (default: "moderate")
            include_performance_analysis: Include performance analysis (default: True)
            enable_cross_validation: Enable cross-validation (default: True)
            analysis_mode: Analysis mode (default: "diagnostic")
            analysis_type: Analysis type for performance component (default: "comprehensive")
            analysis_depth: Analysis depth for indexing component (default: "standard")
            include_delay_analysis: Include delay analysis for indexing (default: True)
            include_platform_instrumentation: Include platform instrumentation for indexing (default: True)
        
        Returns:
            Dict containing the agent's analysis, workflow execution results, and recommendations
        """
        try:
            await ctx.info(f"🚀 Starting OpenAI agent workflow for {agent_type} - {component}")
            logger.info(f"Starting OpenAI agent execution: {agent_type} - {component}")
            
            # Validate inputs
            if agent_type not in self.prompt_map:
                available_types = list(self.prompt_map.keys())
                raise ValueError(f"Unknown agent type '{agent_type}'. Available types: {available_types}")
            
            if component not in self.prompt_map[agent_type]:
                available_components = list(self.prompt_map[agent_type].keys())
                raise ValueError(f"Unknown component '{component}' for type '{agent_type}'. Available components: {available_components}")
            
            # STEP 1: Initialize tools and resources
            initialization_result = await self._initialize_tools_and_resources(ctx)
            
            # STEP 2: Fetch prompt
            prompt_kwargs = {
                "earliest_time": earliest_time,
                "latest_time": latest_time,
                "focus_index": focus_index,
                "focus_host": focus_host,
                "complexity_level": complexity_level,
                "include_performance_analysis": include_performance_analysis,
                "enable_cross_validation": enable_cross_validation,
                "analysis_mode": analysis_mode,
                "analysis_type": analysis_type,
                "analysis_depth": analysis_depth,
                "include_delay_analysis": include_delay_analysis,
                "include_platform_instrumentation": include_platform_instrumentation
            }
            
            prompt_content = await self._fetch_prompt(ctx, agent_type, component, **prompt_kwargs)
            
            # STEP 3: Define workflow steps
            workflow_steps = await self._define_workflow_steps(ctx, prompt_content)
            
            # STEP 4: Fetch required resources
            resource_content = await self._fetch_required_resources(ctx, workflow_steps)
            
            # STEP 5: Execute agent with context
            agent_response = await self._execute_agent_with_context(
                ctx, prompt_content, workflow_steps, resource_content, initialization_result
            )
            
            # STEP 6: Verify and execute tool calls
            workflow_execution = await self._verify_and_execute_tool_calls(ctx, workflow_steps)
            
            await ctx.info("🎉 OpenAI agent workflow completed successfully")
            logger.info("OpenAI agent workflow completed successfully")
            
            return {
                "status": "success",
                "agent_type": agent_type,
                "component": component,
                "agent_response": agent_response,
                "workflow_execution": {
                    "total_steps": workflow_execution.total_steps,
                    "completed_steps": workflow_execution.completed_steps,
                    "failed_steps": workflow_execution.failed_steps,
                    "success_rate": workflow_execution.completed_steps / workflow_execution.total_steps if workflow_execution.total_steps > 0 else 0,
                    "step_results": workflow_execution.step_results
                },
                "context": {
                    "tools_available": initialization_result["tool_count"],
                    "resources_available": initialization_result["resource_count"],
                    "resources_fetched": len(resource_content),
                    "workflow_steps_defined": len(workflow_steps),
                    "tool_calls_extracted": sum(len(step.tool_calls) for step in workflow_steps),
                    "resource_calls_extracted": sum(len(step.resource_calls) for step in workflow_steps)
                },
                "parameters": prompt_kwargs
            }
            
        except ValueError as e:
            error_msg = f"Invalid parameters: {str(e)}"
            await ctx.error(error_msg)
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "error_type": "validation_error"
            }
        except Exception as e:
            error_msg = f"Agent execution failed: {str(e)}"
            logger.error(f"OpenAI Agent tool error: {e}", exc_info=True)
            await ctx.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "error_type": "execution_error"
            } 