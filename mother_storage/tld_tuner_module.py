# mother_storage/tld_tuner_module.py
"""
TLD Memory Tier Calibrator & Hysteresis Engine
================================================
A modular controller for TLD Memory V2 tiering management.

Uses the Dual-Foci Ellipse Memory dynamics:
- Focus 1 (F1): Long-term structural persistence (COLD archive tier)
- Focus 2 (F2): Short-term sensory momentum / active access (HOT tier)
- Orbit Region: Transitional working memory (WARM tier)

Resolves:
1. HOT-tier starvation (0% HOT allocation) via adaptive heat boost.
2. High WARM<->COLD migration rates via dual-threshold Hysteresis.
"""

from enum import Enum, auto
from typing import Dict, Any, Tuple, List


class MemoryTier(Enum):
    COLD = auto()  # F1 Structural / Archived
    WARM = auto()  # Orbital Transition
    HOT = auto()   # F2 Sensory / High-Access Active


class TLDTierCalibrator:
    """
    Manages heat accumulation, decay, and state transitions for memory records
    using hysteresis to suppress boundary migration noise.
    """
    def __init__(
        self,
        hot_enter: float = 0.75,
        hot_exit: float = 0.55,
        warm_enter: float = 0.30,
        warm_exit: float = 0.15,
        base_decay_rate: float = 0.015,
        access_heat_gain: float = 0.25,
        f1_structural_weight: float = 0.6,
        f2_momentum_weight: float = 0.4
    ):
        # Hysteresis Thresholds
        self.hot_enter = hot_enter
        self.hot_exit = hot_exit
        self.warm_enter = warm_enter
        self.warm_exit = warm_exit
        
        # Thermal Dynamics Parameters
        self.base_decay_rate = base_decay_rate
        self.access_heat_gain = access_heat_gain
        
        # Ellipse Foci Weights
        self.f1_weight = f1_structural_weight  # Long-term retention inertia
        self.f2_weight = f2_momentum_weight    # Immediate access burst

    def calculate_decay(self, current_heat: float, age_ticks: int, access_frequency: float) -> float:
        """
        Calculates adjusted heat decay considering access frequency momentum (F2) 
        and structural persistence (F1).
        """
        # Frequency dampens decay (frequent touches keep records in active orbit)
        momentum_factor = 1.0 / (1.0 + (access_frequency * self.f2_weight))
        effective_decay = self.base_decay_rate * momentum_factor
        
        new_heat = current_heat * (1.0 - effective_decay)
        return max(0.0, min(1.0, new_heat))

    def apply_access_event(self, current_heat: float, hit_count: int = 1) -> float:
        """
        Boosts record heat upon access event to drive HOT tier promotion.
        """
        boost = self.access_heat_gain * hit_count
        # Non-linear gain towards F2 sensory peak
        new_heat = current_heat + boost * (1.0 - (current_heat * 0.5))
        return min(1.0, new_heat)

    def evaluate_tier_transition(self, current_state: MemoryTier, heat: float) -> Tuple[MemoryTier, bool]:
        """
        Evaluates state transition using a Hysteresis Buffer to minimize unwanted oscillations.
        Returns: (New MemoryTier, bool indicating if a migration occurred)
        """
        next_state = current_state
        
        if current_state == MemoryTier.COLD:
            if heat >= self.warm_enter:
                next_state = MemoryTier.WARM
                
        elif current_state == MemoryTier.WARM:
            if heat >= self.hot_enter:
                next_state = MemoryTier.HOT
            elif heat < self.warm_exit:
                next_state = MemoryTier.COLD
                
        elif current_state == MemoryTier.HOT:
            if heat < self.hot_exit:
                next_state = MemoryTier.WARM
                
        migrated = (next_state != current_state)
        return next_state, migrated


class TLDMemoryController:
    """
    High-level state controller ready to be plugged directly into TLD Memory V2 pipelines.
    """
    def __init__(self, calibrator: TLDTierCalibrator = None):
        self.calibrator = calibrator or TLDTierCalibrator()
        self.stats = {
            "total_migrations": 0,
            "cold_to_warm": 0,
            "warm_to_hot": 0,
            "hot_to_warm": 0,
            "warm_to_cold": 0
        }

    def process_tick(self, record_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single tick for a given memory record dict.
        Expects keys: 'heat', 'tier', 'age_ticks', 'access_count'
        """
        heat = record_state.get('heat', 0.0)
        current_tier = record_state.get('tier', MemoryTier.COLD)
        age = record_state.get('age_ticks', 0)
        accesses = record_state.get('access_count', 0)
        
        # 1. Apply Decay
        updated_heat = self.calibrator.calculate_decay(heat, age, accesses)
        
        # 2. Evaluate Tier with Hysteresis
        new_tier, migrated = self.calibrator.evaluate_tier_transition(current_tier, updated_heat)
        
        if migrated:
            self._record_migration(current_tier, new_tier)
            
        record_state['heat'] = updated_heat
        record_state['tier'] = new_tier
        record_state['age_ticks'] = age + 1
        
        return record_state

    def touch_record(self, record_state: Dict[str, Any], hits: int = 1) -> Dict[str, Any]:
        """
        Triggered whenever a record is accessed by queries or pipeline runs.
        """
        current_heat = record_state.get('heat', 0.0)
        boosted_heat = self.calibrator.apply_access_event(current_heat, hits)
        
        record_state['heat'] = boosted_heat
        record_state['access_count'] = record_state.get('access_count', 0) + hits
        
        # Immediate state check post-access
        current_tier = record_state.get('tier', MemoryTier.COLD)
        new_tier, migrated = self.calibrator.evaluate_tier_transition(current_tier, boosted_heat)
        
        if migrated:
            self._record_migration(current_tier, new_tier)
            
        record_state['tier'] = new_tier
        return record_state

    def _record_migration(self, src: MemoryTier, dst: MemoryTier):
        self.stats["total_migrations"] += 1
        key = f"{src.name.lower()}_to_{dst.name.lower()}"
        if key in self.stats:
            self.stats[key] += 1


# ==========================================
# VERIFICATION & SELF-TEST RUNNER
# ==========================================
if __name__ == "__main__":
    print("🧪 Testing TLD Memory Tier Calibrator Module...")
    
    controller = TLDMemoryController()
    
    # Create sample record initial state
    sample_record = {
        "id": "rec_001",
        "heat": 0.10,
        "tier": MemoryTier.COLD,
        "age_ticks": 0,
        "access_count": 0
    }
    
    print(f"Initial: Tier={sample_record['tier'].name}, Heat={sample_record['heat']:.3f}")
    
    # Simulate Access hits (F2 Sensory Impulse)
    for touch in range(3):
        sample_record = controller.touch_record(sample_record, hits=2)
        print(f"After Touch {touch+1}: Tier={sample_record['tier'].name}, Heat={sample_record['heat']:.3f}")
        
    # Simulate Decay over ticks
    print("\nSimulating 20 logical decay ticks...")
    for tick in range(20):
        sample_record = controller.process_tick(sample_record)
        if tick % 5 == 0 or sample_record['tier'] != MemoryTier.HOT:
            print(f"Tick {tick+1:02d}: Tier={sample_record['tier'].name}, Heat={sample_record['heat']:.3f}")

    print("\nMigration Stats:", controller.stats)
    print("✅ Module test completed successfully.")
