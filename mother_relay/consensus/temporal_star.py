#!/usr/bin/env python3
"""
temporal_star.py – Updated with TemporalSchedule and ExperienceTracker fix
"""

import time
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from .temporal_schedule import TemporalSchedule, TemporalObservation, calculate_temporal_agreement


@dataclass
class TemporalStar:
    path: List[int]
    phase_index: int
    tick: int
    timestamp: float


class ExperienceTracker:
    """
    Credibility tracker that uses both consensus score and temporal agreement.
    """
    def __init__(self, window_size: int = 10, initial_credibility: float = 0.5):
        self.history: List[float] = []
        self.window_size = window_size
        self.credibility = initial_credibility

    def update_from_consensus(self, score: float, temporal_agreement: float) -> float:
        """
        Update credibility based on consensus quality.
        quality = weighted combination of score and temporal agreement.
        """
        quality = 0.6 * score + 0.4 * temporal_agreement

        # If quality is high, increase credibility; if low, decrease.
        if quality >= 0.85:
            self.credibility = min(1.0, self.credibility + 0.08)
        elif quality < 0.50:
            self.credibility = max(0.0, self.credibility - 0.10)
        else:
            # Slight drift toward 0.5 when uncertain
            self.credibility += (0.5 - self.credibility) * 0.02

        # Clamp
        self.credibility = min(1.0, max(0.0, self.credibility))

        # Store history
        self.history.append(self.credibility)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        return self.credibility

    def get_credibility(self) -> float:
        return self.credibility

    def is_reliable(self, threshold: float = 0.6) -> bool:
        return self.credibility >= threshold

    def reset(self):
        self.history.clear()
        self.credibility = 0.5


