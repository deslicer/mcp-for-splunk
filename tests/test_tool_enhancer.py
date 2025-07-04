"""
Tests for the Tool Description Enhancer functionality.
"""

import pytest
from typing import Any

from src.tools.admin.tool_enhancer import ToolDescriptionEnhancer


class TestToolDescriptionEnhancer:
    """Test tool description enhancement functionality"""

    @pytest.fixture
    async def enhancer_tool(self):
        """Create a ToolDescriptionEnhancer instance for testing"""
        return ToolDescriptionEnhancer("enhance_tool_description", "Tool description enhancer")

    async def test_enhance_existing_tool_description(self, enhancer_tool, fastmcp_client, extract_tool_result):
        """Test enhancing a known tool's description"""
        async with fastmcp_client as client:
            result = await client.call_tool(
                "enhance_tool_description",
                {"tool_name": "get_configurations"}
            )
            
            data = extract_tool_result(result)
            
            if "error" not in data:
                assert "tool_name" in data
                assert "original_description" in data
                assert "enhanced_description" in data
                assert "analysis" in data
                assert "recommendations" in data
                
                # Verify enhanced description has Args section
                enhanced_desc = data["enhanced_description"]
                assert "Args:" in enhanced_desc
                
                # Verify analysis contains parameters
                analysis = data["analysis"]
                assert "parameters" in analysis
                assert "examples" in analysis

    async def test_enhance_nonexistent_tool(self, enhancer_tool, fastmcp_client, extract_tool_result):
        """Test error handling for non-existent tool"""
        async with fastmcp_client as client:
            result = await client.call_tool(
                "enhance_tool_description",
                {"tool_name": "nonexistent_tool"}
            )
            
            data = extract_tool_result(result)
            # Should return error for non-existent tool
            assert "error" in data or "not found" in str(result)

    async def test_parameter_analysis(self, enhancer_tool):
        """Test parameter analysis functionality"""
        # Test with our own tool to ensure consistent results
        analysis = await enhancer_tool._analyze_tool(
            None,  # ctx not needed for this test
            "enhance_tool_description",
            enhancer_tool.METADATA,
            ToolDescriptionEnhancer,
            generate_examples=True,
            include_response_format=True
        )
        
        # Verify analysis structure
        assert "metadata" in analysis
        assert "parameters" in analysis
        assert "examples" in analysis
        assert "response_format" in analysis
        
        # Check specific parameters
        params = analysis["parameters"]
        assert "tool_name" in params
        assert params["tool_name"]["required"] is True
        assert "str" in params["tool_name"]["type"]
        
        assert "generate_examples" in params
        assert params["generate_examples"]["required"] is False
        assert "bool" in params["generate_examples"]["type"]

    async def test_admin_category_examples(self, enhancer_tool):
        """Test example generation for admin category tools"""
        parameters = {
            "conf_file": {"type": "str", "required": True},
            "stanza": {"type": "str", "required": False},
            "app_name": {"type": "str", "required": False}
        }
        
        examples = enhancer_tool._generate_admin_examples(parameters)
        
        # Verify admin-specific examples
        assert "conf_file" in examples
        assert "props" in examples["conf_file"]
        assert "transforms" in examples["conf_file"]
        
        assert "stanza" in examples
        assert "default" in examples["stanza"]
        
        assert "app_name" in examples
        assert isinstance(examples["app_name"], list)

    async def test_search_category_examples(self, enhancer_tool):
        """Test example generation for search category tools"""
        parameters = {
            "query": {"type": "str", "required": True},
            "earliest_time": {"type": "str", "required": False},
            "max_results": {"type": "int", "required": False}
        }
        
        examples = enhancer_tool._generate_search_examples(parameters)
        
        # Verify search-specific examples
        assert "query" in examples
        assert any("index=" in str(q) for q in examples["query"])
        
        assert "earliest_time" in examples
        assert "-24h@h" in examples["earliest_time"]
        
        assert "max_results" in examples
        assert 100 in examples["max_results"]

    async def test_metadata_category_examples(self, enhancer_tool):
        """Test example generation for metadata category tools"""
        parameters = {
            "index_name": {"type": "str", "required": True},
            "sourcetype": {"type": "str", "required": False}
        }
        
        examples = enhancer_tool._generate_metadata_examples(parameters)
        
        # Verify metadata-specific examples
        assert "index_name" in examples
        assert "main" in examples["index_name"]
        
        assert "sourcetype" in examples
        assert "access_combined" in examples["sourcetype"]

    async def test_generic_examples(self, enhancer_tool):
        """Test generic example generation"""
        parameters = {
            "string_param": {"type": "str", "required": True},
            "int_param": {"type": "int", "required": False},
            "bool_param": {"type": "bool", "required": False}
        }
        
        examples = enhancer_tool._generate_generic_examples(parameters)
        
        assert "string_param" in examples
        assert isinstance(examples["string_param"], list)
        
        assert "int_param" in examples
        assert isinstance(examples["int_param"], list)
        assert all(isinstance(x, int) for x in examples["int_param"])
        
        assert "bool_param" in examples
        assert True in examples["bool_param"]
        assert False in examples["bool_param"]

    async def test_enhanced_description_generation(self, enhancer_tool):
        """Test enhanced description generation"""
        # Mock analysis data
        analysis = {
            "parameters": {
                "tool_name": {
                    "type": "str",
                    "required": True,
                    "default": None,
                    "description": "Name of the tool to enhance"
                },
                "generate_examples": {
                    "type": "bool",
                    "required": False,
                    "default": "True",
                    "description": "Whether to generate examples"
                }
            },
            "examples": {
                "tool_name": ["get_configurations", "list_indexes"],
                "generate_examples": [True, False]
            },
            "response_format": {
                "type": "object",
                "common_fields": ["status"]
            }
        }
        
        enhanced_desc = await enhancer_tool._generate_enhanced_description(
            None,  # ctx not needed
            "test_tool",
            enhancer_tool.METADATA,
            analysis
        )
        
        # Verify enhanced description structure
        assert "Args:" in enhanced_desc
        assert "tool_name (str):" in enhanced_desc
        assert "generate_examples (bool), optional:" in enhanced_desc
        assert "Example Values:" in enhanced_desc
        assert "Response Format:" in enhanced_desc

    async def test_recommendations_generation(self, enhancer_tool):
        """Test recommendation generation"""
        # Test with analysis that has undocumented parameters
        analysis = {
            "metadata": {"category": "admin", "requires_connection": True},
            "parameters": {
                "documented_param": {"description": "This is documented"},
                "undocumented_param": {"description": ""}
            },
            "examples": {}
        }
        
        recommendations = enhancer_tool._generate_recommendations(analysis)
        
        assert len(recommendations) > 0
        assert any("undocumented_param" in rec for rec in recommendations)
        
        # Test with well-documented analysis
        well_documented_analysis = {
            "metadata": {"category": "search", "requires_connection": False},
            "parameters": {
                "query": {"description": "Search query to execute"},
                "max_results": {"description": "Maximum number of results"}
            },
            "examples": {
                "query": ["index=main"],
                "max_results": [100]
            }
        }
        
        good_recommendations = enhancer_tool._generate_recommendations(well_documented_analysis)
        # For search category, we should get query validation suggestion
        assert any("query validation" in rec for rec in good_recommendations)

    async def test_parameter_description_extraction(self, enhancer_tool):
        """Test parameter description extraction from docstrings"""
        
        def sample_method(self, ctx, param1: str, param2: int = 100):
            """
            Sample method for testing.
            
            Args:
                param1 (str): First parameter description
                param2 (int, optional): Second parameter with default value
                
            Returns:
                Dict with results
            """
            pass
        
        # Test extraction for param1
        desc1 = enhancer_tool._extract_param_description_from_docstring(sample_method, "param1")
        assert "First parameter description" in desc1
        
        # Test extraction for param2
        desc2 = enhancer_tool._extract_param_description_from_docstring(sample_method, "param2")
        assert "Second parameter" in desc2
        
        # Test for non-existent parameter
        desc3 = enhancer_tool._extract_param_description_from_docstring(sample_method, "param3")
        assert desc3 == ""

    async def test_response_format_analysis(self, enhancer_tool):
        """Test response format analysis"""
        
        def sample_method(self) -> dict[str, Any]:
            """Sample method"""
            return {}
        
        response_format = enhancer_tool._analyze_response_format(sample_method)
        
        assert "type" in response_format
        assert "common_fields" in response_format
        assert "status" in response_format["common_fields"]
        assert response_format["type"] == "object" 