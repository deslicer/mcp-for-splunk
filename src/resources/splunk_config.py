"""
Splunk Configuration Resource Implementation.

Provides access to Splunk configuration files through the MCP resource system.
"""

import json
import logging
from typing import Any

from fastmcp.server.context import Context

from ..core.base import BaseResource, ResourceMetadata
from ..core.client_identity import get_client_manager
from ..core.enhanced_config_extractor import EnhancedConfigExtractor
from ..core.utils import filter_customer_indexes

logger = logging.getLogger(__name__)


class SplunkConfigResource(BaseResource):
    """
    Template resource for accessing Splunk configuration files.

    Provides secure access to any configuration file (indexes.conf, props.conf, etc.)
    with proper client isolation. The specific config file is determined from the URI.
    """

    # Metadata for resource registry (template pattern)
    METADATA = ResourceMetadata(
        uri="splunk://config/{config_file}",
        name="Splunk Configuration Files",
        description="Access to Splunk configuration files (indexes.conf, props.conf, transforms.conf, etc.) with client isolation",
        mime_type="text/plain",
        category="configuration",
        tags=["config", "splunk", "client-scoped", "template"],
    )

    def __init__(self, uri: str, name: str, description: str, mime_type: str = "text/plain"):
        super().__init__(uri, name, description, mime_type)
        self.client_manager = get_client_manager()
        self.config_extractor = EnhancedConfigExtractor()

    async def get_content(self, ctx: Context, uri: str = None) -> str:
        """
        Get configuration file content with client isolation.

        Args:
            ctx: MCP context containing client information
            uri: Optional URI override (used for template pattern)

        Returns:
            Configuration file content as string

        Raises:
            PermissionError: If access is denied
            ValueError: If configuration not found
        """
        try:
            # Use provided URI or fall back to instance URI
            request_uri = uri or self.uri

            # Extract client configuration (now includes fallback to server default)
            client_config = await self.config_extractor.extract_client_config(ctx)
            if not client_config:
                # This should rarely happen now due to fallback, but handle gracefully
                return self._create_error_response("No Splunk configuration available", request_uri)

            # Get client identity and connection
            identity, service = await self.client_manager.get_client_connection(ctx, client_config)

            # Extract config file from URI
            config_file = self._extract_config_file_from_uri(request_uri)
            if not config_file:
                return self._create_error_response(
                    f"Could not determine config file from URI: {request_uri}", request_uri
                )

            # Validate config file name for security
            if not self._is_valid_config_file(config_file):
                return self._create_error_response(
                    f"Invalid or unsupported config file: {config_file}", request_uri
                )

            # Get configuration content from Splunk
            config_content = await self._get_config_content(
                service, config_file, identity, request_uri
            )

            self.logger.info(f"Retrieved config {config_file} for client {identity.client_id}")
            return config_content

        except ConnectionError as e:
            self.logger.warning(f"Splunk connection error for {request_uri}: {e}")
            return self._create_error_response(f"Splunk connection failed: {str(e)}", request_uri)
        except Exception as e:
            self.logger.error(f"Failed to get config content for {request_uri}: {e}")
            return self._create_error_response(
                f"Error retrieving configuration: {str(e)}", request_uri
            )

    def _is_valid_config_file(self, config_file: str) -> bool:
        """
        Validate config file name for security.

        Args:
            config_file: Configuration file name to validate

        Returns:
            True if valid, False otherwise
        """
        # List of allowed config files
        allowed_configs = {
            "indexes.conf",
            "props.conf",
            "transforms.conf",
            "server.conf",
            "web.conf",
            "inputs.conf",
            "outputs.conf",
            "savedsearches.conf",
            "macros.conf",
            "tags.conf",
            "eventtypes.conf",
            "alert_actions.conf",
        }

        # Basic validation: must end with .conf and be in allowed list
        if not config_file.endswith(".conf"):
            return False

        # Check against allowed list
        if config_file not in allowed_configs:
            self.logger.warning(f"Requested config file '{config_file}' is not in allowed list")
            return False

        # Additional security: no path traversal
        if ".." in config_file or "/" in config_file or "\\" in config_file:
            return False

        return True

    def _extract_config_file_from_uri(self, uri: str) -> str | None:
        """Extract config file name from URI"""
        try:
            # Handle patterns like:
            # splunk://config/indexes.conf
            # splunk://client/{client_id}/config/indexes.conf
            parts = uri.split("/")

            if "config" in parts:
                config_index = parts.index("config")
                if config_index + 1 < len(parts):
                    return parts[config_index + 1]

            return None
        except Exception:
            return None

    async def _get_config_content(
        self, service, config_file: str, identity, uri: str = None
    ) -> str:
        """Get configuration content from Splunk service"""
        try:
            # Get configuration using Splunk REST API
            configs = service.confs[config_file.replace(".conf", "")]

            config_data = {}
            for stanza in configs:
                stanza_data = {}
                for key in stanza.content:
                    stanza_data[key] = stanza.content[key]
                config_data[stanza.name] = stanza_data

            # Format as readable configuration text
            content_lines = [f"# Configuration: {config_file}"]
            content_lines.append(f"# Client: {identity.client_id}")
            content_lines.append(f"# Host: {identity.splunk_host}")
            content_lines.append("")

            for stanza_name, stanza_data in config_data.items():
                content_lines.append(f"[{stanza_name}]")
                for key, value in stanza_data.items():
                    content_lines.append(f"{key} = {value}")
                content_lines.append("")

            return "\n".join(content_lines)

        except Exception as e:
            # Fallback to JSON format if text parsing fails
            self.logger.warning(f"Could not format as config text, using JSON: {e}")
            return json.dumps(
                {
                    "config_file": config_file,
                    "client_id": identity.client_id,
                    "error": str(e),
                    "available_configs": list(service.confs.keys())
                    if hasattr(service, "confs")
                    else [],
                },
                indent=2,
            )

    def _create_error_response(self, error_message: str, uri: str = None) -> str:
        """Create a helpful error response for configuration issues"""
        request_uri = uri or self.uri
        return f"""# Configuration Error
# URI: {request_uri}
# Error: {error_message}
#
# To access Splunk configurations, provide credentials via HTTP headers:
#   X-Splunk-Host: your-splunk-host
#   X-Splunk-Username: your-username
#   X-Splunk-Password: your-password
#   X-Splunk-Port: 8089 (optional)
#   X-Splunk-Scheme: https (optional)
#   X-Splunk-Verify-SSL: false (optional)
#
# Or ensure server environment variables are set:
#   SPLUNK_HOST, SPLUNK_USERNAME, SPLUNK_PASSWORD
"""


