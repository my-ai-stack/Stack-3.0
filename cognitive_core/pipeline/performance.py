"""
Performance Monitoring System

Monitors and tracks model performance metrics.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import json
from pathlib import Path


class PerformanceMetric:
    """Represents a single performance metric."""

    def __init__(
        self,
        metric_type: str,
        value: float,
        unit: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.metric_type = metric_type
        self.value = value
        self.unit = unit
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_type": self.metric_type,
            "value": self.value,
            "unit": self.unit,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class PerformanceMonitor:
    """Monitors model performance over time."""

    def __init__(
        self,
        storage_path: str = "data/performance",
    ):
        """
        Initialize the performance monitor.

        Args:
            storage_path: Path to store performance data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.metrics: List[PerformanceMetric] = []
        self._session_stats: Dict[str, Any] = {
            "total_sessions": 0,
            "total_messages": 0,
            "total_conversations": 0,
        }

    def record_metric(
        self,
        metric_type: str,
        value: float,
        unit: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a performance metric."""
        metric = PerformanceMetric(metric_type, value, unit, metadata)
        self.metrics.append(metric)

    def record_response_time(self, seconds: float) -> None:
        """Record response time."""
        self.record_metric("response_time", seconds, "seconds")

    def record_token_count(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Record token count."""
        self.record_metric(
            "prompt_tokens",
            prompt_tokens,
            "tokens",
            {"completion_tokens": completion_tokens},
        )

    def record_successful_interaction(self) -> None:
        """Record a successful interaction."""
        self.record_metric("successful_interaction", 1, "count")

    def record_failed_interaction(self, error_type: str) -> None:
        """Record a failed interaction."""
        self.record_metric(
            "failed_interaction",
            1,
            "count",
            {"error_type": error_type},
        )

    def record_user_rating(self, rating: int) -> None:
        """Record user rating."""
        self.record_metric("user_rating", rating, "stars")

    def get_metrics(
        self,
        metric_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[PerformanceMetric]:
        """Get recorded metrics."""
        results = self.metrics

        if metric_type:
            results = [m for m in results if m.metric_type == metric_type]

        if since:
            results = [m for m in results if m.timestamp >= since]

        return results[-limit:]

    def get_average_response_time(
        self,
        since: Optional[datetime] = None,
    ) -> float:
        """Get average response time."""
        metrics = self.get_metrics("response_time", since=since)
        if not metrics:
            return 0.0
        return sum(m.value for m in metrics) / len(metrics)

    def get_success_rate(
        self,
        since: Optional[datetime] = None,
    ) -> float:
        """Get interaction success rate."""
        successful = len(self.get_metrics("successful_interaction", since=since))
        failed = len(self.get_metrics("failed_interaction", since=since))

        total = successful + failed
        if total == 0:
            return 0.0

        return successful / total

    def get_average_rating(
        self,
        since: Optional[datetime] = None,
    ) -> float:
        """Get average user rating."""
        ratings = self.get_metrics("user_rating", since=since)
        if not ratings:
            return 0.0
        return sum(m.value for m in ratings) / len(ratings)

    def get_summary(
        self,
        since: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get performance summary."""
        since = since or (datetime.now() - timedelta(hours=24))

        return {
            "period": "last_24_hours" if since == datetime.now() - timedelta(hours=24) else "custom",
            "average_response_time": self.get_average_response_time(since),
            "success_rate": self.get_success_rate(since),
            "average_rating": self.get_average_rating(since),
            "total_interactions": len(self.get_metrics("successful_interaction", since=since)) +
                                 len(self.get_metrics("failed_interaction", since=since)),
            "total_tokens": sum(
                m.value for m in self.get_metrics("prompt_tokens", since=since)
            ),
        }

    def increment_session_count(self) -> None:
        """Increment session count."""
        self._session_stats["total_sessions"] += 1

    def increment_message_count(self) -> None:
        """Increment message count."""
        self._session_stats["total_messages"] += 1

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        return self._session_stats.copy()

    def export_metrics(
        self,
        filepath: Optional[str] = None,
    ) -> str:
        """Export metrics to JSON file."""
        filepath = filepath or str(self.storage_path / f"metrics_{datetime.now().strftime('%Y%m%d')}.json")

        data = {
            "exported_at": datetime.now().isoformat(),
            "metrics": [m.to_dict() for m in self.metrics],
            "session_stats": self._session_stats,
        }

        Path(filepath).write_text(json.dumps(data, indent=2))
        return filepath

    def load_metrics(
        self,
        filepath: str,
    ) -> None:
        """Load metrics from JSON file."""
        data = json.loads(Path(filepath).read_text())

        for metric_data in data.get("metrics", []):
            metric = PerformanceMetric(
                metric_type=metric_data["metric_type"],
                value=metric_data["value"],
                unit=metric_data.get("unit", ""),
                metadata=metric_data.get("metadata", {}),
            )
            metric.timestamp = datetime.fromisoformat(metric_data["timestamp"])
            self.metrics.append(metric)

        if "session_stats" in data:
            self._session_stats.update(data["session_stats"])

    def clear_old_metrics(self, days: int = 30) -> int:
        """Clear metrics older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        original_count = len(self.metrics)

        self.metrics = [
            m for m in self.metrics
            if m.timestamp > cutoff
        ]

        return original_count - len(self.metrics)

    def get_trend(
        self,
        metric_type: str,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get trend data for a metric."""
        since = datetime.now() - timedelta(hours=hours)
        metrics = self.get_metrics(metric_type, since=since)

        # Group by hour
        hourly_data: Dict[str, List[float]] = defaultdict(list)
        for m in metrics:
            hour_key = m.timestamp.strftime("%Y-%m-%d %H:00")
            hourly_data[hour_key].append(m.value)

        # Calculate hourly averages
        trend = []
        for hour, values in sorted(hourly_data.items()):
            avg = sum(values) / len(values) if values else 0
            trend.append({
                "hour": hour,
                "average": avg,
                "count": len(values),
            })

        return trend

    def __repr__(self) -> str:
        return f"PerformanceMonitor(metrics={len(self.metrics)}, sessions={self._session_stats['total_sessions']})"