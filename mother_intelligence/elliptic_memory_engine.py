"""
elliptic_memory_engine.py
هسته حافظه بیضوی (Elliptic Memory Core)
جایگزین مفهوم «ذخیره‌سازی» با «حالت روی منیفولد»

ویژگی‌ها:
- محاسبه انرژی V(L, θ)
- حرکت روی منیفولد با معادله‌ی دیفرانسیل
- تولید Recovery Vector از وضعیت فعلی
- تشخیص خروج از منیفولد هماهنگ
- Drift Detector یکپارچه
"""

import math
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple, Any
from enum import Enum

from .drift_detector import DriftDetector
from .recovery_vector import RecoveryVectorBuilder, RecoveryVector, DynamicState

class EllipticState(Enum):
    EQUILIBRIUM = "equilibrium"
    CONVERGING = "converging"
    DEVIATING = "deviating"
    COLLAPSING = "collapsing"

@dataclass
class EllipticBubble:
    bubble_id: str
    phase: float
    L: float
    theta: float
    energy: float = 0.0
    trajectory: List[Dict] = field(default_factory=list)
    state: EllipticState = EllipticState.EQUILIBRIUM
    recovery_vector: Optional[Dict] = None
    alpha: float = 0.1
    beta: float = 0.05
    basin: str = "core_A"

    def to_dict(self) -> Dict:
        return {
            "bubble_id": self.bubble_id,
            "phase": self.phase,
            "L": self.L,
            "theta": self.theta,
            "energy": self.energy,
            "state": self.state.value,
            "trajectory_len": len(self.trajectory),
            "recovery_vector": self.recovery_vector,
            "basin": self.basin
        }

