"""
Ultra-Skill: Automated Dependency Mapping
Analyzes a codebase to map internal and external dependencies.
"""
from __future__ import annotations
from typing import Any, Dict, List
import os
import re
from .ultra_skill import UltraSkill

class DependencyMapper(UltraSkill):
    def __init__(self):
        super().__init__(
            name="dependency_mapper",
            description="Maps all internal and external dependencies of a given file or module by analyzing imports.",
            category="Software Engineering"
        )

    async def execute(self, input_data: Dict[str, Any]) -> Any:
        file_path = input_data.get("file_path")
        if not file_path:
            return {"error": "Missing file_path"}

        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Simple regex for imports (Python)
        imports = re.findall(r'^(?:from\s+([\w\.]+)\s+import\s+.*|import\s+([\w\.]+))', content, re.MULTILINE)

        dependencies = []
        for imp in imports:
            dep = imp[0] if imp[0] else imp[1]
            dependencies.append(dep)

        return {
            "file": file_path,
            "dependencies": list(set(dependencies)),
            "count": len(set(dependencies))
        }
