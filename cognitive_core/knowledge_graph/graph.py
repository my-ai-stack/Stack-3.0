"""
Knowledge Graph Implementation

Graph-based knowledge representation using networkx.
"""

from typing import List, Dict, Optional, Any, Set, Tuple
import networkx as nx
import numpy as np
from datetime import datetime
import json
from pathlib import Path


class KnowledgeGraph:
    """Graph-based knowledge representation with entities and relationships."""

    def __init__(
        self,
        max_nodes: int = 10000,
        max_edges: int = 50000,
    ):
        """
        Initialize the knowledge graph.

        Args:
            max_nodes: Maximum number of nodes
            max_edges: Maximum number of edges
        """
        self.max_nodes = max_nodes
        self.max_edges = max_edges
        self.graph = nx.MultiDiGraph()
        self._node_attributes: Dict[str, Dict[str, Any]] = {}
        self._edge_attributes: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def add_entity(
        self,
        entity_id: str,
        entity_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add an entity to the knowledge graph.

        Args:
            entity_id: Unique identifier for the entity
            entity_type: Type of entity (e.g., 'person', 'concept', 'code')
            properties: Additional properties

        Returns:
            True if added, False if limit reached
        """
        if self.graph.number_of_nodes() >= self.max_nodes:
            return False

        if entity_id not in self.graph:
            self.graph.add_node(entity_id, type=entity_type)

        self._node_attributes[entity_id] = {
            "type": entity_type,
            "created_at": datetime.now().isoformat(),
            "properties": properties or {},
        }

        return True

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add a relationship between entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Type of relationship
            properties: Additional properties

        Returns:
            True if added, False if limit reached or entities don't exist
        """
        if self.graph.number_of_edges() >= self.max_edges:
            return False

        # Ensure entities exist
        if source_id not in self.graph:
            self.add_entity(source_id, "unknown")
        if target_id not in self.graph:
            self.add_entity(target_id, "unknown")

        self.graph.add_edge(source_id, target_id, type=relationship_type)

        edge_key = (source_id, target_id)
        self._edge_attributes[edge_key] = {
            "type": relationship_type,
            "created_at": datetime.now().isoformat(),
            "properties": properties or {},
        }

        return True

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity information."""
        if entity_id not in self.graph:
            return None

        return {
            "id": entity_id,
            **self._node_attributes.get(entity_id, {}),
        }

    def get_relationships(
        self,
        entity_id: str,
        relationship_type: Optional[str] = None,
        transitive: bool = False,
        max_depth: int = 2,
    ) -> List[Dict[str, Any]]:
        """Get relationships for an entity.

        Args:
            entity_id: The entity to find relationships for.
            relationship_type: Optional filter for relationship type.
            transitive: If True, perform transitive reasoning to infer relationships.
            max_depth: Maximum depth for transitive reasoning.
        """
        if entity_id not in self.graph:
            return []

        if not transitive:
            relationships = []
            for source, target, data in self.graph.edges(data=True):
                if source == entity_id or target == entity_id:
                    rel_type = data.get("type", "unknown")
                    if relationship_type and rel_type != relationship_type:
                        continue

                    relationships.append({
                        "source": source,
                        "target": target,
                        "type": rel_type,
                    })
            return relationships

        # Transitive Reasoning implementation
        # We use a BFS/DFS approach to find reachable nodes and infer relationships
        inferred_relationships = []
        visited = {entity_id}
        queue = [(entity_id, [], 0)]  # (current_node, path_of_rels, current_depth)

        while queue:
            current_node, path, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for _, neighbor, data in self.graph.out_edges(current_node, data=True):
                rel_type = data.get("type", "unknown")

                # If we're filtering by type, we only follow those edges
                if relationship_type and rel_type != relationship_type:
                    continue

                new_path = path + [rel_type]

                # If we found a node not directly connected, it's a transitive relationship
                if not self.graph.has_edge(entity_id, neighbor):
                    inferred_relationships.append({
                        "source": entity_id,
                        "target": neighbor,
                        "type": f"transitive_{'_'.join(new_path)}",
                        "path": [current_node] + [neighbor] if depth == 0 else path,
                        "depth": depth + 1
                    })

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, new_path, depth + 1))

        return inferred_relationships

    def find_similar_entities(
        self,
        entity_id: str,
        max_results: int = 5,
    ) -> List[Tuple[str, float]]:
        """
        Find similar entities using graph-based similarity.

        Args:
            entity_id: Entity to find similar
            max_results: Maximum number of results

        Returns:
            List of (entity_id, similarity_score) tuples
        """
        if entity_id not in self.graph:
            return []

        # Use common neighbors as simple similarity
        neighbors = set(self.graph.neighbors(entity_id))
        scores = []

        for node in self.graph.nodes():
            if node == entity_id:
                continue

            node_neighbors = set(self.graph.neighbors(node))
            common = len(neighbors & node_neighbors)

            if common > 0:
                # Jaccard-like similarity
                union = len(neighbors | node_neighbors)
                score = common / union if union > 0 else 0
                scores.append((node, score))

        scores.sort(key=lambda x: -x[1])
        return scores[:max_results]

    def search_entities(
        self,
        entity_type: Optional[str] = None,
        property_filter: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Search for entities.

        Args:
            entity_type: Filter by entity type
            property_filter: Filter by properties

        Returns:
            List of matching entity IDs
        """
        results = []

        for node in self.graph.nodes():
            attrs = self._node_attributes.get(node, {})

            # Check type filter
            if entity_type and attrs.get("type") != entity_type:
                continue

            # Check property filter
            if property_filter:
                props = attrs.get("properties", {})
                if not all(props.get(k) == v for k, v in property_filter.items()):
                    continue

            results.append(node)

        return results

    def get_subgraph(
        self,
        entity_ids: List[str],
        depth: int = 1,
    ) -> nx.MultiDiGraph:
        """
        Get a subgraph around specified entities.

        Args:
            entity_ids: Center entities
            depth: How many hops to include

        Returns:
            Subgraph
        """
        nodes = set(entity_ids)

        for _ in range(depth):
            for entity in list(nodes):
                nodes.update(self.graph.neighbors(entity))

        return self.graph.subgraph(nodes).copy()

    def export_json(self, filepath: str) -> None:
        """Export graph to JSON."""
        data = {
            "nodes": [
                {
                    "id": node,
                    **self._node_attributes.get(node, {}),
                }
                for node in self.graph.nodes()
            ],
            "edges": [
                {
                    "source": source,
                    "target": target,
                    "type": data.get("type", "unknown"),
                }
                for source, target, data in self.graph.edges(data=True)
            ],
        }

        Path(filepath).write_text(json.dumps(data, indent=2))

    def import_json(self, filepath: str) -> None:
        """Import graph from JSON."""
        data = json.loads(Path(filepath).read_text())

        for node_data in data.get("nodes", []):
            node_id = node_data.pop("id")
            self.add_entity(node_id, node_data.get("type", "unknown"), node_data.get("properties"))

        for edge_data in data.get("edges", []):
            self.add_relationship(
                edge_data["source"],
                edge_data["target"],
                edge_data.get("type", "unknown"),
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "num_nodes": self.graph.number_of_nodes(),
            "num_edges": self.graph.number_of_edges(),
            "num_node_types": len(set(
                attrs.get("type") for attrs in self._node_attributes.values()
            )),
            "num_edge_types": len(set(
                data.get("type") for _, _, data in self.graph.edges(data=True)
            )),
        }

    def __repr__(self) -> str:
        stats = self.get_stats()
        return f"KnowledgeGraph(nodes={stats['num_nodes']}, edges={stats['num_edges']})"