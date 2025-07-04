"""
Tool Enhancement Utility for MCP Server for Splunk

This tool analyzes existing MCP tools, calls them to understand their behavior,
and generates improved descriptions with detailed argument definitions and examples.
"""

import inspect
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.discovery import discover_tools
from src.core.registry import tool_registry
from src.core.utils import log_tool_execution


class ToolDescriptionEnhancer(BaseTool):
    """
    Enhance tool descriptions with detailed argument definitions and examples.
    """

    METADATA = ToolMetadata(
        name="enhance_tool_description",
        description=(
            "Analyzes existing MCP tools and enhances their descriptions with detailed "
            "argument definitions, parameter examples, and usage patterns. This tool "
            "examines the current tool's metadata, inspects its execute method signature, "
            "and generates comprehensive documentation improvements.\n\n"
            "Args:\n"
            "    tool_name (str): Name of the tool to enhance (e.g., 'get_configurations', 'list_indexes')\n"
            "    generate_examples (bool, optional): Whether to generate parameter examples "
            "based on the tool's signature and category. Defaults to True.\n"
            "    include_response_format (bool, optional): Whether to analyze and include "
            "expected response format information. Defaults to True."
        ),
        category="admin",
        tags=["tool-enhancement", "metadata", "documentation", "analysis"],
        requires_connection=False,
    )

    async def execute(
        self,
        ctx: Context,
        tool_name: str,
        generate_examples: bool = True,
        include_response_format: bool = True,
    ) -> dict[str, Any]:
        """
        Enhance a tool's description with detailed argument definitions and examples.

        Args:
            tool_name (str): Name of the tool to enhance
            generate_examples (bool): Whether to generate parameter examples
            include_response_format (bool): Whether to include response format info

        Returns:
            Dict containing enhanced tool description and metadata
        """
        log_tool_execution(
            "enhance_tool_description",
            target_tool=tool_name,
            generate_examples=generate_examples,
        )

        if ctx:
            await ctx.info(f"Analyzing tool: {tool_name}")

        try:
            # Discover tools if not already done
            discover_tools()

            # Get the tool from registry
            tool_metadata = tool_registry.get_metadata(tool_name)
            tool_class = tool_registry._tools.get(tool_name)

            if not tool_metadata or not tool_class:
                return self.format_error_response(f"Tool '{tool_name}' not found in registry")

            if ctx:
                await ctx.info(f"Found tool metadata and class for: {tool_name}")

            # Analyze the tool
            analysis_result = await self._analyze_tool(
                ctx, tool_name, tool_metadata, tool_class, generate_examples, include_response_format
            )

            # Generate enhanced description
            enhanced_description = await self._generate_enhanced_description(
                ctx, tool_name, tool_metadata, analysis_result
            )

            if ctx:
                await ctx.info(f"Successfully enhanced description for tool: {tool_name}")

            return self.format_success_response({
                "tool_name": tool_name,
                "original_description": tool_metadata.description,
                "enhanced_description": enhanced_description,
                "analysis": analysis_result,
                "recommendations": self._generate_recommendations(analysis_result),
            })

        except Exception as e:
            error_msg = f"Failed to enhance tool description for '{tool_name}': {str(e)}"
            self.logger.error(error_msg)
            if ctx:
                await ctx.error(error_msg)
            return self.format_error_response(error_msg)

    async def _analyze_tool(
        self,
        ctx: Context | None,
        tool_name: str,
        tool_metadata: ToolMetadata,
        tool_class: type[BaseTool],
        generate_examples: bool,
        include_response_format: bool,
    ) -> dict[str, Any]:
        """Analyze a tool to understand its structure and behavior."""
        analysis = {
            "metadata": {
                "name": tool_metadata.name,
                "category": tool_metadata.category,
                "tags": tool_metadata.tags,
                "requires_connection": tool_metadata.requires_connection,
            },
            "parameters": {},
            "examples": {},
            "response_format": {},
        }

        # Analyze the execute method signature
        execute_method = tool_class.execute
        sig = inspect.signature(execute_method)

        # Get parameter information
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "ctx"):
                continue

            param_info = {
                "name": param_name,
                "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                "default": str(param.default) if param.default != inspect.Parameter.empty else None,
                "required": param.default == inspect.Parameter.empty,
                "description": self._extract_param_description_from_docstring(execute_method, param_name),
            }

            analysis["parameters"][param_name] = param_info

        # Generate examples if requested
        if generate_examples:
            analysis["examples"] = self._generate_parameter_examples(tool_metadata.category, analysis["parameters"])

        # Analyze response format if requested
        if include_response_format:
            analysis["response_format"] = self._analyze_response_format(execute_method)

        return analysis

    def _extract_param_description_from_docstring(self, method, param_name: str) -> str:
        """Extract parameter description from method docstring."""
        if not method.__doc__:
            return ""

        docstring = method.__doc__
        lines = docstring.split('\n')

        # Look for Args section
        in_args_section = False
        for line in lines:
            line = line.strip()
            if line.startswith("Args:"):
                in_args_section = True
                continue
            elif in_args_section and line.startswith("Returns:"):
                break
            elif in_args_section and line.startswith(f"{param_name} "):
                # Found parameter description
                return line.split(":", 1)[1].strip() if ":" in line else line
            elif in_args_section and line.startswith(f"{param_name}("):
                # Alternative format
                return line.split(":", 1)[1].strip() if ":" in line else line

        return ""

    def _generate_parameter_examples(self, category: str, parameters: dict) -> dict[str, Any]:
        """Generate example parameter values based on tool category and parameter types."""
        examples = {}

        # Category-specific example generators
        category_examples = {
            "admin": self._generate_admin_examples,
            "search": self._generate_search_examples,
            "metadata": self._generate_metadata_examples,
            "health": self._generate_health_examples,
            "kvstore": self._generate_kvstore_examples,
        }

        generator = category_examples.get(category, self._generate_generic_examples)
        examples = generator(parameters)

        return examples

    def _generate_admin_examples(self, parameters: dict) -> dict[str, Any]:
        """Generate examples for admin tools."""
        examples = {}
        for param_name, param_info in parameters.items():
            if "conf_file" in param_name:
                examples[param_name] = ["props", "transforms", "inputs", "outputs", "server"]
            elif "stanza" in param_name:
                examples[param_name] = ["default", "splunk_web_access", "monitor:///var/log/messages"]
            elif "app" in param_name:
                examples[param_name] = ["search", "splunk_monitoring_console", "my_custom_app"]
            elif "user" in param_name:
                examples[param_name] = ["admin", "splunk-system-user", "analyst"]
            else:
                examples[param_name] = self._generate_generic_example(param_name, param_info)
        return examples

    def _generate_search_examples(self, parameters: dict) -> dict[str, Any]:
        """Generate examples for search tools."""
        examples = {}
        for param_name, param_info in parameters.items():
            if "query" in param_name:
                examples[param_name] = [
                    "index=main sourcetype=access_combined",
                    "| stats count by source",
                    "search error OR failure | head 10"
                ]
            elif "earliest_time" in param_name:
                examples[param_name] = ["-24h@h", "-7d", "2024-01-01T00:00:00"]
            elif "latest_time" in param_name:
                examples[param_name] = ["now", "@d", "2024-01-02T00:00:00"]
            elif "max_results" in param_name:
                examples[param_name] = [100, 500, 1000]
            else:
                examples[param_name] = self._generate_generic_example(param_name, param_info)
        return examples

    def _generate_metadata_examples(self, parameters: dict) -> dict[str, Any]:
        """Generate examples for metadata tools."""
        examples = {}
        for param_name, param_info in parameters.items():
            if "index" in param_name:
                examples[param_name] = ["main", "_internal", "security", "summary"]
            elif "sourcetype" in param_name:
                examples[param_name] = ["access_combined", "syslog", "splunkd", "csv"]
            elif "source" in param_name:
                examples[param_name] = ["/var/log/access.log", "udp:514", "tcp:1514"]
            else:
                examples[param_name] = self._generate_generic_example(param_name, param_info)
        return examples

    def _generate_health_examples(self, parameters: dict) -> dict[str, Any]:
        """Generate examples for health tools."""
        examples = {}
        for param_name, param_info in parameters.items():
            if "component" in param_name:
                examples[param_name] = ["indexer", "search_head", "forwarder", "deployment_server"]
            elif "feature" in param_name:
                examples[param_name] = ["data_inputs", "saved_searches", "kvstore", "cluster_health"]
            else:
                examples[param_name] = self._generate_generic_example(param_name, param_info)
        return examples

    def _generate_kvstore_examples(self, parameters: dict) -> dict[str, Any]:
        """Generate examples for KV store tools."""
        examples = {}
        for param_name, param_info in parameters.items():
            if "collection" in param_name:
                examples[param_name] = ["users", "configurations", "lookup_table", "audit_log"]
            elif "app" in param_name:
                examples[param_name] = ["search", "my_app", "splunk_monitoring_console"]
            elif "query" in param_name:
                examples[param_name] = ["{}", '{"status": "active"}', '{"timestamp": {"$gte": "2024-01-01"}}']
            else:
                examples[param_name] = self._generate_generic_example(param_name, param_info)
        return examples

    def _generate_generic_examples(self, parameters: dict) -> dict[str, Any]:
        """Generate generic examples for unknown categories."""
        examples = {}
        for param_name, param_info in parameters.items():
            examples[param_name] = self._generate_generic_example(param_name, param_info)
        return examples

    def _generate_generic_example(self, param_name: str, param_info: dict) -> Any:
        """Generate a generic example for a parameter."""
        param_type = param_info.get("type", "str")
        
        if "bool" in param_type:
            return [True, False]
        elif "int" in param_type:
            if "count" in param_name or "limit" in param_name:
                return [10, 50, 100]
            elif "port" in param_name:
                return [8089, 8000, 9997]
            else:
                return [1, 5, 10]
        elif "str" in param_type:
            if "host" in param_name:
                return ["localhost", "splunk.example.com", "10.1.1.100"]
            elif "username" in param_name:
                return ["admin", "splunk", "analyst"]
            elif "name" in param_name:
                return ["example_name", "my_item", "test_object"]
            else:
                return [f"example_{param_name}", f"sample_{param_name}"]
        else:
            return [f"example_{param_name}"]

    def _analyze_response_format(self, method) -> dict[str, Any]:
        """Analyze the expected response format from the method."""
        response_format = {
            "type": "object",
            "common_fields": ["status"],
            "success_fields": [],
            "error_fields": ["error"],
            "description": "Standard tool response format with status and relevant data fields"
        }

        # Try to extract return type information
        sig = inspect.signature(method)
        if sig.return_annotation != inspect.Parameter.empty:
            response_format["return_type"] = str(sig.return_annotation)

        return response_format

    async def _generate_enhanced_description(
        self, ctx: Context | None, tool_name: str, tool_metadata: ToolMetadata, analysis: dict
    ) -> str:
        """Generate an enhanced description based on analysis."""
        
        description_parts = []
        
        # Start with original description (cleaned up)
        original_desc = tool_metadata.description.split("\n\nArgs:")[0]  # Remove existing Args if present
        description_parts.append(original_desc)
        
        # Add parameter documentation
        if analysis["parameters"]:
            description_parts.append("\n\nArgs:")
            for param_name, param_info in analysis["parameters"].items():
                param_line = f"    {param_name}"
                
                # Add type information
                if param_info["type"] != "Any":
                    param_line += f" ({param_info['type']})"
                
                # Add required/optional indicator
                if not param_info["required"]:
                    param_line += ", optional"
                
                # Add description
                if param_info["description"]:
                    param_line += f": {param_info['description']}"
                elif param_name in analysis["examples"]:
                    # Generate description from examples
                    examples = analysis["examples"][param_name]
                    if isinstance(examples, list) and examples:
                        example_str = ", ".join(str(ex) for ex in examples[:3])
                        param_line += f": Parameter for {param_name}. Examples: {example_str}"
                
                # Add default value
                if param_info["default"] and param_info["default"] != "None":
                    param_line += f" (default: {param_info['default']})"
                
                description_parts.append(param_line)
        
        # Add examples section
        if analysis["examples"]:
            description_parts.append("\n\nExample Values:")
            for param_name, examples in analysis["examples"].items():
                if isinstance(examples, list) and examples:
                    example_values = ", ".join(f'"{ex}"' for ex in examples[:3])
                    description_parts.append(f"    {param_name}: {example_values}")
        
        # Add response format information
        if analysis["response_format"]:
            description_parts.append("\n\nResponse Format:")
            description_parts.append("    Returns a dictionary with 'status' field and relevant data fields.")
            if analysis["response_format"].get("common_fields"):
                common_fields = ", ".join(analysis["response_format"]["common_fields"])
                description_parts.append(f"    Common fields: {common_fields}")
        
        return "".join(description_parts)

    def _generate_recommendations(self, analysis: dict) -> list[str]:
        """Generate recommendations for improving the tool."""
        recommendations = []
        
        # Check if all parameters have descriptions
        undocumented_params = [
            param for param, info in analysis["parameters"].items()
            if not info["description"]
        ]
        if undocumented_params:
            recommendations.append(
                f"Add descriptions for parameters: {', '.join(undocumented_params)}"
            )
        
        # Check if examples are comprehensive
        if not analysis["examples"]:
            recommendations.append("Add parameter examples to improve usability")
        
        # Category-specific recommendations
        category = analysis["metadata"]["category"]
        if category == "search" and "query" in analysis["parameters"]:
            recommendations.append("Consider adding query validation and syntax examples")
        elif category == "admin" and analysis["metadata"]["requires_connection"]:
            recommendations.append("Document connection requirements and error handling")
        
        if not recommendations:
            recommendations.append("Tool description appears comprehensive")
        
        return recommendations 