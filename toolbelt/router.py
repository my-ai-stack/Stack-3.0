"""Hierarchical Tool Router for Stack 3.0 tools."""

from __future__ import annotations

from typing import Any
from .registry import get_registry, ToolRegistry

class ToolRouter:
    """
    Implements a two-stage tool selection process to prevent prompt saturation.

    Stage 1: Agent selects a tool category from the list of available categories.
    Stage 2: The framework provides the specific tools available within that category.
    """

    def __init__(self, registry: ToolRegistry | None = None):
        self.registry = registry or get_registry()
        self._fast_path_cache: dict[str, str] = {}

    def get_categories(self) -> list[str]:
        """Retrieve the list of available tool categories for Stage 1."""
        return self.registry.list_categories()

    def get_tools_for_category(self, category: str) -> dict[str, dict[str, Any]]:
        """Retrieve tools for a specific category for Stage 2."""
        return self.registry.list_tools_in_category(category)

    def route_query(self, query: str) -> dict[str, dict[str, Any]]:
        """
        Routes a natural language query to the most relevant tool category.
        1. Checks fast-path cache.
        2. If miss, identifies category based on keywords.
        3. Returns tools in that category.
        """
        # 1. Fast-Path Cache Check
        if query in self._fast_path_cache:
            category = self._fast_path_cache[query]
            return self.get_tools_for_category(category)

        # 2. Category Identification (Basic Keyword Map)
        categories = self.get_categories()

        # Basic mapping for simulation
        keyword_map = {
            "file": "General",
            "search": "General",
            "web": "General",
            "task": "General",
            "team": "General",
            "dependency": "General",
            "refactor": "General",
            "impact": "General",
        }

        selected_category = "General"
        query_lower = query.lower()
        for keyword, category in keyword_map.items():
            if keyword in query_lower:
                selected_category = category
                break

        # If the selected category isn't actually in the registry, fallback to first available or General
        if selected_category not in categories:
            selected_category = categories[0] if categories else "General"

        # Update Cache
        self._fast_path_cache[query] = selected_category

        return self.get_tools_for_category(selected_category)

    def route_to_category(self, category_name: str) -> dict[str, dict[str, Any]]:
        """
        Helper method to route to a category and return its tools.
        If the category is not found, it returns an empty dict or a warning.
        """
        return self.get_tools_for_category(category_name)

    def is_tool_noisy(self, tool_name: str) -> bool:
        """
        Check if a tool is marked as 'noisy' and should be routed through a fork.
        """
        tool = self.registry.get(tool_name)
        if tool and hasattr(tool, 'is_noisy'):
            return tool.is_noisy
        return False

    def spawn_specialized_worker(self, domain: str) -> str:
        """
        Spawns a specialized worker based on the domain (category).
        This allows the Coordinator to request a worker tailored to a specific toolset.
        """
        # In a real system, this would interface with an AgentFactory
        # For now, it returns a role string that the Coordinator can use
        if domain in self.get_categories():
            return f"worker_{domain}"
        return "worker_general"


# Global router instance
tool_router = ToolRouter()
