"""
Splunk Configuration Resource Implementation.

Provides access to Splunk configuration files through the MCP resource system.
"""

import json
import logging
import time
from typing import Any, Dict

from fastmcp.server.context import Context

from ..base import BaseResource, ResourceMetadata
from ..client_identity import get_client_manager
from ..enhanced_config_extractor import EnhancedConfigExtractor
from .base import ClientScopedResource

logger = logging.getLogger(__name__)


class SplunkConfigResource(BaseResource):
    """
    Resource for accessing Splunk configuration files.
    
    Provides secure access to configuration files like indexes.conf, props.conf, etc.
    with proper client isolation.
    """
    
    # Metadata for resource registry
    METADATA = ResourceMetadata(
        uri="splunk://config/indexes.conf",
        name="Splunk Configuration Files",
        description="Access to Splunk configuration files with client isolation",
        mime_type="text/plain",
        category="configuration",
        tags=["config", "splunk", "client-scoped"]
    )
    
    def __init__(self, uri: str, name: str, description: str, mime_type: str = "text/plain"):
        super().__init__(uri, name, description, mime_type)
        self.client_manager = get_client_manager()
        self.config_extractor = EnhancedConfigExtractor()
    
    async def get_content(self, ctx: Context) -> str:
        """
        Get configuration file content with client isolation.
        
        Args:
            ctx: MCP context containing client information
            
        Returns:
            Configuration file content as string
            
        Raises:
            PermissionError: If access is denied
            ValueError: If configuration not found
        """
        try:
            # Extract client configuration
            client_config = await self.config_extractor.extract_client_config(ctx)
            if not client_config:
                raise PermissionError("No client configuration found")
            
            # Get client identity and connection
            identity, service = await self.client_manager.get_client_connection(ctx, client_config)
            
            # Extract config file from URI
            config_file = self._extract_config_file_from_uri(self.uri)
            if not config_file:
                raise ValueError(f"Could not determine config file from URI: {self.uri}")
            
            # Get configuration content from Splunk
            config_content = await self._get_config_content(service, config_file, identity)
            
            self.logger.info(f"Retrieved config {config_file} for client {identity.client_id}")
            return config_content
            
        except Exception as e:
            self.logger.error(f"Failed to get config content for {self.uri}: {e}")
            raise
    
    def _extract_config_file_from_uri(self, uri: str) -> str | None:
        """Extract config file name from URI"""
        try:
            # Handle patterns like:
            # splunk://config/indexes.conf
            # splunk://client/{client_id}/config/indexes.conf
            parts = uri.split('/')
            
            if 'config' in parts:
                config_index = parts.index('config')
                if config_index + 1 < len(parts):
                    return parts[config_index + 1]
            
            return None
        except Exception:
            return None
    
    async def _get_config_content(self, service, config_file: str, identity) -> str:
        """Get configuration content from Splunk service"""
        try:
            # Get configuration using Splunk REST API
            configs = service.confs[config_file.replace('.conf', '')]
            
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
            return json.dumps({
                "config_file": config_file,
                "client_id": identity.client_id,
                "error": str(e),
                "available_configs": list(service.confs.keys()) if hasattr(service, 'confs') else []
            }, indent=2)


class SplunkHealthResource(BaseResource):
    """Resource for Splunk health status information"""
    
    METADATA = ResourceMetadata(
        uri="splunk://health/status",
        name="Splunk Health Status",
        description="Real-time health monitoring for Splunk components",
        mime_type="application/json",
        category="monitoring",
        tags=["health", "monitoring", "splunk"]
    )
    
    def __init__(self, uri: str, name: str, description: str, mime_type: str = "application/json"):
        super().__init__(uri, name, description, mime_type)
        self.client_manager = get_client_manager()
        self.config_extractor = EnhancedConfigExtractor()
    
    async def get_content(self, ctx: Context) -> str:
        """Get health status information"""
        try:
            # Extract client configuration
            client_config = await self.config_extractor.extract_client_config(ctx)
            if not client_config:
                raise PermissionError("No client configuration found")
            
            # Get client identity and connection
            identity, service = await self.client_manager.get_client_connection(ctx, client_config)
            
            # Get health information
            health_data = await self._get_health_data(service, identity)
            
            return json.dumps(health_data, indent=2)
            
        except Exception as e:
            self.logger.error(f"Failed to get health data: {e}")
            error_response = {
                "error": str(e),
                "status": "error",
                "timestamp": "N/A"
            }
            return json.dumps(error_response, indent=2)
    
    async def _get_health_data(self, service, identity) -> Dict[str, Any]:
        """Get comprehensive health data from Splunk"""
        try:
            info = service.info()
            
            health_data = {
                "client_id": identity.client_id,
                "splunk_host": identity.splunk_host,
                "timestamp": info.get("_time", "unknown"),
                "server_info": {
                    "version": info.get("version"),
                    "build": info.get("build"),
                    "server_name": info.get("serverName"),
                    "license_state": info.get("licenseState"),
                    "startup_time": info.get("startup_time")
                },
                "status": "healthy" if info.get("licenseState") != "EXPIRED" else "warning"
            }
            
            # Add index information if available
            try:
                indexes = service.indexes
                health_data["indexes"] = {
                    "count": len(indexes),
                    "total_size": sum(int(idx.get("totalEventCount", 0)) for idx in indexes),
                    "available": [idx.name for idx in indexes[:5]]  # First 5 indexes
                }
            except Exception as e:
                health_data["indexes"] = {"error": str(e)}
            
            return health_data
            
        except Exception as e:
            return {
                "client_id": identity.client_id,
                "error": str(e),
                "status": "error"
            }


