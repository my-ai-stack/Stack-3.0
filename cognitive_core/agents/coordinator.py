from typing import List
import logging
from worker_agent import WorkerAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Coordinator")

class Coordinator:
    """
    Coordinates multiple WorkerAgents and assigns them personas.
    """
    def __init__(self):
        self.workers = {}

    def spawn_worker(self, agent_id: str, persona: str = 'Default') -> WorkerAgent:
        """
        Spawns a new WorkerAgent with a specified persona.
        """
        worker = WorkerAgent(agent_id, persona)
        self.workers[agent_id] = worker
        logger.info(f"Coordinator spawned worker {agent_id} with persona {persona}")
        return worker

    def distribute_task(self, task_description: str, worker_ids: List[str]):
        """
        Distributes a task to specific workers and collects their reasoning.
        """
        results = {}
        for wid in worker_ids:
            if wid in self.workers:
                worker = self.workers[wid]
                results[wid] = worker.reason(task_description)
        return results
