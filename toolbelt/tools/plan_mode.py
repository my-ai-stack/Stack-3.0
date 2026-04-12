"""Plan mode tools — EnterPlanMode and ExitPlanMode.

EnterPlanMode switches the agent into a reasoning/planning mode where it
explores the codebase read-only before writing any code.

ExitPlanMode exits planning mode and returns to normal execution mode.

Plan state is stored in ~/.stack-3.0/plan_mode.json
Reasoning steps are tracked in ~/.stack-3.0/plan_reasoning.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from .base import BaseTool, ToolResult
from .registry import get_registry

DATA_DIR = os.path.expanduser("~/.stack-3.0")
PLAN_STATE_FILE = os.path.join(DATA_DIR, "plan_mode.json")
REASONING_FILE = os.path.join(DATA_DIR, "plan_reasoning.json")


def _load_plan_state() -> dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(PLAN_STATE_FILE):
        try:
            with open(PLAN_STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"active": False, "entered_at": None, "plan_text": None, "context": None}


def _save_plan_state(state: dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PLAN_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def _load_reasoning() -> list[dict[str, Any]]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(REASONING_FILE):
        try:
            with open(REASONING_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_reasoning(steps: list[dict[str, Any]]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REASONING_FILE, "w") as f:
        json.dump(steps, f, indent=2, default=str)


# ── EnterPlanModeTool ───────────────────────────────────────────────────────────


class EnterPlanModeTool(BaseTool[dict[str, Any], dict[str, Any]]):
    """Enter plan mode — a read-only reasoning phase for exploring and designing.

    Parameters
    ----------
    plan_text : str, optional
        Initial plan text to record.
    context : str, optional
        Context or task description for the plan.
    """

    name = "EnterPlanMode"
    description = (
        "Switch to plan mode for complex tasks requiring exploration and design. "
        "In plan mode, you should explore the codebase read-only and design an approach "
        "before writing any code. Use ExitPlanMode when ready to present your plan."
    )
    search_hint = "switch to plan mode to design approach before coding"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_text": {
                    "type": "string",
                    "description": "Initial plan text or summary to record",
                },
                "context": {
                    "type": "string",
                    "description": "Context or task description guiding the plan",
                },
            },
            "properties": {},
        }

    def is_enabled(self) -> bool:
        state = _load_plan_state()
        return not state.get("active", False)

    def execute(self, input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        state = _load_plan_state()
        if state.get("active"):
            return ToolResult(success=False, error="Already in plan mode. Use ExitPlanMode first.")

        now = datetime.now(timezone.utc).isoformat()
        plan_text = input_data.get("plan_text", "")
        context = input_data.get("context", "")

        new_state = {
            "active": True,
            "entered_at": now,
            "plan_text": plan_text,
            "context": context,
            "exited_at": None,
        }
        _save_plan_state(new_state)

        # Initialize reasoning log
        reasoning = _load_reasoning()
        reasoning.append({
            "step": 1,
            "action": "enter_plan_mode",
            "timestamp": now,
            "context": context,
            "note": "Entered plan mode. Begin read-only exploration and design.",
        })
        _save_reasoning(reasoning)

        return ToolResult(
            success=True,
            data={
                "message": "Entered plan mode. Explore the codebase read-only and design your implementation approach.",
                "plan_text": plan_text,
                "context": context,
                "entered_at": now,
            },
        )

    def map_result_to_message(self, result: dict, tool_use_id: str | None = None) -> str:
        data = result.get("data", {})
        msg = data.get(
            "message",
            "Entered plan mode. Explore the codebase read-only and design your approach.",
        )
        return f"""{msg}

In plan mode, you should:
1. Explore the codebase to understand existing patterns
2. Identify similar features and architectural approaches
3. Consider multiple approaches and trade-offs
4. Use FileReadTool to understand the structure
5. Design a concrete implementation strategy
6. When ready, use ExitPlanMode to present your plan

DO NOT write or edit any files yet. This is a read-only exploration phase."""


# ── ExitPlanModeTool ────────────────────────────────────────────────────────────


class ExitPlanModeTool(BaseTool[dict[str, Any], dict[str, Any]]):
    """Exit plan mode and return to normal execution.

    Parameters
    ----------
    confirm : bool, optional
        Whether the plan is approved (default: True).
    summary : str, optional
        A summary or the full plan text to save.
    """

    name = "ExitPlanMode"
    description = (
        "Exit plan mode and return to normal execution. "
        "Call this when you have finished your plan and are ready to code, "
        "or to abandon the plan without implementing."
    )
    search_hint = "exit plan mode and start coding present plan for approval"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "confirm": {
                    "type": "boolean",
                    "description": "Whether the plan is approved (default: True)",
                    "default": True,
                },
                "summary": {
                    "type": "string",
                    "description": "Plan summary or full plan text to save",
                },
            },
            "properties": {},
        }

    def execute(self, input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        state = _load_plan_state()
        if not state.get("active"):
            return ToolResult(success=False, error="Not in plan mode. Use EnterPlanMode first.")

        confirm = input_data.get("confirm", True)
        summary = input_data.get("summary") or state.get("plan_text", "")

        now = datetime.now(timezone.utc).isoformat()

        # Log exit reasoning step
        reasoning = _load_reasoning()
        reasoning.append({
            "step": len(reasoning) + 1,
            "action": "exit_plan_mode",
            "timestamp": now,
            "confirm": confirm,
            "summary_length": len(summary) if summary else 0,
            "note": "Exited plan mode" + (" (plan approved)" if confirm else " (plan rejected/abandoned)"),
        })
        _save_reasoning(reasoning)

        # Update plan state
        new_state = {
            **state,
            "active": False,
            "exited_at": now,
            "plan_text": summary if summary else state.get("plan_text"),
            "approved": confirm,
        }
        _save_plan_state(new_state)

        return ToolResult(
            success=True,
            data={
                "message": "Exited plan mode. Ready to proceed." if confirm else "Plan abandoned.",
                "plan_text": summary,
                "confirmed": confirm,
                "exited_at": now,
            },
        )

    def map_result_to_message(self, result: dict, tool_use_id: str | None = None) -> str:
        data = result.get("data", {})
        confirm = data.get("confirmed", True)
        plan_text = data.get("plan_text", "")

        if confirm:
            lines = ["Plan approved. You can now start coding."]
            if plan_text:
                lines.append(f"\nPlan saved:\n{plan_text}")
            return "\n".join(lines)
        else:
            return "Plan abandoned. Exited plan mode."


# Auto-register plan mode tools
get_registry().register(EnterPlanModeTool())
get_registry().register(ExitPlanModeTool())

