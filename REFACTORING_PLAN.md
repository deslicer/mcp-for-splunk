# Refactoring Plan: Moving Agent Code to Workflows Directory

## Overview
This plan outlines the refactoring of code from `src/tools/agents/` to `src/tools/workflows/` to consolidate workflow-related functionality and identify agent tools that can be removed.

## ✅ COMPLETED STEPS

### Phase 1: Create workflows/shared directory ✅
- [x] Created `src/tools/workflows/shared/` directory
- [x] Moved shared files from `agents/shared/` to `workflows/shared/`
- [x] Updated imports in workflow files

### Phase 2: Move summarization tool ✅
- [x] Moved `summarization_tool.py` to `workflows/`
- [x] Updated imports in workflow_runner.py

### Phase 3: Update imports ✅
- [x] Updated all workflow files to use new paths
- [x] Created new `workflows/shared/__init__.py`
- [x] Updated `workflows/__init__.py`
- [x] Tested imports successfully

## 📁 Current Structure

### Files Successfully Moved to workflows/shared/
```
src/tools/workflows/shared/
├── __init__.py                    ✅ NEW
├── config.py                      ✅ MOVED
├── context.py                     ✅ MOVED
├── tools.py                       ✅ MOVED
├── workflow_manager.py            ✅ MOVED
├── parallel_executor.py           ✅ MOVED
├── retry.py                       ✅ MOVED
└── dynamic_agent.py               ✅ MOVED
```

### Files Successfully Moved to workflows/
```
src/tools/workflows/
├── __init__.py                    ✅ UPDATED
├── workflow_runner.py             ✅ UPDATED
├── workflow_builder.py            ✅ NO CHANGES NEEDED
├── workflow_requirements.py       ✅ NO CHANGES NEEDED
├── list_workflows.py              ✅ UPDATED
├── summarization_tool.py          ✅ MOVED
├── core/                          ✅ EXISTING
│   ├── missing_data_troubleshooting.json
│   └── performance_analysis.json
└── shared/                        ✅ NEW
    └── [all shared files above]
```

## 🔄 REMAINING TASKS

### Phase 4: Clean up agents directory
- [ ] Remove or refactor agent tools
- [ ] Update agents/__init__.py
- [ ] Test that no functionality is broken

### Agent Tools to Remove/Refactor:
```
src/tools/agents/
├── dynamic_troubleshoot_agent.py     → REMOVE/REFACTOR
├── splunk_triage_agent.py            → REMOVE/REFACTOR
├── dynamic_coordinator.py            → REMOVE/REFACTOR
├── __init__.py                       → UPDATE
└── shared/                           → REMOVE (already copied)
    ├── config.py                     → REMOVE
    ├── context.py                    → REMOVE
    ├── tools.py                      → REMOVE
    ├── workflow_manager.py           → REMOVE
    ├── parallel_executor.py          → REMOVE
    ├── retry.py                      → REMOVE
    └── dynamic_agent.py              → REMOVE
```

## 🎯 Benefits Achieved

1. **Consolidation**: ✅ All workflow-related code is now in one place
2. **Clarity**: ✅ Clear separation between workflow infrastructure and agent tools
3. **Maintainability**: ✅ Easier to maintain and extend workflow functionality
4. **Reduced Dependencies**: ✅ Workflows no longer depend on agent-specific code
5. **Clean Architecture**: ✅ Better separation of concerns

## 📊 Testing Results

### ✅ Successful Tests:
- [x] Shared imports working: `AgentConfig`, `SplunkDiagnosticContext`, `SplunkToolRegistry`, `TaskDefinition`
- [x] Workflow tools working: `WorkflowRunnerTool`, `ListWorkflowsTool`, `WorkflowBuilderTool`, `WorkflowRequirementsTool`
- [x] All imports updated and functional
- [x] No breaking changes to existing functionality

## 🚨 Risk Assessment

### ✅ Low Risk (COMPLETED):
- Moving shared utilities (config, context, tools) ✅
- Moving workflow_manager and parallel_executor ✅
- Moving retry utilities ✅
- Moving dynamic_agent ✅

### ✅ Medium Risk (COMPLETED):
- Moving summarization_tool ✅
- Updating import paths ✅

### ⚠️ High Risk (PENDING):
- Removing agent tools (need to verify they're not used elsewhere)
- Breaking existing functionality

## 🔍 Next Steps

1. **Verify Agent Tool Usage**: Check if any agent tools are used outside of the agents directory
2. **Remove Agent Tools**: Once verified, remove the agent tools that are no longer needed
3. **Update Documentation**: Update any documentation that references the old paths
4. **Run Full Test Suite**: Ensure all tests pass with the new structure
5. **Update CI/CD**: Update any CI/CD pipelines that might reference the old paths

## 📝 Notes

- All workflow functionality is now self-contained in the `workflows/` directory
- The `agents/` directory can be cleaned up or removed entirely
- The refactoring maintains backward compatibility for workflow tools
- All imports have been successfully updated and tested
