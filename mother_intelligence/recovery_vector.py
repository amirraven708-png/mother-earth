"""
recovery_vector.py
بردار بازیابی کامل دینامیکی شامل:
- وضعیت (L, theta)
- سرعت (dL, dtheta)
- گرادیان انرژی
- حوضه جذب (basin)
"""

import math  # ✅ اضافه شد
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

@dataclass
class DynamicState:
    """وضعیت کامل دینامیکی یک حباب"""
    L: float
    theta: float
    dL: float = 0.0
    dtheta: float = 0.0
    energy: float = 0.0
    gradient_L: float = 0.0
    gradient_theta: float = 0.0
    basin_id: str = "unknown"

@dataclass
class RecoveryVector:
    """
    بردار بازیابی کامل:
    - وضعیت هدف
    - سرعت هدف
    - گرادیان انرژی در هدف
    - حوضه جذب
    - مسیر بازگشت (اختیاری)
    """
    target_state: DynamicState
    velocity: Dict[str, float]
    gradient: Dict[str, float]
    basin_id: str
    trajectory: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "target_L": self.target_state.L,
            "target_theta": self.target_state.theta,
            "velocity": self.velocity,
            "gradient": self.gradient,
            "basin_id": self.basin_id,
            "trajectory": self.trajectory[-5:] if self.trajectory else []
        }

class RecoveryVectorBuilder:
    """
    سازنده بردار بازیابی از وضعیت فعلی حباب
    """

    @staticmethod
    def build(bubble, engine) -> RecoveryVector:
        """
        ساخت بردار بازیابی از یک حباب و موتور بیضوی
        """
        # وضعیت فعلی
        state = DynamicState(
            L=bubble.L,
            theta=bubble.theta,
            dL=bubble.trajectory[-1].get("dL", 0.0) if bubble.trajectory else 0.0,
            dtheta=bubble.trajectory[-1].get("dtheta", 0.0) if bubble.trajectory else 0.0,
            energy=bubble.energy,
            gradient_L=4 * bubble.alpha * (bubble.L ** 3),
            gradient_theta=bubble.beta * math.sin(2 * bubble.theta),
            basin_id="core_A"
        )

        # بردار بازیابی
        rv = RecoveryVector(
            target_state=state,
            velocity={"dL": state.dL, "dtheta": state.dtheta},
            gradient={"dV_dL": state.gradient_L, "dV_dtheta": state.gradient_theta},
            basin_id=state.basin_id,
            trajectory=[entry.copy() for entry in bubble.trajectory[-10:]]
        )

        return rv

    @staticmethod
    def apply(bubble, rv: RecoveryVector) -> None:
        """
        اعمال بردار بازیابی به حباب
        """
        bubble.L = rv.target_state.L
        bubble.theta = rv.target_state.theta
        bubble.energy = rv.target_state.energy

        if rv.trajectory:
            last = rv.trajectory[-1]
            bubble.trajectory.append(last.copy())

        bubble.basin = rv.basin_id
