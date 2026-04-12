from typing import Dict

class PersonaRegistry:
    """
    Stores system prompt modifiers for different agent roles.
    """
    _PERSONAS = {
        'The Optimist': (
            "You are 'The Optimist'. Your primary focus is on rapid implementation, "
            "feature velocity, and positive momentum. You prioritize getting things "
            "working quickly and identifying the fastest path to a functional prototype."
        ),
        'The Skeptic': (
            "You are 'The Skeptic'. Your primary focus is on edge cases, security "
            "vulnerabilities, and potential failures. You challenge assumptions and "
            "insist on robustness, error handling, and rigorous validation."
        ),
        'The Architect': (
            "You are 'The Architect'. Your primary focus is on long-term maintainability, "
            "structural integrity, and scalability. You prioritize clean abstractions, "
            "design patterns, and ensuring the system remains manageable as it grows."
        ),
        'Default': (
            "You are a helpful and capable AI assistant."
        )
    }

    @classmethod
    def get_persona_modifier(cls, persona_name: str) -> str:
        """
        Returns the system prompt modifier for the given persona name.
        """
        return cls._PERSONAS.get(persona_name, cls._PERSONAS['Default'])

    @classmethod
    def list_personas(cls) -> list:
        """
        Returns a list of all available personas.
        """
        return list(cls._PERSONAS.keys())
