#!/usr/bin/env python3

import asyncio
from src.tools.workflows.list_workflows import ListWorkflowsTool

class MockContext:
    async def info(self, msg):
        print(f"INFO: {msg}")
    async def error(self, msg):
        print(f"ERROR: {msg}")

async def test_contrib_count():
    tool = ListWorkflowsTool('test', 'test')
    ctx = MockContext()
    
    print("Testing contrib workflow count...")
    print("=" * 50)
    
    # Test contrib workflows only
    result = await tool.execute(ctx, format_type='summary', include_core=False, include_contrib=True)
    
    if result.get('status') == 'success':
        total_workflows = result.get('total_workflows', 0)
        workflows = result.get('workflows', {})
        
        print(f"✅ Contrib workflows found: {total_workflows}")
        print("\nContrib workflow details:")
        for workflow_id, workflow in workflows.items():
            print(f"  - {workflow_id}: {workflow['name']} ({workflow['category']})")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(test_contrib_count())
