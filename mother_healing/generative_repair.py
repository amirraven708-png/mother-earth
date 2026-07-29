"""
generative_repair.py
ترمیم تولیدی (Generative Repair)
ایجاد حالت جدید بر اساس recovery vector یا تاریخچه
"""

from typing import Dict, Optional
from mother_intelligence.elliptic_memory_engine import EllipticBubble, EllipticMemoryEngine

class GenerativeRepair:
    """
    ترمیم تولیدی: تولید وضعیت جدید بر اساس داده‌های موجود
    """

    def __init__(self, engine: EllipticMemoryEngine):
        self.engine = engine

    def repair_from_recovery_vector(self, bubble: EllipticBubble, recovery_vector: Dict) -> EllipticBubble:
        """
        ترمیم از recovery vector
        """
        return self.engine.apply_recovery_vector(bubble, recovery_vector)

    def repair_from_nearest_neighbor(self, bubble: EllipticBubble, neighbors: list) -> EllipticBubble:
        """
        ترمیم از نزدیک‌ترین همسایه (در فضای فاز)
        """
        if not neighbors:
            return bubble

        # پیدا کردن نزدیک‌ترین همسایه از نظر فاز
        nearest = min(neighbors, key=lambda n: abs(n.phase - bubble.phase))
        bubble.L = nearest.L
        bubble.theta = nearest.theta
        bubble.phase = nearest.phase
        bubble.energy = self.engine.compute_energy(bubble.L, bubble.theta)
        bubble.state = self.engine.determine_state(bubble.energy)

        return bubble

    def generate_new_state(self, bubble: EllipticBubble) -> EllipticBubble:
        """
        تولید وضعیت جدید بر اساس اطلاعات موجود
        """
        # اگر recovery vector موجود است، از آن استفاده کن
        if bubble.recovery_vector:
            return self.repair_from_recovery_vector(bubble, bubble.recovery_vector)

        # اگر تاریخچه دارد، از آن استفاده کن
        if bubble.trajectory:
            last_stable = None
            for entry in reversed(bubble.trajectory):
                if entry.get("energy", 1.0) < 0.01:
                    last_stable = entry
                    break
            if last_stable:
                bubble.L = last_stable.get("L", bubble.L)
                bubble.theta = last_stable.get("theta", bubble.theta)
                bubble.energy = last_stable.get("energy", bubble.energy)

        return bubble
