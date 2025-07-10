"""Workflow Requirements Tool

Provides comprehensive requirements and schema information for creating custom workflows
that integrate with the MCP Server for Splunk dynamic troubleshooting system.
"""

import json
from typing import Any, Dict, Optional

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata


class WorkflowRequirementsTool(BaseTool):
    """
    Workflow Requirements Tool for Custom Workflow Creation.

    This tool provides detailed requirements, schemas, and guidelines for creating custom
    troubleshooting workflows that integrate with the dynamic troubleshoot agent.
    It serves as a comprehensive reference for workflow contributors.

    ## Key Features:
    - **Complete Schema Documentation**: Full WorkflowDefinition and TaskDefinition schemas
    - **Available Tools Reference**: Comprehensive list of available Splunk tools
    - **Context Variables Guide**: Documentation of all available context variables
    - **Validation Rules**: Requirements and constraints for workflow validation
    - **Best Practices**: Guidelines for creating effective workflows
    - **Integration Information**: How workflows integrate with the dynamic troubleshoot agent

    ## Output Formats:
    - **detailed**: Complete requirements with examples and explanations
    - **schema**: JSON schema definitions for validation
    - **quick**: Quick reference for experienced contributors
    - **examples**: Example workflow structures and patterns

    ## Use Cases:
    - Understanding workflow structure requirements
    - Getting schema definitions for validation
    - Learning available tools and context variables
    - Understanding integration points with dynamic troubleshoot agent
    - Quick reference during workflow development
    """

    METADATA = ToolMetadata(
        name="workflow_requirements",
        description="""Get comprehensive requirements and schema information for creating custom workflows.

This tool provides detailed documentation for creating custom troubleshooting workflows that integrate
with the MCP Server for Splunk dynamic troubleshooting system. It includes complete schema definitions,
available tools, context variables, validation rules, and integration guidelines.

## Output Formats:
- **detailed**: Complete requirements with examples and explanations (default)
- **schema**: JSON schema definitions for validation tools
- **quick**: Quick reference for experienced contributors
- **examples**: Example workflow structures and common patterns

## Key Information Provided:
- WorkflowDefinition and TaskDefinition schema structures
- Complete list of available Splunk tools with descriptions
- Context variables and their usage patterns
- Validation rules and constraints
- Integration points with dynamic troubleshoot agent
- Best practices for workflow design and task creation

Perfect for workflow contributors who need to understand the requirements and structure
for creating custom diagnostic workflows.""",
        category="workflows",
    )

    def __init__(self, name: str, category: str):
        super().__init__(name, self.METADATA.description)
        self.category = category

    async def execute(
        self,
        ctx: Context,
        format_type: str = "detailed"
    ) -> Dict[str, Any]:
        """
        Get workflow requirements and schema information.

        Args:
            format_type: Output format - "detailed", "schema", "quick", or "examples"

        Returns:
            Dict containing comprehensive workflow requirements information
        """
        try:
            if format_type == "schema":
                return self.format_success_response(self._get_schema_definitions())
            elif format_type == "quick":
                return self.format_success_response(self._get_quick_reference())
            elif format_type == "examples":
                return self.format_success_response(self._get_examples())
            else:  # detailed
                return self.format_success_response(self._get_detailed_requirements())

        except Exception as e:
            return self.format_error_response(f"Failed to get workflow requirements: {str(e)}")

    def _get_detailed_requirements(self) -> Dict[str, Any]:
        """Get detailed workflow requirements with explanations."""
        return {
            "workflow_requirements": {
                "overview": {
                    "purpose": "Custom workflows enable community members to create specialized troubleshooting procedures",
                    "integration": "Workflows integrate with dynamic_troubleshoot_agent via workflow_type parameter",
                    "execution": "Tasks execute in parallel where possible, with dependency-aware orchestration",
                    "format": "JSON files following WorkflowDefinition schema"
                },
                "workflow_definition_schema": {
                    "required_fields": {
                        "workflow_id": {
                            "type": "string",
                            "description": "Unique identifier for the workflow",
                            "constraints": [
                                "Must be unique across all workflows",
                                "Use snake_case format (e.g., 'custom_security_analysis')",
                                "No spaces or special characters except underscores",
                                "Maximum 50 characters"
                            ],
                            "examples": ["custom_security_analysis", "data_quality_check", "performance_deep_dive"]
                        },
                        "name": {
                            "type": "string",
                            "description": "Human-readable workflow name",
                            "constraints": [
                                "Clear, descriptive name for the workflow",
                                "Maximum 100 characters",
                                "Should indicate the workflow's purpose"
                            ],
                            "examples": ["Custom Security Analysis", "Data Quality Assessment", "Performance Deep Dive"]
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of workflow purpose and use cases",
                            "constraints": [
                                "Comprehensive description of what the workflow does",
                                "Include when to use this workflow",
                                "Mention key features and capabilities",
                                "Maximum 1000 characters"
                            ]
                        },
                        "tasks": {
                            "type": "array",
                            "description": "List of TaskDefinition objects",
                            "constraints": [
                                "Must contain at least one task",
                                "Maximum 20 tasks per workflow",
                                "Each task must have unique task_id within workflow"
                            ]
                        }
                    },
                    "optional_fields": {
                        "default_context": {
                            "type": "object",
                            "description": "Default context variables for the workflow",
                            "usage": "Define workflow-specific default values",
                            "examples": {
                                "security_threshold": "medium",
                                "compliance_framework": "SOX",
                                "notification_email": "admin@company.com"
                            }
                        }
                    }
                },
                "task_definition_schema": {
                    "required_fields": {
                        "task_id": {
                            "type": "string",
                            "description": "Unique identifier for the task within the workflow",
                            "constraints": [
                                "Must be unique within the workflow",
                                "Use snake_case format",
                                "Maximum 50 characters",
                                "Should indicate the task's purpose"
                            ]
                        },
                        "name": {
                            "type": "string",
                            "description": "Human-readable task name",
                            "constraints": ["Clear, descriptive name", "Maximum 100 characters"]
                        },
                        "description": {
                            "type": "string",
                            "description": "Brief description of what the task accomplishes",
                            "constraints": ["Concise task description", "Maximum 200 characters"]
                        },
                        "instructions": {
                            "type": "string",
                            "description": "Detailed instructions for the AI agent executing this task",
                            "constraints": [
                                "Comprehensive instructions for AI agent",
                                "Include specific Splunk searches when possible",
                                "Provide analysis steps and expected outcomes",
                                "Use context variables (e.g., {focus_index})",
                                "Maximum 5000 characters"
                            ]
                        }
                    },
                    "optional_fields": {
                        "required_tools": {
                            "type": "array",
                            "description": "List of Splunk tools required for this task",
                            "default": "[]",
                            "available_tools": self._get_available_tools()
                        },
                        "dependencies": {
                            "type": "array",
                            "description": "List of task_ids this task depends on",
                            "default": "[]",
                            "constraints": [
                                "Task IDs must exist in the same workflow",
                                "No circular dependencies allowed",
                                "Use only when data from other tasks is needed"
                            ]
                        },
                        "context_requirements": {
                            "type": "array",
                            "description": "List of context variables required for this task",
                            "default": "[]",
                            "available_variables": self._get_context_variables()
                        }
                    }
                },
                "validation_rules": {
                    "workflow_level": [
                        "workflow_id must be unique across all workflows",
                        "Must contain at least one task",
                        "All task dependencies must reference valid task_ids",
                        "No circular dependencies allowed",
                        "All required_tools must be available in the system"
                    ],
                    "task_level": [
                        "task_id must be unique within the workflow",
                        "instructions must be comprehensive and actionable",
                        "required_tools must exist in the tool registry",
                        "dependencies must reference valid task_ids in same workflow",
                        "context_requirements must reference valid context variables"
                    ]
                },
                "integration_information": {
                    "dynamic_troubleshoot_agent": {
                        "usage": "Users execute custom workflows via workflow_type parameter",
                        "example": "await agent.execute(ctx=ctx, problem_description='...', workflow_type='your_workflow_id')",
                        "automatic_loading": "Workflows are automatically discovered from contrib/workflows/ directory",
                        "registration": "Workflows are registered with WorkflowManager during system startup"
                    },
                    "execution_flow": [
                        "1. User specifies workflow_type parameter",
                        "2. WorkflowLoader discovers and validates workflow",
                        "3. WorkflowManager registers workflow",
                        "4. Dynamic troubleshoot agent executes workflow",
                        "5. Tasks execute in parallel phases based on dependencies",
                        "6. Results are synthesized and returned to user"
                    ]
                },
                "best_practices": {
                    "workflow_design": [
                        "Focus on single problem domain per workflow",
                        "Design tasks for parallel execution when possible",
                        "Use clear, descriptive names and descriptions",
                        "Include comprehensive documentation"
                    ],
                    "task_instructions": [
                        "Be specific and actionable in instructions",
                        "Include exact Splunk searches when possible",
                        "Use context variables for flexibility",
                        "Provide clear analysis steps and expected outcomes",
                        "Include error handling guidance"
                    ],
                    "performance": [
                        "Use efficient Splunk searches",
                        "Include appropriate time ranges",
                        "Consider system resource impact",
                        "Set reasonable task timeouts"
                    ]
                }
            }
        }

    def _get_schema_definitions(self) -> Dict[str, Any]:
        """Get JSON schema definitions for validation."""
        return {
            "schemas": {
                "WorkflowDefinition": {
                    "type": "object",
                    "required": ["workflow_id", "name", "description", "tasks"],
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "pattern": "^[a-z0-9_]+$",
                            "maxLength": 50,
                            "description": "Unique identifier using snake_case"
                        },
                        "name": {
                            "type": "string",
                            "maxLength": 100,
                            "description": "Human-readable workflow name"
                        },
                        "description": {
                            "type": "string",
                            "maxLength": 1000,
                            "description": "Detailed description of workflow purpose"
                        },
                        "tasks": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 20,
                            "items": {"$ref": "#/definitions/TaskDefinition"},
                            "description": "List of tasks in the workflow"
                        },
                        "default_context": {
                            "type": "object",
                            "description": "Default context variables",
                            "additionalProperties": True
                        }
                    },
                    "additionalProperties": False
                },
                "TaskDefinition": {
                    "type": "object",
                    "required": ["task_id", "name", "description", "instructions"],
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "pattern": "^[a-z0-9_]+$",
                            "maxLength": 50,
                            "description": "Unique task identifier using snake_case"
                        },
                        "name": {
                            "type": "string",
                            "maxLength": 100,
                            "description": "Human-readable task name"
                        },
                        "description": {
                            "type": "string",
                            "maxLength": 200,
                            "description": "Brief task description"
                        },
                        "instructions": {
                            "type": "string",
                            "maxLength": 5000,
                            "description": "Detailed AI agent instructions"
                        },
                        "required_tools": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": list(self._get_available_tools().keys())
                            },
                            "default": [],
                            "description": "List of required Splunk tools"
                        },
                        "dependencies": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": [],
                            "description": "List of task IDs this task depends on"
                        },
                        "context_requirements": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": list(self._get_context_variables().keys())
                            },
                            "default": [],
                            "description": "List of required context variables"
                        }
                    },
                    "additionalProperties": False
                }
            },
            "validation_example": {
                "command": "python -c \"import jsonschema; jsonschema.validate(workflow_data, schema)\"",
                "note": "Use the schemas above to validate your workflow JSON files"
            }
        }

    def _get_quick_reference(self) -> Dict[str, Any]:
        """Get quick reference for experienced contributors."""
        return {
            "quick_reference": {
                "minimal_workflow_structure": {
                    "workflow_id": "your_workflow_id",
                    "name": "Your Workflow Name",
                    "description": "What your workflow does and when to use it",
                    "tasks": [
                        {
                            "task_id": "your_task_id",
                            "name": "Your Task Name",
                            "description": "What this task does",
                            "instructions": "Detailed instructions for AI agent...",
                            "required_tools": ["run_splunk_search"],
                            "dependencies": [],
                            "context_requirements": ["focus_index"]
                        }
                    ]
                },
                "available_tools": list(self._get_available_tools().keys()),
                "context_variables": list(self._get_context_variables().keys()),
                "validation_command": "python contrib/tools/workflows/workflow_builder.py --mode validate --file your_workflow.json",
                "integration_usage": "workflow_type='your_workflow_id' in dynamic_troubleshoot_agent.execute()",
                "file_location": "contrib/workflows/category/your_workflow.json"
            }
        }

    def _get_examples(self) -> Dict[str, Any]:
        """Get example workflow structures and patterns."""
        return {
            "examples": {
                "minimal_example": {
                    "workflow_id": "simple_health_check",
                    "name": "Simple Health Check",
                    "description": "Basic Splunk health verification workflow",
                    "tasks": [
                        {
                            "task_id": "server_health_check",
                            "name": "Server Health Check",
                            "description": "Check basic Splunk server health and connectivity",
                            "instructions": "Execute health check using get_splunk_health tool. Analyze server status, licensing, and basic connectivity. Report any issues found and provide recommendations for resolution.",
                            "required_tools": ["get_splunk_health"],
                            "dependencies": [],
                            "context_requirements": []
                        }
                    ]
                },
                "parallel_tasks_example": {
                    "workflow_id": "parallel_security_analysis",
                    "name": "Parallel Security Analysis",
                    "description": "Security analysis with parallel task execution",
                    "tasks": [
                        {
                            "task_id": "authentication_analysis",
                            "name": "Authentication Analysis",
                            "description": "Analyze authentication patterns and failures",
                            "instructions": "Search for authentication events in {focus_index} from {earliest_time} to {latest_time}. Look for failed logins, unusual patterns, and potential brute force attacks.",
                            "required_tools": ["run_splunk_search"],
                            "dependencies": [],
                            "context_requirements": ["focus_index", "earliest_time", "latest_time"]
                        },
                        {
                            "task_id": "privilege_analysis",
                            "name": "Privilege Analysis",
                            "description": "Analyze privilege escalation attempts",
                            "instructions": "Search for privilege escalation indicators in {focus_index}. Look for sudo usage, admin access, and unusual privilege changes.",
                            "required_tools": ["run_splunk_search"],
                            "dependencies": [],
                            "context_requirements": ["focus_index", "earliest_time", "latest_time"]
                        }
                    ]
                },
                "dependent_tasks_example": {
                    "workflow_id": "sequential_analysis",
                    "name": "Sequential Analysis with Dependencies",
                    "description": "Analysis workflow with task dependencies",
                    "tasks": [
                        {
                            "task_id": "initial_scan",
                            "name": "Initial System Scan",
                            "description": "Perform initial system assessment",
                            "instructions": "Execute comprehensive system scan using available tools. Gather basic system information, user details, and index availability.",
                            "required_tools": ["get_splunk_health", "get_current_user_info", "list_splunk_indexes"],
                            "dependencies": [],
                            "context_requirements": []
                        },
                        {
                            "task_id": "detailed_analysis",
                            "name": "Detailed Analysis",
                            "description": "Perform detailed analysis based on initial scan results",
                            "instructions": "Based on results from {initial_scan}, perform detailed analysis of identified issues. Focus on areas flagged in the initial scan.",
                            "required_tools": ["run_splunk_search"],
                            "dependencies": ["initial_scan"],
                            "context_requirements": ["focus_index", "earliest_time", "latest_time"]
                        }
                    ]
                },
                "custom_context_example": {
                    "workflow_id": "compliance_check",
                    "name": "Compliance Check with Custom Context",
                    "description": "Compliance verification with custom context variables",
                    "tasks": [
                        {
                            "task_id": "sox_compliance_check",
                            "name": "SOX Compliance Check",
                            "description": "Verify SOX compliance requirements",
                            "instructions": "Check SOX compliance for framework {compliance_framework} with risk threshold {risk_threshold}. Verify audit trails, access controls, and data integrity.",
                            "required_tools": ["run_splunk_search"],
                            "dependencies": [],
                            "context_requirements": ["focus_index"]
                        }
                    ],
                    "default_context": {
                        "compliance_framework": "SOX",
                        "risk_threshold": "medium",
                        "audit_retention_days": 2555
                    }
                }
            }
        }

    def _get_available_tools(self) -> Dict[str, str]:
        """Get available Splunk tools with descriptions."""
        return {
            # Search Tools
            "run_splunk_search": "Execute comprehensive Splunk searches with full SPL support",
            "run_oneshot_search": "Execute quick, lightweight searches for immediate results",
            "run_saved_search": "Execute predefined saved searches",
            
            # Metadata Tools
            "list_splunk_indexes": "Get list of available Splunk indexes",
            "list_splunk_sources": "Get list of available data sources",
            "list_splunk_sourcetypes": "Get list of available sourcetypes",
            
            # Administrative Tools
            "get_current_user_info": "Get current user information, roles, and permissions",
            "get_splunk_health": "Check Splunk server health and connectivity status",
            "get_splunk_apps": "List installed Splunk applications",
            
            # Alert Tools
            "get_alert_status": "Check alert configurations and firing status",
            
            # Utility Tools
            "report_specialist_progress": "Report progress during task execution",
        }

    def _get_context_variables(self) -> Dict[str, str]:
        """Get available context variables with descriptions."""
        return {
            # Time Context
            "earliest_time": "Start time for analysis (e.g., '-24h', '2023-01-01T00:00:00')",
            "latest_time": "End time for analysis (e.g., 'now', '-1h', '@d')",
            
            # Focus Context
            "focus_index": "Target index for focused analysis",
            "focus_host": "Target host for focused analysis",
            "focus_sourcetype": "Target sourcetype for focused analysis",
            
            # User Context
            "complexity_level": "Analysis depth level ('basic', 'moderate', 'advanced')",
            
            # Custom Context
            # Note: Custom context variables can be defined in default_context
            "custom_variable_example": "Example of custom context variable from default_context"
        } 