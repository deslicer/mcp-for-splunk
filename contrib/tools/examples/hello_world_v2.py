"""
Second run example tool
"""

from typing import Any, Dict

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class HelloWorldV2Tool(BaseTool):
    """
    Second run example tool

    This tool provides functionality for:
    - TODO: Add specific functionality descriptions
    - TODO: Add use cases
    - TODO: Add examples
    """

    METADATA = ToolMetadata(
        name="hello_world_v2",
        description="Second run example tool",
        category="examples",
        tags=["example", "tutorial", "demo"],
        requires_connection=False,
        version="1.0.0"
    )

    async def execute(self, ctx: Context, **kwargs) -> Dict[str, Any]:
        """
        Execute the hello_world_v2 functionality.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            Dict containing the tool results

        Example:
            hello_world_v2() -> {"result": "TODO: Add example result"}
        """
        log_tool_execution("hello_world_v2", **kwargs)

        self.logger.info(f"Executing hello_world_v2 tool")
        ctx.info(f"Running hello_world_v2 operation")

        try:
            # TODO: Implement tool functionality here
            #
            # If this tool requires Splunk connection:
            # is_available, service, error_msg = self.check_splunk_available(ctx)
            # if not is_available:
            #     return self.format_error_response(error_msg)
            #
            # Example implementation:
            result = {
                "message": "TODO: Implement hello_world_v2 functionality",
                "tool": "hello_world_v2",
                "parameters": kwargs
            }

            return self.format_success_response(result)

        except Exception as e:
            self.logger.error(f"Failed to execute hello_world_v2: {str(e)}")
            ctx.error(f"Failed to execute hello_world_v2: {str(e)}")
            return self.format_error_response(str(e))