class SplunkAppsResource(BaseResource):
    """
    Resource for Splunk installed applications with comprehensive analysis.
    
    Provides installed Splunk apps as contextual information for LLMs.
    Apps help LLMs understand what functionality, data models, dashboards,
    and search capabilities are available in the client's Splunk environment.
    """
    
    METADATA = ResourceMetadata(
        uri="splunk://apps/installed",
        name="Splunk Installed Apps",
        description="Information about installed Splunk applications and add-ons with capability analysis",
        mime_type="application/json",
        category="applications",
        tags=["apps", "applications", "splunk", "capabilities"]
    )
    
    def __init__(self, uri: str, name: str, description: str, mime_type: str = "application/json"):
        super().__init__(uri, name, description, mime_type)
        self.client_manager = get_client_manager()
        self.config_extractor = EnhancedConfigExtractor()
    
    async def get_content(self, ctx: Context) -> str:
        """Get installed applications information with detailed analysis"""
        try:
            # Extract client configuration
            client_config = await self.config_extractor.extract_client_config(ctx)
            if not client_config:
                raise PermissionError("No client configuration found")
            
            # Get client identity and connection
            identity, service = await self.client_manager.get_client_connection(ctx, client_config)
            
            # Get comprehensive apps information
            apps_data = await self._get_comprehensive_apps_data(service, identity)
            
            return json.dumps(apps_data, indent=2)
            
        except Exception as e:
            self.logger.error(f"Failed to get apps data: {e}")
            error_response = {
                "error": str(e),
                "status": "error",
                "apps": []
            }
            return json.dumps(error_response, indent=2)
    
    async def _get_comprehensive_apps_data(self, service, identity) -> Dict[str, Any]:
        """Get comprehensive apps data with capability analysis"""
        try:
            import time
            
            # Get all installed apps
            apps_data = []
            app_count = 0
            
            for app in service.apps:
                app_info = {
                    "name": app.name,
                    "label": app.content.get("label", app.name),
                    "version": app.content.get("version", "unknown"),
                    "description": app.content.get("description", "No description available"),
                    "author": app.content.get("author", "unknown"),
                    "visible": app.content.get("visible", True),
                    "disabled": app.content.get("disabled", False),
                    "configured": app.content.get("configured", False),
                    "state_change_requires_restart": app.content.get("state_change_requires_restart", False)
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
                    "configured_apps": len([app for app in apps_data if app["configured"]])
                },
                "installed_apps": apps_data,
                "llm_context": {
                    "purpose": "This data helps understand what Splunk functionality is available",
                    "key_apps": self._identify_key_apps(apps_data),
                    "data_capabilities": self._summarize_data_capabilities(apps_data),
                    "search_capabilities": self._summarize_search_capabilities(apps_data)
                },
                "status": "success"
            }
            
            return apps_context
            
        except Exception as e:
            return {
                "client_id": identity.client_id,
                "error": str(e),
                "status": "error",
                "apps": []
            }
    
    def _analyze_app_capabilities(self, app) -> Dict[str, Any]:
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
            "notable_features": []
        }
        
        app_name = app.name.lower()
        
        # Categorize common Splunk apps
        if "enterprise_security" in app_name or app_name == "splunk_security_essentials":
            capabilities.update({
                "type": "security",
                "provides": ["threat_detection", "incident_response", "security_analytics"],
                "data_sources": ["security_events", "threat_intelligence", "vulnerability_data"],
                "notable_features": ["correlation_searches", "notable_events", "risk_analysis"]
            })
        elif "itsi" in app_name or "it_service_intelligence" in app_name:
            capabilities.update({
                "type": "itsi",
                "provides": ["service_monitoring", "kpi_management", "incident_management"],
                "data_sources": ["infrastructure_metrics", "service_data", "kpi_data"],
                "notable_features": ["service_analyzer", "deep_dives", "glass_tables"]
            })
        elif "db_connect" in app_name or "dbx" in app_name:
            capabilities.update({
                "type": "database_integration",
                "provides": ["database_connectivity", "data_ingestion"],
                "data_sources": ["sql_databases", "relational_data"],
                "notable_features": ["database_inputs", "sql_queries"]
            })
        elif "splunk_app_for_aws" in app_name or app_name == "aws":
            capabilities.update({
                "type": "cloud_platform",
                "provides": ["aws_monitoring", "cloud_analytics"],
                "data_sources": ["aws_cloudtrail", "aws_s3", "aws_ec2", "aws_vpc"],
                "notable_features": ["aws_dashboards", "aws_topology"]
            })
        elif "machine_learning" in app_name or app_name == "mltk":
            capabilities.update({
                "type": "analytics",
                "provides": ["machine_learning", "statistical_analysis", "forecasting"],
                "data_sources": ["processed_data", "model_results"],
                "notable_features": ["ml_algorithms", "predictive_analytics", "anomaly_detection"]
            })
        elif app_name == "search":
            capabilities.update({
                "type": "core_platform",
                "provides": ["search_interface", "basic_analytics"],
                "data_sources": ["all_indexed_data"],
                "notable_features": ["search_app", "reports", "dashboards"]
            })
        elif "common_information_model" in app_name or app_name == "splunk_sa_cim":
            capabilities.update({
                "type": "data_model",
                "provides": ["data_normalization", "common_schema"],
                "data_sources": ["normalized_data"],
                "notable_features": ["cim_data_models", "field_mappings", "tags"]
            })
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
    
    def _identify_key_apps(self, apps_data: list[Dict]) -> list[Dict[str, str]]:
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
            "splunk_app_for_aws": "AWS cloud monitoring and analytics"
        }
        
        for app in apps_data:
            app_name = app["name"].lower()
            for key_name, description in important_apps.items():
                if key_name in app_name and not app["disabled"]:
                    key_apps.append({
                        "name": app["name"],
                        "label": app["label"],
                        "importance": description,
                        "version": app["version"]
                    })
                    break
        
        return key_apps
    
    def _summarize_data_capabilities(self, apps_data: list[Dict]) -> Dict[str, list[str]]:
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
            "network_data": []
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
    
    def _summarize_search_capabilities(self, apps_data: list[Dict]) -> Dict[str, list[str]]:
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
            "machine_learning": []
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
        name="Splunk Search Results",
        description="Recent search results from client's Splunk instance",
        mime_type="application/json",
        category="search",
        tags=["search", "results", "client-scoped"]
    )
    
    def __init__(self, uri: str, name: str, description: str, mime_type: str = "application/json"):
        super().__init__(uri, name, description, mime_type)
        self.client_manager = get_client_manager()
        self.config_extractor = EnhancedConfigExtractor()
    
    async def get_content(self, ctx: Context) -> str:
        """Get recent search results"""
        try:
            # Extract client configuration
            client_config = await self.config_extractor.extract_client_config(ctx)
            if not client_config:
                raise PermissionError("No client configuration found")
            
            # Get client identity and connection
            identity, service = await self.client_manager.get_client_connection(ctx, client_config)
            
            # Get search results
            search_data = await self._get_search_results(service, identity)
            
            return json.dumps(search_data, indent=2)
            
        except Exception as e:
            self.logger.error(f"Failed to get search results: {e}")
            error_response = {
                "error": str(e),
                "status": "error",
                "results": []
            }
            return json.dumps(error_response, indent=2)
    
    async def _get_search_results(self, service, identity) -> Dict[str, Any]:
        """Get recent search results from Splunk"""
        try:
            # Get recent jobs
            jobs = service.jobs
            recent_results = []
            
            count = 0
            for job in jobs:
                if count >= 10:  # Limit to 10 recent searches
                    break
                
                if job.is_done():
                    job_info = {
                        "search_id": job.sid,
                        "search_query": str(job.search)[:200] + "..." if len(str(job.search)) > 200 else str(job.search),
                        "event_count": job.eventCount,
                        "result_count": job.resultCount,
                        "earliest_time": str(job.earliestTime),
                        "latest_time": str(job.latestTime),
                        "status": "completed"
                    }
                    recent_results.append(job_info)
                    count += 1
            
            return {
                "client_id": identity.client_id,
                "splunk_host": identity.splunk_host,
                "timestamp": time.time(),
                "recent_searches": recent_results,
                "total_results": len(recent_results),
                "status": "success"
            }
            
        except Exception as e:
            return {
                "client_id": identity.client_id,
                "error": str(e),
                "status": "error",
                "recent_searches": []
            }