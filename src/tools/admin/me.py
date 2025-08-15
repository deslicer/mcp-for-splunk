"""
Tool for getting current user information.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class Me(BaseTool):
    """
    Get current authenticated user information.
    """

    METADATA = ToolMetadata(
        name="me",
        description=(
            "Retrieve information about the currently authenticated Splunk user. "
            "Use this tool whenever you need to check the current user's details, permissions, "
            "roles, or capabilities, such as for debugging access issues, understanding available "
            "actions, or verifying user context in Splunk environments. "
            "This tool requires no arguments.\n\n"
            "Response Format:\n"
            "Returns a dictionary with 'status' field indicating success/error and 'data' containing:\n"
            "- username: Current authenticated username\n"
            "- realname: Full display name\n"
            "- email: Email address\n"
            "- roles: Array of assigned role names\n"
            "- type: User type (e.g., 'Splunk')\n"
            "- defaultApp: Default application for the user\n"
            "- capabilities: Array of capabilities granted through roles"
        ),
        category="admin",
        tags=["user", "authentication", "current", "me", "identity"],
        requires_connection=True,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """
        Get current authenticated user information.

        Returns:
            Dict containing current user information and capabilities
        """
        log_tool_execution("me")

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        self.logger.info("Retrieving current user information")
        await ctx.info("Retrieving current user information")

        try:
            # Get current username from the service
            current_username = service.username
            if not current_username:
                return self.format_error_response("Unable to determine current username")

            self.logger.info(f"Current username: {current_username}")
            await ctx.info(f"Getting details for user: {current_username}")

            # Get user object from users collection
            if current_username not in service.users:
                return self.format_error_response(
                    f"User '{current_username}' not found in users collection"
                )

            user = service.users[current_username]

            # Extract user information
            user_info = {
                "username": user.name,
                "realname": user.content.get("realname"),
                "email": user.content.get("email"),
                "roles": user.content.get("roles", []),
                "type": user.content.get("type"),
                "defaultApp": user.content.get("defaultApp"),
                "force_change_pass": user.content.get("force_change_pass"),
                "locked_out": user.content.get("locked_out"),
                "restart_background_jobs": user.content.get("restart_background_jobs"),
                "tz": user.content.get("tz"),
            }

            # Get capabilities by iterating through user's roles
            capabilities = set()
            try:
                for role_name in user_info.get("roles", []):
                    if role_name in service.roles:
                        role = service.roles[role_name]
                        role_capabilities = role.content.get("capabilities", [])
                        if isinstance(role_capabilities, list):
                            capabilities.update(role_capabilities)
                        elif isinstance(role_capabilities, str):
                            # Handle case where capabilities might be a single string
                            capabilities.add(role_capabilities)

                user_info["capabilities"] = sorted(list(capabilities))
            except Exception as e:
                self.logger.warning(f"Could not retrieve capabilities: {str(e)}")
                user_info["capabilities"] = []

            # Filter out None values for cleaner output
            user_info = {k: v for k, v in user_info.items() if v is not None}

            await ctx.info(f"Retrieved information for user: {current_username}")
            return self.format_success_response({"data": user_info})

        except Exception as e:
            self.logger.error(f"Failed to get current user information: {str(e)}")
            await ctx.error(f"Failed to get current user information: {str(e)}")
            return self.format_error_response(str(e))