class SplunkHealthResource(BaseResource):
    """Resource for Splunk health status information"""

    METADATA = ResourceMetadata(
        uri="splunk://health/status",
        name="Splunk Health Status",
        description="Real-time health monitoring for Splunk components (includes filtered customer indexes)",
        mime_type="application/json",
        category="monitoring",
        tags=["health", "monitoring", "splunk"],
    )

    def __init__(self, uri: str, name: str, description: str, mime_type: str = "application/json"):
        super().__init__(uri, name, description, mime_type)
        self.client_manager = get_client_manager()
        self.config_extractor = EnhancedConfigExtractor()

    async def get_content(self, ctx: Context) -> str:
        """Get health status information"""
        try:
            # Extract client configuration (now includes fallback to server default)
            client_config = await self.config_extractor.extract_client_config(ctx)
            if not client_config:
                # Fallback to error response with helpful info
                return self._create_health_error_response("No Splunk configuration available")

            # Get client identity and connection
            identity, service = await self.client_manager.get_client_connection(ctx, client_config)

            # Get health information
            health_data = await self._get_health_data(service, identity)

            return json.dumps(health_data, indent=2)

        except ConnectionError as e:
            self.logger.warning(f"Splunk connection error for health check: {e}")
            return self._create_health_error_response(f"Splunk connection failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to get health data: {e}")
            return self._create_health_error_response(f"Health check error: {str(e)}")

    def _create_health_error_response(self, error_message: str) -> str:
        """Create a helpful JSON error response for health check issues"""
        error_response = {
            "status": "error",
            "error": error_message,
            "timestamp": "N/A",
            "uri": self.uri,
            "help": {
                "message": "To access Splunk health information, provide credentials via HTTP headers or environment variables",
                "http_headers": {
                    "X-Splunk-Host": "your-splunk-host",
                    "X-Splunk-Username": "your-username",
                    "X-Splunk-Password": "your-password",
                    "X-Splunk-Port": "8089",
                    "X-Splunk-Scheme": "https",
                    "X-Splunk-Verify-SSL": "false",
                },
                "environment_variables": ["SPLUNK_HOST", "SPLUNK_USERNAME", "SPLUNK_PASSWORD"],
            },
        }
        return json.dumps(error_response, indent=2)

    async def _get_health_data(self, service, identity) -> dict[str, Any]:
        """Get comprehensive health data from Splunk"""
        try:
            info = service.info()
            logger.debug(f"Health data: {info}")

            health_data = {
                "client_id": identity.client_id,
                "splunk_host": identity.splunk_host,
                "timestamp": info.get("_time", "unknown"),
                "server_info": {
                    "version": info.get("version"),
                    "build": info.get("build"),
                    "server_name": info.get("serverName"),
                    "license_state": info.get("licenseState"),
                    "startup_time": info.get("startup_time"),
                    "server_roles": info.get("server_roles"),
                    "cpu_count": info.get("numberOfCores"),
                    "memory_mb": info.get("physicalMemoryMB"),
                    "os_name": info.get("os_name"),
                    "os_version": info.get("os_version"),
                    "os_build": info.get("os_build"),
                    "os_name_extended": info.get("os_name_extended"),
                    "os_version_extended": info.get("os_version_extended"),
                },
                "kvstore_status": info.get("kvStoreStatus"),
                "status": "healthy"
                if info.get("licenseState") != "EXPIRED" and info.get("health_info") == "green"
                else "warning",
            }

            # Add index information if available (excluding internal indexes)
            # try:
            #     indexes = service.indexes
            #     # Filter out internal indexes for better performance and relevance
            #     customer_indexes = filter_customer_indexes(indexes)

            #     health_data["indexes"] = {
            #         "count": len(customer_indexes),
            #         "total_count_including_internal": len(indexes),
            #         "total_size": sum(int(idx.get("totalEventCount", 0)) for idx in customer_indexes),
            #         "available": [idx.name for idx in customer_indexes[:5]]  # First 5 customer indexes
            #     }
            # except Exception as e:
            #     health_data["indexes"] = {"error": str(e)}

            return health_data

        except Exception as e:
            return {"client_id": identity.client_id, "error": str(e), "status": "error"}


