import logging
import sys
import os

# Add the agents directory to path to allow imports
sys.path.append('/Users/walidsobhi/stack-3.0/cognitive_core/agents')

from coordinator import Coordinator
from worker_agent import WorkerAgent
from persona_registry import PersonaRegistry

def test_personas():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger("TestPersona")

    coordinator = Coordinator()

    # Spawn two workers with different personas
    optimist_id = "worker-optimist"
    skeptic_id = "worker-skeptic"

    coordinator.spawn_worker(optimist_id, persona='The Optimist')
    coordinator.spawn_worker(skeptic_id, persona='The Skeptic')

    task = "Implement a new user authentication system."

    logger.info(f"Distributing task: {task}")
    results = coordinator.distribute_task(task, [optimist_id, skeptic_id])

    for wid, reasoning in results.items():
        print(f"\nAgent {wid}:\n{reasoning}")

if __name__ == "__main__":
    test_personas()
