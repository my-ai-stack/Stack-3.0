"""Tool registry for Stack 3.0 tools."""

from __future__ import annotations

from typing import Any

from .tools.base import BaseTool


class ToolRegistry:
    """Singleton registry mapping tool names to tool instances and categories."""

    _instance: ToolRegistry | None = None
    _tools: dict[str, BaseTool] = {}
    _categories: dict[str, set[str]] = {}

    def __new__(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._tools = {}
            cls._categories = {}
            cls._instance.discover_tools()
        return cls._instance

    def discover_tools(self) -> None:
        """Scan the tools directory and automatically register all BaseTool subclasses."""
        import os
        import importlib
        import inspect
        from pathlib import Path

        tools_dir = Path(__file__).parent / "tools"
        if not tools_dir.exists() or not tools_dir.is_dir():
            return

        for file in tools_dir.glob("*.py"):
            if file.name == "base.py" or file.name.startswith("__"):
                continue

            module_name = f"{__package__}.tools.{file.stem}"
            try:
                module = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseTool) and obj is not BaseTool:
                        try:
                            self.register(obj())
                        except Exception as e:
                            print(f"Failed to instantiate tool {name} in {module_name}: {e}")
            except Exception as e:
                print(f"Failed to import module {module_name}: {e}")


    def register(self, tool: BaseTool) -> None:
        """Register a tool instance by name and category."""
        if not tool.name:
            raise ValueError("Tool must have a non-empty name")
        self._tools[tool.name] = tool

        category = tool.category or "General"
        if category not in self._categories:
            self._categories[category] = set()
        self._categories[category].add(tool.name)

    def get(self, name: str) -> BaseTool | None:
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def list(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def list_categories(self) -> list[str]:
        """List all registered tool categories."""
        return list(self._categories.keys())

    def list_tools_in_category(self, category: str) -> dict[str, dict[str, Any]]:
        """List all registered tools within a specific category.

        Returns a dict mapping tool name to info dict with keys:
        - name: str
        - description: str
        - input_schema: dict
        """
        tool_names = self._categories.get(category, set())
        result = {}
        for name in tool_names:
            tool = self._tools[name]
            schema = tool.input_schema
            if callable(schema):
                schema = schema()
            result[name] = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": schema,
            }
        return result

    def list_tools(self) -> dict[str, dict[str, Any]]:
        """List all registered tools with their info.

        Returns a dict mapping tool name to info dict with keys:
        - name: str
        - description: str
        - input_schema: dict
        """
        # Optimization: Use a cached version if the registry hasn't changed
        # For now, we'll optimize the loop to avoid repeated callable checks if possible
        result = {}
        for name, tool in self._tools.items():
            schema = tool.input_schema
            if callable(schema):
                schema = schema()
            result[name] = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": schema,
            }
        return result

    async def call(self, name: str, input_data: dict[str, Any]) -> Any:
        """Convenience: get tool and call it in one step."""
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Tool not found: {name}")

        # We keep this as a raw call. Routing logic resides in ToolRouter or Orchestration.
        return await tool.call(input_data)

    def unregister(self, name: str) -> bool:
        """Remove a tool from the registry. Returns True if it existed."""
        if name in self._tools:
            tool = self._tools[name]
            category = tool.category or "General"
            if category in self._categories:
                self._categories[category].discard(name)
                if not self._categories[category]:
                    del self._categories[category]
            del self._tools[name]
            return True
        return False


def get_registry() -> ToolRegistry:
    """Get the global ToolRegistry instance."""
    return ToolRegistry()

# Global registry instance
tool_registry = ToolRegistry()
