from typing import Optional
import logging

# Import PersonaRegistry from the registry file
from persona_registry import PersonaRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WorkerAgent")

class WorkerAgent:
    """
    A worker agent that can be assigned a specific persona to influence its reasoning.
    """
    def __init__(self, agent_id: str, persona: Optional[str] = None):
        self.agent_id = agent_id
        self.persona_name = persona or 'Default'
        self.persona_modifier = PersonaRegistry.get_persona_modifier(self.persona_name)
        logger.info(f"Initialized WorkerAgent {self.agent_id} with persona: {self.persona_name}")

    def reason(self, task_description: str) -> str:
        """
        Simulates the agent's reasoning process based on its persona.
        """
        # In a real implementation, the persona_modifier would be prepended to the system prompt
        # of the LLM call. Here we simulate the effect in the output.
        reasoning_prefix = f"[{self.persona_name} Reasoning]: "

        # Simulating different styles of reasoning
        if self.persona_name == 'The Optimist':
            response = f"Let's move fast! I'll implement the core functionality immediately and iterate. Task: {task_description}. Shipping it now!"
        elif self.persona_name == 'The Skeptic':
            response = f"Wait, what happens if the input is null? I see several security risks here. Task: {task_description}. We need a full audit first."
        elif self.persona_name == 'The Architect':
            response = f"We should define a clear interface and a plugin architecture for this. Task: {task_description}. Let's prioritize the data model for long-term scale."
        else:
            response = f"Processing task: {task_description}. I will handle this efficiently."

        return reasoning_prefix + response
