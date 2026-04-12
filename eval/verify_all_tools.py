
import asyncio
import os
from pathlib import Path
from toolbelt.registry import get_registry

def generate_mock_args(tool):
    """Generate generic mock arguments based on the tool's input schema."""
    schema = tool.input_schema
    if callable(schema):
        schema = schema()

    mock_args = {}
    if not schema or 'properties' not in schema:
        return mock_args

    required = schema.get('required', [])
    properties = schema.get('properties', {})

    for prop_name in required:
        prop_info = properties.get(prop_name, {})
        prop_type = prop_info.get('type', 'string')

        if prop_type == 'string':
            if 'path' in prop_name.lower():
                mock_args[prop_name] = "/tmp/test_file.txt"
            elif 'url' in prop_name.lower():
                mock_args[prop_name] = "https://example.com"
            else:
                mock_args[prop_name] = "mock_string"
        elif prop_type == 'integer':
            mock_args[prop_name] = 1
        elif prop_type == 'number':
            mock_args[prop_name] = 1.0
        elif prop_type == 'boolean':
            mock_args[prop_name] = True
        elif prop_type == 'array':
            mock_args[prop_name] = []
        elif prop_type == 'object':
            mock_args[prop_name] = {}
        else:
            mock_args[prop_name] = "mock_value"

    return mock_args

async def verify_tool(name, args):
    print(f"Testing tool: {name} with args: {args}...", end=" ")
    try:
        registry = get_registry()
        # Now that ToolRegistry.call is async, we await it directly.
        result = await registry.call(name, args)

        if hasattr(result, 'success') and result.success:
            print("✅ SUCCESS")
            return True
        elif isinstance(result, dict) and result.get("success"):
            print("✅ SUCCESS")
            return True
        else:
            error = getattr(result, 'error', str(result)) if hasattr(result, 'error') else result.get('error', 'Unknown error') if isinstance(result, dict) else "Unexpected result format"
            print(f"❌ FAILED: {error}")
            return False
    except Exception as e:
        print(f"💥 EXCEPTION: {str(e)}")
        return False

async def main():
    print("=== Stack 3.0 Comprehensive Tool Verification ===\n")

    # Setup temp environment
    test_dir = Path("tool_test_env")
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "test.txt"
    test_file.write_text("Hello Stack 3.0")

    registry = get_registry()
    all_tool_names = registry.list()

    # Define test cases for core tools to ensure high quality
    test_cases = {
        "file_read": {"path": str(test_file)},
        "file_write": {"path": str(test_dir / "write.txt"), "content": "test content"},
        "file_exists": {"path": str(test_file)},
        "TaskList": {},
        "TaskCreate": {"subject": "Verification Task", "description": "Testing tool", "priority": "low"},
        "glob": {"pattern": "*.txt", "path": str(test_dir)},
        "grep": {"pattern": "Hello", "path": str(test_file)},
        "web_search": {"query": "what is stack 3.0"},
        "web_fetch": {"url": "https://google.com"},
        "brief": {"content": "This is a test for the brief tool."},
        "Config": {"key": "test_key", "value": "test_val"},
        "TodoWrite": {"item": "Test todo item"},
    }

    success_count = 0
    total_tested = 0

    # 1. Test specific critical tools
    print("--- Testing Critical Tools ---")
    for name, args in test_cases.items():
        if name in all_tool_names:
            total_tested += 1
            if await verify_tool(name, args):
                success_count += 1

    # 2. Test a sample of others with mock args to check for crashes
    print("\n--- Testing General Registry Connectivity ---")
    for name in all_tool_names:
        if name not in test_cases:
            total_tested += 1
            tool = registry.get(name)
            args = generate_mock_args(tool)
            if await verify_tool(name, args):
                success_count += 1

    # 3. Verify Hierarchical Router categorization
    print("\n--- Verifying Hierarchical Router Categorization ---")
    try:
        from cognitive_core.router import HierarchicalRouter
        router = HierarchicalRouter()
        for tool_name in all_tool_names:
            category = router.get_category(tool_name)
            if category:
                print(f"Tool {tool_name} is correctly categorized as {category}")
            else:
                print(f"❌ Tool {tool_name} is missing a category in the router")
    except ImportError:
        print("⚠️ HierarchicalRouter not found, skipping categorization check.")

    print(f"\nFinal Result: {success_count}/{total_tested} passed ({(success_count/total_tested)*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())
