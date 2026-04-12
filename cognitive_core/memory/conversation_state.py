"""
Conversation State Management for Stack 3.0

Manages conversation state across multiple sessions with persistence and timeout capabilities.
Integrated into the cognitive_core memory layer.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import json
from pathlib import Path

class ConversationSession:
    """Represents a single conversation session in Stack 3.0."""

    def __init__(
        self,
        session_id: str,
        user_id: Optional[str] = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.messages: List[Dict[str, Any]] = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.metadata: Dict[str, Any] = {}
        self.context: Dict[str, Any] = {}

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a message to the session and update activity timestamp."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        })
        self.last_activity = datetime.now()

    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get messages, optionally limited to the most recent N."""
        if limit:
            return self.messages[-limit:]
        return self.messages

    def clear(self) -> None:
        """Clear session messages and context."""
        self.messages = []
        self.context = {}


class ConversationStateManager:
    """
    Manages multiple conversation sessions and state within the 3.0 memory layout.
    Handles session persistence, timeouts, and multi-user state tracking.
    """

    def __init__(
        self,
        max_sessions: int = 10,
        session_timeout_minutes: int = 60,
        persistence_path: Optional[str] = None,
    ):
        """
        Initialize the conversation state manager.

        Args:
            max_sessions: Maximum number of concurrent sessions
            session_timeout_minutes: Session timeout in minutes
            persistence_path: Path to save/load session data
        """
        self.max_sessions = max_sessions
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.sessions: Dict[str, ConversationSession] = {}
        self.active_session_id: Optional[str] = None
        self.persistence_path = persistence_path

    def create_session(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Create a new session.

        Args:
            user_id: Optional user ID for multi-user tracking
            session_id: Optional session ID
        Returns:
            Session ID
        """
        # Clean up old sessions if at max
        if len(self.sessions) >= self.max_sessions:
            self._cleanup_old_sessions()

        session_id = session_id or str(uuid.uuid4())
        session = ConversationSession(session_id, user_id)
        self.sessions[session_id] = session
        self.active_session_id = session_id

        return session_id

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get a session by ID, returning None if it has timed out."""
        session = self.sessions.get(session_id)
        if session:
            # Check timeout
            if datetime.now() - session.last_activity > self.session_timeout:
                self.delete_session(session_id)
                return None
        return session

    def get_active_session(self) -> Optional[ConversationSession]:
        """Get the currently active session."""
        if self.active_session_id:
            return self.get_session(self.active_session_id)
        return None

    def set_active_session(self, session_id: str) -> bool:
        """Set the active session if it exists."""
        if session_id in self.sessions:
            self.active_session_id = session_id
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from memory."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            if self.active_session_id == session_id:
                self.active_session_id = None
            return True
        return False

    def add_message(
        self,
        role: str,
        content: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a message to a specific or active session."""
        session = self.get_session(session_id or self.active_session_id or "")
        if not session:
            session_id = self.create_session()
            session = self.sessions[session_id]

        session.add_message(role, content, metadata)
        return True

    def get_conversation_history(
        self,
        session_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve conversation history for a session."""
        session = self.get_session(session_id or self.active_session_id or "")
        if not session:
            return []
        return session.get_messages(limit)

    def update_context(
        self,
        key: str,
        value: Any,
        session_id: Optional[str] = None,
    ) -> bool:
        """Update session-specific context."""
        session = self.get_session(session_id or self.active_session_id or "")
        if not session:
            return False
        session.context[key] = value
        return True

    def get_context(
        self,
        key: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Any:
        """Retrieve session-specific context."""
        session = self.get_session(session_id or self.active_session_id or "")
        if not session:
            return None
        if key:
            return session.context.get(key)
        return session.context

    def _cleanup_old_sessions(self) -> None:
        """Clean up expired or overflow sessions."""
        now = datetime.now()
        to_delete = []

        for session_id, session in self.sessions.items():
            if now - session.last_activity > self.session_timeout:
                to_delete.append(session_id)

        # Also delete oldest if still at max
        if len(self.sessions) - len(to_delete) >= self.max_sessions:
            oldest = min(
                self.sessions.values(),
                key=lambda s: s.last_activity
            )
            to_delete.append(oldest.session_id)

        for session_id in to_delete:
            self.delete_session(session_id)

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata and stats for a session."""
        session = self.get_session(session_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "message_count": len(session.messages),
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "metadata": session.metadata,
        }

    def get_all_sessions(self) -> List[str]:
        """List all valid active session IDs."""
        self._cleanup_old_sessions()
        return list(self.sessions.keys())

    def save_sessions(self, filepath: Optional[str] = None) -> None:
        """Save sessions to a file for persistence."""
        path = filepath or self.persistence_path
        if not path:
            return

        data = {
            session_id: {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "messages": session.messages,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "metadata": session.metadata,
                "context": session.context,
            }
            for session_id, session in self.sessions.items()
        }
        Path(path).write_text(json.dumps(data, indent=2))

    def load_sessions(self, filepath: Optional[str] = None) -> None:
        """Load sessions from a file."""
        path = filepath or self.persistence_path
        if not path or not Path(path).exists():
            return

        data = json.loads(Path(path).read_text())

        for session_id, session_data in data.items():
            session = ConversationSession(
                session_data["session_id"],
                session_data.get("user_id"),
            )
            session.messages = session_data.get("messages", [])
            session.created_at = datetime.fromisoformat(session_data["created_at"])
            session.last_activity = datetime.fromisoformat(session_data["last_activity"])
            session.metadata = session_data.get("metadata", {})
            session.context = session_data.get("context", {})
            self.sessions[session_id] = session

    def __repr__(self) -> str:
        return f"ConversationStateManager(sessions={len(self.sessions)}, max={self.max_sessions})"
