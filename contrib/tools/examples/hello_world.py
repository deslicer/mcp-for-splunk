"""
Hello World example tool demonstrating the contribution pattern.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class HelloWorldTool(BaseTool):
    """
    A simple example tool that demonstrates the contribution pattern.

    This tool shows how to:
    - Inherit from BaseTool
    - Define metadata
    - Implement the execute method
    - Handle parameters
    - Return formatted responses
    """

    METADATA = ToolMetadata(
        name="hello_world",
        description="A simple hello world example tool for demonstrating contributions",
        category="examples",
        tags=["example", "tutorial", "demo"],
        requires_connection=False,  # This tool doesn't need Splunk connection
        version="1.0.0",
    )

    async def execute(self, ctx: Context, name: str | None = "World") -> dict[str, Any]:
        """
        Say hello to someone.

        Args:
            name: Name to greet (default: "World")

        Returns:
            Dict containing greeting message

        Example:
            hello_world(name="Alice") -> {"message": "Hello, Alice!"}
        """
        log_tool_execution("hello_world", name=name)

        self.logger.info(f"Greeting: {name}")
        ctx.info(f"Saying hello to {name}")

        try:
            message = f"Hello, {name}!"

            return self.format_success_response(
                {"message": message, "greeted": name, "tool": "hello_world"}
            )

        except Exception as e:
            self.logger.error(f"Failed to generate greeting: {str(e)}")
            ctx.error(f"Failed to generate greeting: {str(e)}")
            return self.format_error_response(str(e))
