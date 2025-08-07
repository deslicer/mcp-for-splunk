#!/usr/bin/env python3

try:
    from contrib.workflows.loaders import WorkflowLoader
    print("✅ SUCCESS: Contrib workflow loader imported successfully")
    
    # Test creating a loader instance
    loader = WorkflowLoader()
    workflows = loader.discover_workflows()
    print(f"✅ SUCCESS: Discovered {len(workflows)} workflow files")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
