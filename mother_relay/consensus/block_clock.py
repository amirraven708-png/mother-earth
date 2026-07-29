#!/usr/bin/env python3
"""
block_clock.py
Non-linear temporal rhythm for consensus timing
"""

import time
import math
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class ClockTick:
    """A single tick in block clock history"""
    clock: float
    difficulty: float
    migration_pressure: float
    timestamp: float = field(default_factory=time.time)


class BlockClock:
    """
    Non-linear block clock that accelerates with difficulty and history.
    Used for timing consensus rounds, migration decisions, and evolution cycles.
    """

    def __init__(self, initial_clock: float = 0.0):
        self.clock = initial_clock
        self.history: List[ClockTick] = []
        self._a = 0.0001      # quadratic coefficient
        self._b_base = 0.000005  # difficulty coefficient base
        self._c = 0.001       # base increment

    def tick(self, difficulty: float, migration_pressure: float = 0.0) -> float:
        n = len(self.history)
        delta = (
            self._a * (n * n) +
            self._b_base * difficulty * n +
            self._c +
            migration_pressure
        )
        self.clock += delta
        self.history.append(ClockTick(
            clock=self.clock,
            difficulty=difficulty,
            migration_pressure=migration_pressure
        ))
        return self.clock

    def get_clock(self) -> float:
        return self.clock

    def get_ticks(self) -> int:
        return len(self.history)

    def get_last_tick(self) -> Optional[ClockTick]:
        if not self.history:
            return None
        return self.history[-1]

    def get_clock_rate(self) -> float:
        if len(self.history) < 2:
            return 0.0
        last = self.history[-1]
        prev = self.history[-2]
        return last.clock - prev.clock

    def predict_next_clock(self, difficulty: float, migration_pressure: float = 0.0) -> float:
        n = len(self.history)
        delta = (
            self._a * (n * n) +
            self._b_base * difficulty * n +
            self._c +
            migration_pressure
        )
        return self.clock + delta

    def reset(self) -> None:
        self.clock = 0.0
        self.history.clear()

    def set_coefficients(self, a: float = None, b_base: float = None, c: float = None) -> None:
        if a is not None:
            self._a = a
        if b_base is not None:
            self._b_base = b_base
        if c is not None:
            self._c = c

    def to_dict(self) -> Dict:
        return {
            "clock": self.clock,
            "ticks": len(self.history),
            "rate": self.get_clock_rate(),
            "last_tick": self.get_last_tick().__dict__ if self.get_last_tick() else None
        }
