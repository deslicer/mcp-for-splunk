"""
Workflow Builder Tool Demonstration.

This example demonstrates how to use the WorkflowBuilderTool to create, edit,
validate, and process workflows with various modes and configurations.
"""

import asyncio
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Mock FastMCP Context for demonstration
class MockContext:
    """Mock context for demonstration purposes."""

    def __init__(self):
        self.info_messages = []
        self.error_messages = []

    async def info(self, message: str):
        """Mock info message."""
        self.info_messages.append(message)
        logger.info(f"INFO: {message}")

    async def error(self, message: str):
        """Mock error message."""
        self.error_messages.append(message)
        logger.error(f"ERROR: {message}")


async def demonstrate_workflow_builder():
    """Demonstrate the WorkflowBuilderTool capabilities."""

    print("=" * 80)
    print("WORKFLOW BUILDER TOOL DEMONSTRATION")
    print("=" * 80)

    try:
        # Import the workflow builder tool
        from src.tools.workflows.workflow_builder import WorkflowBuilderTool

        print("✅ WorkflowBuilderTool imported successfully")

        # Create the tool instance
        print("\n🔧 Initializing WorkflowBuilderTool...")
        workflow_builder = WorkflowBuilderTool("workflow_builder", "workflows")
        print("✅ WorkflowBuilderTool initialized")

        # Create mock context
        ctx = MockContext()

        # Example 1: Process a finished workflow as a dict object
        print("\n" + "=" * 60)
        print("EXAMPLE 1: Process Finished Workflow (Dict Object)")
        print("=" * 60)

        finished_workflow_dict = {
            "workflow_id": "custom_security_analysis",
            "name": "Custom Security Analysis",
            "description": "A comprehensive security analysis workflow for detecting threats and vulnerabilities",
            "tasks": [
                {
                    "task_id": "authentication_analysis",
                    "name": "Authentication Analysis",
                    "description": "Analyze authentication patterns and failures",
                    "instructions": """
You are analyzing authentication events for security threats.

**Context:** Analyzing authentication in index {focus_index} from {earliest_time} to {latest_time}

**Analysis Steps:**
1. Search for failed authentication attempts
2. Identify patterns of brute force attacks
3. Check for successful logins after failures
4. Analyze geographic and temporal patterns

**Searches to Execute:**
- index={focus_index} sourcetype=auth* action=failure | stats count by src_ip, user | sort -count
- index={focus_index} sourcetype=auth* | timechart count by action

**What to Look For:**
- High numbers of failed attempts from single IP
- Unusual login patterns outside business hours
- Geographic anomalies in login sources

**Output:** Return DiagnosticResult with authentication analysis and security recommendations.
                    """,
                    "required_tools": ["run_splunk_search"],
                    "dependencies": [],
                    "context_requirements": ["focus_index", "earliest_time", "latest_time"],
                },
                {
                    "task_id": "privilege_escalation_check",
                    "name": "Privilege Escalation Check",
                    "description": "Check for privilege escalation attempts",
                    "instructions": """
You are checking for privilege escalation attempts.

**Context:** Analyzing privilege changes in index {focus_index} from {earliest_time} to {latest_time}

**Analysis Steps:**
1. Search for sudo and administrative command usage
2. Check for role changes and permission modifications
3. Identify unusual administrative activity
4. Analyze privilege usage patterns

**Searches to Execute:**
- index={focus_index} sourcetype=linux_secure "sudo" | stats count by user, command
- index={focus_index} sourcetype=wineventlog EventCode=4672 | stats count by user

**What to Look For:**
- Unusual sudo command usage
- Administrative commands from non-admin users
- Privilege modification events

**Output:** Return DiagnosticResult with privilege escalation findings.
                    """,
                    "required_tools": ["run_splunk_search"],
                    "dependencies": [],
                    "context_requirements": ["focus_index", "earliest_time", "latest_time"],
                },
            ],
            "default_context": {"security_threshold": "medium", "alert_threshold": 100},
        }

        try:
            result1 = await workflow_builder.execute(
                ctx=ctx, mode="process", workflow_data=finished_workflow_dict
            )

            print(f"✅ Processing Status: {result1['status']}")
            print(f"🔍 Validation Passed: {result1['validation']['valid']}")
            print(f"🎯 Integration Ready: {result1['integration_ready']}")
            print(
                f"🏃 Compatible with Runner: {result1['processing_metadata']['compatible_with_runner']}"
            )
            print(f"📋 Total Tasks: {result1['validation']['summary']['total_tasks']}")
            print(
                f"🔧 Required Tools: {', '.join(result1['validation']['summary']['required_tools'])}"
            )
            print(
                f"📝 Context Variables: {', '.join(result1['validation']['summary']['context_variables'])}"
            )

            if result1["integration_ready"]:
                print("\n💡 Usage Instructions:")
                print(f"   - Workflow Runner: {result1['usage_instructions']['workflow_runner']}")
                print(
                    f"   - Dynamic Troubleshoot: {result1['usage_instructions']['dynamic_troubleshoot']}"
                )
                print(f"   - File Save: {result1['usage_instructions']['file_save']}")

        except Exception as e:
            print(f"❌ Example 1 failed: {e}")

        # Example 2: Process a finished workflow as a JSON string
        print("\n" + "=" * 60)
        print("EXAMPLE 2: Process Finished Workflow (JSON String)")
        print("=" * 60)

        finished_workflow_json = json.dumps(
            {
                "workflow_id": "data_quality_assessment",
                "name": "Data Quality Assessment",
                "description": "Comprehensive data quality and integrity assessment workflow",
                "tasks": [
                    {
                        "task_id": "data_availability_check",
                        "name": "Data Availability Check",
                        "description": "Check data availability and ingestion patterns",
                        "instructions": """
You are checking data availability and ingestion.

**Context:** Analyzing data in index {focus_index} from {earliest_time} to {latest_time}

**Analysis Steps:**
1. Check data volume and distribution
2. Analyze ingestion patterns over time
3. Identify data gaps or delays
4. Verify expected data sources

**Searches to Execute:**
- index={focus_index} | stats count by sourcetype | sort -count
- index={focus_index} | timechart count span=1h
- index={focus_index} | stats latest(_time) as latest_data by sourcetype

**What to Look For:**
- Missing or delayed data
- Unexpected changes in data volume
- Data source availability issues

**Output:** Return DiagnosticResult with data availability analysis.
                    """,
                        "required_tools": ["run_splunk_search"],
                        "dependencies": [],
                        "context_requirements": ["focus_index", "earliest_time", "latest_time"],
                    },
                    {
                        "task_id": "data_integrity_check",
                        "name": "Data Integrity Check",
                        "description": "Verify data integrity and consistency",
                        "instructions": """
You are verifying data integrity and consistency.

**Context:** Analyzing data integrity in index {focus_index}

**Analysis Steps:**
1. Check for duplicate events
2. Verify timestamp consistency
3. Analyze field extraction accuracy
4. Check for data corruption indicators

**Searches to Execute:**
- index={focus_index} | stats dc(_raw) as unique_events, count as total_events
- index={focus_index} | eval time_diff=abs(_time-_indextime) | stats avg(time_diff) as avg_delay

**What to Look For:**
- High duplicate event ratios
- Significant timestamp delays
- Field extraction failures

**Output:** Return DiagnosticResult with data integrity findings.
                    """,
                        "required_tools": ["run_splunk_search"],
                        "dependencies": ["data_availability_check"],
                        "context_requirements": ["focus_index"],
                    },
                ],
            }
        )

        try:
            result2 = await workflow_builder.execute(
                ctx=ctx, mode="process", workflow_data=finished_workflow_json
            )

            print(f"✅ Processing Status: {result2['status']}")
            print(f"🔍 Validation Passed: {result2['validation']['valid']}")
            print(f"🎯 Integration Ready: {result2['integration_ready']}")
            print(f"🔗 Has Dependencies: {result2['validation']['summary']['has_dependencies']}")
            print(f"📋 Total Tasks: {result2['validation']['summary']['total_tasks']}")

        except Exception as e:
            print(f"❌ Example 2 failed: {e}")

        # Example 3: Process an invalid workflow to show validation errors
        print("\n" + "=" * 60)
        print("EXAMPLE 3: Process Invalid Workflow (Validation Errors)")
        print("=" * 60)

        invalid_workflow = {
            "workflow_id": "INVALID-ID-FORMAT",  # Invalid format (uppercase, hyphens)
            "name": "Test Workflow",
            # Missing required description field
            "tasks": [
                {
                    "task_id": "invalid_task",
                    "name": "Invalid Task",
                    # Missing required description and instructions
                    "required_tools": ["non_existent_tool"],  # Invalid tool
                    "context_requirements": ["invalid_context_var"],  # Invalid context variable
                }
            ],
        }

        try:
            result3 = await workflow_builder.execute(
                ctx=ctx, mode="process", workflow_data=invalid_workflow
            )

            print(f"✅ Processing Status: {result3['status']}")
            print(f"🔍 Validation Passed: {result3['validation']['valid']}")
            print(f"🎯 Integration Ready: {result3['integration_ready']}")
            print(f"❌ Validation Errors: {len(result3['validation']['errors'])}")

            if result3["validation"]["errors"]:
                print("\n🚨 Validation Errors Found:")
                for error in result3["validation"]["errors"][:5]:  # Show first 5 errors
                    print(f"   - {error}")

            if result3["validation"]["warnings"]:
                print(f"\n⚠️  Validation Warnings: {len(result3['validation']['warnings'])}")
                for warning in result3["validation"]["warnings"][:3]:  # Show first 3 warnings
                    print(f"   - {warning}")

            if result3["validation"]["suggestions"]:
                print("\n💡 Fix Suggestions:")
                for suggestion in result3["validation"]["suggestions"][
                    :3
                ]:  # Show first 3 suggestions
                    print(f"   - {suggestion}")

        except Exception as e:
            print(f"❌ Example 3 failed: {e}")

        # Example 4: Use other modes (template, validate, create)
        print("\n" + "=" * 60)
        print("EXAMPLE 4: Other Workflow Builder Modes")
        print("=" * 60)

        # Template generation
        try:
            print("\n🎨 Generating Security Template:")
            template_result = await workflow_builder.execute(
                ctx=ctx, mode="template", template_type="security"
            )

            if template_result["status"] == "success":
                template = template_result["template"]
                print(f"   ✅ Template: {template['name']}")
                print(f"   📋 Tasks: {len(template['tasks'])}")
                print(f"   🔧 Template Type: {template_result['template_type']}")

        except Exception as e:
            print(f"   ❌ Template generation failed: {e}")

        # Validation mode
        try:
            print("\n🔍 Validating Workflow Data:")
            validation_result = await workflow_builder.execute(
                ctx=ctx,
                mode="validate",
                workflow_data=finished_workflow_dict,  # Use the valid workflow from Example 1
            )

            if validation_result["status"] == "success":
                print(f"   ✅ Validation: {validation_result['valid']}")
                print(
                    f"   📊 Summary: {validation_result['summary']['total_tasks']} tasks, {len(validation_result['summary']['required_tools'])} tools"
                )

        except Exception as e:
            print(f"   ❌ Validation failed: {e}")

        # Interactive creation mode
        try:
            print("\n🛠️  Interactive Workflow Creation:")
            create_result = await workflow_builder.execute(ctx=ctx, mode="create")

            if create_result["status"] == "success":
                workflow = create_result["workflow"]
                print(f"   ✅ Created: {workflow['name']}")
                print(f"   📋 Tasks: {len(workflow['tasks'])}")
                print(f"   🔍 Validation: {create_result['validation']['valid']}")

        except Exception as e:
            print(f"   ❌ Interactive creation failed: {e}")

        print("\n" + "=" * 80)
        print("WORKFLOW BUILDER DEMONSTRATION COMPLETED")
        print("=" * 80)

        # Summary
        print("\n📋 SUMMARY:")
        print(f"   - Total info messages: {len(ctx.info_messages)}")
        print(f"   - Total error messages: {len(ctx.error_messages)}")

    except ImportError as e:
        print(f"❌ Failed to import WorkflowBuilderTool: {e}")
        print("   Make sure the tool is properly installed and dependencies are met.")
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        import traceback

        traceback.print_exc()


