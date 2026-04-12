"""
Knowledge Graph Context Injection
Provides native context provider for the Knowledge Graph.
"""

from typing import List, Dict, Any, Optional, Tuple
import networkx as nx
import numpy as np
from .graph import KnowledgeGraph
from ..nlp.contextual_embeddings import ContextualEmbedder

class SurgicalChunker:
    """
    Breaks down retrieved Graph-RAG context into small, semantic blocks.
    """
    def __init__(self, chunk_size: int = 60):
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> List[str]:
        """
        Splits text into semantic blocks. For Graph-RAG, we treat each
        entity description or relationship line as a semantic block.
        """
        if not text:
            return []

        # Split by newlines as the current get_context_for_entities uses them
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_len = 0

        for line in lines:
            if not line.strip():
                continue

            if current_len + len(line) > self.chunk_size and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_len = 0

            current_chunk.append(line)
            current_len += len(line) + 1

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

class ImportanceScorer:
    """
    Ranks semantic blocks based on their relation to the user's intent.
    """
    def __init__(self, embedder: ContextualEmbedder):
        self.embedder = embedder

    def score_blocks(self, query: str, blocks: List[str]) -> List[Tuple[float, str]]:
        """
        Scores blocks using cosine similarity between query embedding and block embedding.
        """
        if not blocks:
            return []

        query_emb = self.embedder.get_sentence_embedding(query)
        scored_blocks = []

        for block in blocks:
            block_emb = self.embedder.get_sentence_embedding(block)
            # Cosine similarity
            similarity = np.dot(query_emb, block_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(block_emb) + 1e-9
            )
            scored_blocks.append((float(similarity), block))

        # Sort by score descending
        scored_blocks.sort(key=lambda x: x[0], reverse=True)
        return scored_blocks

class ContextInjector:
    """
    Analyzes user queries for entities and injects relevant Knowledge Graph
    context directly into the system prompt.
    """
    def __init__(self, knowledge_graph: KnowledgeGraph, embedder: Optional[ContextualEmbedder] = None):
        self.kg = knowledge_graph
        self.embedder = embedder or ContextualEmbedder()
        self.chunker = SurgicalChunker()
        self.scorer = ImportanceScorer(self.embedder)

    def extract_entities(self, text: str, entity_recognizer: Any) -> List[str]:
        """
        Extracts entity IDs from the text using the provided entity recognizer.
        """
        if not entity_recognizer:
            return []

        entities = entity_recognizer.recognize_entities(text)
        return [e["text"] for e in entities]

    def get_context_for_entities(self, entities: List[str]) -> str:
        """
        Retrieves relevant context from the Knowledge Graph for a set of entities.
        """
        if not entities or not self.kg:
            return ""

        context_parts = []
        seen_entities = set()

        for entity_id in entities:
            if entity_id in seen_entities:
                continue

            # 1. Get core entity info
            entity_info = self.kg.get_entity(entity_id)
            if entity_info:
                context_parts.append(f"Entity: {entity_id} ({entity_info.get('type')})")
                seen_entities.add(entity_id)

            # 2. Find similar entities
            similar = self.kg.find_similar_entities(entity_id, max_results=3)
            for sim_id, score in similar:
                if sim_id not in seen_entities:
                    sim_info = self.kg.get_entity(sim_id)
                    if sim_info:
                        context_parts.append(f"Related Entity: {sim_id} ({sim_info.get('type')})")
                        seen_entities.add(sim_id)

        # 3. Get a small subgraph for connected entities
        if entities:
            subgraph = self.kg.get_subgraph(entities, depth=1)
            relationships = []
            for u, v, data in subgraph.edges(data=True):
                rel_type = data.get("type", "unknown")
                relationships.append(f"{u} --{rel_type}--> {v}")

            if relationships:
                context_parts.append("\nRelationships:\n" + "\n".join(relationships))

        return "\n".join(context_parts)

    def compress_graph_context(self, context: str, subgraph: nx.Graph) -> str:
        """
        Compresses the graph context by pruning low-importance edges and
        grouping related nodes into semantic clusters based on centrality.
        """
        if not context or subgraph is None or len(subgraph.nodes) == 0:
            return context

        # 1. Calculate Centrality (Node Degree)
        degree_centrality = nx.degree_centrality(subgraph)
        avg_centrality = sum(degree_centrality.values()) / len(degree_centrality) if degree_centrality else 0

        # 2. Prune low-importance edges (edges connecting two low-centrality nodes)
        pruned_edges = []
        for u, v, data in subgraph.edges(data=True):
            if degree_centrality[u] < avg_centrality * 0.5 and degree_centrality[v] < avg_centrality * 0.5:
                pruned_edges.append((u, v))

        # We don't actually modify the subgraph object to avoid side effects,
        # but we filter the context representation.

        # 3. Semantic Clustering
        # Group nodes by type or common neighbor to reduce redundancy
        clusters = {}
        for node, data in subgraph.nodes(data=True):
            node_type = data.get('type', 'unknown')
            if node_type not in clusters:
                clusters[node_type] = []
            clusters[node_type].append(node)

        compressed_parts = []

        # Add High-Centrality Entities with condensed info
        important_nodes = [node for node, cent in degree_centrality.items() if cent >= avg_centrality]
        for node in important_nodes:
            info = self.kg.get_entity(node)
            if info:
                compressed_parts.append(f"Key {info.get('type')}: {node}")

        # Add Clusters for lower importance nodes
        for node_type, members in clusters.items():
            # Only add members that aren't already listed as key nodes
            cluster_members = [m for m in members if m not in important_nodes]
            if cluster_members:
                compressed_parts.append(f"Cluster {node_type}: {', '.join(cluster_members)}")

        # Add only high-importance relationships
        important_rels = []
        for u, v, data in subgraph.edges(data=True):
            if (u, v) not in pruned_edges:
                rel_type = data.get("type", "unknown")
                important_rels.append(f"{u}-{rel_type}-{v}")

        if important_rels:
            compressed_parts.append("Rels: " + "; ".join(important_rels))

        return "\n".join(compressed_parts)

    def inject_context(self, user_input: str, entity_recognizer: Any, top_n: int = 5, surgical: bool = True) -> str:
        """
        The main entry point to analyze and retrieve KG context.
        """
        entities = self.extract_entities(user_input, entity_recognizer)

        # Retrieve raw context and the subgraph for compression
        if not entities or not self.kg:
            return ""

        subgraph = self.kg.get_subgraph(entities, depth=1)
        raw_context = self.get_context_for_entities(entities)

        if not surgical:
            # Apply standard compression
            compressed_context = self.compress_graph_context(raw_context, subgraph)
            if not compressed_context:
                return ""
            return f"\nKnowledge Graph Context (Compressed):\n{compressed_context}\n"

        # Surgical Injection Flow:
        # 1. Get raw context (detailed)
        # 2. Chunk into semantic blocks
        # 3. Score blocks based on user intent
        # 4. Select top-N

        blocks = self.chunker.chunk(raw_context)
        scored_blocks = self.scorer.score_blocks(user_input, blocks)

        # filter for blocks with high similarity (> 0.5) to maximize precision
        top_blocks = [block for score, block in scored_blocks if score > 0.5][:top_n]
        surgical_context = "\n".join(top_blocks)

        if not surgical_context:
            # Fallback to standard compression if surgical fails to find relevant blocks
            compressed_context = self.compress_graph_context(raw_context, subgraph)
            return f"\nKnowledge Graph Context (Compressed):\n{compressed_context}\n" if compressed_context else ""

        return f"\nKnowledge Graph Context (Surgical):\n{surgical_context}\n"
