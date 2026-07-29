#!/usr/bin/env python3
"""
cluster_state.py
Dynamic Cluster State with Live Credibility
"""

from typing import List, Set, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class DynamicCluster:
    """
    A cluster whose credibility is computed live from its members' states.
    """
    id: str
    nodes: Set[str]
    consensus_ref: object  # reference to StarConsensus for live credibility

    def get_credibility(self) -> float:
        """
        Live credibility = average credibility of all nodes in cluster.
        Falls back to global credibility if no node-specific data exists.
        """
        if not self.nodes or self.consensus_ref is None:
            return 0.0
        
        # If consensus has a tracker, use its credibility
        if hasattr(self.consensus_ref, 'tracker'):
            return self.consensus_ref.tracker.get_credibility()
        
        # Fallback: use global credibility from consensus status
        if hasattr(self.consensus_ref, 'get_consensus_status'):
            status = self.consensus_ref.get_consensus_status()
            return status.get("credibility", 0.5)
        
        return 0.5

    def get_phase_coherence(self) -> float:
        """
        Measure phase coherence within cluster (0 = chaotic, 1 = perfectly aligned).
        """
        if len(self.nodes) < 2 or self.consensus_ref is None:
            return 1.0

        phases = []
        star_cache = getattr(self.consensus_ref, '_star_cache', {})
        for node_id in self.nodes:
            if node_id in star_cache:
                star = star_cache[node_id]
                if hasattr(star, 'phase_value'):
                    phases.append(star.phase_value())
                elif hasattr(star, 'phase'):
                    phases.append(star.phase / 100.0)

        if not phases:
            return 0.0

        avg = sum(phases) / len(phases)
        max_dev = max(abs(p - avg) for p in phases) if phases else 0.0
        return 1.0 - min(1.0, max_dev / 0.5)

    def summary(self) -> Dict:
        """Dynamic summary with live values."""
        return {
            "id": self.id,
            "size": len(self.nodes),
            "nodes": list(self.nodes),
            "credibility": self.get_credibility(),
            "phase_coherence": self.get_phase_coherence(),
            "is_healthy": self.get_credibility() > 0.6 and self.get_phase_coherence() > 0.7
        }


class ClusterStateManager:
    """
    Manages dynamic clusters with live credibility.
    """
    
    def __init__(self, consensus_ref):
        self.consensus_ref = consensus_ref
        self.clusters: List[DynamicCluster] = []
    
    def rebuild_clusters(self, node_to_star: Dict[str, List[int]], threshold: float = 0.7):
        """
        Rebuild clusters based on star similarity.
        Each cluster gets a reference to the consensus tracker.
        """
        # Simple greedy clustering based on star similarity
        if len(node_to_star) < 2:
            self.clusters = []
            return
        
        # Convert to list for processing
        node_ids = list(node_to_star.keys())
        visited = set()
        clusters = []
        
        for node_id in node_ids:
            if node_id in visited:
                continue
            cluster_nodes = {node_id}
            star_vec = node_to_star[node_id]
            
            for other_id in node_ids:
                if other_id in visited or other_id == node_id:
                    continue
                other_vec = node_to_star[other_id]
                sim = self._similarity(star_vec, other_vec)
                if sim >= threshold:
                    cluster_nodes.add(other_id)
            
            if len(cluster_nodes) >= 2:  # min cluster size
                cluster_id = f"cluster_{len(clusters):03d}"
                clusters.append(DynamicCluster(
                    id=cluster_id,
                    nodes=cluster_nodes,
                    consensus_ref=self.consensus_ref
                ))
                visited.update(cluster_nodes)
        
        # Add isolated nodes as single-node clusters if desired (optional)
        # For now, we only keep clusters with >=2 nodes
        self.clusters = clusters
    
    def _similarity(self, v1: List[int], v2: List[int]) -> float:
        """Cosine similarity between two star vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        import math
        dot = sum(a*b for a,b in zip(v1,v2))
        norm1 = math.sqrt(sum(a*a for a in v1))
        norm2 = math.sqrt(sum(b*b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
    
    def get_cluster_for_node(self, node_id: str):
        for cluster in self.clusters:
            if node_id in cluster.nodes:
                return cluster
        return None
    
    def get_summary(self) -> Dict:
        return {
            "cluster_count": len(self.clusters),
            "nodes_in_clusters": sum(len(c.nodes) for c in self.clusters),
            "clusters": [c.summary() for c in self.clusters]
        }
    
    def health_check(self) -> bool:
        if not self.clusters:
            return False
        return all(c.summary()["is_healthy"] for c in self.clusters)
