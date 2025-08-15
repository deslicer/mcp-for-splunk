"""
Saved search tools for Splunk MCP server.

Provides comprehensive functionality for managing and executing Splunk saved searches
including listing, executing, creating, updating, and deleting saved searches.
"""

import time
from typing import Any, Literal

from fastmcp import Context
from splunklib.results import JSONResultsReader

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution, sanitize_search_query


class ListSavedSearches(BaseTool):
    """
    List saved searches available in the Splunk environment with filtering options.
    Returns metadata about saved searches including ownership, scheduling, and permissions.
    """

    METADATA = ToolMetadata(
        name="list_saved_searches",
        description=(
            "List saved searches with ownership, schedule, visibility, and permission metadata. "
            "Use this to discover available reports/automations and to filter by owner/app/sharing. "
            "Results reflect only saved searches the current user can access.\n\n"
            "Args:\n"
            "    owner (str, optional): Filter by owner name (optional)\n"
            "    app (str, optional): Filter by application name (optional)\n"
            "    sharing (str, optional): Filter by sharing level (optional)\n"
            "    include_disabled (bool, optional): Include disabled saved searches (default: False)\n\n"
        ),
        category="search",
        tags=["saved_searches", "list", "metadata"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        owner: str | None = None,
        app: str | None = None,
        sharing: Literal["user", "app", "global", "system"] | None = None,
        include_disabled: bool = False,
    ) -> dict[str, Any]:
        """
        List saved searches with optional filtering.

        Args:
            owner: Filter by owner name (optional)
            app: Filter by application name (optional)
            sharing: Filter by sharing level (optional)
            include_disabled: Include disabled saved searches (default: False)

        Returns:
            Dict containing:
                - saved_searches: List of saved search metadata
                - total_count: Total number of saved searches found
                - filtered_count: Number after applying filters

        Example:
            list_saved_searches(owner="admin", app="search", include_disabled=True)
        """
        log_tool_execution("list_saved_searches", owner=owner, app=app, sharing=sharing)

        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            await ctx.error(f"List saved searches failed: {error_msg}")
            return self.format_error_response(error_msg, saved_searches=[], total_count=0)

        try:
            await ctx.info("Retrieving saved searches list")
            saved_searches_list = []
            total_count = 0

            for saved_search in service.saved_searches:
                total_count += 1

                # Extract saved search metadata
                search_info = {
                    "name": saved_search.name,
                    "search": saved_search.content.get("search", ""),
                    "description": saved_search.content.get("description", ""),
                    "owner": saved_search.content.get("eai:acl", {}).get("owner", ""),
                    "app": saved_search.content.get("eai:acl", {}).get("app", ""),
                    "sharing": saved_search.content.get("eai:acl", {}).get("sharing", ""),
                    "disabled": self._convert_splunk_boolean(
                        saved_search.content.get("disabled"), False
                    ),
                    "is_scheduled": self._convert_splunk_boolean(
                        saved_search.content.get("is_scheduled"), False
                    ),
                    "is_visible": self._convert_splunk_boolean(
                        saved_search.content.get("is_visible"), True
                    ),
                    "cron_schedule": saved_search.content.get("cron_schedule", ""),
                    "next_scheduled_time": saved_search.content.get("next_scheduled_time", ""),
                    "earliest_time": saved_search.content.get("dispatch.earliest_time", ""),
                    "latest_time": saved_search.content.get("dispatch.latest_time", ""),
                    "updated": saved_search.content.get("updated", ""),
                    "permissions": {
                        "read": saved_search.content.get("eai:acl", {})
                        .get("perms", {})
                        .get("read", []),
                        "write": saved_search.content.get("eai:acl", {})
                        .get("perms", {})
                        .get("write", []),
                    },
                }

                # Apply filters
                if owner and search_info["owner"] != owner:
                    continue
                if app and search_info["app"] != app:
                    continue
                if sharing and search_info["sharing"] != sharing:
                    continue
                if not include_disabled and search_info["disabled"]:
                    continue

                saved_searches_list.append(search_info)

            # Sort by name for consistent output
            saved_searches_list.sort(key=lambda x: x["name"])

            return self.format_success_response(
                {
                    "saved_searches": saved_searches_list,
                    "total_count": total_count,
                    "filtered_count": len(saved_searches_list),
                    "filters_applied": {
                        "owner": owner,
                        "app": app,
                        "sharing": sharing,
                        "include_disabled": include_disabled,
                    },
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to list saved searches: {str(e)}")
            await ctx.error(f"Failed to list saved searches: {str(e)}")
            return self.format_error_response(str(e), saved_searches=[], total_count=0)

    def _convert_splunk_boolean(self, value, default=False):
        """Convert Splunk boolean values to Python booleans"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        if isinstance(value, int | float):
            return bool(value)
        return default


class ExecuteSavedSearch(BaseTool):
    """
    Execute a saved search by name with optional parameter overrides.
    Supports both oneshot and job execution modes based on search complexity.
    """

    METADATA = ToolMetadata(
        name="execute_saved_search",
        description=(
            "Run a saved search by name with optional time overrides and mode selection. Use this to "
            "execute existing reports/automations quickly. Choose 'oneshot' for immediate results or "
            "'job' for progress tracking and large result sets.\\n\\n"
            "Outputs: results list (capped by max_results), mode used, timing, and job id (if job).\\n"
            "Security: execution and results are constrained by the authenticated user's permissions."
        ),
        category="search",
        tags=["saved_searches", "execute", "search"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        name: str,
        earliest_time: str | None = None,
        latest_time: str | None = None,
        mode: Literal["oneshot", "job"] = "oneshot",
        max_results: int = 100,
        app: str | None = None,
        owner: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute a saved search by name.

        Args:
            name: Name of the saved search to execute
            earliest_time: Override earliest time for search (optional)
            latest_time: Override latest time for search (optional)
            mode: Execution mode - 'oneshot' for immediate results or 'job' for progress tracking
            max_results: Maximum number of results to return (default: 100)
            app: Application context for the saved search (optional)
            owner: Owner context for the saved search (optional)

        Returns:
            Dict containing:
                - saved_search_name: Name of the executed saved search
                - results: List of search results
                - results_count: Number of results returned
                - execution_mode: Mode used for execution
                - job_id: Search job ID (if job mode)
                - duration: Execution time in seconds

        Example:
            execute_saved_search(
                name="Security Alerts",
                earliest_time="-1h",
                mode="job"
            )
        """
        log_tool_execution(
            "execute_saved_search", name=name, mode=mode, earliest_time=earliest_time
        )

        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            await ctx.error(f"Execute saved search failed: {error_msg}")
            return self.format_error_response(error_msg, saved_search_name=name)

        try:
            # Find the saved search
            await ctx.info(f"Looking for saved search: {name}")

            # Build search criteria
            search_kwargs = {}
            if app:
                search_kwargs["app"] = app
            if owner:
                search_kwargs["owner"] = owner

            saved_search = None
            try:
                if search_kwargs:
                    # Search with specific criteria
                    for ss in service.saved_searches(**search_kwargs):
                        if ss.name == name:
                            saved_search = ss
                            break
                else:
                    # Direct access
                    saved_search = service.saved_searches[name]
            except KeyError:
                # Try to find it by iterating through all saved searches
                for ss in service.saved_searches:
                    if ss.name == name:
                        if app and ss.content.get("eai:acl", {}).get("app") != app:
                            continue
                        if owner and ss.content.get("eai:acl", {}).get("owner") != owner:
                            continue
                        saved_search = ss
                        break

            if not saved_search:
                error_msg = f"Saved search '{name}' not found"
                if app or owner:
                    error_msg += f" (app: {app}, owner: {owner})"
                await ctx.error(error_msg)
                return self.format_error_response(error_msg, saved_search_name=name)

            # Check if saved search is disabled
            if self._convert_splunk_boolean(saved_search.content.get("disabled"), False):
                error_msg = f"Saved search '{name}' is disabled"
                await ctx.error(error_msg)
                return self.format_error_response(error_msg, saved_search_name=name)

            # Prepare execution parameters
            dispatch_kwargs = {}

            # Use override times if provided, otherwise use saved search defaults
            if earliest_time is not None:
                dispatch_kwargs["earliest_time"] = earliest_time
            elif saved_search.content.get("dispatch.earliest_time"):
                dispatch_kwargs["earliest_time"] = saved_search.content.get(
                    "dispatch.earliest_time"
                )

            if latest_time is not None:
                dispatch_kwargs["latest_time"] = latest_time
            elif saved_search.content.get("dispatch.latest_time"):
                dispatch_kwargs["latest_time"] = saved_search.content.get("dispatch.latest_time")

            await ctx.info(f"Executing saved search '{name}' in {mode} mode")
            start_time = time.time()

            if mode == "oneshot":
                return await self._execute_oneshot(
                    ctx, saved_search, dispatch_kwargs, max_results, start_time
                )
            else:
                return await self._execute_job(
                    ctx, saved_search, dispatch_kwargs, max_results, start_time
                )

        except Exception as e:
            self.logger.error(f"Failed to execute saved search '{name}': {str(e)}")
            await ctx.error(f"Failed to execute saved search '{name}': {str(e)}")
            return self.format_error_response(str(e), saved_search_name=name)

    async def _execute_oneshot(
        self, ctx: Context, saved_search, dispatch_kwargs: dict, max_results: int, start_time: float
    ) -> dict[str, Any]:
        """Execute saved search in oneshot mode"""
        dispatch_kwargs["count"] = max_results
        dispatch_kwargs["output_mode"] = "json"

        job = saved_search.dispatch(**dispatch_kwargs)
        results = []
        result_count = 0

        reader = JSONResultsReader(job)
        for result in reader:
            if isinstance(result, dict):
                results.append(result)
                result_count += 1
                if result_count >= max_results:
                    break

        duration = time.time() - start_time

        return self.format_success_response(
            {
                "saved_search_name": saved_search.name,
                "results": results,
                "results_count": result_count,
                "execution_mode": "oneshot",
                "duration": round(duration, 3),
                "search_query": saved_search.content.get("search", ""),
                "dispatch_parameters": dispatch_kwargs,
            }
        )

    async def _execute_job(
        self, ctx: Context, saved_search, dispatch_kwargs: dict, max_results: int, start_time: float
    ) -> dict[str, Any]:
        """Execute saved search in job mode with progress tracking"""
        job = saved_search.dispatch(**dispatch_kwargs)

        # Wait for job completion with progress reporting
        while not job.is_done():
            await ctx.report_progress(
                progress=int(float(job.content.get("dispatchState", {}).get("percentComplete", 0))),
                total=100,
            )
            time.sleep(0.5)
            job.refresh()

        # Get job statistics
        stats = job.content

        # Get results
        results = []
        result_count = 0

        kwargs_paginate = {"count": max_results, "output_mode": "json"}
        reader = JSONResultsReader(job.results(**kwargs_paginate))
        for result in reader:
            if isinstance(result, dict):
                results.append(result)
                result_count += 1
                if result_count >= max_results:
                    break

        duration = time.time() - start_time

        return self.format_success_response(
            {
                "saved_search_name": saved_search.name,
                "job_id": job.sid,
                "results": results,
                "results_count": result_count,
                "execution_mode": "job",
                "scan_count": int(float(stats.get("scanCount", 0))),
                "event_count": int(float(stats.get("eventCount", 0))),
                "duration": round(duration, 3),
                "search_query": saved_search.content.get("search", ""),
                "dispatch_parameters": dispatch_kwargs,
                "status": {
                    "is_finalized": stats.get("isFinalized", "0") == "1",
                    "is_failed": stats.get("isFailed", "0") == "1",
                    "progress": 100,
                },
            }
        )

    def _convert_splunk_boolean(self, value, default=False):
        """Convert Splunk boolean values to Python booleans"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        if isinstance(value, int | float):
            return bool(value)
        return default


class CreateSavedSearch(BaseTool):
    """
    Create a new saved search with specified configuration.
    Supports scheduling, alerting, and sharing configuration.
    """

    METADATA = ToolMetadata(
        name="create_saved_search",
        description=(
            "Create a saved search (report/automation) with optional scheduling and sharing. Use this "
            "to persist useful SPL queries and optionally schedule them via cron.\\n\\n"
            "Outputs: creation status and the applied configuration.\\n"
            "Security: visibility and execution are constrained by permissions and chosen sharing level."
        ),
        category="search",
        tags=["saved_searches", "create", "management"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        name: str,
        search: str,
        description: str = "",
        earliest_time: str = "",
        latest_time: str = "",
        app: str | None = None,
        sharing: Literal["user", "app", "global"] = "user",
        is_scheduled: bool = False,
        cron_schedule: str = "",
        is_visible: bool = True,
    ) -> dict[str, Any]:
        """
        Create a new saved search.

        Args:
            name: Name for the new saved search (must be unique)
            search: The SPL search query to save
            description: Description of the saved search
            earliest_time: Default earliest time for the search
            latest_time: Default latest time for the search
            app: Application context (uses current app if not specified)
            sharing: Sharing level for the saved search
            is_scheduled: Whether to enable scheduling
            cron_schedule: Cron expression for scheduling (required if is_scheduled=True)
            is_visible: Whether the saved search is visible in the UI

        Returns:
            Dict containing:
                - name: Name of the created saved search
                - created: Whether creation was successful
                - configuration: Applied configuration

        Example:
            create_saved_search(
                name="Daily Error Count",
                search="index=main error | stats count",
                description="Count of daily errors",
                earliest_time="-24h@h",
                latest_time="@h",
                is_scheduled=True,
                cron_schedule="0 8 * * *"
            )
        """
        log_tool_execution("create_saved_search", name=name, search=search[:50] + "...")

        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            await ctx.error(f"Create saved search failed: {error_msg}")
            return self.format_error_response(error_msg, name=name, created=False)

        try:
            # Validate inputs
            if not name.strip():
                return self.format_error_response(
                    "Saved search name cannot be empty", name=name, created=False
                )

            if not search.strip():
                return self.format_error_response(
                    "Search query cannot be empty", name=name, created=False
                )

            if is_scheduled and not cron_schedule.strip():
                return self.format_error_response(
                    "Cron schedule is required when is_scheduled=True", name=name, created=False
                )

            # Check if saved search already exists
            try:
                existing = service.saved_searches[name]
                if existing:
                    return self.format_error_response(
                        f"Saved search '{name}' already exists", name=name, created=False
                    )
            except KeyError:
                # This is expected - saved search doesn't exist yet
                pass

            # Sanitize search query
            search = sanitize_search_query(search)

            # Build configuration
            config = {
                "search": search,
                "description": description,
                "is_visible": "1" if is_visible else "0",
            }

            # Add time range if specified
            if earliest_time:
                config["dispatch.earliest_time"] = earliest_time
            if latest_time:
                config["dispatch.latest_time"] = latest_time

            # Add scheduling if enabled
            if is_scheduled:
                config["is_scheduled"] = "1"
                config["cron_schedule"] = cron_schedule
            else:
                config["is_scheduled"] = "0"

            await ctx.info(f"Creating saved search '{name}'")

            # Create the saved search
            if app:
                service.saved_searches.create(name, **config, app=app, sharing=sharing)
            else:
                service.saved_searches.create(name, **config, sharing=sharing)

            return self.format_success_response(
                {
                    "name": name,
                    "created": True,
                    "configuration": {
                        "search": search,
                        "description": description,
                        "earliest_time": earliest_time,
                        "latest_time": latest_time,
                        "app": app or "default",
                        "sharing": sharing,
                        "is_scheduled": is_scheduled,
                        "cron_schedule": cron_schedule if is_scheduled else "",
                        "is_visible": is_visible,
                    },
                    "created_at": time.time(),
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to create saved search '{name}': {str(e)}")
            await ctx.error(f"Failed to create saved search '{name}': {str(e)}")
            return self.format_error_response(str(e), name=name, created=False)


class UpdateSavedSearch(BaseTool):
    """
    Update an existing saved search's configuration.
    Allows modification of search query, scheduling, and other properties.
    """

    METADATA = ToolMetadata(
        name="update_saved_search",
        description=(
            "Update an existing saved search's configuration including query, scheduling, "
            "and other properties. Allows selective modification of saved search parameters "
            "while preserving unchanged settings. Supports updating search logic, time ranges, "
            "scheduling configuration, and visibility settings for flexible search management.\\n\\n"
            "Args:\\n"
            "    name (str): Name of the saved search to update (required)\\n"
            "    search (str, optional): New SPL search query\\n"
            "    description (str, optional): New description text\\n"
            "    earliest_time (str, optional): New default earliest time "
            "(e.g., '-24h@h', '-7d', '2024-01-01T00:00:00')\\n"
            "    latest_time (str, optional): New default latest time "
            "(e.g., 'now', '@d', '2024-01-02T00:00:00')\\n"
            "    is_scheduled (bool, optional): Enable or disable scheduled execution\\n"
            "    cron_schedule (str, optional): New cron expression for scheduling\\n"
            "    is_visible (bool, optional): Show or hide in Splunk UI\\n"
            "    app (str, optional): Application context for saved search lookup\\n"
            "    owner (str, optional): Owner context for saved search lookup\\n\\n"
            "Response Format:\\n"
            "Returns dictionary with 'status', 'name', 'updated', 'changes_made', and 'updated_at' fields."
        ),
        category="search",
        tags=["saved_searches", "update", "management"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        name: str,
        search: str | None = None,
        description: str | None = None,
        earliest_time: str | None = None,
        latest_time: str | None = None,
        is_scheduled: bool | None = None,
        cron_schedule: str | None = None,
        is_visible: bool | None = None,
        app: str | None = None,
        owner: str | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing saved search.

        Args:
            name: Name of the saved search to update
            search: New search query (optional)
            description: New description (optional)
            earliest_time: New earliest time (optional)
            latest_time: New latest time (optional)
            is_scheduled: Enable/disable scheduling (optional)
            cron_schedule: New cron schedule (optional)
            is_visible: Show/hide in UI (optional)
            app: Application context (optional)
            owner: Owner context (optional)

        Returns:
            Dict containing:
                - name: Name of the updated saved search
                - updated: Whether update was successful
                - changes_made: List of properties that were changed

        Example:
            update_saved_search(
                name="Daily Error Count",
                description="Updated: Count of daily errors with severity",
                search="index=main error | stats count by severity",
                is_scheduled=False
            )
        """
        log_tool_execution("update_saved_search", name=name)

        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            await ctx.error(f"Update saved search failed: {error_msg}")
            return self.format_error_response(error_msg, name=name, updated=False)

        try:
            # Find the saved search
            await ctx.info(f"Looking for saved search to update: {name}")

            saved_search = None
            try:
                # Try direct access first
                saved_search = service.saved_searches[name]

                # Check app/owner constraints if specified
                if app and saved_search.content.get("eai:acl", {}).get("app") != app:
                    saved_search = None
                if owner and saved_search.content.get("eai:acl", {}).get("owner") != owner:
                    saved_search = None

            except KeyError:
                # Search by iterating if direct access fails
                for ss in service.saved_searches:
                    if ss.name == name:
                        if app and ss.content.get("eai:acl", {}).get("app") != app:
                            continue
                        if owner and ss.content.get("eai:acl", {}).get("owner") != owner:
                            continue
                        saved_search = ss
                        break

            if not saved_search:
                error_msg = f"Saved search '{name}' not found"
                if app or owner:
                    error_msg += f" (app: {app}, owner: {owner})"
                await ctx.error(error_msg)
                return self.format_error_response(error_msg, name=name, updated=False)

            # Build update configuration
            update_config = {}
            changes_made = []

            if search is not None:
                search = sanitize_search_query(search)
                update_config["search"] = search
                changes_made.append("search")

            if description is not None:
                update_config["description"] = description
                changes_made.append("description")

            if earliest_time is not None:
                update_config["dispatch.earliest_time"] = earliest_time
                changes_made.append("earliest_time")

            if latest_time is not None:
                update_config["dispatch.latest_time"] = latest_time
                changes_made.append("latest_time")

            if is_scheduled is not None:
                update_config["is_scheduled"] = "1" if is_scheduled else "0"
                changes_made.append("is_scheduled")

            if cron_schedule is not None:
                if is_scheduled is not False:  # Only update if not explicitly disabled
                    update_config["cron_schedule"] = cron_schedule
                    changes_made.append("cron_schedule")

            if is_visible is not None:
                update_config["is_visible"] = "1" if is_visible else "0"
                changes_made.append("is_visible")

            if not update_config:
                return self.format_error_response(
                    "No update parameters provided", name=name, updated=False
                )

            # Validate scheduling configuration
            if "is_scheduled" in update_config and update_config["is_scheduled"] == "1":
                current_cron = saved_search.content.get("cron_schedule", "")
                new_cron = update_config.get("cron_schedule", current_cron)
                if not new_cron.strip():
                    return self.format_error_response(
                        "Cron schedule is required when enabling scheduling",
                        name=name,
                        updated=False,
                    )

            await ctx.info(f"Updating saved search '{name}' with changes: {changes_made}")

            # Apply updates
            saved_search.update(**update_config)

            return self.format_success_response(
                {
                    "name": name,
                    "updated": True,
                    "changes_made": changes_made,
                    "updated_at": time.time(),
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to update saved search '{name}': {str(e)}")
            await ctx.error(f"Failed to update saved search '{name}': {str(e)}")
            return self.format_error_response(str(e), name=name, updated=False)


class DeleteSavedSearch(BaseTool):
    """
    Delete a saved search from Splunk.
    Requires confirmation and provides safety checks.
    """

    METADATA = ToolMetadata(
        name="delete_saved_search",
        description="Delete a saved search with confirmation and safety checks",
        category="search",
        tags=["saved_searches", "delete", "management"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        name: str,
        confirm: bool = False,
        app: str | None = None,
        owner: str | None = None,
    ) -> dict[str, Any]:
        """
        Delete a saved search.

        Args:
            name: Name of the saved search to delete
            confirm: Confirmation that deletion is intended (must be True)
            app: Application context (optional)
            owner: Owner context (optional)

        Returns:
            Dict containing:
                - name: Name of the saved search
                - deleted: Whether deletion was successful
                - was_scheduled: Whether the deleted search was scheduled

        Example:
            delete_saved_search(
                name="Old Test Search",
                confirm=True
            )
        """
        log_tool_execution("delete_saved_search", name=name, confirm=confirm)

        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            await ctx.error(f"Delete saved search failed: {error_msg}")
            return self.format_error_response(error_msg, name=name, deleted=False)

        try:
            # Safety check - require explicit confirmation
            if not confirm:
                return self.format_error_response(
                    "Deletion requires explicit confirmation. Set confirm=True to proceed.",
                    name=name,
                    deleted=False,
                )

            # Find the saved search
            await ctx.info(f"Looking for saved search to delete: {name}")

            saved_search = None
            try:
                # Try direct access first
                saved_search = service.saved_searches[name]

                # Check app/owner constraints if specified
                if app and saved_search.content.get("eai:acl", {}).get("app") != app:
                    saved_search = None
                if owner and saved_search.content.get("eai:acl", {}).get("owner") != owner:
                    saved_search = None

            except KeyError:
                # Search by iterating if direct access fails
                for ss in service.saved_searches:
                    if ss.name == name:
                        if app and ss.content.get("eai:acl", {}).get("app") != app:
                            continue
                        if owner and ss.content.get("eai:acl", {}).get("owner") != owner:
                            continue
                        saved_search = ss
                        break

            if not saved_search:
                error_msg = f"Saved search '{name}' not found"
                if app or owner:
                    error_msg += f" (app: {app}, owner: {owner})"
                await ctx.error(error_msg)
                return self.format_error_response(error_msg, name=name, deleted=False)

            # Get information before deletion
            was_scheduled = self._convert_splunk_boolean(
                saved_search.content.get("is_scheduled"), False
            )
            search_app = saved_search.content.get("eai:acl", {}).get("app", "")
            search_owner = saved_search.content.get("eai:acl", {}).get("owner", "")

            await ctx.info(
                f"Deleting saved search '{name}' (app: {search_app}, owner: {search_owner})"
            )

            # Delete the saved search
            saved_search.delete()

            return self.format_success_response(
                {
                    "name": name,
                    "deleted": True,
                    "was_scheduled": was_scheduled,
                    "app": search_app,
                    "owner": search_owner,
                    "deleted_at": time.time(),
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to delete saved search '{name}': {str(e)}")
            await ctx.error(f"Failed to delete saved search '{name}': {str(e)}")
            return self.format_error_response(str(e), name=name, deleted=False)

    def _convert_splunk_boolean(self, value, default=False):
        """Convert Splunk boolean values to Python booleans"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        if isinstance(value, int | float):
            return bool(value)
        return default


class GetSavedSearchDetails(BaseTool):
    """
    Get detailed information about a specific saved search.
    Returns comprehensive metadata including scheduling, alerting, and permissions.
    """

    METADATA = ToolMetadata(
        name="get_saved_search_details",
        description=(
            "Get comprehensive details about a specific saved search including configuration, "
            "metadata, scheduling, permissions, and alert actions. Returns detailed information "
            "about saved search properties, execution settings, and access control configuration. "
            "Essential for troubleshooting, auditing, and understanding saved search configurations.\\n\\n"
            "Args:\\n"
            "    name (str): Name of the saved search to inspect (required)\\n"
            "    app (str, optional): Application context for saved search lookup\\n"
            "    owner (str, optional): Owner context for saved search lookup\\n\\n"
            "Response Format:\\n"
            "Returns dictionary with 'status', 'name', 'details', and 'retrieved_at' fields. "
            "The 'details' field contains comprehensive nested information including:\\n"
            "- basic_info: Name, description, search query, visibility\\n"
            "- scheduling: Schedule configuration and timing\\n"
            "- dispatch: Time range and execution settings\\n"
            "- permissions: Access control and sharing settings\\n"
            "- actions: Email, script, and other alert actions\\n"
            "- alert: Alert conditions and suppression settings\\n"
            "- metadata: Creation timestamps and authorship"
        ),
        category="search",
        tags=["saved_searches", "details", "metadata"],
        requires_connection=True,
    )

    async def execute(
        self, ctx: Context, name: str, app: str | None = None, owner: str | None = None
    ) -> dict[str, Any]:
        """
        Get detailed information about a saved search.

        Args:
            name: Name of the saved search
            app: Application context (optional)
            owner: Owner context (optional)

        Returns:
            Dict containing comprehensive saved search details:
                - basic_info: Name, description, search query
                - scheduling: Schedule configuration and status
                - dispatch: Time range and execution settings
                - permissions: Access control and sharing
                - actions: Alert actions configuration
                - metadata: Creation and modification timestamps

        Example:
            get_saved_search_details(name="Security Alerts")
        """
        log_tool_execution("get_saved_search_details", name=name)

        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            await ctx.error(f"Get saved search details failed: {error_msg}")
            return self.format_error_response(error_msg, name=name)

        try:
            # Find the saved search
            await ctx.info(f"Retrieving details for saved search: {name}")

            saved_search = None
            try:
                # Try direct access first
                saved_search = service.saved_searches[name]

                # Check app/owner constraints if specified
                if app and saved_search.content.get("eai:acl", {}).get("app") != app:
                    saved_search = None
                if owner and saved_search.content.get("eai:acl", {}).get("owner") != owner:
                    saved_search = None

            except KeyError:
                # Search by iterating if direct access fails
                for ss in service.saved_searches:
                    if ss.name == name:
                        if app and ss.content.get("eai:acl", {}).get("app") != app:
                            continue
                        if owner and ss.content.get("eai:acl", {}).get("owner") != owner:
                            continue
                        saved_search = ss
                        break

            if not saved_search:
                error_msg = f"Saved search '{name}' not found"
                if app or owner:
                    error_msg += f" (app: {app}, owner: {owner})"
                await ctx.error(error_msg)
                return self.format_error_response(error_msg, name=name)

            content = saved_search.content
            acl = content.get("eai:acl", {})

            # Build comprehensive details
            details = {
                "basic_info": {
                    "name": saved_search.name,
                    "search": content.get("search", ""),
                    "description": content.get("description", ""),
                    "qualified_search": content.get("qualifiedSearch", ""),
                    "disabled": self._convert_splunk_boolean(content.get("disabled"), False),
                    "is_visible": self._convert_splunk_boolean(content.get("is_visible"), True),
                },
                "scheduling": {
                    "is_scheduled": self._convert_splunk_boolean(
                        content.get("is_scheduled"), False
                    ),
                    "cron_schedule": content.get("cron_schedule", ""),
                    "next_scheduled_time": content.get("next_scheduled_time", ""),
                    "schedule_priority": content.get("schedule_priority", "default"),
                    "schedule_window": content.get("schedule_window", ""),
                },
                "dispatch": {
                    "earliest_time": content.get("dispatch.earliest_time", ""),
                    "latest_time": content.get("dispatch.latest_time", ""),
                    "index_earliest": content.get("dispatch.index_earliest", ""),
                    "index_latest": content.get("dispatch.index_latest", ""),
                    "max_count": content.get("dispatch.max_count", ""),
                    "max_time": content.get("dispatch.max_time", ""),
                    "spawn_process": self._convert_splunk_boolean(
                        content.get("dispatch.spawn_process"), True
                    ),
                    "time_format": content.get("dispatch.time_format", ""),
                },
                "permissions": {
                    "owner": acl.get("owner", ""),
                    "app": acl.get("app", ""),
                    "sharing": acl.get("sharing", ""),
                    "modifiable": acl.get("modifiable", ""),
                    "can_write": acl.get("can_write", ""),
                    "can_share_app": acl.get("can_share_app", ""),
                    "can_share_global": acl.get("can_share_global", ""),
                    "read_permissions": acl.get("perms", {}).get("read", []),
                    "write_permissions": acl.get("perms", {}).get("write", []),
                },
                "actions": {
                    "email": {
                        "enabled": self._convert_splunk_boolean(content.get("action.email"), False),
                        "to": content.get("action.email.to", ""),
                        "subject": content.get("action.email.subject", ""),
                        "message": content.get("action.email.message", ""),
                    },
                    "populate_lookup": {
                        "enabled": self._convert_splunk_boolean(
                            content.get("action.populate_lookup"), False
                        ),
                        "dest": content.get("action.populate_lookup.dest", ""),
                    },
                    "rss": {
                        "enabled": self._convert_splunk_boolean(content.get("action.rss"), False)
                    },
                    "script": {
                        "enabled": self._convert_splunk_boolean(
                            content.get("action.script"), False
                        ),
                        "filename": content.get("action.script.filename", ""),
                    },
                    "summary_index": {
                        "enabled": self._convert_splunk_boolean(
                            content.get("action.summary_index"), False
                        ),
                        "name": content.get("action.summary_index._name", ""),
                    },
                },
                "alert": {
                    "type": content.get("alert_type", ""),
                    "condition": content.get("alert.condition", ""),
                    "comparator": content.get("alert.comparator", ""),
                    "threshold": content.get("alert.threshold", ""),
                    "track": content.get("alert.track", ""),
                    "digest_mode": self._convert_splunk_boolean(
                        content.get("alert.digest_mode"), False
                    ),
                    "suppress": {
                        "enabled": self._convert_splunk_boolean(
                            content.get("alert.suppress"), False
                        ),
                        "period": content.get("alert.suppress.period", ""),
                        "fields": content.get("alert.suppress.fields", ""),
                    },
                },
                "metadata": {
                    "created": content.get("eai:acl", {}).get("created", ""),
                    "updated": content.get("updated", ""),
                    "author": content.get("eai:acl", {}).get("author", ""),
                    "splunk_server": content.get("splunk_server", ""),
                    "version": content.get("eai:acl", {}).get("version", ""),
                },
            }

            return self.format_success_response(
                {"name": name, "details": details, "retrieved_at": time.time()}
            )

        except Exception as e:
            self.logger.error(f"Failed to get saved search details for '{name}': {str(e)}")
            await ctx.error(f"Failed to get saved search details for '{name}': {str(e)}")
            return self.format_error_response(str(e), name=name)

    def _convert_splunk_boolean(self, value, default=False):
        """Convert Splunk boolean values to Python booleans"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        if isinstance(value, int | float):
            return bool(value)
        return default
