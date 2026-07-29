"""
decision_guard.py
نگهبان تصمیم‌گیری (Decision Guard)
مسئول: تشخیص اینکه آیا سیستم نیاز به بازیابی دارد یا مسیر طبیعی خود را ادامه می‌دهد.
"""

import math
from typing import Dict, Optional, Tuple
from mother_intelligence.elliptic_memory_engine import EllipticMemoryEngine, EllipticBubble

class DecisionGuard:
    """
    نگهبان تصمیم‌گیری: مرز بین «نیاز به بازیابی» و «حرکت طبیعی روی منیفولد»
    """

    def __init__(self, engine: EllipticMemoryEngine, energy_threshold: float = 0.1):
        self.engine = engine
        self.energy_threshold = energy_threshold

    def should_recover(self, bubble: EllipticBubble) -> Tuple[bool, str]:
        """
        تصمیم‌گیری در مورد نیاز به بازیابی
        """
        # ۱. اگر انرژی خیلی زیاد باشد → نیاز به بازیابی
        if bubble.energy > self.energy_threshold:
            return True, f"energy_exceeded: {bubble.energy:.3f} > {self.energy_threshold}"

        # ۲. اگر انحراف تشخیص داده شده باشد → نیاز به بازیابی
        if self.engine.detect_deviation(bubble):
            return True, "deviation_detected"

        # ۳. اگر سقوط تشخیص داده شده باشد → نیاز به بازیابی
        if self.engine.detect_collapse(bubble):
            return True, "collapse_detected"

        # ۴. در غیر این صورت → طبیعی
        return False, "natural_flow"

    def decide_recovery_action(self, bubble: EllipticBubble) -> Dict:
        """
        تصمیم‌گیری در مورد نوع بازیابی
        """
        should, reason = self.should_recover(bubble)

        if not should:
            return {
                "action": "none",
                "reason": reason,
                "bubble_id": bubble.bubble_id
            }

        # آیا recovery vector موجود است؟
        if bubble.recovery_vector:
            return {
                "action": "apply_recovery_vector",
                "reason": reason,
                "bubble_id": bubble.bubble_id,
                "recovery_vector": bubble.recovery_vector
            }

        # آیا می‌توانیم از تاریخچه استفاده کنیم؟
        if len(bubble.trajectory) >= 5:
            # آخرین نقطه تعادل را پیدا کن
            for entry in reversed(bubble.trajectory):
                if entry.get("energy", 1.0) < self.energy_threshold:
                    return {
                        "action": "converge_from_trajectory",
                        "reason": reason,
                        "bubble_id": bubble.bubble_id,
                        "target": entry
                    }

        # در غیر این صورت: همگرایی از وضعیت فعلی
        return {
            "action": "converge_from_current",
            "reason": reason,
            "bubble_id": bubble.bubble_id
        }
