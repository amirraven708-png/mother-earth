"""
distributed_bubbledb.py
لایهٔ ذخیره‌سازی توزیع‌شده با پشتیبانی از:
- Tiering (HOT/WARM/COLD)
- Recovery Vectors
- Elliptic Memory State (حالت بیضوی)
"""

import time
import math
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .tld_tuner_module import TLDMemoryController, MemoryTier, TLDTierCalibrator
from mother_intelligence.elliptic_memory_engine import EllipticMemoryEngine, EllipticBubble, EllipticState

@dataclass
class DistributedBubbleDBConfig:
    replication_factors: Dict[str, int] = field(default_factory=lambda: {"hot": 1, "warm": 2, "cold": 3})
    initial_state: str = "cold"
    calibrator_params: Optional[Dict[str, float]] = None

class DistributedBubbleDB:
    def __init__(self, config: Optional[DistributedBubbleDBConfig] = None):
        self.config = config or DistributedBubbleDBConfig()
        calibrator = TLDTierCalibrator(**(self.config.calibrator_params or {}))
        self.controller = TLDMemoryController(calibrator)
        self.records: Dict[str, Dict[str, Any]] = {}
        self._recovery_vectors: Dict[str, Dict] = {}
        self._tick = 0

        # ✅ Elliptic Memory Engine
        self.elliptic_engine = EllipticMemoryEngine(tolerance=1e-6)

    # ============================================================
    # 1. Core Operations (with Elliptic State)
    # ============================================================
    def put(self, key: str, value: Any, phase_vector: Dict[str, float],
            L: float = 0.5, theta: float = 0.3) -> bool:
        """ذخیره رکورد با وضعیت بیضوی"""
        initial_tier = MemoryTier[self.config.initial_state.upper()]

        # ایجاد حباب بیضوی
        bubble = self.elliptic_engine.create_bubble(
            bubble_id=key,
            phase=phase_vector.get("R", 0.5),
            L=L,
            theta=theta
        )

        self.records[key] = {
            "key": key,
            "value": value,
            "phase_vector": phase_vector,
            "heat": 0.0,
            "tier": initial_tier,
            "age_ticks": 0,
            "access_count": 0,
            "elliptic_bubble": bubble,  # ⭐ وضعیت بیضوی
            "recovery_vector": None
        }
        return True

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if key not in self.records:
            return None
        self.records[key] = self.controller.touch_record(self.records[key], hits=1)

        # ⭐ به‌روزرسانی Elliptic State در هر دسترسی
        self._update_elliptic_state(key)

        return self.records[key].copy()

    def _update_elliptic_state(self, key: str):
        """به‌روزرسانی حالت بیضوی بر اساس heat و phase فعلی"""
        rec = self.records[key]
        bubble = rec["elliptic_bubble"]
        # انتقال heat به L
        bubble.L = rec["heat"]
        # انتقال phase به theta (با نگاشت ساده)
        bubble.theta = rec["phase_vector"].get("theta", bubble.theta)
        # به‌روزرسانی انرژی
        bubble.energy = self.elliptic_engine.compute_energy(bubble.L, bubble.theta)
        rec["elliptic_bubble"] = bubble

    def update_phase(self, key: str, phase_vector: Dict[str, float]):
        if key in self.records:
            self.records[key]["phase_vector"] = phase_vector
            self._update_elliptic_state(key)

    def tick(self, storage_pressure: float = 0.0):
        self._tick += 1

        for key, rec in self.records.items():
            # 1. Tiering (موجود)
            self.records[key] = self.controller.process_tick(rec)

            # 2. Elliptic Dynamics (جدید)
            bubble = rec["elliptic_bubble"]
            # یک گام روی منیفولد بیضوی
            bubble = self.elliptic_engine.step_manifold(bubble, dt=0.01)
            rec["elliptic_bubble"] = bubble
            # هماهنگ‌سازی heat با L
            rec["heat"] = bubble.L

            self.records[key] = rec

    # ============================================================
    # 2. Recovery Vector Support
    # ============================================================
    def store_recovery_vector(self, node_id: str, recovery_vector: Dict):
        self._recovery_vectors[node_id] = {
            "vector": recovery_vector,
            "timestamp": time.time(),
            "tick": self._tick
        }
        # همچنین در رکورد ذخیره کن
        if node_id in self.records:
            self.records[node_id]["recovery_vector"] = recovery_vector

    def get_recovery_vector(self, node_id: str) -> Optional[Dict]:
        if node_id in self.records and self.records[node_id]["recovery_vector"]:
            return self.records[node_id]["recovery_vector"]
        if node_id in self._recovery_vectors:
            return self._recovery_vectors[node_id]["vector"]
        return None

    def clear_recovery_vector(self, node_id: str):
        if node_id in self.records:
            self.records[node_id]["recovery_vector"] = None
        if node_id in self._recovery_vectors:
            del self._recovery_vectors[node_id]

    # ============================================================
    # 3. Elliptic Memory Queries
    # ============================================================
    def get_elliptic_status(self, key: str) -> Optional[Dict]:
        if key not in self.records:
            return None
        bubble = self.records[key]["elliptic_bubble"]
        return bubble.to_dict()

    def get_bubble_energy(self, key: str) -> Optional[float]:
        if key not in self.records:
            return None
        return self.records[key]["elliptic_bubble"].energy

    def get_attractor(self, key: str) -> Optional[Dict]:
        if key not in self.records:
            return None
        bubble = self.records[key]["elliptic_bubble"]
        return self.elliptic_engine.build_recovery_vector(bubble)

    def detect_deviation(self, key: str, threshold: float = 0.1) -> bool:
        if key not in self.records:
            return False
        bubble = self.records[key]["elliptic_bubble"]
        return self.elliptic_engine.detect_deviation(bubble, threshold)

    def detect_collapse(self, key: str, threshold: float = 0.5) -> bool:
        if key not in self.records:
            return False
        bubble = self.records[key]["elliptic_bubble"]
        return self.elliptic_engine.detect_collapse(bubble, threshold)

    # ============================================================
    # 4. Statistics
    # ============================================================
    def get_stats(self) -> Dict[str, Any]:
        tier_counts = {"HOT": 0, "WARM": 0, "COLD": 0}
        heat_sum = 0.0
        energy_sum = 0.0
        for rec in self.records.values():
            tier_counts[rec["tier"].name] += 1
            heat_sum += rec["heat"]
            energy_sum += rec["elliptic_bubble"].energy

        n = max(1, len(self.records))
        return {
            "total_records": n,
            "avg_heat": heat_sum / n,
            "avg_energy": energy_sum / n,
            "tier_counts": tier_counts,
            "migration_stats": self.controller.stats,
            "recovery_vectors": len(self._recovery_vectors)
        }

    def get_elliptic_summary(self) -> Dict:
        """خلاصه وضعیت بیضوی کل دیتابیس"""
        states = {"equilibrium": 0, "converging": 0, "deviating": 0, "collapsing": 0}
        for rec in self.records.values():
            state = rec["elliptic_bubble"].state.value
            if state in states:
                states[state] += 1
        return {
            "total_bubbles": len(self.records),
            "state_distribution": states,
            "average_energy": sum(r["elliptic_bubble"].energy for r in self.records.values()) / max(1, len(self.records))
        }

    def set_calibrator_params(self, **kwargs):
        calibrator = TLDTierCalibrator(**kwargs)
        self.controller = TLDMemoryController(calibrator)
