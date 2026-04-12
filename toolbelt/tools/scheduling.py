"""ScheduleCronTool — schedule prompts for later/recurring execution.

Schedules are stored in ~/.stack-3.0/schedules.json.

Supports standard 5-field cron expressions in local time:
  minute hour day-of-month month day-of-week

Examples:
  "*/5 * * * *"   every 5 minutes
  "0 9 * * *"     9am daily
  "30 14 * * 1-5" weekdays at 2:30pm
  "0 0 1 * *"     midnight on the 1st of each month
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any

from .base import BaseTool, ToolResult
from .registry import get_registry

TOOL_NAME = "ScheduleCron"
DATA_DIR = os.path.expanduser("~/.stack-3.0")
SCHEDULES_FILE = os.path.join(DATA_DIR, "schedules.json")
DEFAULT_MAX_AGE_DAYS = 30


def _load_schedules() -> list[dict[str, Any]]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(SCHEDULES_FILE):
        try:
            with open(SCHEDULES_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_schedules(schedules: list[dict[str, Any]]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SCHEDULES_FILE, "w") as f:
        json.dump(schedules, f, indent=2, default=str)


# ── cron parsing helpers ──────────────────────────────────────────────────────

# 5-field cron: minute hour day-of-month month day-of-week
CRON_RE = re.compile(
    r"^"
    r"(\*|([0-5]?\d))"           # minute
    r"\s+"
    r"(\*|([01]?\d|2[0-3]))"      # hour
    r"\s+"
    r"(\*|([12]?\d|3[01]))"       # day-of-month
    r"\s+"
    r"(\*|(1[0-2]|0?[1-9]))"      # month
    r"\s+"
    r"(\*|([0-6]))"               # day-of-week
    r"$"
)


def parse_cron(cron: str) -> tuple[bool, str | None]:
    """Validate a 5-field cron expression. Returns (valid, error)."""
    parts = cron.split()
    if len(parts) != 5:
        return False, f"Expected 5 fields, got {len(parts)}"

    minute, hour, dom, month, dow = parts

    def check_field(name: str, value: str, max_val: int) -> str | None:
        if value == "*":
            return None
        if value.isdigit():
            v = int(value)
            if 0 <= v <= max_val:
                return None
            return f"{name}={v} out of range [0,{max_val}]"
        if "/" in value:
            parts = value.split("/")
            if len(parts) != 2:
                return f"Invalid {name} step format: {value}"
            base, step = parts
            if step.isdigit() and int(step) > 0:
                if base == "*" or (base.isdigit() and 0 <= int(base) <= max_val):
                    return None
            return f"Invalid {name} step: {value}"
        if "-" in value:
            parts = value.split("-")
            if len(parts) != 2:
                return f"Invalid {name} range format: {value}"
            start, end = parts
            if start.isdigit() and end.isdigit():
                s, e = int(start), int(end)
                if 0 <= s <= max_val and 0 <= e <= max_val and s <= e:
                    return None
            return f"Invalid {name} range: {value}"
        if "," in value:
            parts = value.split(",")
            for p in parts:
                if not p:
                    return f"Empty value in {name} list: {value}"
                if p == "*":
                    continue
                if p.isdigit():
                    v = int(p)
                    if not (0 <= v <= max_val):
                        return f"Value {v} in {name} list out of range [0,{max_val}]"
                elif "/" in p:
                    # Simplified check for steps in list
                    s_parts = p.split("/")
                    if len(s_parts) == 2 and s_parts[1].isdigit() and int(s_parts[1]) > 0:
                        base = s_parts[0]
                        if base == "*" or (base.isdigit() and 0 <= int(base) <= max_val):
                            continue
                    return f"Invalid {name} step in list: {p}"
                elif "-" in p:
                    # Simplified check for ranges in list
                    r_parts = p.split("-")
                    if len(r_parts) == 2 and r_parts[0].isdigit() and r_parts[1].isdigit():
                        s, e = int(r_parts[0]), int(r_parts[1])
                        if 0 <= s <= max_val and 0 <= e <= max_val and s <= e:
                            continue
                    return f"Invalid {name} range in list: {p}"
                else:
                    return f"Invalid {name} value: {p}"
            return None
        return f"Invalid {name}: {value}"

    for name, val, maxv in [
        ("minute", minute, 59),
        ("hour", hour, 23),
        ("day-of-month", dom, 31),
        ("month", month, 12),
        ("day-of-week", dow, 6),
    ]:
        err = check_field(name, val, maxv)
        if err:
            return False, f"Invalid cron field: {err}"

    return True, None


def cron_to_human(cron: str) -> str:
    """Convert a cron expression to a human-readable string."""
    minute, hour, dom, month, dow = cron.split()

    # Common patterns
    if cron == "* * * * *":
        return "every minute"
    if minute.startswith("*/") and hour == "*" and dom == "*" and month == "*" and dow == "*":
        step = minute[2:]
        return f"every {step} minutes"
    if hour.startswith("*/") and minute == "0" and dom == "*" and month == "*" and dow == "*":
        step = hour[2:]
        return f"every {step} hours"
    if minute == "0" and hour == "*" and dom == "*" and month == "*" and dow == "*":
        return "every hour"
    if minute != "*" and hour != "*" and dom == "*" and month == "*" and dow == "*":
        h = int(hour) if hour.isdigit() else hour
        m = int(minute) if minute.isdigit() else minute
        period = "am" if h < 12 else "pm"
        h12 = h % 12 or 12
        return f"daily at {h12}:{m:02d} {period}"
    if dom != "*" and month != "*":
        return f"on day {dom} of month {month} at {hour}:{minute}"
    if dow != "*" and dow.isdigit():
        days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        return f"weekly on {days[int(dow)]} at {hour}:{minute}"

    return f"at {hour}:{minute}"


def next_cron_run(cron: str, from_time: datetime | None = None) -> datetime | None:
    """Return the next datetime this cron expression fires after from_time.

    This is a simplified implementation that handles common cases.
    For production, consider using croniter.
    """
    if from_time is None:
        from_time = datetime.now()

    minute, hour, dom, month, dow = cron.split()
    now = from_time

    # Simple approach: check each minute for the next 525600 minutes (1 year)
    for delta_minutes in range(1, 525601):
        candidate = now + timedelta(minutes=delta_minutes)
        if candidate.month == 1 and candidate.year > now.year + 1:
            return None  # Beyond our horizon

        # Check each field
        def matches(val: str, actual: int, max_val: int) -> bool:
            if val == "*":
                return True
            if "/" in val:
                base, step = val.split("/", 1)
                base_v = int(base) if base != "*" else 0
                step_v = int(step)
                return (actual - base_v) % step_v == 0
            if "-" in val:
                start, end = val.split("-")
                return int(start) <= actual <= int(end)
            return int(val) == actual

        if not matches(minute, candidate.minute, 59):
            continue
        if not matches(hour, candidate.hour, 23):
            continue
        if not matches(dom, candidate.day, 31):
            continue
        if not matches(month, candidate.month, 12):
            continue
        if not matches(dow, candidate.weekday(), 6):
            continue

        return candidate.replace(second=0, microsecond=0)

    return None


# ── tool classes ──────────────────────────────────────────────────────────────


class CronCreateTool(BaseTool[dict[str, Any], dict[str, Any]]):
    """Schedule a prompt for later or recurring execution.

    Parameters
    ----------
    cron : str
        Standard 5-field cron expression in local time
        (minute hour day-of-month month day-of-week).
        Examples: "*/5 * * * *" (every 5 min), "30 14 * * *" (2:30pm daily).
    prompt : str
        The text to execute/send when the schedule fires.
    recurring : bool, optional
        True (default) = fire on every cron match.
        False = fire once, then auto-delete.
    durable : bool, optional
        True = persist to ~/.stack-3.0/schedules.json (survives restarts).
        False (default) = session-only, dies when the process exits.
    """

    name = "CronCreate"
    description = (
        "Schedule a prompt to run at a future time — "
        "either recurring on a cron schedule, or once at a specific time."
    )
    search_hint = "schedule a recurring or one-shot prompt"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "cron": {
                    "type": "string",
                    "description": (
                        "Standard 5-field cron in local time: "
                        "min hour day-of-month month day-of-week. "
                        'e.g. "*/5 * * * *" = every 5 min, '
                        '"30 14 * * *" = 2:30pm daily.'
                    ),
                },
                "prompt": {"type": "string", "description": "Text to execute when fired."},
                "recurring": {
                    "type": "boolean",
                    "description": "True (default) = recurring; False = one-shot",
                    "default": True,
                },
                "durable": {
                    "type": "boolean",
                    "description": "True = persist to disk; False = session-only (default)",
                    "default": False,
                },
            },
            "required": ["cron", "prompt"],
        }

    def validate_input(self, input_data: dict[str, Any]) -> tuple[bool, str | None]:
        valid, err = parse_cron(input_data.get("cron", ""))
        if not valid:
            return False, f"Invalid cron expression: {err}"
        if not input_data.get("prompt"):
            return False, "Error: prompt is required"
        schedules = _load_schedules()
        if len(schedules) >= 50:
            return False, f"Too many scheduled jobs (max 50). Delete one first."
        return True, None

    def execute(self, input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        cron = input_data["cron"]
        prompt = input_data["prompt"]
        recurring = input_data.get("recurring", True)
        durable = input_data.get("durable", False)

        schedule_id = str(uuid.uuid4())[:8]
        next_run = next_cron_run(cron)

        schedule = {
            "id": schedule_id,
            "cron": cron,
            "prompt": prompt,
            "recurring": recurring,
            "durable": durable,
            "human_schedule": cron_to_human(cron),
            "next_run": next_run.isoformat() if next_run else None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_run": None,
            "run_count": 0,
        }

        if durable:
            schedules = _load_schedules()
            schedules.append(schedule)
            _save_schedules(schedules)

        return ToolResult(
            success=True,
            data={
                "id": schedule_id,
                "cron": cron,
                "human_schedule": cron_to_human(cron),
                "recurring": recurring,
                "durable": durable,
                "next_run": schedule["next_run"],
            },
        )

    def map_result_to_message(self, result: dict, tool_use_id: str | None = None) -> str:
        where = f"Persisted to {SCHEDULES_FILE}" if result.get("durable") else "Session-only"
        recurring = "Recurring" if result.get("recurring") else "One-shot"
        return (
            f"{recurring} job {result['id']} scheduled ({result['human_schedule']}). "
            f"{where}. Next run: {result.get('next_run', 'unknown')}"
        )


class CronListTool(BaseTool[dict[str, Any], dict[str, Any]]):
    """List all scheduled cron jobs.

    Parameters
    ----------
    (none)
    """

    name = "CronList"
    description = "List all scheduled cron jobs."
    search_hint = "list active cron jobs"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def execute(self, input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        schedules = _load_schedules()
        return ToolResult(
            success=True,
            data={
                "jobs": [
                    {
                        "id": s["id"],
                        "cron": s["cron"],
                        "human_schedule": s.get("human_schedule", cron_to_human(s["cron"])),
                        "prompt": s["prompt"],
                        "recurring": s.get("recurring", True),
                        "durable": s.get("durable", False),
                        "next_run": s.get("next_run"),
                        "last_run": s.get("last_run"),
                        "run_count": s.get("run_count", 0),
                    }
                    for s in schedules
                ],
                "total": len(schedules),
            },
        )

    def map_result_to_message(self, result: dict, tool_use_id: str | None = None) -> str:
        jobs = result.get("jobs", [])
        if not jobs:
            return "No scheduled jobs."
        lines = [f"{result['total']} scheduled job(s):\n"]
        for j in jobs:
            durable = " [durable]" if j.get("durable") else " [session-only]"
            recurring = "↻" if j.get("recurring") else "⚡"
            next_run = j.get("next_run", "unknown")
            lines.append(
                f"  {recurring} {j['id']}{durable} — {j['human_schedule']} | "
                f"next: {next_run} | \"{j['prompt'][:60]}...\""
            )
        return "\n".join(lines)


class CronDeleteTool(BaseTool[dict[str, Any], dict[str, Any]]):
    """Delete a scheduled cron job by ID.

    Parameters
    ----------
    id : str
        The schedule ID to cancel (required).
    """

    name = "CronDelete"
    description = "Cancel a scheduled cron job by ID."
    search_hint = "cancel a scheduled cron job"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Schedule ID to cancel"},
            },
            "required": ["id"],
        }

    def validate_input(self, input_data: dict[str, Any]) -> tuple[bool, str | None]:
        if not input_data.get("id"):
            return False, "Error: id is required"
        return True, None

    def execute(self, input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        schedules = _load_schedules()
        schedule_id = input_data["id"]
        original_len = len(schedules)
        schedules = [s for s in schedules if s["id"] != schedule_id]

        if len(schedules) == original_len:
            return ToolResult(success=False, error=f"Schedule #{schedule_id} not found")

        _save_schedules(schedules)
        return ToolResult(success=True, data={"id": schedule_id, "deleted": True})

    def map_result_to_message(self, result: dict, tool_use_id: str | None = None) -> str:
        return f"Schedule #{result['id']} cancelled."


# Register all cron tools
_registry = get_registry()
_registry.register(CronCreateTool())
_registry.register(CronListTool())
_registry.register(CronDeleteTool())
