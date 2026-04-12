"""
Empathy Engine Module

Provides empathetic response generation based on detected emotions.
"""

from typing import Dict, List, Optional, Any
from .sentiment import SentimentAnalyzer


class EmpathyEngine:
    """Generate empathetic and contextually appropriate responses."""

    # Response templates for different emotional states
    EMPATHETIC_RESPONSES = {
        "frustrated": [
            "I understand this is frustrating. Let me help you work through this.",
            "I can see you're frustrated. Let's take this step by step together.",
            "Don't worry - we'll get this sorted out. I'm here to help.",
        ],
        "sad": [
            "I'm sorry you're going through this. I'm here to help in any way I can.",
            "That sounds difficult. Let me see what I can do to help.",
            "I appreciate you sharing this with me. How can I help make things better?",
        ],
        "angry": [
            "I understand you're frustrated. Let me help resolve this for you.",
            "I hear you. Let's work together to find a solution.",
            "I'm sorry you're having this experience. Let me see what I can do.",
        ],
        "worried": [
            "I understand your concern. Let me help put your mind at ease.",
            "Don't worry - I'm here to help. Let's figure this out together.",
            "I can see you're worried. Let me provide some clarity.",
        ],
        "confused": [
            "I understand this can be confusing. Let me explain in a clearer way.",
            "That's a great question. Let me break this down for you.",
            "No worries - I'll help you understand this better.",
        ],
        "excited": [
            "That's great to hear! I'm excited to help you with this.",
            "Awesome! Let me help you make the most of this.",
            "I love your enthusiasm! Let's dive in and make something great.",
        ],
        "neutral": [
            "I'm here to help. What would you like to work on?",
            "How can I assist you today?",
            "What would you like to do next?",
        ],
    }

    TONE_MODIFIERS = {
        "empathetic": {
            "prefix": "I understand. ",
            "soften_errors": True,
            "add_reassurance": True,
        },
        "enthusiastic": {
            "prefix": "Great question! ",
            "add_excitement": True,
            "use_strong_positives": True,
        },
        "supportive": {
            "prefix": "No problem at all. ",
            "reassure_user": True,
            "offer_encouragement": True,
        },
        "helpful": {
            "prefix": "Happy to help! ",
            "be_direct": True,
            "include_steps": True,
        },
        "neutral": {
            "prefix": "",
            "be_concise": True,
        },
    }

    def __init__(self):
        """Initialize the empathy engine."""
        self.sentiment_analyzer = SentimentAnalyzer()

    def generate_empathetic_response(
        self,
        user_message: str,
        base_response: str,
    ) -> str:
        """
        Generate an empathetic version of the response.

        Args:
            user_message: The user's original message
            base_response: The generated response

        Returns:
            Empathetic response
        """
        # Analyze user sentiment
        analysis = self.sentiment_analyzer.analyze_sentiment(user_message)

        # Determine appropriate tone
        tone = self.sentiment_analyzer.get_tone_adjustment(user_message)

        # Get empathetic template
        emotional_state = self._get_dominant_emotion(user_message)
        templates = self.EMPATHETIC_RESPONSES.get(emotional_state, self.EMPATHETIC_RESPONSES["neutral"])

        # Apply tone modifiers
        modifiers = self.TONE_MODIFIERS.get(tone, self.TONE_MODIFIERS["neutral"])

        # Build response
        response = self._build_response(
            base_response,
            modifiers,
            templates,
            analysis,
        )

        return response

    def _get_dominant_emotion(self, text: str) -> str:
        """Get the dominant emotional state."""
        if self.sentiment_analyzer.is_frustrated(text):
            return "frustrated"
        elif self.sentiment_analyzer.is_asking_for_help(text):
            return "confused"

        emotions = self.sentiment_analyzer.detect_emotions(text)
        if emotions:
            return emotions[0]["emotion"]

        return "neutral"

    def _build_response(
        self,
        base_response: str,
        modifiers: Dict[str, bool],
        templates: List[str],
        analysis: Dict[str, Any],
    ) -> str:
        """Build the modified response."""
        # Start with prefix if available
        prefix = modifiers.get("prefix", "")
        response = prefix + base_response

        # Add reassurance for negative emotions
        if modifiers.get("add_reassurance") and analysis["sentiment"] == "negative":
            # Add a supportive note
            if not response.endswith((". ", "!", "?")):
                response += "."
            response += " I'm here to help you work through this."

        return response

    def get_response_tone(
        self,
        user_message: str,
    ) -> Dict[str, Any]:
        """
        Get recommended response tone.

        Args:
            user_message: User's message

        Returns:
            Dictionary with tone recommendations
        """
        analysis = self.sentiment_analyzer.analyze_sentiment(user_message)
        tone = self.sentiment_analyzer.get_tone_adjustment(user_message)
        is_frustrated = self.sentiment_analyzer.is_frustrated(user_message)

        return {
            "recommended_tone": tone,
            "user_sentiment": analysis["sentiment"],
            "user_emotions": analysis["emotions"],
            "needs_empathy": analysis["sentiment"] == "negative" or is_frustrated,
            "modifiers": self.TONE_MODIFIERS.get(tone, {}),
        }

    def adjust_response_length(
        self,
        user_message: str,
        base_response: str,
    ) -> str:
        """
        Adjust response length based on user state.

        Args:
            user_message: User's message
            base_response: Base response

        Returns:
            Adjusted response
        """
        # If user is frustrated or confused, be more concise
        if self.sentiment_analyzer.is_frustrated(user_message):
            # Return first paragraph/section only
            paragraphs = base_response.split("\n\n")
            if paragraphs:
                return paragraphs[0]
        elif self.sentiment_analyzer.is_asking_for_help(user_message):
            # Keep it comprehensive but clear
            return base_response

        return base_response

    def get_supportive_phrase(self, emotion: str) -> str:
        """Get a supportive phrase for the emotion."""
        phrases = {
            "frustrated": "I understand this is frustrating. Let's work through it together.",
            "sad": "I'm sorry you're experiencing this. I'm here to help.",
            "angry": "I hear your frustration. Let me help resolve this.",
            "worried": "I understand your concern. Let's figure this out.",
            "confused": "That's a good question. Let me clarify.",
            "excited": "I'm excited to help with this!",
            "neutral": "How can I help you today?",
        }
        return phrases.get(emotion, phrases["neutral"])

    def __repr__(self) -> str:
        return f"EmpathyEngine(sentiment_analyzer={self.sentiment_analyzer})"