class SplunkAppsResource(BaseResource):
    """
    Resource for Splunk installed applications with comprehensive analysis.

    Provides installed Splunk apps as contextual information for LLMs.
    Apps help LLMs understand what functionality, data models, dashboards,
    and search capabilities are available in the client's Splunk environment.
    """

    METADATA = ResourceMetadata(
        uri="splunk://apps/installed",
        name="Splunk Apps Installed",
        description="Information about installed Splunk applications and add-ons with capability analysis",
        mime_type="application/json",
        category="applications",
        tags=["apps", "applications", "splunk", "capabilities"],
    )

    def __init__(self, uri: str, name: str, description: str, mime_type: str = "application/json"):
        super().__init__(uri, name, description, mime_type)
        self.client_manager = get_client_manager()
        self.config_extractor = EnhancedConfigExtractor()

    async def get_content(self, ctx: Context) -> str:
        """Get installed applications information with detailed analysis"""
        try:
            # Extract client configuration (now includes fallback to server default)
            client_config = await self.config_extractor.extract_client_config(ctx)
            if not client_config:
                # Fallback to error response with helpful info
                return self._create_apps_error_response("No Splunk configuration available")

            # Get client identity and connection
            identity, service = await self.client_manager.get_client_connection(ctx, client_config)

            # Get comprehensive apps information
            apps_data = await self._get_comprehensive_apps_data(service, identity)

            return json.dumps(apps_data, indent=2)

        except ConnectionError as e:
            self.logger.warning(f"Splunk connection error for apps: {e}")
            return self._create_apps_error_response(f"Splunk connection failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to get apps data: {e}")
            return self._create_apps_error_response(f"Apps retrieval error: {str(e)}")

    def _create_apps_error_response(self, error_message: str) -> str:
        """Create a helpful JSON error response for apps retrieval issues"""
        error_response = {
            "status": "error",
            "error": error_message,
            "uri": self.uri,
            "apps": [],
            "help": {
                "message": "To access Splunk apps information, provide credentials via HTTP headers or environment variables",
                "http_headers": {
                    "X-Splunk-Host": "your-splunk-host",
                    "X-Splunk-Username": "your-username",
                    "X-Splunk-Password": "your-password",
                },
                "environment_variables": ["SPLUNK_HOST", "SPLUNK_USERNAME", "SPLUNK_PASSWORD"],
            },
        }
        return json.dumps(error_response, indent=2)

    def _convert_splunk_boolean(self, value, default=False):
        """
        Convert Splunk boolean values to Python booleans.

        Splunk API returns boolean values as strings:
        - "1" or "true" -> True
        - "0" or "false" -> False

        Args:
            value: The value to convert
            default: Default value if conversion fails

        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        if isinstance(value, int | float):
            return bool(value)
        return default

    async def _get_comprehensive_apps_data(self, service, identity) -> dict[str, Any]:
        """Get comprehensive apps data with capability analysis"""
        try:
            import time

            # Get all installed apps
            apps_data = []
            app_count = 0

            for app in service.apps:
                logger.info(f"Processing app: {app.name}")
                logger.info(f"App content: {dict(app.content)}")
                logger.info(
                    f"App attributes: {[attr for attr in dir(app) if not attr.startswith('_')]}"
                )

                app_info = {
                    "name": app.name,
                    "label": app.content.get("label", app.name),
                    "version": app.content.get("version", "unknown"),
                    "description": app.content.get("description", "No description available"),
                    "author": app.content.get("author", "unknown"),
                    "visible": self._convert_splunk_boolean(app.content.get("visible"), True),
                    "disabled": self._convert_splunk_boolean(app.content.get("disabled"), False),
                    "configured": self._convert_splunk_boolean(
                        app.content.get("configured"), False
                    ),
                    "state_change_requires_restart": self._convert_splunk_boolean(
                        app.content.get("state_change_requires_restart"), False
                    ),
                }

                # Add app capabilities information for LLM context
                app_info["capabilities"] = self._analyze_app_capabilities(app)

                apps_data.append(app_info)
                app_count += 1

            # Create comprehensive apps context for LLMs
            apps_context = {
                "client_id": identity.client_id,
                "splunk_host": identity.splunk_host,
                "timestamp": time.time(),
                "apps_summary": {
                    "total_apps": app_count,
                    "visible_apps": len([app for app in apps_data if app["visible"]]),
                    "enabled_apps": len([app for app in apps_data if not app["disabled"]]),
                    "configured_apps": len([app for app in apps_data if app["configured"]]),
                },
                "installed_apps": apps_data,
                "llm_context": {
                    "purpose": "This data helps understand what Splunk functionality is available",
                    "key_apps": self._identify_key_apps(apps_data),
                    "data_capabilities": self._summarize_data_capabilities(apps_data),
                    "search_capabilities": self._summarize_search_capabilities(apps_data),
                },
                "status": "success",
            }

            return apps_context

        except Exception as e:
            return {"client_id": identity.client_id, "error": str(e), "status": "error", "apps": []}

    def _analyze_app_capabilities(self, app) -> dict[str, Any]:
        """
        Analyze what capabilities an app provides for LLM context.

        Args:
            app: Splunk app object

        Returns:
            Dict describing app capabilities
        """
        capabilities = {
            "type": "unknown",
            "provides": [],
            "data_sources": [],
            "notable_features": [],
        }

        app_name = app.name.lower()

        # Categorize common Splunk apps
        if "enterprise_security" in app_name or app_name == "splunk_security_essentials":
            capabilities.update(
                {
                    "type": "security",
                    "provides": ["threat_detection", "incident_response", "security_analytics"],
                    "data_sources": [
                        "security_events",
                        "threat_intelligence",
                        "vulnerability_data",
                    ],
                    "notable_features": ["correlation_searches", "notable_events", "risk_analysis"],
                }
            )
        elif "itsi" in app_name or "it_service_intelligence" in app_name:
            capabilities.update(
                {
                    "type": "itsi",
                    "provides": ["service_monitoring", "kpi_management", "incident_management"],
                    "data_sources": ["infrastructure_metrics", "service_data", "kpi_data"],
                    "notable_features": ["service_analyzer", "deep_dives", "glass_tables"],
                }
            )
        elif "db_connect" in app_name or "dbx" in app_name:
            capabilities.update(
                {
                    "type": "database_integration",
                    "provides": ["database_connectivity", "data_ingestion"],
                    "data_sources": ["sql_databases", "relational_data"],
                    "notable_features": ["database_inputs", "sql_queries"],
                }
            )
        elif "splunk_app_for_aws" in app_name or app_name == "aws":
            capabilities.update(
                {
                    "type": "cloud_platform",
                    "provides": ["aws_monitoring", "cloud_analytics"],
                    "data_sources": ["aws_cloudtrail", "aws_s3", "aws_ec2", "aws_vpc"],
                    "notable_features": ["aws_dashboards", "aws_topology"],
                }
            )
        elif "machine_learning" in app_name or app_name == "mltk":
            capabilities.update(
                {
                    "type": "analytics",
                    "provides": ["machine_learning", "statistical_analysis", "forecasting"],
                    "data_sources": ["processed_data", "model_results"],
                    "notable_features": [
                        "ml_algorithms",
                        "predictive_analytics",
                        "anomaly_detection",
                    ],
                }
            )
        elif app_name == "search":
            capabilities.update(
                {
                    "type": "core_platform",
                    "provides": ["search_interface", "basic_analytics"],
                    "data_sources": ["all_indexed_data"],
                    "notable_features": ["search_app", "reports", "dashboards"],
                }
            )
        elif "common_information_model" in app_name or app_name == "splunk_sa_cim":
            capabilities.update(
                {
                    "type": "data_model",
                    "provides": ["data_normalization", "common_schema"],
                    "data_sources": ["normalized_data"],
                    "notable_features": ["cim_data_models", "field_mappings", "tags"],
                }
            )
        else:
            # Try to infer from app description
            description = app.content.get("description", "").lower()
            if "dashboard" in description:
                capabilities["provides"].append("dashboards")
            if "report" in description:
                capabilities["provides"].append("reports")
            if "alert" in description:
                capabilities["provides"].append("alerting")
            if "data" in description:
                capabilities["provides"].append("data_enrichment")

        return capabilities

    def _identify_key_apps(self, apps_data: list[dict]) -> list[dict[str, str]]:
        """
        Identify key apps that are important for LLM context.

        Args:
            apps_data: List of app information

        Returns:
            List of key apps with descriptions
        """
        key_apps = []

        important_apps = {
            "search": "Core Splunk search application",
            "enterprise_security": "Security analytics and threat detection",
            "itsi": "IT Service Intelligence for service monitoring",
            "splunk_sa_cim": "Common Information Model for data normalization",
            "machine_learning_toolkit": "Advanced analytics and ML capabilities",
            "db_connect": "Database connectivity and integration",
            "splunk_app_for_aws": "AWS cloud monitoring and analytics",
        }

        for app in apps_data:
            app_name = app["name"].lower()
            for key_name, description in important_apps.items():
                if key_name in app_name and not app["disabled"]:
                    key_apps.append(
                        {
                            "name": app["name"],
                            "label": app["label"],
                            "importance": description,
                            "version": app["version"],
                        }
                    )
                    break

        return key_apps

    def _summarize_data_capabilities(self, apps_data: list[dict]) -> dict[str, list[str]]:
        """
        Summarize what data capabilities are available based on installed apps.

        Args:
            apps_data: List of app information

        Returns:
            Dict summarizing data capabilities
        """
        capabilities = {
            "security_data": [],
            "infrastructure_data": [],
            "cloud_data": [],
            "application_data": [],
            "network_data": [],
        }

        for app in apps_data:
            if app["disabled"]:
                continue

            app_capabilities = app.get("capabilities", {})
            data_sources = app_capabilities.get("data_sources", [])

            for source in data_sources:
                if "security" in source or "threat" in source:
                    capabilities["security_data"].append(f"{app['label']}: {source}")
                elif "infrastructure" in source or "server" in source:
                    capabilities["infrastructure_data"].append(f"{app['label']}: {source}")
                elif "aws" in source or "cloud" in source:
                    capabilities["cloud_data"].append(f"{app['label']}: {source}")
                elif "application" in source or "app" in source:
                    capabilities["application_data"].append(f"{app['label']}: {source}")
                elif "network" in source or "vpc" in source:
                    capabilities["network_data"].append(f"{app['label']}: {source}")

        return capabilities

    def _summarize_search_capabilities(self, apps_data: list[dict]) -> dict[str, list[str]]:
        """
        Summarize what search capabilities are available based on installed apps.

        Args:
            apps_data: List of app information

        Returns:
            Dict summarizing search capabilities
        """
        capabilities = {
            "analytics": [],
            "visualization": [],
            "reporting": [],
            "alerting": [],
            "machine_learning": [],
        }

        for app in apps_data:
            if app["disabled"]:
                continue

            app_capabilities = app.get("capabilities", {})
            provides = app_capabilities.get("provides", [])
            features = app_capabilities.get("notable_features", [])

            for capability in provides + features:
                if "analytics" in capability or "analysis" in capability:
                    capabilities["analytics"].append(f"{app['label']}: {capability}")
                elif "dashboard" in capability or "visualization" in capability:
                    capabilities["visualization"].append(f"{app['label']}: {capability}")
                elif "report" in capability:
                    capabilities["reporting"].append(f"{app['label']}: {capability}")
                elif "alert" in capability or "notable" in capability:
                    capabilities["alerting"].append(f"{app['label']}: {capability}")
                elif "ml" in capability or "machine_learning" in capability:
                    capabilities["machine_learning"].append(f"{app['label']}: {capability}")

        return capabilities


class SplunkSearchResultsResource(BaseResource):
    """
    Resource for recent search results with client isolation.

    Provides access to recent search results from the client's Splunk instance.
    """

    METADATA = ResourceMetadata(
        uri="splunk://search/results/recent",
        name="Recent Search Results",
        description="Recent search results from client's Splunk instance",
        mime_type="application/json",
        category="search",
        tags=["search", "results", "client-scoped"],
    )

    def __init__(self, uri: str, name: str, description: str, mime_type: str = "application/json"):
        super().__init__(uri, name, description, mime_type)
        self.client_manager = get_client_manager()
        self.config_extractor = EnhancedConfigExtractor()

    async def get_content(self, ctx: Context) -> str:
        """Get recent search results"""
        try:
            # Extract client configuration (now includes fallback to server default)
            client_config = await self.config_extractor.extract_client_config(ctx)
            if not client_config:
                # Fallback to error response with helpful info
                return self._create_search_error_response("No Splunk configuration available")

            # Get client identity and connection
            identity, service = await self.client_manager.get_client_connection(ctx, client_config)
            # Get search results
            search_data = await self._get_search_results(service, identity)

            return json.dumps(search_data, indent=2)

        except ConnectionError as e:
            self.logger.warning(f"Splunk connection error for search results: {e}")
            return self._create_search_error_response(f"Splunk connection failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to get search results: {e}")
            return self._create_search_error_response(f"Search results error: {str(e)}")

    def _create_search_error_response(self, error_message: str) -> str:
        """Create a helpful JSON error response for search results issues"""
        error_response = {
            "status": "error",
            "error": error_message,
            "uri": self.uri,
            "results": [],
            "recent_searches": [],
            "help": {
                "message": "To access Splunk search results, provide credentials via HTTP headers or environment variables",
                "http_headers": {
                    "X-Splunk-Host": "your-splunk-host",
                    "X-Splunk-Username": "your-username",
                    "X-Splunk-Password": "your-password",
                },
                "environment_variables": ["SPLUNK_HOST", "SPLUNK_USERNAME", "SPLUNK_PASSWORD"],
            },
        }
        return json.dumps(error_response, indent=2)

    async def _get_search_results(self, service, identity) -> dict[str, Any]:
        """Get recent search results from Splunk"""
        try:
            import time

            # Get recent jobs
            jobs = service.jobs
            recent_results = []

            # Debug logging
            self.logger.info(f"Attempting to retrieve jobs for client {identity.client_id}")

            # Check if jobs collection exists and is iterable
            if not jobs:
                self.logger.warning("No jobs collection found")
                return {
                    "client_id": identity.client_id,
                    "splunk_host": identity.splunk_host,
                    "timestamp": time.time(),
                    "recent_searches": [],
                    "total_results": 0,
                    "status": "success",
                    "message": "No jobs collection found"
                }

            try:
                # Convert to list to check if there are any jobs
                jobs_list = list(jobs)
                self.logger.info(f"Found {len(jobs_list)} total jobs")

                if not jobs_list:
                    return {
                        "client_id": identity.client_id,
                        "splunk_host": identity.splunk_host,
                        "timestamp": time.time(),
                        "recent_searches": [],
                        "total_results": 0,
                        "status": "success",
                        "message": "No jobs found in collection"
                    }

            except Exception as list_error:
                self.logger.error(f"Error converting jobs to list: {list_error}")
                return {
                    "client_id": identity.client_id,
                    "splunk_host": identity.splunk_host,
                    "timestamp": time.time(),
                    "recent_searches": [],
                    "total_results": 0,
                    "status": "error",
                    "error": f"Error accessing jobs collection: {str(list_error)}"
                }

            count = 0
            processed_jobs = 0

            for job in jobs_list:
                if count >= 10:  # Limit to 10 recent searches
                    break

                processed_jobs += 1
                self.logger.debug(f"Processing job {processed_jobs}: {getattr(job, 'sid', 'unknown')}")

                try:
                    # Check if job is done - some jobs might not have this method
                    is_done = getattr(job, 'is_done', lambda: True)()
                    if not is_done:
                        self.logger.debug(f"Job {getattr(job, 'sid', 'unknown')} is not done, skipping")
                        continue

                    # Safely access job properties with fallbacks
                    job_info = {
                        "search_id": getattr(job, 'sid', 'unknown'),
                        "search_query": self._safe_get_search_query(job),
                        "event_count": self._safe_get_job_count(job, 'eventCount'),
                        "result_count": self._safe_get_job_count(job, 'resultCount'),
                        "earliest_time": self._safe_get_job_time(job, 'earliestTime'),
                        "latest_time": self._safe_get_job_time(job, 'latestTime'),
                        "status": "completed",
                    }
                    recent_results.append(job_info)
                    count += 1
                    self.logger.debug(f"Successfully processed job {job_info['search_id']}")

                except Exception as job_error:
                    # Log individual job errors but continue processing
                    self.logger.warning(f"Error processing job {getattr(job, 'sid', 'unknown')}: {job_error}")
                    continue

            self.logger.info(f"Successfully processed {count} jobs out of {processed_jobs} examined")

            return {
                "client_id": identity.client_id,
                "splunk_host": identity.splunk_host,
                "timestamp": time.time(),
                "recent_searches": recent_results,
                "total_results": len(recent_results),
                "total_jobs_examined": processed_jobs,
                "status": "success",
            }

        except Exception as e:
            self.logger.error(f"Failed to get search results: {e}", exc_info=True)
            return {
                "client_id": identity.client_id,
                "error": str(e),
                "status": "error",
                "recent_searches": [],
            }

    def _safe_get_search_query(self, job) -> str:
        """Safely get search query from job object"""
        try:
            search_query = getattr(job, 'search', None)
            if search_query is None:
                # Try accessing from content
                search_query = getattr(job, 'content', {}).get('search', 'N/A')

            search_str = str(search_query)
            if len(search_str) > 200:
                return search_str[:200] + "..."
            return search_str
        except Exception:
            return "N/A"

    def _safe_get_job_count(self, job, count_attr: str) -> int:
        """Safely get count attributes from job object"""
        try:
            # Try direct attribute access first
            count_value = getattr(job, count_attr, None)
            if count_value is not None:
                return int(count_value)

            # Try accessing from content
            content = getattr(job, 'content', {})
            if hasattr(content, 'get'):
                count_value = content.get(count_attr, 0)
                return int(count_value)

            return 0
        except (ValueError, TypeError, AttributeError):
            return 0

    def _safe_get_job_time(self, job, time_attr: str) -> str:
        """Safely get time attributes from job object"""
        try:
            # Try direct attribute access first
            time_value = getattr(job, time_attr, None)
            if time_value is not None:
                return str(time_value)

            # Try accessing from content
            content = getattr(job, 'content', {})
            if hasattr(content, 'get'):
                time_value = content.get(time_attr, 'N/A')
                return str(time_value)

            return 'N/A'
        except (AttributeError, TypeError):
            return 'N/A'


class SplunkIndexesResource(BaseResource):
    """
    Resource for Splunk indexes with client isolation.

    Provides access to the list of Splunk indexes available to the client.
    Automatically filters out internal indexes for better performance and relevance.
    """

    METADATA = ResourceMetadata(
        uri="splunk://indexes/list",
        name="Splunk Indexes",
        description="List of accessible Splunk indexes (excluding internal indexes)",
        mime_type="application/json",
        category="metadata",
        tags=["indexes", "metadata", "client-scoped"],
    )

    def __init__(self, uri: str, name: str, description: str, mime_type: str = "application/json"):
        super().__init__(uri, name, description, mime_type)
        self.client_manager = get_client_manager()
        self.config_extractor = EnhancedConfigExtractor()

    async def get_content(self, ctx: Context) -> str:
        """Get indexes information"""
        try:
            # Extract client configuration (now includes fallback to server default)
            client_config = await self.config_extractor.extract_client_config(ctx)
            if not client_config:
                # Fallback to error response with helpful info
                return self._create_indexes_error_response("No Splunk configuration available")

            # Get client identity and connection
            identity, service = await self.client_manager.get_client_connection(ctx, client_config)

            # Get indexes information
            indexes_data = await self._get_indexes_data(service, identity)

            return json.dumps(indexes_data, indent=2)

        except ConnectionError as e:
            self.logger.warning(f"Splunk connection error for indexes: {e}")
            return self._create_indexes_error_response(f"Splunk connection failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to get indexes data: {e}")
            return self._create_indexes_error_response(f"Indexes retrieval error: {str(e)}")

    def _create_indexes_error_response(self, error_message: str) -> str:
        """Create a helpful JSON error response for indexes retrieval issues"""
        error_response = {
            "status": "error",
            "error": error_message,
            "uri": self.uri,
            "indexes": [],
            "help": {
                "message": "To access Splunk indexes information, provide credentials via HTTP headers or environment variables",
                "http_headers": {
                    "X-Splunk-Host": "your-splunk-host",
                    "X-Splunk-Username": "your-username",
                    "X-Splunk-Password": "your-password",
                },
                "environment_variables": ["SPLUNK_HOST", "SPLUNK_USERNAME", "SPLUNK_PASSWORD"],
            },
        }
        return json.dumps(error_response, indent=2)

    async def _get_indexes_data(self, service, identity) -> dict[str, Any]:
        """Get comprehensive indexes data from Splunk"""
        try:
            import time

            # Get all indexes and filter out internal ones
            all_indexes = list(service.indexes)
            customer_indexes = filter_customer_indexes(all_indexes)

            # Build detailed index information
            indexes_list = []
            for index in customer_indexes:
                index_info = {
                    "name": index.name,
                    "max_data_size": index.content.get("maxDataSize", "auto"),
                    "max_hot_buckets": index.content.get("maxHotBuckets", "auto"),
                    "max_warm_db_count": index.content.get("maxWarmDBCount", "auto"),
                    "home_path": index.content.get("homePath", ""),
                    "cold_path": index.content.get("coldPath", ""),
                    "thawed_path": index.content.get("thawedPath", ""),
                    "disabled": self._convert_splunk_boolean(index.content.get("disabled"), False),
                    "splunk_server": index.content.get("splunk_server", ""),
                    "eai_acl": index.content.get("eai:acl", {}),
                    "current_db_size_mb": index.content.get("currentDBSizeMB", 0),
                    "max_total_data_size_mb": index.content.get("maxTotalDataSizeMB", 0),
                    "total_event_count": index.content.get("totalEventCount", 0),
                }
                indexes_list.append(index_info)

            # Create comprehensive indexes context
            indexes_context = {
                "client_id": identity.client_id,
                "splunk_host": identity.splunk_host,
                "timestamp": time.time(),
                "indexes_summary": {
                    "total_indexes": len(indexes_list),
                    "total_count_including_internal": len(all_indexes),
                    "enabled_indexes": len([idx for idx in indexes_list if not idx["disabled"]]),
                    "disabled_indexes": len([idx for idx in indexes_list if idx["disabled"]]),
                },
                "indexes": sorted(indexes_list, key=lambda x: x["name"]),
                "status": "success",
            }

            return indexes_context

        except Exception as e:
            return {
                "client_id": identity.client_id,
                "error": str(e),
                "status": "error",
                "indexes": [],
            }

    def _convert_splunk_boolean(self, value, default=False):
        """Convert Splunk boolean values to Python booleans"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        if isinstance(value, int | float):
            return bool(value)
        return default