async def demonstrate_workflow_requirements():
    """Demonstrate the WorkflowRequirementsTool for understanding workflow structure."""

    print("\n" + "=" * 80)
    print("WORKFLOW REQUIREMENTS DEMONSTRATION")
    print("=" * 80)

    try:
        from src.tools.workflows.workflow_requirements import WorkflowRequirementsTool

        workflow_requirements = WorkflowRequirementsTool("workflow_requirements", "workflows")
        ctx = MockContext()

        # Get quick reference
        print("\n📚 Getting Quick Reference:")
        quick_ref = await workflow_requirements.execute(ctx=ctx, format_type="quick")

        if quick_ref["status"] == "success":
            ref = quick_ref["quick_reference"]
            print(f"   ✅ Available Tools: {len(ref['available_tools'])}")
            print(f"   📋 Context Variables: {len(ref['context_variables'])}")
            print(f"   🔧 Integration Usage: {ref['integration_usage']}")

        # Get schema definitions
        print("\n🏗️  Getting Schema Definitions:")
        schema_result = await workflow_requirements.execute(ctx=ctx, format_type="schema")

        if schema_result["status"] == "success":
            schemas = schema_result["schemas"]
            print(
                f"   ✅ WorkflowDefinition Schema: {len(schemas['WorkflowDefinition']['properties'])} properties"
            )
            print(
                f"   📋 TaskDefinition Schema: {len(schemas['TaskDefinition']['properties'])} properties"
            )

        # Get examples
        print("\n📖 Getting Workflow Examples:")
        examples_result = await workflow_requirements.execute(ctx=ctx, format_type="examples")

        if examples_result["status"] == "success":
            examples = examples_result["examples"]
            print(f"   ✅ Available Examples: {len(examples)}")
            for example_name in examples.keys():
                print(f"      - {example_name}")

    except Exception as e:
        print(f"❌ Workflow requirements demonstration failed: {e}")


