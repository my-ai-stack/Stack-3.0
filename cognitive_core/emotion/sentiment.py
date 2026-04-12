"""
Sentiment Analysis Module

Provides sentiment and emotion detection for text.
"""

from typing import Dict, List, Optional, Any
import re


class SentimentAnalyzer:
    """Analyze sentiment and emotions in text."""

    # Emotion keywords for rule-based fallback
    EMOTION_KEYWORDS = {
        "joy": ["happy", "joy", "excited", "wonderful", "great", "love", "amazing", "awesome", "fantastic"],
        "sadness": ["sad", "unhappy", "depressed", "down", "disappointed", "unfortunate", "sorry"],
        "anger": ["angry", "mad", "frustrated", "annoyed", "irritated", "furious", "hate"],
        "fear": ["afraid", "scared", "worried", "anxious", "nervous", "terrified", "fear"],
        "surprise": ["surprised", "amazing", "incredible", "unexpected", "shocked", "wow"],
        "anticipation": ["looking forward", "hope", "expect", "excited about", "can't wait"],
    }

    def __init__(
        self,
        use_transformers: bool = True,
        model_name: str = "distilbert-base-uncased-finetuned-sst-2-english",
    ):
        """
        Initialize the sentiment analyzer.

        Args:
            use_transformers: Use transformer-based sentiment analysis
            model_name: Model name for transformer-based analysis
        """
        self.use_transformers = use_transformers and self._check_transformers()
        self.model_name = model_name
        self._pipeline = None

    def _check_transformers(self) -> bool:
        """Check if transformers is available."""
        try:
            import transformers
            return True
        except ImportError:
            return False

    def _load_pipeline(self):
        """Lazy load the sentiment pipeline."""
        if self._pipeline is None:
            try:
                from transformers import pipeline
                self._pipeline = pipeline(
                    "sentiment-analysis",
                    model=self.model_name,
                )
            except Exception as e:
                print(f"Warning: Could not load transformer sentiment model: {e}")
                self.use_transformers = False

    def analyze_sentiment(
        self,
        text: str,
        return_scores: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of text.

        Args:
            text: Input text
            return_scores: Return confidence scores

        Returns:
            Dictionary with sentiment, score, and emotions
        """
        sentiment = "neutral"
        score = 0.5
        emotions = []

        # Try transformer-based first
        if self.use_transformers:
            try:
                result = self._analyze_transformers(text)
                sentiment = result["label"]
                score = result["score"]
            except Exception:
                pass

        # Fall back to rule-based
        if sentiment == "neutral":
            result = self._analyze_rule_based(text)
            sentiment = result["sentiment"]
            score = result["score"]
            emotions = result["emotions"]

        # Detect emotions
        emotions = self.detect_emotions(text)

        return {
            "sentiment": sentiment,
            "score": score,
            "emotions": emotions,
        }

    def _analyze_transformers(self, text: str) -> Dict[str, Any]:
        """Use transformer for sentiment analysis."""
        self._load_pipeline()

        if self._pipeline is None:
            return {"label": "neutral", "score": 0.5}

        # Truncate long text
        text = text[:512]
        result = self._pipeline(text)[0]

        return {
            "label": result["label"].lower(),
            "score": result["score"],
        }

    def _analyze_rule_based(self, text: str) -> Dict[str, Any]:
        """Rule-based sentiment analysis."""
        text_lower = text.lower()

        positive_words = ["good", "great", "excellent", "amazing", "wonderful", "fantastic",
                          "love", "happy", "joy", "best", "perfect", "awesome", "like"]
        negative_words = ["bad", "terrible", "awful", "horrible", "worst", "hate", "sad",
                          "angry", "disappointed", "frustrated", "annoying", "poor", "fail"]

        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)

        total = pos_count + neg_count
        if total == 0:
            return {"sentiment": "neutral", "score": 0.5, "emotions": []}

        if pos_count > neg_count:
            score = min(0.5 + (pos_count - neg_count) * 0.1, 0.95)
            sentiment = "positive"
        elif neg_count > pos_count:
            score = max(0.5 - (neg_count - pos_count) * 0.1, 0.05)
            sentiment = "negative"
        else:
            sentiment = "neutral"
            score = 0.5

        return {"sentiment": sentiment, "score": score, "emotions": []}

    def detect_emotions(self, text: str) -> List[Dict[str, float]]:
        """
        Detect emotions in text.

        Args:
            text: Input text

        Returns:
            List of emotion dictionaries with scores
        """
        text_lower = text.lower()
        emotions = []

        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            score = 0.0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1.0

            if score > 0:
                # Normalize score
                score = min(score / len(keywords), 1.0)
                emotions.append({
                    "emotion": emotion,
                    "score": score,
                })

        # Sort by score
        emotions.sort(key=lambda x: -x["score"])
        return emotions[:3]

    def get_emotion_intensity(self, text: str) -> float:
        """
        Get overall emotion intensity (0-1).

        Args:
            text: Input text

        Returns:
            Emotion intensity score
        """
        emotions = self.detect_emotions(text)
        if not emotions:
            return 0.0

        return max(e["score"] for e in emotions)

    def is_frustrated(self, text: str) -> bool:
        """Check if user seems frustrated."""
        frustration_indicators = [
            "frustrated", "annoyed", "angry", "mad", "sick of", "tired of",
            "this is useless", "this doesn't work", "why won't", "can't figure out",
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in frustration_indicators)

    def is_asking_for_help(self, text: str) -> bool:
        """Check if user is asking for help."""
        help_indicators = [
            "help", "how do i", "can you", "please", "i need", "need help",
            "stuck", "confused", "don't understand", "having trouble",
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in help_indicators)

    def get_tone_adjustment(self, text: str) -> str:
        """
        Get recommended tone adjustment based on sentiment.

        Args:
            text: Input text

        Returns:
            Tone adjustment recommendation
        """
        analysis = self.analyze_sentiment(text)

        if analysis["sentiment"] == "negative":
            return "empathetic"
        elif analysis["sentiment"] == "positive":
            return "enthusiastic"
        elif self.is_frustrated(text):
            return "supportive"
        elif self.is_asking_for_help(text):
            return "helpful"
        else:
            return "neutral"

    def __repr__(self) -> str:
        return f"SentimentAnalyzer(use_transformers={self.use_transformers}, model='{self.model_name}')"