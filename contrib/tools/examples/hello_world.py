"""
A simple example tool that returns a greeting
"""

from typing import Any, Dict

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class HelloWorldTool(BaseTool):
    """
    A simple example tool that returns a greeting

    This tool provides functionality for:
    - TODO: Add specific functionality descriptions
    - TODO: Add use cases
    - TODO: Add examples
    """

    METADATA = ToolMetadata(
        name="hello_world",
        description="A simple example tool that returns a greeting",
        category="examples",
        tags=["example", "tutorial", "demo"],
        requires_connection=False,
        version="1.0.0"
    )

    async def execute(self, ctx: Context, **kwargs) -> Dict[str, Any]:
        """
        Execute the hello_world functionality.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            Dict containing the tool results

        Example:
            hello_world() -> {"result": "TODO: Add example result"}
        """
        log_tool_execution("hello_world", **kwargs)

        self.logger.info(f"Executing hello_world tool")
        ctx.info(f"Running hello_world operation")

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
                "message": "TODO: Implement hello_world functionality",
                "tool": "hello_world",
                "parameters": kwargs
            }

            return self.format_success_response(result)

        except Exception as e:
            self.logger.error(f"Failed to execute hello_world: {str(e)}")
            ctx.error(f"Failed to execute hello_world: {str(e)}")
            return self.format_error_response(str(e))
