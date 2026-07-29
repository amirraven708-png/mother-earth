"""
replay_engine.py
موتور بازپخش (Replay Engine)
بازپخش مسیر حالت برای یافتن آخرین جاذب پایدار (stable attractor)
"""

from typing import Dict, List, Optional
from mother_intelligence.elliptic_memory_engine import EllipticBubble

class ReplayEngine:
    """
    بازپخش تاریخچه حالت برای یافتن آخرین نقطه تعادل
    """

    def __init__(self, max_history: int = 100):
        self.max_history = max_history

    def find_last_stable_attractor(self, bubble: EllipticBubble, energy_threshold: float = 0.01) -> Optional[Dict]:
        """
        پیدا کردن آخرین جاذب پایدار در تاریخچه
        """
        if not bubble.trajectory:
            return None

        # از آخرین به اولین
        for entry in reversed(bubble.trajectory):
            if entry.get("energy", 1.0) < energy_threshold:
                return entry

        return None

    def replay_to_stability(self, bubble: EllipticBubble, engine) -> EllipticBubble:
        """
        بازپخش مسیر تا رسیدن به پایداری
        """
        if not bubble.trajectory:
            return bubble

        # پیدا کردن آخرین نقطه پایدار
        last_stable = self.find_last_stable_attractor(bubble)

        if last_stable:
            bubble.L = last_stable.get("L", bubble.L)
            bubble.theta = last_stable.get("theta", bubble.theta)
            bubble.energy = last_stable.get("energy", bubble.energy)
            bubble.state = engine.determine_state(bubble.energy)
        else:
            # اگر نقطه پایدار پیدا نشد، از ابتدا همگرا شو
            bubble = engine.converge_to_equilibrium(bubble)

        return bubble

    def generate_recovery_report(self, bubble: EllipticBubble) -> Dict:
        """
        تولید گزارش بازیابی
        """
        last_stable = self.find_last_stable_attractor(bubble)

        return {
            "bubble_id": bubble.bubble_id,
            "trajectory_length": len(bubble.trajectory),
            "last_stable_energy": last_stable.get("energy") if last_stable else None,
            "last_stable_position": last_stable,
            "current_energy": bubble.energy,
            "current_state": bubble.state.value
        }
