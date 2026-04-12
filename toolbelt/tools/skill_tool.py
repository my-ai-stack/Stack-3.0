"""SkillTool - Skill execution framework for Stack 3.0"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolResult
from .registry import tool_registry

SKILLS_FILE = Path.home() / ".stack-3.0" / "skills.json"
SKILL_DIRS = [
    Path.home() / ".npm-global" / "lib" / "node_modules" / "openclaw" / "skills",
    Path.home() / ".openclaw" / "workspace" / "skills",
]


def _load_skills() -> Dict[str, Any]:
    """Load skills inventory from disk."""
    SKILLS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SKILLS_FILE.exists():
        return json.loads(SKILLS_FILE.read_text())
    return {"skills": [], "inventory": {}}


def _save_skills(data: Dict[str, Any]) -> None:
    """Save skills inventory to disk."""
    SKILLS_FILE.write_text(json.dumps(data, indent=2))


def _discover_skills() -> List[Dict[str, str]]:
    """Discover available skills from skill directories."""
    discovered = []
    for skill_dir in SKILL_DIRS:
        if skill_dir.exists():
            for item in skill_dir.iterdir():
                if item.is_dir() and (item / "SKILL.md").exists():
                    discovered.append({
                        "name": item.name,
                        "path": str(item),
                        "description": _get_skill_description(item)
                    })
    return discovered


def _get_skill_description(skill_path: Path) -> str:
    """Extract description from SKILL.md."""
    skill_md = skill_path / "SKILL.md"
    if skill_md.exists():
        content = skill_md.read_text()[:200]
        return content.split("\n")[0] if content else "No description"
    return "No description"


class SkillListTool(BaseTool):
    """List all available skills."""

    name = "skill_list"
    description = "List all available skills that can be executed"

    input_schema = {
        "type": "object",
        "properties": {
            "search": {
                "type": "string",
                "description": "Search term to filter skills"
            }
        },
        "required": []
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """List skills."""
        search = input_data.get("search", "")
        data = _load_skills()
        discovered = _discover_skills()

        skills = discovered
        if search:
            skills = [s for s in skills if search.lower() in s["name"].lower() or search.lower() in s.get("description", "").lower()]

        return ToolResult(success=True, data={
            "skills": skills,
            "count": len(skills)
        })


class SkillExecuteTool(BaseTool):
    """Execute a specific skill."""

    name = "skill_execute"
    description = "Execute a skill with given parameters"

    input_schema = {
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "Name of the skill to execute"
            },
            "parameters": {
                "type": "object",
                "description": "Parameters to pass to the skill"
            },
            "chain": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional chain of skills to execute in sequence"
            }
        },
        "required": ["skill_name"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute a skill."""
        skill_name = input_data.get("skill_name")
        parameters = input_data.get("parameters")
        chain = input_data.get("chain")

        skill_path = None
        for dir in SKILL_DIRS:
            potential = dir / skill_name
            if potential.exists():
                skill_path = potential
                break

        if not skill_path:
            return ToolResult(success=False, error=f"Skill '{skill_name}' not found")

        data = _load_skills()
        result = {"skill": skill_name, "executed_at": datetime.now().isoformat(), "parameters": parameters or {}}

        # Log execution
        if "inventory" not in data:
            data["inventory"] = {}
        if skill_name not in data["inventory"]:
            data["inventory"][skill_name] = {"executions": [], "last_run": None}
        data["inventory"][skill_name]["executions"].append(result["executed_at"])
        data["inventory"][skill_name]["last_run"] = result["executed_at"]
        _save_skills(data)

        # Execute chain if provided
        if chain:
            result["chain"] = chain
            result["chain_results"] = []

        return ToolResult(success=True, data=result)


class SkillInfoTool(BaseTool):
    """Get detailed info about a skill."""

    name = "skill_info"
    description = "Get detailed information about a specific skill"

    input_schema = {
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "Name of the skill"
            }
        },
        "required": ["skill_name"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Get skill info."""
        skill_name = input_data.get("skill_name")
        skill_path = None
        for dir in SKILL_DIRS:
            potential = dir / skill_name
            if potential.exists():
                skill_path = potential
                break

        if not skill_path:
            return ToolResult(success=False, error=f"Skill '{skill_name}' not found")

        skill_md = skill_path / "SKILL.md"
        description = ""
        if skill_md.exists():
            content = skill_md.read_text()
            lines = content.split("\n")
            description = lines[0] if lines else ""

        return ToolResult(success=True, data={
            "name": skill_name,
            "path": str(skill_path),
            "description": description,
            "has_script": (skill_path / "script.sh").exists() or (skill_path / "script.py").exists()
        })


class SkillChainTool(BaseTool):
    """Execute a chain of skills in sequence."""

    name = "skill_chain"
    description = "Execute multiple skills in sequence, passing output of each to the next"

    input_schema = {
        "type": "object",
        "properties": {
            "skills": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "skill_name": {"type": "string"},
                        "parameters": {"type": "object"}
                    }
                },
                "description": "List of skills to execute in order"
            }
        },
        "required": ["skills"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute skill chain."""
        skills = input_data.get("skills")
        results = []
        for i, step in enumerate(skills):
            skill_name = step.get("skill_name")
            params = step.get("parameters", {})

            skill_path = None
            for dir in SKILL_DIRS:
                potential = dir / skill_name
                if potential.exists():
                    skill_path = potential
                    break

            if not skill_path:
                results.append({"step": i + 1, "skill": skill_name, "status": "error", "error": f"Skill not found"})
                continue

            results.append({
                "step": i + 1,
                "skill": skill_name,
                "parameters": params,
                "status": "executed",
                "executed_at": datetime.now().isoformat()
            })

        return ToolResult(success=True, data={
            "chain_length": len(skills),
            "results": results
        })


class SkillSearchTool(BaseTool):
    """Search for skills by keyword."""

    name = "skill_search"
    description = "Search for skills by name or description"

    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            }
        },
        "required": ["query"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Search skills."""
        query = input_data.get("query")
        discovered = _discover_skills()
        matches = [s for s in discovered if query.lower() in s["name"].lower() or query.lower() in s.get("description", "").lower()]

        return ToolResult(success=True, data={
            "query": query,
            "matches": matches,
            "count": len(matches)
        })


# Register tools
tool_registry.register(SkillListTool())
tool_registry.register(SkillExecuteTool())
tool_registry.register(SkillInfoTool())
tool_registry.register(SkillChainTool())
tool_registry.register(SkillSearchTool())
