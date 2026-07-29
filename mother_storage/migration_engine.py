"""
migration_engine.py — نسخه ۲
مدل مهاجرت نرم با:
- weighted_mean به‌جای جمع بایاس‌دار
- smoothing (فیلتر پایین‌گذر) روی فشار مهاجرت
- hysteresis state-aware (آستانه‌های متفاوت برای هر مسیر)
- logical_age به‌جای wall_clock_age
"""

import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List, Any
from enum import Enum

class MigrationAction(Enum):
    PROMOTE = "promote"      # COLD → WARM یا WARM → HOT
    DEMOTE = "demote"        # HOT → WARM یا WARM → COLD
    KEEP = "keep"

class ThermalState(Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"

@dataclass
class MigrationDecision:
    action: MigrationAction
    pressure: float           # فشار مهاجرت نرمال‌شده (۰ تا ۱)
    smoothed_pressure: float  # فشار هموار شده
    target_state: ThermalState
    reason: str

@dataclass
class RecordMetadata:
    key: str
    phase_vector: Dict[str, float]  # {R, V, R_fp, D_eff, H, B, BR}
    state: ThermalState = ThermalState.WARM
    heat: float = 0.5               # ۰ تا ۱ (مقدار فعلی)
    resonance: float = 0.0
    age_ticks: int = 0              # logical age (تعداد چرخه)
    last_migration_tick: int = 0
    smoothed_pressure: float = 0.5  # مقدار هموار شدهٔ فشار
    previous_state: Optional[ThermalState] = None

class MigrationEngineV2:
    """
    موتور مهاجرت نسخه ۲:
    - امتیازدهی متوازن حول ۰.۵
    - smoothing با فیلتر پایین‌گذر
    - hysteresis دوطرفه با آستانه‌های متفاوت
    - logical_age برای تست‌های سریع
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        smoothing: float = 0.20,
        promote_thresholds: Optional[Dict[str, float]] = None,
        demote_thresholds: Optional[Dict[str, float]] = None,
        logical_decay_ticks: int = 100,
    ):
        self.weights = weights or {
            "activity": 0.30,
            "resonance": 0.25,
            "phase_alignment": 0.20,
            "recency": 0.15,
            "storage_pressure": -0.10,
        }
        self.smoothing = smoothing

        # آستانه‌های promote (انتقال به گرم‌تر)
        self.promote_thresholds = promote_thresholds or {
            "cold_to_warm": 0.55,
            "warm_to_hot": 0.65,
        }
        # آستانه‌های demote (انتقال به سردتر)
        self.demote_thresholds = demote_thresholds or {
            "hot_to_warm": 0.45,
            "warm_to_cold": 0.35,
        }

        self.logical_decay_ticks = logical_decay_ticks

    def compute_migration_pressure(self, metadata: RecordMetadata, storage_pressure: float = 0.0) -> float:
        """
        محاسبه فشار مهاجرت نرمال‌شده (۰ تا ۱) با weighted_mean.
        - activity: نرخ تغییرات بردار فاز
        - resonance: تشدید با فاز شبکه
        - phase_alignment: هم‌ترازی با فاز غالب
        - recency: تازگی داده (بر اساس logical_age)
        - storage_pressure: فشار ذخیره‌سازی (هرچه بیشتر، تمایل به سردتر)
        """
        vec = metadata.phase_vector

        # ۱. activity = نرم مشتق (ساده‌شده)
        activity = sum(abs(v) for v in vec.values()) / max(1, len(vec))

        # ۲. resonance (با استفاده از R و B)
        R = vec.get("R", 0.5)
        B = vec.get("B", 0.5)
        resonance = 0.5 * R + 0.5 * B

        # ۳. phase_alignment (با استفاده از BR و H)
        BR = vec.get("BR", 0.0)
        H = vec.get("H", 0.5)
        phase_alignment = 0.5 * (1 - BR) + 0.5 * H

        # ۴. recency (بر اساس logical_age)
        age_factor = math.exp(-metadata.age_ticks / self.logical_decay_ticks)
        recency = 1.0 - age_factor

        # ۵. weighted_mean
        weighted_sum = (
            self.weights["activity"] * activity
            + self.weights["resonance"] * resonance
            + self.weights["phase_alignment"] * phase_alignment
            + self.weights["recency"] * recency
            + self.weights["storage_pressure"] * (1.0 - storage_pressure)
        )
        total_weight = sum(w for w in self.weights.values() if w > 0)
        pressure = weighted_sum / max(1, total_weight)

        return max(0.0, min(1.0, pressure))

    def smooth_pressure(self, current_pressure: float, previous_smoothed: float) -> float:
        """فیلتر پایین‌گذر مرتبه اول: smoothed = (1-α)*prev + α*current"""
        return (1 - self.smoothing) * previous_smoothed + self.smoothing * current_pressure

    def decide_action(
        self,
        metadata: RecordMetadata,
        storage_pressure: float = 0.0,
    ) -> MigrationDecision:
        """
        تصمیم‌گیری با hysteresis state-aware:
        - هر مسیر آستانهٔ خاص خود را دارد
        - smoothing روی فشار اعمال می‌شود
        """
        current_state = metadata.state

        # ۱. محاسبه فشار خام
        raw_pressure = self.compute_migration_pressure(metadata, storage_pressure)

        # ۲. smoothing
        smoothed = self.smooth_pressure(raw_pressure, metadata.smoothed_pressure)
        metadata.smoothed_pressure = smoothed  # به‌روزرسانی برای چرخه بعد

        # ۳. منطق تصمیم‌گیری با آستانه‌های state-aware
        action = MigrationAction.KEEP
        target_state = current_state
        reason = ""

        # انتقال به گرم‌تر (PROMOTE)
        if current_state == ThermalState.COLD and smoothed > self.promote_thresholds["cold_to_warm"]:
            action = MigrationAction.PROMOTE
            target_state = ThermalState.WARM
            reason = f"COLD → WARM (smoothed={smoothed:.3f} > {self.promote_thresholds['cold_to_warm']})"

        elif current_state == ThermalState.WARM and smoothed > self.promote_thresholds["warm_to_hot"]:
            action = MigrationAction.PROMOTE
            target_state = ThermalState.HOT
            reason = f"WARM → HOT (smoothed={smoothed:.3f} > {self.promote_thresholds['warm_to_hot']})"

        # انتقال به سردتر (DEMOTE)
        elif current_state == ThermalState.HOT and smoothed < self.demote_thresholds["hot_to_warm"]:
            action = MigrationAction.DEMOTE
            target_state = ThermalState.WARM
            reason = f"HOT → WARM (smoothed={smoothed:.3f} < {self.demote_thresholds['hot_to_warm']})"

        elif current_state == ThermalState.WARM and smoothed < self.demote_thresholds["warm_to_cold"]:
            action = MigrationAction.DEMOTE
            target_state = ThermalState.COLD
            reason = f"WARM → COLD (smoothed={smoothed:.3f} < {self.demote_thresholds['warm_to_cold']})"

        # اگر تغییری نکرد، KEEP
        if action == MigrationAction.KEEP:
            reason = f"KEEP at {current_state.value} (smoothed={smoothed:.3f})"

        return MigrationDecision(
            action=action,
            pressure=raw_pressure,
            smoothed_pressure=smoothed,
            target_state=target_state,
            reason=reason,
        )
