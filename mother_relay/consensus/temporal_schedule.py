#!/usr/bin/env python3
"""
temporal_schedule.py
Temporal Step Schedule for Star Consensus (2/3 rhythm)
"""

from typing import List, Optional
from dataclasses import dataclass

# Core pattern: 5 steps of +2, then 5 steps of +3, repeat
STAR_STEP_PATTERN = [2, 2, 2, 2, 2, 3, 3, 3, 3, 3]
CYCLE_LENGTH = len(STAR_STEP_PATTERN)
TOTAL_STEPS_PER_CYCLE = sum(STAR_STEP_PATTERN)  # 25


class TemporalSchedule:
    """
    Manages the deterministic 2/3 step schedule for star phase advancement.
    """
    
    def __init__(self, pattern: Optional[List[int]] = None):
        self.pattern = pattern or STAR_STEP_PATTERN
        self.length = len(self.pattern)
        self._tick = 0  # global tick counter (shared across nodes)
    
    def expected_step(self, tick: int) -> int:
        """Return the expected step size at a given global tick."""
        return self.pattern[tick % self.length]
    
    def advance_phase(self, current_phase: int, tick: int) -> int:
        """Advance phase by the expected step at given tick."""
        step = self.expected_step(tick)
        return (current_phase + step) % 101
    
    def validate_step(self, previous_phase: int, current_phase: int, tick: int) -> bool:
        """
        Check if a node's phase transition matches the expected schedule.
        """
        expected = self.expected_step(tick)
        actual = (current_phase - previous_phase) % 101
        return actual == expected
    
    def advance_global_tick(self) -> int:
        """Advance global tick and return new value."""
        self._tick += 1
        return self._tick
    
    def get_global_tick(self) -> int:
        return self._tick
    
    def reset(self) -> None:
        self._tick = 0


@dataclass
class TemporalObservation:
    node_id: str
    previous_phase: int
    current_phase: int
    tick: int
    expected_step: int
    actual_step: int
    follows_schedule: bool


def calculate_temporal_agreement(observations: List[TemporalObservation]) -> float:
    """
    Calculate the fraction of nodes that follow the temporal schedule.
    """
    if not observations:
        return 0.0
    valid = sum(1 for obs in observations if obs.follows_schedule)
    return valid / len(observations)
