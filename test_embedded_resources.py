#!/usr/bin/env python3
"""
Test script for embedded Splunk documentation resources.

This script tests the embedded documentation resources to ensure they are working correctly.
"""

import asyncio
import sys
import os

# Add the project root to the path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.resources.embedded_splunk_docs import (
    embedded_splunk_docs_registry,
    list_embedded_splunk_docs,
    get_embedded_splunk_doc
)


async def test_embedded_docs():
    """Test the embedded documentation resources."""
    print("🧪 Testing Embedded Splunk Documentation Resources")
    print("=" * 60)
    
    # Test 1: List all embedded docs
    print("\n1. Testing list_embedded_splunk_docs()...")
    try:
        docs = list_embedded_splunk_docs()
        print(f"✅ Found {len(docs)} embedded documentation resources:")
        for doc in docs:
            print(f"   - {doc['name']}: {doc['title']}")
            print(f"     URI: {doc['uri']}")
            print(f"     Description: {doc['description']}")
            print()
    except Exception as e:
        print(f"❌ Error listing embedded docs: {e}")
    
    # Test 2: Test each embedded resource
    print("\n2. Testing individual embedded resources...")
    for name, resource in embedded_splunk_docs_registry.items():
        print(f"\n   Testing {name}...")
        try:
            # Test basic properties
            print(f"     Name: {resource.name}")
            print(f"     URI: {resource.uri}")
            print(f"     Description: {resource.description}")
            print(f"     MIME Type: {resource.mime_type}")
            
            # Test content retrieval
            content = await resource.get_content(None)  # No context needed for embedded
            print(f"     Content length: {len(content)} characters")
            print(f"     Content preview: {content[:100]}...")
            
            print(f"   ✅ {name} - PASSED")
            
        except Exception as e:
            print(f"   ❌ {name} - FAILED: {e}")
    
    # Test 3: Test get_embedded_splunk_doc function
    print("\n3. Testing get_embedded_splunk_doc() function...")
    try:
        # Test by URI
        cheat_sheet_uri = "embedded://splunk/docs/cheat-sheet"
        resource = get_embedded_splunk_doc(cheat_sheet_uri)
        if resource:
            print(f"✅ Found resource by URI: {resource.name}")
        else:
            print(f"❌ Could not find resource by URI: {cheat_sheet_uri}")
            
        # Test by name
        resource = embedded_splunk_docs_registry.get("cheat_sheet")
        if resource:
            print(f"✅ Found resource by name: {resource.name}")
        else:
            print(f"❌ Could not find resource by name: cheat_sheet")
            
    except Exception as e:
        print(f"❌ Error testing get_embedded_splunk_doc: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Embedded documentation resources test completed!")


if __name__ == "__main__":
    asyncio.run(test_embedded_docs())