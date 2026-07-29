#!/usr/bin/env python3
"""
star_consensus.py
Phase-based State Attestation with Dynamic Credibility
"""

import hashlib
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Star:
    """A 5-point star pattern representing node state"""
    phase: int      # 0-100, from node phase
    heat: int       # 0-100, from avg heat
    density: int    # 0-100, from data density
    migration: int  # 0-100, migration count mod 101
    gossip: int     # 0-100, gossip round mod 101

    def to_list(self) -> List[int]:
        return [self.phase, self.heat, self.density, self.migration, self.gossip]

    @classmethod
    def from_list(cls, data: List[int]) -> 'Star':
        return cls(*data)

    def hash(self) -> str:
        raw = ":".join(str(v) for v in self.to_list())
        return hashlib.sha256(raw.encode()).hexdigest()

    def phase_value(self) -> float:
        return self.phase / 100.0


class ExperienceTracker:
    """
    Tracks historical phase distances to build dynamic credibility.
    Credibility grows when system is stable, decays when diverging.
    """

    def __init__(self, window_size: int = 10, initial_credibility: float = 0.5):
        self.history: List[float] = []
        self.window_size = window_size
        self.credibility = initial_credibility
        self._trend_history: List[float] = []

    def update(self, max_distance: float) -> float:
        """Update tracker with new max distance and return new credibility."""
        self.history.append(max_distance)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        if len(self.history) < 3:
            return self.credibility

        # Trend: compare recent (last 3) vs older (first 3)
        recent = self.history[-3:]
        older = self.history[:3]
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        trend = recent_avg - older_avg

        # Volatility: standard deviation of recent window
        recent_window = self.history[-5:] if len(self.history) >= 5 else self.history
        mean = sum(recent_window) / len(recent_window)
        variance = sum((x - mean) ** 2 for x in recent_window) / len(recent_window)
        volatility = variance ** 0.5

        # Store trend for analysis
        self._trend_history.append(trend)
        if len(self._trend_history) > self.window_size:
            self._trend_history.pop(0)

        # Update credibility
        # Case 1: Stable (trend down or flat, low volatility) → increase
        if trend < 0.005 and volatility < 0.02:
            self.credibility = min(1.0, self.credibility + 0.04)
        # Case 2: Diverging (trend up, high volatility) → decrease
        elif trend > 0.01 and volatility > 0.025:
            self.credibility = max(0.0, self.credibility - 0.07)
        # Case 3: Mild instability → slight decrease
        elif trend > 0.005 or volatility > 0.03:
            self.credibility = max(0.0, self.credibility - 0.02)
        else:
            # Neutral: credibility slightly drifts toward 0.5 (forgetfulness)
            self.credibility += (0.5 - self.credibility) * 0.01

        return self.credibility

    def is_reliable(self, threshold: float = 0.6) -> bool:
        """Check if system is reliable based on credibility."""
        return self.credibility >= threshold

    def get_credibility(self) -> float:
        return self.credibility

    def reset(self):
        self.history.clear()
        self._trend_history.clear()
        self.credibility = 0.5


class StarConsensus:
    """
    Decentralized phase agreement using star patterns.
    Uses dynamic credibility instead of fixed threshold for decisions.
    """

    def __init__(self, emergency_threshold: float = 0.15, min_nodes: int = 3,
                 credibility_threshold: float = 0.6, window_size: int = 10):
        self.emergency_threshold = emergency_threshold  # fallback hard limit
        self.min_nodes = min_nodes
        self.credibility_threshold = credibility_threshold
        self._star_cache: Dict[str, Star] = {}
        self.tracker = ExperienceTracker(window_size=window_size, initial_credibility=0.5)

    def draw_star(self, node_state: Dict) -> Star:
        """Convert node state into a 5-point star pattern."""
        return Star(
            phase=int(node_state.get("phase", 0.0) * 100) % 101,
            heat=int(node_state.get("heat", 0.0) * 100) % 101,
            density=int(node_state.get("density", 0.0) * 100) % 101,
            migration=node_state.get("migration_count", 0) % 101,
            gossip=node_state.get("gossip_round", 0) % 101
        )

    def receive_star(self, node_id: str, star: Star) -> None:
        self._star_cache[node_id] = star

    def receive_star_list(self, star_map: Dict[str, Star]) -> None:
        self._star_cache.update(star_map)

    def clear_cache(self) -> None:
        self._star_cache.clear()

    def get_collective_phase(self) -> Optional[float]:
        if len(self._star_cache) < self.min_nodes:
            return None
        phases = [s.phase_value() for s in self._star_cache.values()]
        return sum(phases) / len(phases)

    def get_max_phase_distance(self) -> Optional[float]:
        """Maximum pairwise circular phase distance."""
        if len(self._star_cache) < self.min_nodes:
            return None
        phases = [s.phase_value() for s in self._star_cache.values()]
        max_dist = 0.0
        for i in range(len(phases)):
            for j in range(i+1, len(phases)):
                raw = abs(phases[i] - phases[j])
                dist = min(raw, 1.0 - raw)
                if dist > max_dist:
                    max_dist = dist
        return max_dist

    def is_phase_agreement(self) -> bool:
        """
        Primary decision: based on dynamic credibility.
        Emergency fallback: max distance < emergency_threshold.
        """
        max_dist = self.get_max_phase_distance()
        if max_dist is None:
            return False

        # Update credibility with current max distance
        self.tracker.update(max_dist)

        # Reliable if credibility is high
        reliable = self.tracker.is_reliable(self.credibility_threshold)

        # Emergency override: if distance exceeds threshold, force disagreement
        if max_dist >= self.emergency_threshold:
            return False

        # Otherwise rely on credibility
        return reliable

    def get_consensus_status(self) -> Dict:
        """Return full status including credibility and max distance."""
        max_dist = self.get_max_phase_distance()
        collective = self.get_collective_phase()
        if max_dist is None:
            return {
                "consensus": False,
                "collective_phase": None,
                "max_distance": None,
                "credibility": self.tracker.get_credibility(),
                "node_count": len(self._star_cache),
                "reason": "insufficient_nodes"
            }

        # Update credibility
        self.tracker.update(max_dist)
        consensus = self.is_phase_agreement()

        return {
            "consensus": consensus,
            "collective_phase": collective,
            "max_distance": max_dist,
            "credibility": self.tracker.get_credibility(),
            "node_count": len(self._star_cache),
            "emergency_threshold": self.emergency_threshold,
            "credibility_threshold": self.credibility_threshold,
            "reason": "ok"
        }

    def star_similarity(self, star1: Star, star2: Star) -> float:
        """Euclidean similarity between two stars (0-1)."""
        v1 = [s / 100.0 for s in star1.to_list()]
        v2 = [s / 100.0 for s in star2.to_list()]
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))
        max_dist = math.sqrt(5)
        return 1.0 - (dist / max_dist)

    def cluster_stars(self, threshold: float = 0.7) -> List[List[str]]:
        if len(self._star_cache) < 2:
            return [list(self._star_cache.keys())]
        nodes = list(self._star_cache.keys())
        clusters = []
        for node in nodes:
            star = self._star_cache[node]
            found = False
            for cluster in clusters:
                first = cluster[0]
                sim = self.star_similarity(star, self._star_cache[first])
                if sim >= threshold:
                    cluster.append(node)
                    found = True
                    break
            if not found:
                clusters.append([node])
        return clusters

    def reset_tracker(self):
        """Reset experience tracker (e.g., after a major system change)."""
        self.tracker.reset()