def print_workflow_integration_examples():
    """Print examples of how to integrate processed workflows."""

    print("\n" + "=" * 80)
    print("WORKFLOW INTEGRATION EXAMPLES")
    print("=" * 80)

    examples = [
        {
            "title": "Process and Validate a Custom Workflow",
            "code": """
# Process a finished workflow definition
workflow_data = {
    "workflow_id": "my_custom_workflow",
    "name": "My Custom Workflow",
    "description": "Custom troubleshooting workflow",
    "tasks": [
        {
            "task_id": "health_check",
            "name": "Health Check",
            "description": "Check system health",
            "instructions": "Perform health check using get_splunk_health tool",
            "required_tools": ["get_splunk_health"],
            "dependencies": [],
            "context_requirements": []
        }
    ]
}

result = await workflow_builder.execute(
    ctx=ctx,
    mode="process",
    workflow_data=workflow_data
)

if result['integration_ready']:
    print(f"Workflow ready for execution: {result['workflow']['workflow_id']}")
            """,
            "description": "Process and validate a complete workflow definition",
        },
        {
            "title": "Use with Workflow Runner",
            "code": """
# After processing with workflow builder, use with workflow runner
from src.tools.workflows.workflow_runner import WorkflowRunnerTool

workflow_runner = WorkflowRunnerTool("workflow_runner", "workflows")

# Execute the processed workflow
result = await workflow_runner.execute(
    ctx=ctx,
    workflow_id="my_custom_workflow",  # Use the workflow_id from processed workflow
    problem_description="Test execution",
    complexity_level="moderate"
)
            """,
            "description": "Execute a processed workflow using the workflow runner",
        },
        {
            "title": "Validate Multiple Tool Categories",
            "code": """
# Create workflow using different tool categories
workflow_with_tools = {
    "workflow_id": "comprehensive_analysis",
    "name": "Comprehensive Analysis",
    "description": "Multi-tool analysis workflow",
    "tasks": [
        {
            "task_id": "search_analysis",
            "name": "Search Analysis",
            "description": "Perform search analysis",
            "instructions": "Execute searches and analyze results",
            "required_tools": [
                "run_splunk_search",      # Search tools
                "run_oneshot_search"
            ],
            "dependencies": [],
            "context_requirements": ["earliest_time", "latest_time"]
        },
        {
            "task_id": "admin_check",
            "name": "Administrative Check",
            "description": "Check administrative settings",
            "instructions": "Verify admin settings and configurations",
            "required_tools": [
                "get_current_user_info",  # Admin tools
                "get_configurations",
                "get_splunk_health"
            ],
            "dependencies": [],
            "context_requirements": []
        },
        {
            "task_id": "kvstore_analysis",
            "name": "KV Store Analysis",
            "description": "Analyze KV Store data",
            "instructions": "Check KV Store collections and data",
            "required_tools": [
                "list_kvstore_collections",  # KV Store tools
                "get_kvstore_data"
            ],
            "dependencies": ["admin_check"],
            "context_requirements": []
        }
    ]
}

# Process and validate
result = await workflow_builder.execute(
    ctx=ctx,
    mode="process",
    workflow_data=workflow_with_tools
)
            """,
            "description": "Create workflows using multiple tool categories",
        },
    ]

    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['title']}")
        print(f"   {example['description']}")
        print(f"   ```python{example['code']}   ```")


