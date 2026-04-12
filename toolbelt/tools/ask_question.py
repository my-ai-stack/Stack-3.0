"""AskUserQuestionTool - Ask user questions interactively for Stack 3.0"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolResult
from .registry import tool_registry

QUESTIONS_FILE = Path.home() / ".stack-3.0" / "questions.json"


def _load_questions() -> Dict[str, Any]:
    """Load pending questions."""
    QUESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if QUESTIONS_FILE.exists():
        return json.loads(QUESTIONS_FILE.read_text())
    return {"questions": []}


def _save_questions(data: Dict[str, Any]) -> None:
    """Save pending questions."""
    QUESTIONS_FILE.write_text(json.dumps(data, indent=2))


class AskQuestionTool(BaseTool):
    """Ask the user a question and wait for response."""

    name = "ask_question"
    description = "Ask user a question with optional choices"

    input_schema = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Question to ask"},
            "options": {"type": "array", "items": {"type": "string"}, "description": "Optional choices"},
            "timeout": {"type": "number", "default": 300, "description": "Timeout in seconds"}
        },
        "required": ["question"]
    }

    async def execute(self, question: str, options: Optional[List[str]] = None, timeout: int = 300) -> ToolResult:
        """Ask question."""
        data = _load_questions()

        q_id = str(uuid.uuid4())[:8]
        q_entry = {
            "id": q_id,
            "question": question,
            "options": options,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "timeout": timeout
        }

        data["questions"].append(q_entry)
        _save_questions(data)

        return ToolResult(success=True, data={
            "question_id": q_id,
            "question": question,
            "options": options,
            "status": "pending",
            "note": f"Question {q_id} is pending. Await user response."
        })


class GetPendingQuestionsTool(BaseTool):
    """Get all pending questions."""

    name = "get_pending_questions"
    description = "List all pending questions"

    input_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self) -> ToolResult:
        """Get pending questions."""
        data = _load_questions()
        pending = [q for q in data.get("questions", []) if q.get("status") == "pending"]

        return ToolResult(success=True, data={
            "pending_questions": pending,
            "count": len(pending)
        })


class AnswerQuestionTool(BaseTool):
    """Answer a pending question."""

    name = "answer_question"
    description = "Submit an answer to a pending question"

    input_schema = {
        "type": "object",
        "properties": {
            "question_id": {"type": "string", "description": "Question ID"},
            "answer": {"type": "string", "description": "Answer"}
        },
        "required": ["question_id", "answer"]
    }

    async def execute(self, question_id: str, answer: str) -> ToolResult:
        """Answer question."""
        data = _load_questions()

        for q in data.get("questions", []):
            if q.get("id") == question_id:
                q["status"] = "answered"
                q["answer"] = answer
                q["answered_at"] = datetime.now().isoformat()
                _save_questions(data)
                return ToolResult(success=True, data={
                    "question_id": question_id,
                    "answer": answer,
                    "status": "answered"
                })

        return ToolResult(success=False, error=f"Question {question_id} not found")


# Register tools
tool_registry.register(AskQuestionTool())
tool_registry.register(GetPendingQuestionsTool())
tool_registry.register(AnswerQuestionTool())