class EllipticMemoryEngine:
    """
    موتور حافظه بیضوی:
    - محاسبه انرژی از روی فاز و فاصله
    - حرکت روی منیفولد با گام‌های زمانی
    - تولید recovery vector برای بازگشت به تعادل
    - تشخیص رانش با DriftDetector
    """

    def __init__(self, tolerance: float = 1e-6, max_steps: int = 100):
        self.tolerance = tolerance
        self.max_steps = max_steps
        self._bubbles: Dict[str, EllipticBubble] = {}
        self.drift_detectors: Dict[str, DriftDetector] = {}

    # ============================================================
    # 1. Bubble Management
    # ============================================================
    def create_bubble(self, bubble_id: str, phase: float, L: float, theta: float,
                      alpha: float = 0.1, beta: float = 0.05) -> EllipticBubble:
        bubble = EllipticBubble(
            bubble_id=bubble_id,
            phase=phase,
            L=L,
            theta=theta,
            alpha=alpha,
            beta=beta
        )
        bubble.energy = self.compute_energy(L, theta, alpha, beta)
        self._bubbles[bubble_id] = bubble
        self.drift_detectors[bubble_id] = DriftDetector(energy_threshold=0.1)
        return bubble

    def get_bubble(self, bubble_id: str) -> Optional[EllipticBubble]:
        return self._bubbles.get(bubble_id)

    def update_bubble(self, bubble: EllipticBubble):
        self._bubbles[bubble.bubble_id] = bubble

    # ============================================================
    # 2. Energy Functions
    # ============================================================
    def compute_energy(self, L: float, theta: float, alpha: float = 0.1, beta: float = 0.05) -> float:
        return alpha * (L ** 4) + beta * (math.sin(theta) ** 2)

    def compute_energy_delta(self, bubble: EllipticBubble, dt: float = 0.01) -> Tuple[float, float]:
        L, theta = bubble.L, bubble.theta
        alpha, beta = bubble.alpha, bubble.beta

        dV_dL = 4 * alpha * (L ** 3)
        dV_dtheta = beta * math.sin(2 * theta)

        dL = -dV_dL * dt
        dtheta = -dV_dtheta * dt
        return dL, dtheta

    # ============================================================
    # 3. Manifold Dynamics
    # ============================================================
    def step_manifold(self, bubble: EllipticBubble, dt: float = 0.01) -> EllipticBubble:
        dL, dtheta = self.compute_energy_delta(bubble, dt)

        bubble.L += dL
        bubble.theta += dtheta

        bubble.energy = self.compute_energy(bubble.L, bubble.theta, bubble.alpha, bubble.beta)

        bubble.trajectory.append({
            "L": bubble.L,
            "theta": bubble.theta,
            "energy": bubble.energy,
            "dL": dL,
            "dtheta": dtheta
        })
        if len(bubble.trajectory) > 100:
            bubble.trajectory.pop(0)

        # تحدید وضعیت
        if abs(bubble.energy) < self.tolerance:
            bubble.state = EllipticState.EQUILIBRIUM
        elif bubble.energy < 0.01:
            bubble.state = EllipticState.CONVERGING
        else:
            bubble.state = EllipticState.DEVIATING

        return bubble

    def converge_to_equilibrium(self, bubble: EllipticBubble, max_steps: int = None) -> EllipticBubble:
        max_steps = max_steps or self.max_steps
        steps = 0
        while bubble.state != EllipticState.EQUILIBRIUM and steps < max_steps:
            bubble = self.step_manifold(bubble)
            steps += 1
        return bubble

    # ============================================================
    # 4. Detection
    # ============================================================
    def detect_deviation(self, bubble: EllipticBubble, threshold: float = 0.1) -> bool:
        if not bubble.trajectory:
            return False
        last = bubble.trajectory[-1]
        energy_deviation = abs(last.get("energy", 0) - bubble.energy)
        return energy_deviation > threshold

    def detect_collapse(self, bubble: EllipticBubble, threshold: float = 0.5) -> bool:
        if len(bubble.trajectory) < 5:
            return False
        recent = bubble.trajectory[-5:]
        energy_values = [e.get("energy", 0) for e in recent]
        if len(energy_values) < 3:
            return False
        slope = (energy_values[-1] - energy_values[0]) / max(1, len(energy_values))
        return slope > threshold

    def get_drift_status(self, bubble_id: str) -> Dict:
        if bubble_id not in self._bubbles:
            return {"status": "unknown", "error": "bubble not found"}
        bubble = self._bubbles[bubble_id]
        if bubble_id not in self.drift_detectors:
            self.drift_detectors[bubble_id] = DriftDetector(energy_threshold=0.1)
        detector = self.drift_detectors[bubble_id]
        status = detector.update(bubble.energy)
        return {
            "bubble_id": bubble_id,
            "energy": bubble.energy,
            "drifting": status["drifting"],
            "accelerating": status["accelerating"],
            "critical": status["critical"],
            "dE": status.get("dE", 0.0),
            "ddE": status.get("ddE", 0.0)
        }

    # ============================================================
    # 5. Recovery Vector
    # ============================================================
    def build_recovery_vector(self, bubble: EllipticBubble) -> Dict:
        rv = RecoveryVectorBuilder.build(bubble, self)
        return rv.to_dict()

    def apply_recovery_vector(self, bubble: EllipticBubble, recovery_vector: Dict) -> EllipticBubble:
        if "target_L" in recovery_vector:
            bubble.L = recovery_vector["target_L"]
        if "target_theta" in recovery_vector:
            bubble.theta = recovery_vector["target_theta"]
        if "velocity" in recovery_vector:
            # ذخیره سرعت در تاریخچه
            bubble.trajectory.append({
                "L": bubble.L,
                "theta": bubble.theta,
                "velocity": recovery_vector["velocity"]
            })
        bubble.energy = self.compute_energy(bubble.L, bubble.theta, bubble.alpha, bubble.beta)
        bubble.state = EllipticState.CONVERGING
        bubble.recovery_vector = recovery_vector
        return bubble

    # ============================================================
    # 6. Health
    # ============================================================
    def evaluate_health(self, bubble_id: str) -> Dict:
        bubble = self.get_bubble(bubble_id)
        if not bubble:
            return {"status": "unknown", "error": "bubble not found"}
        is_deviating = self.detect_deviation(bubble)
        is_collapsing = self.detect_collapse(bubble)
        return {
            "bubble_id": bubble_id,
            "status": "healthy" if not is_deviating else "deviating",
            "energy": bubble.energy,
            "state": bubble.state.value,
            "is_deviating": is_deviating,
            "is_collapsing": is_collapsing,
            "recovery_available": bubble.recovery_vector is not None
        }

    # ============================================================
    # 7. API
    # ============================================================
    def get_all_bubbles(self) -> Dict[str, Dict]:
        return {bid: b.to_dict() for bid, b in self._bubbles.items()}
