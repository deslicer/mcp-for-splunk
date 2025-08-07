# MCP Server for Splunk: Workflow Improvement Plan

## Overview
This plan outlines improvements to the workflow system, focusing on consistency, validation, testing, error handling, and performance. Priorities are based on impact and dependencies. Track status here and update as we progress.

## Phase 1: Migrate All Workflows to JSON Format (Priority: High)
- **Status**: DONE
- **Rationale**: Standardize all workflows as JSON for simplicity, hot-reloading, and consistency. Core workflows remain separate from contrib.
- **Steps**:
  1. ✅ Create `src/tools/workflows/core/` dir for core JSON files (e.g., `missing_data_troubleshooting.json`, `performance_analysis.json`)
  2. ✅ Extract workflow definitions from `workflow_manager.py` to JSON format
  3. ✅ Update `contrib/workflows/loaders.py` to scan both `contrib/workflows/` and `src/tools/workflows/core/`
  4. ✅ Update `workflow_manager.py` to load from JSON instead of hardcoded methods
  5. ✅ Test core workflow loading and execution

## Phase 2: Enhance Workflow Validation (Priority: High)
- **Status**: DONE
- **Rationale**: Improve validation to catch issues early and provide better error messages.
- **Steps**:
  1. ✅ Implement dynamic context validation (include common vars + default_context)
  2. ✅ Add instruction alignment checks (regex scan for {var} and tool mentions)
  3. ✅ Add performance limits check (warn if >20 tasks)
  4. ✅ Add suggestions to validation_result
  5. ✅ Add basic security scan (warn on dangerous keywords)
  6. ✅ Create comprehensive unit tests for validation

## Phase 3: Improve Workflow Runner with Progress Reporting (Priority: High)
- **Status**: DONE
- **Rationale**: Long-running workflows need progress reporting to avoid timeouts.
- **Steps**:
  1. ✅ Add `ctx.report_progress()` calls at key points (0%, 5%, 10%, 15%, 50%, 70%, 85%, 100%)
  2. ✅ Ensure reports every <60s during long operations
  3. ✅ Add progress reporting tests
  4. ✅ Update documentation with progress reporting guide

## Phase 4: Improve Error Handling and Logging (Priority: Medium)
- **Status**: DONE
- **Rationale**: Better error handling and logging for debugging and user experience.
- **Steps**:
  1. ✅ Add try-except blocks in key areas
  2. ✅ Implement structured error responses
  3. ✅ Add retry logic for transient errors
  4. ✅ Improve logging with more info levels
  5. ✅ Add error handling tests

## Phase 5: Documentation and Examples (Priority: Medium)
- **Status**: DONE
- **Rationale**: Comprehensive documentation and examples for users.
- **Steps**:
  1. ✅ Create workflow runner guide
  2. ✅ Update README with workflow information
  3. ✅ Add usage examples and best practices
  4. ✅ Document progress reporting features

## Phase 6: Dynamic Tool Discovery (Priority: High) - **NEW**
- **Status**: DONE
- **Rationale**: Ensure all workflow tools use dynamic tool discovery instead of static lists.
- **Steps**:
  1. ✅ Update `workflow_builder.py` to use `tool_registry.list_tools()` dynamically
  2. ✅ Update `workflow_requirements.py` to use `tool_registry.list_tools()` dynamically
  3. ✅ Update `contrib/workflows/loaders.py` to call `discover_tools()` if needed
  4. ✅ Add proper error handling and fallback to static lists
  5. ✅ Test dynamic tool discovery across all components
  6. ✅ Ensure consistent tool lists across all workflow tools

## Phase 7: Testing and Validation (Priority: High)
- **Status**: TODO
- **Rationale**: Comprehensive testing ensures reliability and catches regressions.
- **Steps**:
  1. Create FastMCP client tests for workflow execution
  2. Add integration tests for workflow validation
  3. Test progress reporting with long-running workflows
  4. Test error handling scenarios
  5. Test dynamic tool discovery
  6. Add performance benchmarks

## Phase 8: Performance Optimization (Priority: Medium)
- **Status**: TODO
- **Rationale**: Optimize workflow execution for better performance.
- **Steps**:
  1. Profile workflow execution performance
  2. Optimize parallel execution
  3. Implement caching for frequently used workflows
  4. Add performance monitoring
  5. Optimize tool discovery and loading

## Phase 9: Advanced Features (Priority: Low)
- **Status**: TODO
- **Rationale**: Advanced features for power users.
- **Steps**:
  1. Add workflow versioning
  2. Implement workflow templates
  3. Add workflow composition
  4. Add workflow scheduling
  5. Add workflow monitoring and alerting

## Notes
- All phases are designed to be backward compatible
- Testing is integrated throughout all phases
- Documentation is updated as features are implemented
- Progress reporting is critical for long-running workflows (>60s)
- Dynamic tool discovery ensures consistency across all workflow tools
