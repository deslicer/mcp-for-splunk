"""
Tool for listing Splunk users.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class ListUsers(BaseTool):
    """
    List all Splunk users.
    """

    METADATA = ToolMetadata(
        name="list_users",
        description="List all Splunk users and their properties",
        category="admin",
        tags=["users", "administration", "management"],
        requires_connection=True
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """
        List all Splunk users.

        Returns:
            Dict containing list of users and their properties
        """
        log_tool_execution("list_users")

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        self.logger.info("Retrieving list of Splunk users")
        ctx.info("Retrieving list of Splunk users")

        try:
            users = []
            for user in service.users:
                users.append({
                    "username": user.name,
                    "realname": user.content.get("realname"),
                    "email": user.content.get("email"),
                    "roles": user.content.get("roles", []),
                    "type": user.content.get("type"),
                    "defaultApp": user.content.get("defaultApp")
                })

            ctx.info(f"Found {len(users)} users")
            return self.format_success_response({
                "count": len(users),
                "users": users
            })
        except Exception as e:
            self.logger.error(f"Failed to list users: {str(e)}")
            ctx.error(f"Failed to list users: {str(e)}")
            return self.format_error_response(str(e))
