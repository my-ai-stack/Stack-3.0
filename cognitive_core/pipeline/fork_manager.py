"""
Fork Manager for handling temporary research forks to prevent context window saturation.
"""

from __future__ import annotations
import uuid
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ResearchFork:
    """
    A temporary research context that can execute 'noisy' tools and synthesize results.
    """
    id: str
    parent_context: Dict[str, Any]
    purpose: str
    created_at: datetime = field(default_factory=datetime.now)
    results: List[Dict[str, Any]] = field(default_factory=list)
    is_active: bool = True

    async def execute_tool(self, tool_call: Dict[str, Any], tool_registry: Any) -> Any:
        """
        Executes a tool within the fork.
        """
        tool_name = tool_call["name"]
        input_data = tool_call["arguments"]

        # Execute the tool using the registry
        raw_output = await tool_registry.call(tool_name, input_data)

        # Store the result in the fork's history
        self.results.append({
            "tool": tool_name,
            "input": input_data,
            "output": raw_output,
            "timestamp": datetime.now()
        })

        return raw_output

    async def synthesize(self, synthesizer_llm: Any) -> str:
        """
        Processes the accumulated results and returns a concise summary.
        """
        if not self.results:
            return "No data collected in this fork."

        # Prepare the raw content for the synthesizer
        raw_content = "\n---\n".join([
            f"Tool: {r['tool']}\nOutput: {r['output']}"
            for r in self.results
        ])

        synthesis_prompt = (
            f"Synthesize the following research data for the purpose: '{self.purpose}'.\n"
            f"Parent Context Goal: {self.parent_context.get('goal', 'N/A')}\n"
            "Extract only the most critical information, patterns, and findings. "
            "Remove redundancies and noise. Provide a concise summary for the main cognitive loop.\n\n"
            f"Data:\n{raw_content}"
        )

        # The synthesizer_llm is expected to have a generate/invoke method
        summary = await synthesizer_llm.generate(synthesis_prompt)
        self.is_active = False
        return summary

class ForkManager:
    """
    Manages the lifecycle of ResearchForks.
    """
    def __init__(self):
        self.active_forks: Dict[str, ResearchFork] = {}

    def create_fork(self, parent_context: Dict[str, Any], purpose: str) -> ResearchFork:
        fork_id = f"fork_{uuid.uuid4().hex[:8]}"
        fork = ResearchFork(id=fork_id, parent_context=parent_context, purpose=purpose)
        self.active_forks[fork_id] = fork
        return fork

    def get_fork(self, fork_id: str) -> Optional[ResearchFork]:
        return self.active_forks.get(fork_id)

    def cleanup_fork(self, fork_id: str):
        if fork_id in self.active_forks:
            del self.active_forks[fork_id]

# Global instance
fork_manager = ForkManager()
get_fork_manager = lambda: fork_manager
