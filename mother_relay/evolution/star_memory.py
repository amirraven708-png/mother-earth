#!/usr/bin/env python3
"""
star_memory.py
Star-Guided Evolution Memory for Mother Earth
"""

import time
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class StarRecord:
    """A single record in evolution memory"""
    star: List[int]
    phase: float
    credibility: float
    fitness: float
    result: str  # "accepted", "rejected"
    mutation_id: str
    timestamp: float = field(default_factory=time.time)
    node_count: int = 0


@dataclass
class AttractorPattern:
    """A cluster of successful star patterns"""
    center: List[float]  # centroid of stars
    radius: float
    count: int
    avg_fitness: float
    phase_range: Tuple[float, float]


class StarEvolutionMemory:
    """
    Stores and learns from star signatures of mutations.
    Builds attractor maps for guiding future mutations.
    """

    def __init__(self, max_history: int = 1000):
        self.history: List[StarRecord] = []
        self.max_history = max_history
        self._attractors: List[AttractorPattern] = []
        self._pattern_cache: Dict[str, List[int]] = {}
        self._needs_rebuild = True

    # ============================================================
    # 1. Record Management
    # ============================================================

    def add_record(self, record: StarRecord) -> None:
        """Add a new record to evolution memory."""
        self.history.append(record)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        self._needs_rebuild = True

    def add_from_proposal(self, proposal: Dict, result: str, fitness: float) -> None:
        """Extract star signature from proposal and add to memory."""
        if "star_signature" not in proposal:
            return
        
        sig = proposal["star_signature"]
        record = StarRecord(
            star=sig.get("star", []),
            phase=sig.get("phase", 0.0),
            credibility=sig.get("credibility", 0.0),
            fitness=fitness,
            result=result,
            mutation_id=proposal.get("id", "unknown"),
            node_count=proposal.get("node_count", 0)
        )
        self.add_record(record)

    def get_successful_patterns(self, min_fitness: float = 0.7) -> List[StarRecord]:
        """Get records with fitness above threshold."""
        return [r for r in self.history if r.result == "accepted" and r.fitness >= min_fitness]

    def get_failed_patterns(self) -> List[StarRecord]:
        """Get records that were rejected."""
        return [r for r in self.history if r.result == "rejected"]

    # ============================================================
    # 2. Attractor Building (Clustering)
    # ============================================================

    def _euclidean_dist(self, v1: List[float], v2: List[float]) -> float:
        """Euclidean distance between two vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return float('inf')
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

    def _normalize_star(self, star: List[int]) -> List[float]:
        """Normalize star values to [0, 1]."""
        return [s / 100.0 for s in star]

    def rebuild_attractors(self, max_clusters: int = 5, min_points: int = 3) -> None:
        """
        Rebuild attractor map from successful patterns.
        Simple greedy clustering.
        """
        if not self._needs_rebuild:
            return

        success = self.get_successful_patterns()
        if len(success) < min_points:
            self._attractors = []
            return

        # Normalize all stars
        points = [self._normalize_star(r.star) for r in success]
        
        # Greedy clustering
        clusters = []
        unassigned = list(range(len(points)))
        
        while unassigned and len(clusters) < max_clusters:
            # Pick first unassigned as cluster center
            idx = unassigned[0]
            center = points[idx]
            cluster = [idx]
            unassigned.remove(idx)
            
            # Find all points within radius of 0.3
            radius = 0.3
            for other_idx in unassigned[:]:
                dist = self._euclidean_dist(center, points[other_idx])
                if dist < radius:
                    cluster.append(other_idx)
                    unassigned.remove(other_idx)
            
            if len(cluster) >= min_points:
                # Calculate cluster centroid
                centroid = [0.0] * len(center)
                for ci in cluster:
                    for d in range(len(center)):
                        centroid[d] += points[ci][d]
                centroid = [c / len(cluster) for c in centroid]
                
                # Calculate cluster radius (max distance from centroid)
                max_dist = 0.0
                for ci in cluster:
                    dist = self._euclidean_dist(centroid, points[ci])
                    if dist > max_dist:
                        max_dist = dist
                
                avg_fitness = sum(success[ci].fitness for ci in cluster) / len(cluster)
                phases = [success[ci].phase for ci in cluster]
                
                clusters.append(AttractorPattern(
                    center=centroid,
                    radius=max_dist,
                    count=len(cluster),
                    avg_fitness=avg_fitness,
                    phase_range=(min(phases), max(phases))
                ))

        self._attractors = clusters
        self._needs_rebuild = False

    def get_attractors(self) -> List[AttractorPattern]:
        """Get current attractor patterns."""
        if self._needs_rebuild:
            self.rebuild_attractors()
        return self._attractors

    # ============================================================
    # 3. Pattern Similarity & Guidance
    # ============================================================

    def find_nearest_attractor(self, star: List[int]) -> Optional[AttractorPattern]:
        """Find the attractor closest to a given star."""
        if not self._attractors:
            return None
        
        norm_star = self._normalize_star(star)
        best = None
        best_dist = float('inf')
        
        for attr in self._attractors:
            dist = self._euclidean_dist(attr.center, norm_star)
            if dist < best_dist:
                best_dist = dist
                best = attr
        
        return best

    def predicted_success_probability(self, star: List[int]) -> float:
        """
        Predict probability of success based on similarity to attractors.
        """
        if not self._attractors:
            return 0.5  # neutral
        
        nearest = self.find_nearest_attractor(star)
        if nearest is None:
            return 0.5
        
        norm_star = self._normalize_star(star)
        dist = self._euclidean_dist(nearest.center, norm_star)
        
        if dist < nearest.radius:
            # Within cluster: high probability
            return min(0.9, 0.7 + (1.0 - dist / nearest.radius) * 0.2)
        else:
            # Outside cluster: probability drops with distance
            return max(0.2, 0.5 - (dist - nearest.radius) * 0.2)

    def get_recommended_phase(self) -> Optional[float]:
        """
        Get phase range that has highest success rate.
        """
        if not self._attractors:
            return None
        
        best = max(self._attractors, key=lambda a: a.avg_fitness)
        return (best.phase_range[0] + best.phase_range[1]) / 2

    # ============================================================
    # 4. Metrics & Statistics
    # ============================================================

    def get_stats(self) -> Dict:
        """Get memory statistics."""
        total = len(self.history)
        accepted = len([r for r in self.history if r.result == "accepted"])
        rejected = total - accepted
        
        return {
            "total_records": total,
            "accepted": accepted,
            "rejected": rejected,
            "acceptance_rate": accepted / total if total > 0 else 0.0,
            "attractor_count": len(self._attractors),
            "avg_fitness_accepted": sum(r.fitness for r in self.history if r.result == "accepted") / max(1, accepted)
        }

    def to_dict(self) -> Dict:
        """Export memory state."""
        return {
            "history": [{
                "star": r.star,
                "phase": r.phase,
                "credibility": r.credibility,
                "fitness": r.fitness,
                "result": r.result,
                "mutation_id": r.mutation_id
            } for r in self.history[-100:]],
            "attractors": [{
                "center": attr.center,
                "radius": attr.radius,
                "count": attr.count,
                "avg_fitness": attr.avg_fitness,
                "phase_range": attr.phase_range
            } for attr in self._attractors]
        }

    # ============================================================
    # 5. Reset
    # ============================================================

    def reset(self) -> None:
        """Clear memory and rebuild."""
        self.history.clear()
        self._attractors.clear()
        self._pattern_cache.clear()
        self._needs_rebuild = True
