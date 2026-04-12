"""
Feedback Collection System

Collects user feedback for continuous improvement.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path
import uuid

# Define a type for training pairs
TrainingPair = Tuple[str, str]  # (instruction, output)


class FeedbackEntry:
    """Represents a single feedback entry."""

    def __init__(
        self,
        feedback_type: str,
        user_id: Optional[str],
        message: str,
        response: str,
        rating: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.feedback_type = feedback_type  # "thumbs_up", "thumbs_down", "correction", "suggestion"
        self.user_id = user_id
        self.message = message
        self.response = response
        self.rating = rating  # 1-5 scale
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.processed = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "feedback_type": self.feedback_type,
            "user_id": self.user_id,
            "message": self.message,
            "response": self.response,
            "rating": self.rating,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "processed": self.processed,
        }


class FeedbackCollector:
    """Collects and manages user feedback."""

    def __init__(
        self,
        storage_path: str = "data/feedback",
        auto_save: bool = True,
    ):
        """
        Initialize the feedback collector.

        Args:
            storage_path: Path to store feedback data
            auto_save: Automatically save feedback to disk
        """
        self.storage_path = Path(storage_path)
        self.auto_save = auto_save
        self.feedback_list: List[FeedbackEntry] = []

        # Create storage directory if it doesn't exist
        if auto_save:
            self.storage_path.mkdir(parents=True, exist_ok=True)

    def add_feedback(
        self,
        feedback_type: str,
        message: str,
        response: str,
        user_id: Optional[str] = None,
        rating: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a feedback entry.

        Args:
            feedback_type: Type of feedback
            message: User's message
            response: AI's response
            user_id: Optional user ID
            rating: Optional rating (1-5)
            metadata: Additional metadata

        Returns:
            Feedback ID
        """
        entry = FeedbackEntry(
            feedback_type=feedback_type,
            user_id=user_id,
            message=message,
            response=response,
            rating=rating,
            metadata=metadata,
        )

        self.feedback_list.append(entry)

        if self.auto_save:
            self._save_feedback(entry)

        return entry.id

    def add_thumbs_up(
        self,
        message: str,
        response: str,
        user_id: Optional[str] = None,
    ) -> str:
        """Add positive feedback."""
        return self.add_feedback(
            feedback_type="thumbs_up",
            message=message,
            response=response,
            user_id=user_id,
            rating=5,
        )

    def add_thumbs_down(
        self,
        message: str,
        response: str,
        user_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> str:
        """Add negative feedback."""
        return self.add_feedback(
            feedback_type="thumbs_down",
            message=message,
            response=response,
            user_id=user_id,
            rating=1,
            metadata={"reason": reason} if reason else {},
        )

    def add_correction(
        self,
        message: str,
        original_response: str,
        corrected_response: str,
        user_id: Optional[str] = None,
    ) -> str:
        """Add a correction."""
        return self.add_feedback(
            feedback_type="correction",
            message=message,
            response=original_response,
            user_id=user_id,
            metadata={"corrected_response": corrected_response},
        )

    def add_suggestion(
        self,
        message: str,
        response: str,
        suggestion: str,
        user_id: Optional[str] = None,
    ) -> str:
        """Add a suggestion."""
        return self.add_feedback(
            feedback_type="suggestion",
            message=message,
            response=response,
            user_id=user_id,
            metadata={"suggestion": suggestion},
        )

    def get_feedback(
        self,
        feedback_id: str,
    ) -> Optional[FeedbackEntry]:
        """Get feedback by ID."""
        for entry in self.feedback_list:
            if entry.id == feedback_id:
                return entry
        return None

    def get_all_feedback(
        self,
        feedback_type: Optional[str] = None,
        unprocessed_only: bool = False,
    ) -> List[FeedbackEntry]:
        """Get all feedback entries."""
        results = self.feedback_list

        if feedback_type:
            results = [f for f in results if f.feedback_type == feedback_type]

        if unprocessed_only:
            results = [f for f in results if not f.processed]

        return results

    def mark_processed(self, feedback_id: str) -> bool:
        """Mark feedback as processed."""
        entry = self.get_feedback(feedback_id)
        if entry:
            entry.processed = True
            return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get feedback statistics."""
        total = len(self.feedback_list)
        if total == 0:
            return {
                "total": 0,
                "by_type": {},
                "average_rating": 0,
                "processed_count": 0,
            }

        by_type: Dict[str, int] = {}
        ratings = []

        for entry in self.feedback_list:
            by_type[entry.feedback_type] = by_type.get(entry.feedback_type, 0) + 1
            if entry.rating is not None:
                ratings.append(entry.rating)

        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        processed = sum(1 for e in self.feedback_list if e.processed)

        return {
            "total": total,
            "by_type": by_type,
            "average_rating": avg_rating,
            "processed_count": processed,
            "unprocessed_count": total - processed,
        }

    def get_corrections_for_finetuning(self) -> List[Dict[str, Any]]:
        """Get corrections formatted for fine-tuning."""
        corrections = self.get_all_feedback(feedback_type="correction")

        return [
            {
                "instruction": entry.message,
                "output": entry.metadata.get("corrected_response", entry.response),
            }
            for entry in corrections
        ]

    def export_finetuning_data(
        self,
        filepath: str,
    ) -> None:
        """Export feedback as fine-tuning data."""
        corrections = self.get_corrections_for_finetuning()
        Path(filepath).write_text(json.dumps(corrections, indent=2))

    def _save_feedback(self, entry: FeedbackEntry) -> None:
        """Save feedback to file."""
        filepath = self.storage_path / f"{entry.id}.json"
        filepath.write_text(json.dumps(entry.to_dict(), indent=2))

    def load_feedback(self) -> None:
        """Load feedback from storage directory."""
        if not self.storage_path.exists():
            return

        for filepath in self.storage_path.glob("*.json"):
            try:
                data = json.loads(filepath.read_text())
                entry = FeedbackEntry(
                    feedback_type=data["feedback_type"],
                    user_id=data.get("user_id"),
                    message=data["message"],
                    response=data["response"],
                    rating=data.get("rating"),
                    metadata=data.get("metadata", {}),
                )
                entry.id = data["id"]
                entry.processed = data.get("processed", False)
                entry.created_at = datetime.fromisoformat(data["created_at"])
                self.feedback_list.append(entry)
            except Exception as e:
                print(f"Error loading feedback from {filepath}: {e}")

    def clear_old_feedback(self, days: int = 30) -> int:
        """Clear feedback older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        original_count = len(self.feedback_list)

        self.feedback_list = [
            f for f in self.feedback_list
            if f.created_at > cutoff
        ]

        return original_count - len(self.feedback_list)

    def __repr__(self) -> str:
        stats = self.get_statistics()
        return f"FeedbackCollector(total={stats['total']}, unprocessed={stats['unprocessed_count']})"


# Add missing import
from datetime import timedelta

class TrainingPairSynthesizer:
    """
    Synthesizes high-quality training pairs from negative feedback and corrections.
    This module acts as the 'synthesis' part of the closed-loop system.
    """

    def __init__(self, model_client: Any = None):
        """
        Initialize the synthesizer.

        Args:
            model_client: An optional LLM client to help refine synthetic corrections
                         if only a 'thumbs_down' is provided without a full correction.
        """
        self.model_client = model_client

    def synthesize(self, entry: 'FeedbackEntry') -> Optional[TrainingPair]:
        """
        Converts a feedback entry into a high-quality training pair.

        Args:
            entry: The FeedbackEntry to synthesize.

        Returns:
            A TrainingPair (instruction, corrected_response) or None if not synthesizable.
        """
        if entry.feedback_type == "correction":
            # Case 1: Explicit correction provided.
            # Use the provided corrected response as the gold label.
            corrected_response = entry.metadata.get("corrected_response")
            if corrected_response:
                return (entry.message, corrected_response)

        elif entry.feedback_type == "thumbs_down":
            # Case 2: Negative feedback without explicit correction.
            # Attempt to synthesize a correction if a model_client is available,
            # or if there's a reason in metadata that can be used to guide correction.
            reason = entry.metadata.get("reason", "")
            if self.model_client:
                return self._refine_with_model(entry.message, entry.response, reason)

        return None

    def _refine_with_model(self, instruction: str, failed_response: str, reason: str) -> Optional[TrainingPair]:
        """
        Uses an LLM to generate a corrected version of a failed response.
        """
        prompt = (
            f"Instruction: {instruction}\n"
            f"Failed Response: {failed_response}\n"
            f"Feedback Reason: {reason}\n\n"
            f"Please provide a high-quality, corrected response that fixes the errors "
            f"mentioned in the feedback."
        )
        try:
            # Assuming model_client has a generate/complete method
            corrected = self.model_client.generate(prompt)
            return (instruction, corrected)
        except Exception as e:
            print(f"Error synthesizing correction via model: {e}")
            return None


class ClosedLoopLearningPipeline:
    """
    The main pipeline that monitors feedback and triggers the synthesis of training data.
    """

    def __init__(self, collector: 'FeedbackCollector', synthesizer: TrainingPairSynthesizer):
        self.collector = collector
        self.synthesizer = synthesizer
        self.training_dataset: List[TrainingPair] = []

    def process_new_feedback(self):
        """
        Monitors for 'thumbs_down' and 'correction' feedback and processes them into training pairs.
        """
        # Only process unprocessed feedback of relevant types
        unprocessed = self.collector.get_all_feedback(unprocessed_only=True)

        for entry in unprocessed:
            if entry.feedback_type in ["thumbs_down", "correction"]:
                pair = self.synthesizer.synthesize(entry)
                if pair:
                    self.training_dataset.append(pair)
                    self.collector.mark_processed(entry.id)
                    print(f"Synthesized training pair from feedback {entry.id}")

    def export_dataset(self, filepath: str):
        """Exports the synthesized training pairs to a JSONL file for fine-tuning."""
        data = [{"instruction": inst, "output": out} for inst, out in self.training_dataset]
        with open(filepath, 'w') as f:
            for item in data:
                f.write(json.dumps(item) + '\n')
        print(f"Exported {len(data)} training pairs to {filepath}")
