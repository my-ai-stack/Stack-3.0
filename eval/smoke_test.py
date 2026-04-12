import asyncio
import os
from toolbelt.registry import get_registry

async def test_router_logic():
    reg = get_registry()
    
    print("--- Testing Filesystem Tool (Glob) ---")
    try:
        # We use the registry.call which mimics what the router would do after selection
        res = await reg.call("glob", {"path": "/Users/walidsobhi", "pattern": "*.txt"})
        print(f"Glob Result: {res.success}")
    except Exception as e:
        print(f"Glob Failed: {e}")

    print("\n--- Testing Web Tool (WebSearch) ---")
    try:
        res = await reg.call("WebSearch", {"query": "Anthropic Claude"})
        print(f"WebSearch Result: {res.success}")
    except Exception as e:
        print(f"WebSearch Failed: {e}")

    print("\n--- Testing Specialized Tool (dependency_mapper) ---")
    try:
        # dependency_mapper requires file_path
        res = await reg.call("dependency_mapper", {"file_path": "/Users/walidsobhi/stack-3.0/toolbelt/registry.py"})
        print(f"DependencyMapper Result: {res.success}")
    except Exception as e:
        print(f"DependencyMapper Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_router_logic())
