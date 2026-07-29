#!/usr/bin/env python3
"""
hypergraph.py
Hypergraph Cluster Formation based on Star Similarity
"""

from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
import math


@dataclass
class Cluster:
    """A cluster of nodes with similar star patterns"""
    id: str
    nodes: Set[str]
    centroid: List[float]
    phase_range: Tuple[float, float]
    credibility: float = 0.0


class HypergraphClusterer:
    """
    Forms clusters based on star similarity using hierarchical approach.
    """

    def __init__(self, min_cluster_size: int = 2, similarity_threshold: float = 0.7):
        self.min_cluster_size = min_cluster_size
        self.similarity_threshold = similarity_threshold
        self.clusters: List[Cluster] = []

    def build_clusters(self, stars: Dict[str, List[int]]) -> List[Cluster]:
        """
        Build clusters from node stars.
        """
        if len(stars) < self.min_cluster_size:
            return []

        # Convert to list for processing
        node_ids = list(stars.keys())
        visited = set()
        clusters = []

        for node_id in node_ids:
            if node_id in visited:
                continue
            # Greedy cluster formation
            cluster_nodes = {node_id}
            star_vec = stars[node_id]
            for other_id in node_ids:
                if other_id in visited or other_id == node_id:
                    continue
                other_vec = stars[other_id]
                sim = self._similarity(star_vec, other_vec)
                if sim >= self.similarity_threshold:
                    cluster_nodes.add(other_id)
            if len(cluster_nodes) >= self.min_cluster_size:
                cluster_id = f"cluster_{len(clusters):03d}"
                centroid = self._centroid([stars[n] for n in cluster_nodes])
                # Placeholder phase range
                clusters.append(Cluster(
                    id=cluster_id,
                    nodes=cluster_nodes,
                    centroid=centroid,
                    phase_range=(0.0, 1.0),
                    credibility=0.5
                ))
                visited.update(cluster_nodes)
        self.clusters = clusters
        return clusters

    def _similarity(self, v1: List[int], v2: List[int]) -> float:
        """Cosine similarity between two star vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a*b for a,b in zip(v1,v2))
        norm1 = math.sqrt(sum(a*a for a in v1))
        norm2 = math.sqrt(sum(b*b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def _centroid(self, vectors: List[List[int]]) -> List[float]:
        """Calculate centroid of vectors."""
        if not vectors:
            return []
        n = len(vectors[0])
        centroid = [0.0]*n
        for v in vectors:
            for i in range(n):
                centroid[i] += v[i]
        return [c / len(vectors) for c in centroid]

    def get_cluster_for_node(self, node_id: str) -> Optional[Cluster]:
        """Find cluster containing a node."""
        for cluster in self.clusters:
            if node_id in cluster.nodes:
                return cluster
        return None

    def get_cluster_count(self) -> int:
        return len(self.clusters)
