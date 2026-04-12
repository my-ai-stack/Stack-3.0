import uuid
import asyncio
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

from cognitive_core.technical.code_analysis import CodeAnalyzer
from cognitive_core.technical.debugging import DebuggingAssistant
from cognitive_core.pipeline.fork_manager import get_fork_manager

@dataclass
class WorkerAgent:
    id: str
    role: str
    status: str = "idle"
    last_result: Any = None

    async def execute(self, task: str, context: Dict[str, Any], request_summary: bool = False) -> Any:
        """
        Executes a task. If request_summary is True, the worker performs 'Synthesis'
        on its own output before returning.
        """
        self.status = "busy"
        try:
            # Simulated worker execution logic
            # In a real implementation, this would call an LLM or a tool
            raw_result = f"Detailed raw result from {self.role} agent for task: {task}. [Context: {context.get('goal', 'N/A')}]"

            if request_summary:
                # Synthesis logic: return a summary instead of raw output
                self.last_result = f"Summary of {self.role} results: The task '{task}' was analyzed and the core finding is that it is feasible."
            else:
                self.last_result = raw_result

            return self.last_result
        finally:
            self.status = "idle"

class Coordinator:
    """
    Coordinator Persona: Manages a fleet of worker agents and implements
    the 'Synthesis -> Delegation' workflow.
    """
    def __init__(self, tool_router=None, session_manager=None):
        self.workers: Dict[str, WorkerAgent] = {}
        self.active_tasks: List[str] = []
        self.tool_router = tool_router
        self.session_manager = session_manager
        self.fork_manager = get_fork_manager()

    def spawn_worker(self, role: str) -> str:
        """
        Spawns a new worker agent.
        """
        worker_id = f"worker_{uuid.uuid4().hex[:8]}"
        self.workers[worker_id] = WorkerAgent(id=worker_id, role=role)
        return worker_id

    async def spawn_debate_workers(self, goal: str) -> List[str]:
        """
        Spawns two workers with opposing personas to debate a goal.
        """
        validator_id = self.spawn_worker("Validator")
        explorer_id = self.spawn_worker("Explorer")
        return [validator_id, explorer_id]

    async def synthesize_consensus(self, worker_results: List[Dict[str, Any]]) -> str:
        """
        Analyzes competing responses, identifies contradictions, and resolves them.
        """
        # In a real implementation, this would use an LLM to find contradictions
        # and possibly loop back to workers for resolution.
        debate_log = "\n".join([f"{res['worker']}: {res['result']}" for res in worker_results])

        consensus = f"Consensus reached after analyzing debate:\n{debate_log}\n\nResolution: The final answer is synthesized by resolving contradictions between the Validator and Explorer."
        return consensus

    async def run_consensus_debate(self, goal: str, context: Dict[str, Any]) -> str:
        """
        Implements a Consensus Debate workflow:
        1. Spawn Worker A (The Optimist) and Worker B (The Skeptic).
        2. Worker A proposes a solution.
        3. Worker B critiques the solution and proposes an alternative.
        4. Worker A responds to the critique.
        5. The Coordinator synthesizes the final, verified answer based on the debate.
        """
        # Step 1: Spawn Workers
        optimist_id = self.spawn_worker("The Optimist")
        skeptic_id = self.spawn_worker("The Skeptic")
        optimist = self.workers[optimist_id]
        skeptic = self.workers[skeptic_id]

        debate_history = []

        # Step 2: Worker A proposes a solution
        proposal_task = f"Propose a comprehensive solution for: {goal}"
        proposal = await optimist.execute(proposal_task, context)
        debate_history.append({"worker": "The Optimist", "role": "Proposal", "result": proposal})

        # Step 3: Worker B critiques and proposes alternative
        critique_task = f"Critique the following proposal and suggest an alternative: {proposal}"
        critique = await skeptic.execute(critique_task, {**context, "current_proposal": proposal})
        debate_history.append({"worker": "The Skeptic", "role": "Critique", "result": critique})

        # Step 4: Worker A responds to critique
        rebuttal_task = f"Address the critique and finalize the solution: {critique}"
        rebuttal = await optimist.execute(rebuttal_task, {**context, "critique": critique})
        debate_history.append({"worker": "The Optimist", "role": "Rebuttal", "result": rebuttal})

        # Step 5: Coordinator synthesizes final answer
        return await self.synthesize_consensus(debate_history)

    async def synthesis_delegation_workflow(self, goal: str, context: Dict[str, Any], summarize_results: bool = False, synthesizer_llm: Any = None, complexity: str = "Normal"):
        """
        Implements the Synthesis -> Delegation workflow.
        1. Synthesis: Analyze the goal and context to create a plan.
        2. Surgical Context Injection: Force proof of understanding.
        3. Delegation: Assign tasks to specific workers (executed in parallel).

        If complexity is 'Critical' or 'Complex', it triggers a Consensus Debate instead of standard parallel execution.
        """
        if complexity in ["Critical", "Complex"]:
            return await self.run_consensus_debate(goal, context)

        # Step 1: Synthesis
        synthesis = self._synthesize_plan(goal, context)

        # Step 2: Surgical Context Injection
        if not self._verify_synthesis_evidence(synthesis, context):
            raise ValueError("Surgical Context Injection Failed: Coordinator failed to provide required evidence (line numbers/paths) for the research.")

        # Step 3: Delegation (Parallel Execution)
        tasks = []
        for task_def in synthesis["tasks"]:
            # If a tool_router is provided, we can use it to refine the role or spawn specialized workers
            role = task_def["role"]
            if self.tool_router:
                # Use ToolRouter to check if there's a more specific category/role for this task
                # This is a conceptual integration with ToolRouter
                categories = self.tool_router.get_categories()
                if role in categories:
                    # Refine role based on category tools
                    role = f"specialized_{role}"

            worker_id = self.spawn_worker(role)
            worker = self.workers[worker_id]

            # Context Forking Integration:
            # Check if the task involves noisy tools (e.g. research, grep, glob)
            if "research" in role or "analyze" in task_def["description"]:
                # Create a research fork for this specific task to keep main context clean
                fork_id = self.fork_manager.create_fork(context, purpose=task_def["description"])

                # Wrap the worker execution to record noisy outputs into the fork
                async def wrapped_execute(w=worker, t=task_def["description"], c=context, s=summarize_results, f=fork_id):
                    result = await w.execute(t, c, request_summary=s)
                    # If the result is 'noisy' (simulated here), we record it to the fork
                    # In a real scenario, the WorkerAgent would use the tool_router and we'd check tool.is_noisy
                    self.fork_manager.record_output(f, w.role, result)
                    return result

                tasks.append(wrapped_execute())
            else:
                tasks.append(worker.execute(task_def["description"], context, request_summary=summarize_results))

        # Execute all workers in parallel using asyncio.gather
        results_raw = await asyncio.gather(*tasks)

        # Fork Synthesis: If forks were created, synthesize them back into the main context
        fork_summaries = []
        active_forks = list(self.fork_manager.active_forks.keys())
        for fid in active_forks:
            if synthesizer_llm:
                summary = await self.fork_manager.synthesize_and_close(fid, synthesizer_llm)
                fork_summaries.append(summary)

        executions = []
        for i, result in enumerate(results_raw):
            worker_id = list(self.workers.keys())[i] # Simplified mapping
            executions.append({"worker": worker_id, "result": result})

        return {
            "plan": synthesis,
            "executions": executions,
            "fork_summaries": fork_summaries,
            "final_synthesis": self._final_synthesis(executions)
        }

    def _verify_synthesis_evidence(self, synthesis: Dict, context: Dict) -> bool:
        """
        Verifies that the synthesis contains proof of understanding
        (e.g., specific file paths and line numbers).
        """
        evidence = synthesis.get("evidence", [])
        if not evidence:
            return False

        for item in evidence:
            if "path" in item and "line" in item:
                return True
        return False

    def _synthesize_plan(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Mock LLM decomposition
        return {
            "goal": goal,
            "evidence": [{"path": "example.py", "line": 10, "content": "Relevant code snippet"}],
            "tasks": [
                {"role": "researcher", "description": f"Research aspects of {goal}"},
                {"role": "implementer", "description": f"Implement solution for {goal}"}
            ]
        }

    def _final_synthesis(self, results: List[Dict]) -> str:
        return "Final synthesized output based on worker results."
