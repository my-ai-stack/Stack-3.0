"""
Base class for Ultra-Skills.
Ultra-Skills are high-level, complex tools that combine multiple primitive operations
to solve advanced software engineering tasks.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from .tools.base import BaseTool

class UltraSkill(BaseTool):
    """
    Abstract base class for Ultra-Skills.
    """
    def __init__(self, name: str, description: str, category: str = "Ultra-Skill"):
        self.name = name
        self.description = description
        self.category = category

    async def execute(self, input_data: Dict[str, Any]) -> Any:
        raise NotImplementedError("UltraSkills must implement execute()")

    async def call(self, input_data: Dict[str, Any]) -> Any:
        return await self.execute(input_data)