class SplunkSavedSearchesResource(BaseResource):
    """
    Resource for Splunk saved searches with client isolation.

    Provides access to saved searches that the user has access to.
    """

    METADATA = ResourceMetadata(
        uri="splunk://savedsearches/list",
        name="Splunk Saved Searches",
        description="List of accessible Splunk saved searches",
        mime_type="application/json",
        category="search",
        tags=["saved_searches", "search", "client-scoped"],
    )

    def __init__(self, uri: str, name: str, description: str, mime_type: str = "application/json"):
        super().__init__(uri, name, description, mime_type)
        self.client_manager = get_client_manager()
        self.config_extractor = EnhancedConfigExtractor()

    async def get_content(self, ctx: Context) -> str:
        """Get saved searches information"""
        try:
            # Extract client configuration (now includes fallback to server default)
            client_config = await self.config_extractor.extract_client_config(ctx)
            if not client_config:
                # Fallback to error response with helpful info
                return self._create_saved_searches_error_response(
                    "No Splunk configuration available"
                )

            # Get client identity and connection
            identity, service = await self.client_manager.get_client_connection(ctx, client_config)

            # Get saved searches information
            saved_searches_data = await self._get_saved_searches_data(service, identity)

            return json.dumps(saved_searches_data, indent=2)

        except ConnectionError as e:
            self.logger.warning(f"Splunk connection error for saved searches: {e}")
            return self._create_saved_searches_error_response(f"Splunk connection failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to get saved searches data: {e}")
            return self._create_saved_searches_error_response(
                f"Saved searches retrieval error: {str(e)}"
            )

    def _create_saved_searches_error_response(self, error_message: str) -> str:
        """Create a helpful JSON error response for saved searches retrieval issues"""
        error_response = {
            "status": "error",
            "error": error_message,
            "uri": self.uri,
            "saved_searches": [],
            "help": {
                "message": "To access Splunk saved searches, provide credentials via HTTP headers or environment variables",
                "http_headers": {
                    "X-Splunk-Host": "your-splunk-host",
                    "X-Splunk-Username": "your-username",
                    "X-Splunk-Password": "your-password",
                },
                "environment_variables": ["SPLUNK_HOST", "SPLUNK_USERNAME", "SPLUNK_PASSWORD"],
            },
        }
        return json.dumps(error_response, indent=2)

    async def _get_saved_searches_data(self, service, identity) -> dict[str, Any]:
        """Get comprehensive saved searches data from Splunk"""
        try:
            import time

            # Get all saved searches
            saved_searches_list = []
            for saved_search in service.saved_searches:
                logger.info(f"Processing saved search: {saved_search.name}")
                logger.debug(f"Saved search content: {dict(saved_search.content)}")

                saved_search_info = {
                    "name": saved_search.name,
                    "search": saved_search.content.get("search", ""),
                    # "dispatch": {
                    #     "earliest_time": saved_search.content.get("dispatch.earliest_time", ""),
                    #     "latest_time": saved_search.content.get("dispatch.latest_time", ""),
                    #     "index_earliest": saved_search.content.get("dispatch.index_earliest", ""),
                    #     "index_latest": saved_search.content.get("dispatch.index_latest", "")
                    # },
                    # "is_scheduled": self._convert_splunk_boolean(saved_search.content.get("is_scheduled"), False),
                    # "is_visible": self._convert_splunk_boolean(saved_search.content.get("is_visible"), True),
                    "disabled": self._convert_splunk_boolean(
                        saved_search.content.get("disabled"), False
                    ),
                    "description": saved_search.content.get("description", ""),
                    "owner": saved_search.content.get("eai:acl", {}).get("owner", ""),
                    "app": saved_search.content.get("eai:acl", {}).get("app", ""),
                    # "sharing": saved_search.content.get("eai:acl", {}).get("sharing", ""),
                    # "permissions": {
                    #     "read": saved_search.content.get("eai:acl", {}).get("perms", {}).get("read", []),
                    #     "write": saved_search.content.get("eai:acl", {}).get("perms", {}).get("write", [])
                    # },
                    # "cron_schedule": saved_search.content.get("cron_schedule", ""),
                    # "next_scheduled_time": saved_search.content.get("next_scheduled_time", ""),
                    # "actions": {
                    #     "email": self._convert_splunk_boolean(saved_search.content.get("action.email"), False),
                    #     "populate_lookup": self._convert_splunk_boolean(saved_search.content.get("action.populate_lookup"), False),
                    #     "rss": self._convert_splunk_boolean(saved_search.content.get("action.rss"), False),
                    #     "script": self._convert_splunk_boolean(saved_search.content.get("action.script"), False),
                    #     "summary_index": self._convert_splunk_boolean(saved_search.content.get("action.summary_index"), False)
                    # },
                    # "alert": {
                    #     "condition": saved_search.content.get("alert.condition", ""),
                    #     "comparator": saved_search.content.get("alert.comparator", ""),
                    #     "threshold": saved_search.content.get("alert.threshold", ""),
                    #     "type": saved_search.content.get("alert_type", ""),
                    #     "track": saved_search.content.get("alert.track", "")
                    # },
                    "updated": saved_search.content.get("updated", ""),
                    # "qualifiedSearch": saved_search.content.get("qualifiedSearch", "")
                }
                saved_searches_list.append(saved_search_info)

            # Create comprehensive saved searches context
            saved_searches_context = {
                "client_id": identity.client_id,
                "splunk_host": identity.splunk_host,
                "timestamp": time.time(),
                "saved_searches_summary": {
                    "total_saved_searches": len(saved_searches_list),
                    # "scheduled_searches": len([ss for ss in saved_searches_list if ss["is_scheduled"]]),
                    # "visible_searches": len([ss for ss in saved_searches_list if ss["is_visible"]]),
                    # "enabled_searches": len([ss for ss in saved_searches_list if not ss["disabled"]]),
                    # "alert_searches": len([ss for ss in saved_searches_list if ss["alert"]["type"]])
                },
                "saved_searches": sorted(saved_searches_list, key=lambda x: x["name"]),
                "status": "success",
            }

            return saved_searches_context

        except Exception as e:
            return {
                "client_id": identity.client_id,
                "error": str(e),
                "status": "error",
                "saved_searches": [],
            }

    def _convert_splunk_boolean(self, value, default=False):
        """Convert Splunk boolean values to Python booleans"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        if isinstance(value, int | float):
            return bool(value)
        return default