class TemporalStarConsensus:
    def __init__(self, emergency_threshold: float = 0.12,
                 min_nodes: int = 3,
                 credibility_threshold: float = 0.6,
                 window_size: int = 10):
        self.emergency_threshold = emergency_threshold
        self.min_nodes = min_nodes
        self.credibility_threshold = credibility_threshold
        self._star_cache: Dict[str, TemporalStar] = {}
        self._phase_history: Dict[str, List[int]] = {}
        self.tracker = ExperienceTracker(window_size=window_size, initial_credibility=0.5)
        self.schedule = TemporalSchedule()
        self._previous_star_cache: Dict[str, TemporalStar] = {}

    def draw_temporal_star(self, node_state: Dict) -> TemporalStar:
        """Draw a temporal star using the global tick and schedule."""
        raw_path = [
            int(node_state.get("phase", 0.0) * 100) % 101,
            int(node_state.get("heat", 0.0) * 100) % 101,
            int(node_state.get("density", 0.0) * 100) % 101,
            node_state.get("migration_count", 0) % 101,
            node_state.get("gossip_round", 0) % 101
        ]

        # Use provided phase_index or compute from phase
        phase_index = node_state.get("phase_index")
        if phase_index is None:
            phase_index = int(node_state.get("phase", 0.5) * 101) % 101

        # Global tick
        tick = node_state.get("tick", self.schedule.get_global_tick())

        return TemporalStar(
            path=raw_path,
            phase_index=phase_index,
            tick=tick,
            timestamp=time.time()
        )

    def receive_star(self, node_id: str, star: TemporalStar) -> None:
        self._star_cache[node_id] = star
        if node_id not in self._phase_history:
            self._phase_history[node_id] = []
        self._phase_history[node_id].append(star.phase_index)
        if len(self._phase_history[node_id]) > 20:
            self._phase_history[node_id].pop(0)

    def receive_star_list(self, star_map: Dict[str, TemporalStar]) -> None:
        for node_id, star in star_map.items():
            self.receive_star(node_id, star)

    def clear_cache(self) -> None:
        self._star_cache.clear()
        self._phase_history.clear()
        self._previous_star_cache.clear()

    # ============================================================
    # Metrics
    # ============================================================

    def calculate_phase_coherence(self) -> Optional[float]:
        if len(self._star_cache) < self.min_nodes:
            return None
        phases = [s.phase_index / 101.0 for s in self._star_cache.values()]
        avg = sum(phases) / len(phases)
        max_dev = max(abs(p - avg) for p in phases) if phases else 0.0
        return 1.0 - min(1.0, max_dev / 0.5)

    def calculate_geometry_similarity(self) -> Optional[float]:
        if len(self._star_cache) < self.min_nodes:
            return None
        paths = [s.path for s in self._star_cache.values()]
        sims = []
        for i in range(len(paths)):
            for j in range(i+1, len(paths)):
                sims.append(self._cosine_similarity(paths[i], paths[j]))
        if not sims:
            return None
        return sum(sims) / len(sims)

    def _cosine_similarity(self, v1: List[int], v2: List[int]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a*b for a,b in zip(v1,v2))
        norm1 = math.sqrt(sum(a*a for a in v1))
        norm2 = math.sqrt(sum(b*b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def calculate_temporal_agreement(self) -> float:
        """
        Compute temporal agreement by comparing each node's recent phase transitions
        against the expected schedule.
        """
        if len(self._phase_history) < self.min_nodes:
            return 0.0

        observations = []
        for node_id, history in self._phase_history.items():
            if len(history) < 2:
                continue
            # Use the latest step
            prev = history[-2]
            curr = history[-1]
            tick = self.schedule.get_global_tick()
            expected = self.schedule.expected_step(tick)
            actual = (curr - prev) % 101
            follows = (actual == expected)

            observations.append(TemporalObservation(
                node_id=node_id,
                previous_phase=prev,
                current_phase=curr,
                tick=tick,
                expected_step=expected,
                actual_step=actual,
                follows_schedule=follows
            ))

        return calculate_temporal_agreement(observations)

    def calculate_block_clock_coherence(self) -> float:
        """
        Block clock coherence: use phase coherence as proxy for now,
        but could be replaced with actual clock comparison.
        """
        coherence = self.calculate_phase_coherence()
        return coherence if coherence is not None else 0.0

    def get_consensus_score(self) -> Dict:
        if len(self._star_cache) < self.min_nodes:
            return {
                "consensus": False,
                "score": 0.0,
                "reason": "insufficient_nodes"
            }

        phase_coherence = self.calculate_phase_coherence() or 0.0
        geometry_sim = self.calculate_geometry_similarity() or 0.0
        temporal_agreement = self.calculate_temporal_agreement()
        block_clock = self.calculate_block_clock_coherence()

        # Weighted consensus score
        score = (
            0.35 * phase_coherence +
            0.25 * geometry_sim +
            0.25 * temporal_agreement +
            0.15 * block_clock
        )

        # Update credibility using both score and temporal agreement
        self.tracker.update_from_consensus(score, temporal_agreement)

        # Emergency threshold check (based on max distance = 1 - score)
        max_dist = 1.0 - score
        if max_dist >= self.emergency_threshold:
            return {
                "consensus": False,
                "score": score,
                "phase_coherence": phase_coherence,
                "geometry_sim": geometry_sim,
                "temporal_agreement": temporal_agreement,
                "block_clock": block_clock,
                "max_distance": max_dist,
                "credibility": self.tracker.get_credibility(),
                "reason": f"max_dist={max_dist:.3f} >= emergency_threshold={self.emergency_threshold:.3f}"
            }

        # Credibility check
        reliable = self.tracker.is_reliable(self.credibility_threshold)

        return {
            "consensus": reliable,
            "score": score,
            "phase_coherence": phase_coherence,
            "geometry_sim": geometry_sim,
            "temporal_agreement": temporal_agreement,
            "block_clock": block_clock,
            "max_distance": max_dist,
            "credibility": self.tracker.get_credibility(),
            "reason": "ok"
        }

    def get_consensus_status(self) -> Dict:
        return self.get_consensus_score()

    def reset_tracker(self):
        self.tracker.reset()
        self.schedule.reset()
        self._star_cache.clear()
        self._phase_history.clear()
        self._previous_star_cache.clear()
