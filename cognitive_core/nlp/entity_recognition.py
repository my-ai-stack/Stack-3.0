"""
Entity Recognition Module

Provides Named Entity Recognition (NER) for extracting entities from text.
"""

from typing import List, Dict, Optional, Any
import re


class EntityRecognizer:
    """Extract named entities from text using pattern matching and NER."""

    def __init__(
        self,
        use_transformers: bool = True,
        model_name: str = "dslim/bert-base-NER",
    ):
        """
        Initialize the entity recognizer.

        Args:
            use_transformers: Whether to use transformer-based NER
            model_name: Name of the NER model (if using transformers)
        """
        self.use_transformers = use_transformers and self._check_transformers()
        self.model_name = model_name
        self._model = None
        self._tokenizer = None

        # Define entity patterns for rule-based fallback
        self._patterns = {
            "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "URL": r'https?://[^\s]+',
            "PHONE": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "IP_ADDRESS": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            "DATE": r'\b\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b',
            "TIME": r'\b\d{1,2}:\d{2}(?:\s*[AaPp][Mm])?\b',
            "FILE_PATH": r'(?:/[a-zA-Z0-9_.-]+)+',
            "CODE": r'`[^`]+`',
            "QUOTED_STRING": r'"[^"]*"|\'[^\']*\'',
        }

    def _check_transformers(self) -> bool:
        """Check if transformers is available."""
        try:
            import transformers
            return True
        except ImportError:
            return False

    def _load_transformer_model(self):
        """Lazy load the transformer NER model."""
        if self._model is None:
            try:
                from transformers import AutoTokenizer, AutoModelForTokenClassification
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModelForTokenClassification.from_pretrained(self.model_name)
                self._model.eval()
            except Exception as e:
                print(f"Warning: Could not load transformer NER model: {e}")
                self.use_transformers = False

    def recognize_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Recognize entities in text.

        Args:
            text: Input text

        Returns:
            List of entity dictionaries with 'text', 'type', 'start', 'end'
        """
        entities = []

        # Use transformer-based NER if available
        if self.use_transformers:
            try:
                entities.extend(self._recognize_transformers(text))
            except Exception:
                pass

        # Add rule-based entities
        entities.extend(self._recognize_patterns(text))

        # Sort by position and remove overlaps
        entities = self._resolve_overlaps(entities)

        return entities

    def _recognize_transformers(self, text: str) -> List[Dict[str, Any]]:
        """Use transformer model for NER."""
        self._load_transformer_model()

        from transformers import pipeline
        from typing import List, Dict, Any

        # Create pipeline if not exists
        if not hasattr(self, "_ner_pipeline"):
            self._ner_pipeline = pipeline(
                "ner",
                model=self._model,
                tokenizer=self._tokenizer,
                aggregation_strategy="simple",
            )
        results = self._ner_pipeline(text)

        entities = []
        for result in results:
            # Map NER tags to simpler types
            entity_type = self._map_ner_tag(result.get("entity_group", ""))

            if entity_type:
                entities.append({
                    "text": result["word"],
                    "type": entity_type,
                    "start": result.get("start", 0),
                    "end": result.get("end", 0),
                    "score": result.get("score", 1.0),
                })

        return entities

    def _map_ner_tag(self, tag: str) -> Optional[str]:
        """Map NER tags to standard entity types."""
        tag_mapping = {
            "PER": "PERSON",
            "ORG": "ORGANIZATION",
            "LOC": "LOCATION",
            "MISC": "MISC",
        }
        return tag_mapping.get(tag)

    def _recognize_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Use pattern matching for entity recognition."""
        entities = []

        for entity_type, pattern in self._patterns.items():
            for match in re.finditer(pattern, text):
                entities.append({
                    "text": match.group(),
                    "type": entity_type,
                    "start": match.start(),
                    "end": match.end(),
                    "score": 1.0,
                })

        return entities

    def _resolve_overlaps(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove overlapping entities, keeping the higher confidence one."""
        if not entities:
            return []

        # Sort by score (descending), then by length (descending)
        entities = sorted(entities, key=lambda x: (-x.get("score", 1.0), -(x["end"] - x["start"])))

        result = []
        for entity in entities:
            overlaps = False
            for existing in result:
                if self._overlaps(entity, existing):
                    overlaps = True
                    break
            if not overlaps:
                result.append(entity)

        # Sort by position
        result = sorted(result, key=lambda x: x["start"])

        return result

    def _overlaps(self, e1: Dict[str, Any], e2: Dict[str, Any]) -> bool:
        """Check if two entities overlap."""
        return not (e1["end"] <= e2["start"] or e2["end"] <= e1["start"])

    def extract_entities_by_type(
        self,
        text: str,
        entity_type: str,
    ) -> List[str]:
        """
        Extract all entities of a specific type.

        Args:
            text: Input text
            entity_type: Type of entity to extract

        Returns:
            List of entity texts
        """
        entities = self.recognize_entities(text)
        return [e["text"] for e in entities if e["type"] == entity_type]

    def get_entity_summary(self, text: str) -> Dict[str, int]:
        """
        Get a summary of entity counts by type.

        Args:
            text: Input text

        Returns:
            Dictionary mapping entity type to count
        """
        entities = self.recognize_entities(text)
        summary: Dict[str, int] = {}
        for entity in entities:
            entity_type = entity["type"]
            summary[entity_type] = summary.get(entity_type, 0) + 1
        return summary

    def __repr__(self) -> str:
        return f"EntityRecognizer(use_transformers={self.use_transformers}, model='{self.model_name}')"