if __name__ == "__main__":
    """Main demonstration runner."""

    print("🚀 Starting Workflow Builder Tool Demonstration")

    # Run the main demonstration
    asyncio.run(demonstrate_workflow_builder())

    # Run workflow requirements demonstration
    asyncio.run(demonstrate_workflow_requirements())

    # Print integration examples
    print_workflow_integration_examples()

    print("\n✅ Demonstration completed!")
    print("\n💡 Key Features Demonstrated:")
    print("   ✅ Process finished workflows as dict objects")
    print("   ✅ Process finished workflows as JSON strings")
    print("   ✅ Comprehensive validation with error reporting")
    print("   ✅ Integration readiness assessment")
    print("   ✅ Compatibility with workflow runner")
    print("   ✅ Template generation for different workflow types")
    print("   ✅ Multiple validation modes and error handling")
    print("\n🔧 To use the WorkflowBuilderTool in your own code:")
    print("   1. Import: from src.tools.workflows.workflow_builder import WorkflowBuilderTool")
    print("   2. Initialize: tool = WorkflowBuilderTool('workflow_builder', 'workflows')")
    print(
        "   3. Process: result = await tool.execute(ctx=context, mode='process', workflow_data=your_workflow)"
    )
    print("   4. Check result['integration_ready'] for execution readiness")
