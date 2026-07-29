"""
drift_detector.py
تشخیص رانش (Drift) بر اساس مشتق انرژی و شتاب آن
"""

from collections import deque
from typing import Dict, Optional, Tuple

class DriftDetector:
    """
    تشخیص رانش با ردیابی:
    - انرژی لحظه‌ای
    - سرعت تغییر انرژی (dE/dt)
    - شتاب تغییر انرژی (d²E/dt²)
    """

    def __init__(self, history_size: int = 10, energy_threshold: float = 0.1):
        self.history_size = history_size
        self.energy_threshold = energy_threshold
        self.energy_history = deque(maxlen=history_size)

    def update(self, energy: float) -> Dict[str, bool]:
        """
        به‌روزرسانی تاریخچه انرژی و تشخیص وضعیت
        """
        self.energy_history.append(energy)

        result = {
            "energy": energy,
            "drifting": False,
            "accelerating": False,
            "critical": False
        }

        if len(self.energy_history) < 3:
            return result

        # سرعت تغییر انرژی (مشتق اول)
        dE = self.energy_history[-1] - self.energy_history[-2]
        result["dE"] = dE

        # شتاب تغییر انرژی (مشتق دوم)
        if len(self.energy_history) >= 3:
            ddE = self.energy_history[-1] - 2 * self.energy_history[-2] + self.energy_history[-3]
            result["ddE"] = ddE
            result["accelerating"] = ddE > 0.001

        # تشخیص رانش: افزایش مداوم انرژی
        if len(self.energy_history) >= 5:
            # میانگین تغییرات اخیر
            recent = list(self.energy_history)[-5:]
            avg_gradient = (recent[-1] - recent[0]) / len(recent)
            result["drifting"] = avg_gradient > 0.001

        # بحرانی: انرژی زیاد و رانش مثبت
        result["critical"] = (
            energy > self.energy_threshold and
            result.get("drifting", False)
        )

        return result

    def get_status(self) -> Dict:
        """دریافت وضعیت کلی"""
        if not self.energy_history:
            return {"status": "unknown", "energy": 0.0}

        last = self.update(self.energy_history[-1])
        return {
            "status": "critical" if last["critical"] else "drifting" if last["drifting"] else "stable",
            "energy": last["energy"],
            "dE": last.get("dE", 0.0),
            "ddE": last.get("ddE", 0.0)
        }
