from .contextual_embeddings import ContextualEmbedder
from .entity_recognition import EntityRecognizer
from .intent_detection import IntentDetector

class NLPService:
    """
    High-level interface for NLP capabilities in Stack 3.0.
    Allows the Coordinator to access embeddings, entity recognition, and intent detection.
    """
    def __init__(self, embedder_model="bert-base-uncased", ner_model="dslim/bert-base-NER"):
        self.embedder = ContextualEmbedder(model_name=embedder_model)
        self.entity_recognizer = EntityRecognizer(model_name=ner_model)
        self.intent_detector = IntentDetector()

    def get_text_embedding(self, text: str):
        """Get a contextual embedding for the given text."""
        return self.embedder.get_embedding(text)

    def extract_entities(self, text: str):
        """Extract named entities from the given text."""
        return self.entity_recognizer.recognize_entities(text)

    def detect_intent(self, text: str):
        """Detect the intent of the given text."""
        return self.intent_detector.detect_intent(text)

    def compute_text_similarity(self, text1: str, text2: str):
        """Compute similarity between two pieces of text."""
        return self.embedder.compute_similarity(text1, text2)
