"""
Intent Detection System
Supports explicit and implicit intent detection.
"""

from typing import List, Dict, Optional, Any, Tuple
import re

class IntentDetector:
    """
    Detects user intents from messages, including support for 'Implicit Intent'.
    Implicit intents are underlying needs not explicitly stated by the user.
    """

    def __init__(self, model_client: Any = None):
        """
        Initialize IntentDetection.

        Args:
            model_client: Optional LLM client for advanced implicit intent analysis.
        """
        self.model_client = model_client
        # Basic pattern-based intents for explicit detection
        self.explicit_patterns = {
            "create_file": [r"create\s+file", r"make\s+a\s+file", r"write\s+a\s+file"],
            "read_file": [r"read\s+file", r"open\s+file", r"show\s+contents\s+of"],
            "edit_file": [r"edit\s+file", r"modify\s+file", r"change\s+line"],
            "search_code": [r"search\s+for", r"find\s+all", r"where\s+is\s+the\s+function"],
            "run_test": [r"run\s+tests", r"execute\s+pytest", r"test\s+this\s+code"],
        }

    def detect_intent(self, message: str) -> Dict[str, Any]:
        """
        Detects the intent of a user message.

        Returns:
            A dictionary containing the primary intent, confidence, and whether it is implicit.
        """
        # 1. Try Explicit Detection first
        explicit_intent = self._detect_explicit(message)
        if explicit_intent:
            return {
                "intent": explicit_intent,
                "confidence": 1.0,
                "is_implicit": False,
                "reasoning": "Pattern match found."
            }

        # 2. Try Implicit Detection if model_client is available
        if self.model_client:
            implicit_intent = self._detect_implicit(message)
            if implicit_intent:
                return implicit_intent

        return {
            "intent": "unknown",
            "confidence": 0.0,
            "is_implicit": False,
            "reasoning": "No clear intent detected."
        }

    def _detect_explicit(self, message: str) -> Optional[str]:
        """Matches message against predefined patterns."""
        msg_lower = message.lower()
        for intent, patterns in self.explicit_patterns.items():
            for pattern in patterns:
                if re.search(pattern, msg_lower):
                    return intent
        return None

    def _detect_implicit(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Uses the model to infer underlying needs not explicitly stated.
        """
        prompt = (
            f"User Message: '{message}'\n\n"
            "Analyze the message for 'Implicit Intent'. The user might not explicitly ask for a tool, "
            "but they may have an underlying need (e.g., 'This code looks buggy' implies a need for analysis or fix).\n"
            "Provide your response in the following format:\n"
            "INTENT: <intent_name>\n"
            "CONFIDENCE: <0.0-1.0>\n"
            "REASONING: <explanation>"
        )

        try:
            response = self.model_client.generate(prompt)
            # Simple parsing of the model response
            intent = None
            confidence = 0.0
            reasoning = ""

            for line in response.split('\n'):
                if line.startswith("INTENT:"):
                    intent = line.replace("INTENT:", "").strip()
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(line.replace("CONFIDENCE:", "").strip())
                    except ValueError:
                        confidence = 0.5
                elif line.startswith("REASONING:"):
                    reasoning = line.replace("REASONING:", "").strip()

            if intent and intent.lower() != "none":
                return {
                    "intent": intent,
                    "confidence": confidence,
                    "is_implicit": True,
                    "reasoning": reasoning
                }
        except Exception as e:
            print(f"Error in implicit intent detection: {e}")

        return None
