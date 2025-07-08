"""
Tests for the OpenAI Agent tool.

Tests the OpenAI agent integration with Splunk MCP server,
including prompt retrieval, tool discovery, and agent execution.
"""

import os
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from fastmcp import FastMCP, Context

from src.tools.agents.openai_agent import OpenAIAgentTool, AgentConfig


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch("src.tools.agents.openai_agent.OpenAI") as mock_openai:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test agent response with analysis and recommendations."
        
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for OpenAI configuration."""
    env_vars = {
        "OPENAI_API_KEY": "test-api-key",
        "OPENAI_MODEL": "gpt-4o",
        "OPENAI_TEMPERATURE": "0.7",
        "OPENAI_MAX_TOKENS": "4000"
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def agent_tool(mock_env_vars, mock_openai_client):
    """Create an OpenAI agent tool instance for testing."""
    return OpenAIAgentTool("execute_openai_agent", "agents")


class TestAgentConfig:
    """Test the AgentConfig dataclass."""
    
    def test_config_creation_with_defaults(self, mock_env_vars):
        """Test creating config with default values."""
        config = AgentConfig(api_key="test-key")
        
        assert config.api_key == "test-key"
        assert config.model == "gpt-4o"
        assert config.temperature == 0.7
        assert config.max_tokens == 4000
    
    def test_config_creation_with_custom_values(self):
        """Test creating config with custom values."""
        config = AgentConfig(
            api_key="custom-key",
            model="gpt-3.5-turbo",
            temperature=0.5,
            max_tokens=2000
        )
        
        assert config.api_key == "custom-key"
        assert config.model == "gpt-3.5-turbo"
        assert config.temperature == 0.5
        assert config.max_tokens == 2000


class TestOpenAIAgentTool:
    """Test the OpenAI Agent tool implementation."""
    
    def test_tool_metadata(self):
        """Test tool metadata is correctly defined."""
        assert OpenAIAgentTool.METADATA.name == "execute_openai_agent"
        assert OpenAIAgentTool.METADATA.category == "agents"
        assert "troubleshooting" in OpenAIAgentTool.METADATA.description.lower()
    
    def test_config_loading_success(self, mock_env_vars, mock_openai_client):
        """Test successful configuration loading from environment."""
        tool = OpenAIAgentTool("test", "agents")
        
        assert tool.config.api_key == "test-api-key"
        assert tool.config.model == "gpt-4o"
        assert tool.config.temperature == 0.7
        assert tool.config.max_tokens == 4000
    
    def test_config_loading_missing_api_key(self, mock_openai_client):
        """Test configuration loading fails without API key."""
        with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is required"):
            OpenAIAgentTool("test", "agents")
    
    def test_prompt_map_initialization(self, agent_tool):
        """Test that prompt map is correctly initialized."""
        assert "troubleshooting" in agent_tool.prompt_map
        troubleshooting_prompts = agent_tool.prompt_map["troubleshooting"]
        
        expected_components = ["performance", "inputs", "indexing", "inputs_multi"]
        for component in expected_components:
            assert component in troubleshooting_prompts
    
    @patch("src.tools.agents.openai_agent.tool_registry")
    def test_get_available_tools(self, mock_registry, agent_tool):
        """Test getting available tools from registry."""
        # Mock tool metadata
        mock_metadata = Mock()
        mock_metadata.name = "test_tool"
        mock_metadata.description = "Test tool description"
        
        mock_registry.list_tools.return_value = [mock_metadata]
        
        tools = agent_tool._get_available_tools()
        
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "test_tool"
        assert tools[0]["function"]["description"] == "Test tool description"
    
    @patch("src.tools.agents.openai_agent.tool_registry")
    def test_get_available_tools_excludes_self(self, mock_registry, agent_tool):
        """Test that the agent tool excludes itself from available tools."""
        # Mock tool metadata including the agent tool itself
        agent_metadata = Mock()
        agent_metadata.name = "execute_openai_agent"
        
        other_metadata = Mock()
        other_metadata.name = "other_tool"
        other_metadata.description = "Other tool"
        
        mock_registry.list_tools.return_value = [agent_metadata, other_metadata]
        
        tools = agent_tool._get_available_tools()
        
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "other_tool"
    
    async def test_get_prompt_content_success(self, agent_tool):
        """Test successful prompt content retrieval."""
        mock_ctx = Mock(spec=Context)
        
        # Mock prompt instance
        prompt_class = agent_tool.prompt_map["troubleshooting"]["performance"]
        with patch.object(prompt_class, '__new__') as mock_prompt_new:
            mock_instance = Mock()
            mock_instance.get_prompt = AsyncMock(return_value={
                "content": [{"type": "text", "text": "Test prompt content"}]
            })
            mock_prompt_new.return_value = mock_instance
            
            content = await agent_tool._get_prompt_content(
                mock_ctx, "troubleshooting", "performance"
            )
            
            assert content == "Test prompt content"
    
    async def test_get_prompt_content_fallback(self, agent_tool):
        """Test fallback prompt content when prompt retrieval fails."""
        mock_ctx = Mock(spec=Context)
        
        # Mock prompt to raise an exception
        prompt_class = agent_tool.prompt_map["troubleshooting"]["performance"]
        with patch.object(prompt_class, '__new__') as mock_prompt_new:
            mock_prompt_new.side_effect = Exception("Prompt error")
            
            content = await agent_tool._get_prompt_content(
                mock_ctx, "troubleshooting", "performance"
            )
            
            assert "Splunk troubleshooting expert" in content
            assert "performance" in content
    
    async def test_get_prompt_content_unknown_type(self, agent_tool):
        """Test prompt content for unknown type returns basic prompt."""
        mock_ctx = Mock(spec=Context)
        
        content = await agent_tool._get_prompt_content(
            mock_ctx, "unknown_type", "unknown_component"
        )
        
        assert "Splunk troubleshooting expert" in content
        assert "unknown_component" in content
    
    async def test_execute_agent_workflow_success(self, agent_tool):
        """Test successful agent workflow execution."""
        mock_ctx = Mock(spec=Context)
        mock_ctx.info = AsyncMock()
        
        prompt_content = "Test prompt for troubleshooting"
        available_tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "Test tool",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        
        result = await agent_tool._execute_agent_workflow(
            mock_ctx, prompt_content, available_tools
        )
        
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Verify context info calls
        assert mock_ctx.info.call_count >= 3
    
    async def test_execute_agent_workflow_openai_error(self, agent_tool):
        """Test agent workflow execution with OpenAI API error."""
        mock_ctx = Mock(spec=Context)
        mock_ctx.info = AsyncMock()
        mock_ctx.error = AsyncMock()
        
        # Mock OpenAI client to raise an exception
        agent_tool.client.chat.completions.create.side_effect = Exception("OpenAI API error")
        
        with pytest.raises(RuntimeError, match="Agent execution failed"):
            await agent_tool._execute_agent_workflow(
                mock_ctx, "test prompt", []
            )
        
        mock_ctx.error.assert_called_once()
    
    async def test_execute_success(self, agent_tool):
        """Test successful tool execution."""
        mock_ctx = Mock(spec=Context)
        mock_ctx.info = AsyncMock()
        
        with patch.object(agent_tool, '_get_prompt_content') as mock_get_prompt:
            mock_get_prompt.return_value = "Test prompt content"
            
            with patch.object(agent_tool, '_get_available_tools') as mock_get_tools:
                mock_get_tools.return_value = []
                
                with patch.object(agent_tool, '_execute_agent_workflow') as mock_execute:
                    mock_execute.return_value = "Agent analysis result"
                    
                    result = await agent_tool.execute(
                        mock_ctx,
                        agent_type="troubleshooting",
                        component="performance"
                    )
        
        assert result["status"] == "success"
        assert result["agent_type"] == "troubleshooting"
        assert result["component"] == "performance"
        assert result["analysis"] == "Agent analysis result"
        assert "tools_available" in result
    
    async def test_execute_invalid_agent_type(self, agent_tool):
        """Test execution with invalid agent type."""
        mock_ctx = Mock(spec=Context)
        mock_ctx.error = AsyncMock()
        
        result = await agent_tool.execute(
            mock_ctx,
            agent_type="invalid_type",
            component="performance"
        )
        
        assert result["status"] == "error"
        assert result["error_type"] == "validation_error"
        assert "Unknown agent type" in result["error"]
    
    async def test_execute_invalid_component(self, agent_tool):
        """Test execution with invalid component."""
        mock_ctx = Mock(spec=Context)
        mock_ctx.error = AsyncMock()
        
        result = await agent_tool.execute(
            mock_ctx,
            agent_type="troubleshooting",
            component="invalid_component"
        )
        
        assert result["status"] == "error"
        assert result["error_type"] == "validation_error"
        assert "Unknown component" in result["error"]
    
    async def test_execute_with_kwargs(self, agent_tool):
        """Test execution with additional keyword arguments."""
        mock_ctx = Mock(spec=Context)
        mock_ctx.info = AsyncMock()
        
        with patch.object(agent_tool, '_get_prompt_content') as mock_get_prompt:
            mock_get_prompt.return_value = "Test prompt content"
            
            with patch.object(agent_tool, '_get_available_tools') as mock_get_tools:
                mock_get_tools.return_value = []
                
                with patch.object(agent_tool, '_execute_agent_workflow') as mock_execute:
                    mock_execute.return_value = "Agent analysis result"
                    
                    result = await agent_tool.execute(
                        mock_ctx,
                        agent_type="troubleshooting",
                        component="inputs",
                        earliest_time="-7d",
                        latest_time="now",
                        focus_index="main"
                    )
        
        assert result["status"] == "success"
        
        # Verify that kwargs were passed to prompt content retrieval
        mock_get_prompt.assert_called_once()
        call_args = mock_get_prompt.call_args
        assert "earliest_time" in call_args.kwargs
        assert call_args.kwargs["earliest_time"] == "-7d"
    
    async def test_execute_exception_handling(self, agent_tool):
        """Test execution with unexpected exception."""
        mock_ctx = Mock(spec=Context)
        mock_ctx.info = AsyncMock()
        mock_ctx.error = AsyncMock()
        
        with patch.object(agent_tool, '_get_prompt_content') as mock_get_prompt:
            mock_get_prompt.side_effect = Exception("Unexpected error")
            
            result = await agent_tool.execute(
                mock_ctx,
                agent_type="troubleshooting",
                component="performance"
            )
        
        assert result["status"] == "error"
        assert result["error_type"] == "execution_error"
        assert "Agent execution failed" in result["error"]


@pytest.mark.asyncio
async def test_real_openai_integration():
    """
    Test with real OpenAI API (requires valid API key).
    
    This test is skipped by default but can be run manually
    when OPENAI_API_KEY is available in the environment.
    """
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not available for real API test")
    
    # This test would use the real OpenAI API
    # Only run when explicitly testing with real credentials
    tool = OpenAIAgentTool("execute_openai_agent", "agents")
    
    mock_ctx = Mock(spec=Context)
    mock_ctx.info = AsyncMock()
    
    # Test with minimal parameters to avoid high API costs
    result = await tool.execute(
        mock_ctx,
        agent_type="troubleshooting",
        component="performance"
    )
    
    assert result["status"] == "success"
    assert "analysis" in result
    assert len(result["analysis"]) > 0 