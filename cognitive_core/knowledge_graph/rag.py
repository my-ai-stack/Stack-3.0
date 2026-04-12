"""
RAG (Retrieval-Augmented Generation) Engine

Provides context retrieval for augmented generation.
"""

from typing import List, Dict, Optional, Any, Tuple
import numpy as np
from collections import defaultdict
import re
from datetime import datetime


class Document:
    """Represents a document for RAG."""

    def __init__(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = doc_id
        self.content = content
        self.metadata = metadata or {}
        self.embeddings: Optional[np.ndarray] = None
        self.created_at = self.metadata.get("created_at", datetime.now().isoformat())

    def __repr__(self) -> str:
        return f"Document(id='{self.id}', content_length={len(self.content)})"


class RAGEngine:
    """Retrieval-Augmented Generation engine for context-aware responses."""

    def __init__(
        self,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
    ):
        """
        Initialize the RAG engine.

        Args:
            top_k: Number of top results to retrieve
            similarity_threshold: Minimum similarity for retrieval
        """
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.documents: Dict[str, Document] = {}
        self.document_embeddings: Dict[str, np.ndarray] = {}
        self._index_initialized = False
        self._keyword_index: Dict[str, set] = defaultdict(set)

    def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[np.ndarray] = None,
    ) -> None:
        """
        Add a document to the RAG index.

        Args:
            doc_id: Unique document ID
            content: Document content
            metadata: Document metadata
            embedding: Pre-computed embedding (optional)
        """
        doc = Document(doc_id, content, metadata)
        if embedding is not None:
            doc.embeddings = embedding

        self.documents[doc_id] = doc

        # Update keyword index
        keywords = self._extract_keywords(content)
        for keyword in keywords:
            self._keyword_index[keyword].add(doc_id)

        self._index_initialized = False

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter short words and common words
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                     'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                     'through', 'during', 'before', 'after', 'above', 'below',
                     'between', 'under', 'again', 'further', 'then', 'once'}
        return [w for w in words if len(w) > 2 and w not in stopwords]

    def _build_index(self) -> None:
        """Build similarity index."""
        if not self.documents:
            return

        # Initialize embeddings for documents without them
        for doc_id, doc in self.documents.items():
            if doc.embeddings is None:
                # Create simple embedding based on word frequencies
                doc.embeddings = self._create_simple_embedding(doc.content)

        self._index_initialized = True

    def _create_simple_embedding(self, text: str) -> np.ndarray:
        """Create a simple bag-of-words embedding."""
        keywords = self._extract_keywords(text)
        embedding = np.zeros(len(self._keyword_index))

        for i, keyword in enumerate(self._keyword_index.keys()):
            if keyword in keywords:
                embedding[i] = keywords.count(keyword)

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding /= norm

        return embedding

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        use_keyword_index: bool = True,
    ) -> List[Tuple[Document, float]]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Query text
            top_k: Override default top_k
            use_keyword_index: Use keyword pre-filtering

        Returns:
            List of (document, similarity_score) tuples
        """
        if not self.documents:
            return []

        self._build_index()

        top_k = top_k or self.top_k

        # Create query embedding
        query_embedding = self._create_simple_embedding(query)

        # Get candidate document IDs
        candidate_ids = set(self.documents.keys())
        if use_keyword_index:
            query_keywords = self._extract_keywords(query)
            keyword_candidates = set()
            for keyword in query_keywords:
                keyword_candidates.update(self._keyword_index.get(keyword, set()))
            if keyword_candidates:
                candidate_ids &= keyword_candidates

        # Calculate similarities
        scores = []
        for doc_id in candidate_ids:
            doc = self.documents[doc_id]
            if doc.embeddings is not None:
                similarity = np.dot(query_embedding, doc.embeddings)
                if similarity >= self.similarity_threshold:
                    scores.append((doc, similarity))

        # Sort by similarity and return top_k
        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]

    def retrieve_as_context(
        self,
        query: str,
        max_context_length: int = 1000,
    ) -> str:
        """
        Retrieve documents and format as context string.

        Args:
            query: Query text
            max_context_length: Maximum length of context

        Returns:
            Formatted context string
        """
        results = self.retrieve(query)

        if not results:
            return ""

        context_parts = []
        current_length = 0

        for doc, score in results:
            if current_length >= max_context_length:
                break

            # Add document with relevance score
            context = f"[Relevance: {score:.2f}]\n{doc.content}\n"
            if current_length + len(context) <= max_context_length:
                context_parts.append(context)
                current_length += len(context)

        return "\n".join(context_parts)

    def search(self, query: str) -> List[Document]:
        """Simple text search in documents."""
        results = []
        query_lower = query.lower()

        for doc in self.documents.values():
            if query_lower in doc.content.lower():
                results.append(doc)

        return results

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return self.documents.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document."""
        if doc_id in self.documents:
            # Update keyword index
            keywords = self._extract_keywords(self.documents[doc_id].content)
            for keyword in keywords:
                self._keyword_index[keyword].discard(doc_id)

            del self.documents[doc_id]
            self._index_initialized = False
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG engine statistics."""
        return {
            "num_documents": len(self.documents),
            "num_keywords": len(self._keyword_index),
            "index_initialized": self._index_initialized,
        }

    def __repr__(self) -> str:
        stats = self.get_stats()
        return f"RAGEngine(docs={stats['num_documents']}, keywords={stats['num_keywords']})"