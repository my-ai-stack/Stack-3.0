"""
Contextual Embeddings using BERT/RoBERTa

Provides contextual word embeddings for improved NLP understanding.
"""

from typing import List, Optional, Dict, Any
import numpy as np
from functools import lru_cache
import torch


class ContextualEmbedder:
    """Generate contextual embeddings using BERT or similar models."""

    def __init__(
        self,
        model_name: str = "bert-base-uncased",
        device: Optional[str] = None,
        cache_size: int = 1000,
    ):
        """
        Initialize the contextual embedder.

        Args:
            model_name: Name of the BERT model to use
            device: Device to run on ('cuda' or 'cpu')
            cache_size: Maximum number of embeddings to cache
        """
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.cache_size = cache_size
        self._model = None
        self._tokenizer = None
        self._embedding_cache: Dict[str, np.ndarray] = {}

    def _load_model(self):
        """Lazy load the BERT model."""
        if self._model is None:
            try:
                from transformers import AutoModel, AutoTokenizer
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModel.from_pretrained(self.model_name)
                self._model.to(self.device)
                self._model.eval()
            except ImportError:
                raise ImportError("transformers library required. Install: pip install transformers")

    def get_embedding(self, text: str, layer: int = -1) -> np.ndarray:
        """
        Get contextual embedding for a text.

        Args:
            text: Input text
            layer: Which layer to extract (-1 for last hidden state)

        Returns:
            Embedding vector as numpy array
        """
        # Check cache
        cache_key = f"{text}:{layer}"
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        self._load_model()

        with torch.no_grad():
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            ).to(self.device)

            outputs = self._model(**inputs)
            # Get the mean of the last hidden state
            embedding = outputs.last_hidden_state.mean(dim=1).cpu().numpy()[0]

        # Cache the embedding
        if len(self._embedding_cache) < self.cache_size:
            self._embedding_cache[cache_key] = embedding

        return embedding

    def get_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """
        Get embeddings for a batch of texts.

        Args:
            texts: List of input texts

        Returns:
            Array of embeddings (num_texts x embedding_dim)
        """
        self._load_model()

        with torch.no_grad():
            inputs = self._tokenizer(
                texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            ).to(self.device)

            outputs = self._model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1).cpu().numpy()

        return embeddings

    def get_sentence_embedding(self, text: str) -> np.ndarray:
        """
        Get a sentence-level embedding using [CLS] token.

        Args:
            text: Input text

        Returns:
            Sentence embedding vector
        """
        self._load_model()

        with torch.no_grad():
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            ).to(self.device)

            outputs = self._model(**inputs)
            # Use [CLS] token embedding (first token)
            embedding = outputs.last_hidden_state[0, 0].cpu().numpy()

        return embedding

    def compute_similarity(
        self,
        text1: str,
        text2: str,
        method: str = "cosine",
    ) -> float:
        """
        Compute similarity between two texts.

        Args:
            text1: First text
            text2: Second text
            method: Similarity method ('cosine' or 'dot')

        Returns:
            Similarity score
        """
        emb1 = self.get_embedding(text1)
        emb2 = self.get_embedding(text2)

        if method == "cosine":
            # Cosine similarity
            dot = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            return dot / (norm1 * norm2)
        else:
            # Dot product
            return np.dot(emb1, emb2)

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._embedding_cache.clear()

    def __repr__(self) -> str:
        return f"ContextualEmbedder(model='{self.model_name}', device='{self.device}')"
