"""
Ultra-Skill: Impact Analysis
Predicts the ripple effect of changing a specific entity or function.
"""
from __future__ import annotations
from typing import Any, Dict, List
import os
from .ultra_skill import UltraSkill
from .ultra_dependency_mapper import DependencyMapper

class ImpactAnalyzer(UltraSkill):
    def __init__(self):
        super().__init__(
            name="impact_analyzer",
            description="Analyzes the impact of changing a specific file or function by finding all its dependents in the codebase.",
            category="Software Engineering"
        )
        self.mapper = DependencyMapper()

    async def execute(self, input_data: Dict[str, Any]) -> Any:
        target_file = input_data.get("file_path")
        root_dir = input_data.get("root_dir", "/Users/walidsobhi/stack-3.0")

        if not target_file:
            return {"error": "Missing file_path"}

        target_filename = os.path.basename(target_file)
        impacted_files = []

        # Simple scan of the codebase for imports of the target file
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".py") and file != target_filename:
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Check if the target file/module is imported
                            module_name = target_filename.replace(".py", "")
                            if f"import {module_name}" in content or f"from {module_name}" in content:
                                impacted_files.append(full_path)
                    except:
                        continue

        return {
            "target": target_file,
            "impacted_files": impacted_files,
            "impact_score": len(impacted_files)
        }
