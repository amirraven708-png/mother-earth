#!/usr/bin/env python3
"""
benchmark_four_tests.py
Scientific Benchmark for Hysteresis Effectiveness in Wave Mother Memory System

Tests:
  A: Full Range Sweep (0.0 → 1.0 → 0.0) — validates transition correctness
  B: HOT Boundary Noise (0.58-0.63) — measures hysteresis effect on HOT/WARM
  C: WARM Boundary Noise (0.28-0.33) — measures hysteresis effect on WARM/COLD
  D: Random Heat Noise (0.60 ± 0.15) — measures overall system stability

Oscillation defined as: A → B → A pattern within a 5-tick window.
"""

import sys
import os
import math
import random
from collections import defaultdict
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from distributed_bubbledb import DistributedBubbleDB, DistributedBubbleDBConfig
from tld_tuner_module import TLDMemoryController, MemoryTier

# ============================================================
# 1. Configuration
# ============================================================
HYSTERESIS_ON_PARAMS = {
    "hot_enter": 0.70,
    "hot_exit": 0.50,
    "warm_enter": 0.35,
    "warm_exit": 0.20,
    "base_decay_rate": 0.0,
    "access_heat_gain": 0.0,
}

HYSTERESIS_OFF_PARAMS = {
    "hot_enter": 0.60,
    "hot_exit": 0.60,
    "warm_enter": 0.40,
    "warm_exit": 0.40,
    "base_decay_rate": 0.0,
    "access_heat_gain": 0.0,
}

# ============================================================
# 2. Heat Generators
# ============================================================
def full_range_sweep(tick: int) -> float:
    """0.0 → 1.0 → 0.0 over 200 ticks"""
    period = 200
    phase = (tick % period) / period * 2 * math.pi
    return max(0.0, min(1.0, 0.5 + 0.5 * math.sin(phase)))

def hot_boundary_noise(tick: int) -> float:
    """Oscillate around HOT boundary (0.58-0.63)"""
    base = 0.605
    noise = 0.025 * math.sin(tick * 1.7)
    return max(0.0, min(1.0, base + noise))

def warm_boundary_noise(tick: int) -> float:
    """Oscillate around WARM boundary (0.28-0.33)"""
    base = 0.305
    noise = 0.025 * math.sin(tick * 1.3 + 0.5)
    return max(0.0, min(1.0, base + noise))

def random_heat_noise(tick: int) -> float:
    """Random heat with noise"""
    base = 0.60
    noise = random.uniform(-0.15, 0.15)
    return max(0.0, min(1.0, base + noise))

# ============================================================
# 3. Core Benchmark Runner
# ============================================================
def run_benchmark(params: Dict, heat_generator, num_records: int = 30, num_ticks: int = 200, test_name: str = "Test"):
    """Run a single benchmark with given parameters and heat generator"""
    print(f"\n{'─'*60}")
    print(f"📊 {test_name}")
    print(f"{'─'*60}")

    # Setup DB
    config = DistributedBubbleDBConfig(initial_state="cold", calibrator_params=params)
    db = DistributedBubbleDB(config)

    # Inject records
    for i in range(num_records):
        key = f"rec_{i:04d}"
        phase_vec = {"R": 0.5, "V": 0.1, "R_fp": 0.0, "D_eff": 0.2, "H": 0.5, "B": 0.5, "BR": 0.3}
        db.put(key, f"val_{i}", phase_vec)
        db.records[key]['heat'] = 0.0

    # Trackers
    transitions = {"cold_to_warm": 0, "warm_to_hot": 0, "hot_to_warm": 0, "warm_to_cold": 0}
    tier_history = defaultdict(list)
    oscillations = 0

    for tick in range(1, num_ticks + 1):
        target_heat = heat_generator(tick)
        for key in db.records.keys():
            db.records[key]['heat'] = target_heat
            old_tier = db.records[key]['tier']
            db.records[key] = db.controller.process_tick(db.records[key])
            new_tier = db.records[key]['tier']

            if old_tier != new_tier:
                trans_key = f"{old_tier.name.lower()}_to_{new_tier.name.lower()}"
                transitions[trans_key] = transitions.get(trans_key, 0) + 1

            tier_history[key].append(new_tier.name)

    # Calculate Oscillations (A → B → A pattern)
    for key, history in tier_history.items():
        for i in range(2, len(history)):
            if history[i-2] == history[i] and history[i-2] != history[i-1]:
                oscillations += 1

    total_migrations = sum(transitions.values())
    residence_times = {"HOT": [], "WARM": [], "COLD": []}
    for key, history in tier_history.items():
        if not history: continue
        current = history[0]
        count = 1
        for tier in history[1:]:
            if tier == current:
                count += 1
            else:
                residence_times[current].append(count)
                current = tier
                count = 1
        residence_times[current].append(count)

    avg_residence = {k: (sum(v)/len(v) if v else 0) for k, v in residence_times.items()}
    false_migration_rate = oscillations / max(1, total_migrations)
    stability_score = 1.0 - min(1.0, oscillations / max(1, total_migrations))

    print(f"   Total Migrations: {total_migrations}")
    print(f"   Oscillations (A→B→A): {oscillations}")
    print(f"   False Migration Rate: {false_migration_rate:.4f}")
    print(f"   Stability Score: {stability_score:.4f}")
    print(f"   Avg Residence: HOT={avg_residence.get('HOT', 0):.1f} WARM={avg_residence.get('WARM', 0):.1f} COLD={avg_residence.get('COLD', 0):.1f} ticks")

    return {
        "total_migrations": total_migrations,
        "oscillations": oscillations,
        "false_migration_rate": false_migration_rate,
        "stability_score": stability_score,
        "avg_residence": avg_residence,
        "transitions": transitions,
        "tier_history": tier_history,
    }

# ============================================================
# 4. Main Execution
# ============================================================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🌊 WAVE MOTHER: SCIENTIFIC HYSTERESIS BENCHMARK")
    print("="*70)
    print("Testing hysteresis effectiveness across 4 distinct scenarios.\n")

    all_results = {
        "ON": {},
        "OFF": {},
    }

    tests = [
        ("A: Full Range Sweep", full_range_sweep),
        ("B: HOT Boundary Noise", hot_boundary_noise),
        ("C: WARM Boundary Noise", warm_boundary_noise),
        ("D: Random Heat Noise", random_heat_noise),
    ]

    for test_name, heat_gen in tests:
        print(f"\n{'='*60}")
        print(f"🔬 TEST {test_name}")
        print(f"{'='*60}")

        print("\n▶ HYSTERESIS OFF")
        result_off = run_benchmark(HYSTERESIS_OFF_PARAMS, heat_gen, test_name=f"{test_name} (OFF)")

        print("\n▶ HYSTERESIS ON")
        result_on = run_benchmark(HYSTERESIS_ON_PARAMS, heat_gen, test_name=f"{test_name} (ON)")

        # Store results
        all_results["OFF"][test_name] = result_off
        all_results["ON"][test_name] = result_on

        # Compare
        print("\n📊 COMPARISON:")
        print(f"   Metric              | OFF        | ON         | Improvement")
        print("   " + "-"*55)
        for key in ["total_migrations", "oscillations", "false_migration_rate", "stability_score"]:
            off_val = result_off[key]
            on_val = result_on[key]
            if isinstance(off_val, float):
                imp = (off_val - on_val) / max(0.001, off_val) * 100 if off_val != 0 else 0
                print(f"   {key:<20} | {off_val:<10.4f} | {on_val:<10.4f} | {imp:>9.1f}%")
            else:
                imp = (off_val - on_val) / max(1, off_val) * 100 if off_val != 0 else 0
                print(f"   {key:<20} | {off_val:<10} | {on_val:<10} | {imp:>9.1f}%")

    # ============================================================
    # 5. Final Summary
    # ============================================================
    print("\n" + "="*70)
    print("📈 FINAL SUMMARY: HYSTERESIS EFFECTIVENESS")
    print("="*70)

    for test_name, _ in tests:
        off_res = all_results["OFF"][test_name]
        on_res = all_results["ON"][test_name]

        osc_imp = (off_res["oscillations"] - on_res["oscillations"]) / max(1, off_res["oscillations"]) * 100
        stab_imp = (on_res["stability_score"] - off_res["stability_score"]) / max(0.001, off_res["stability_score"]) * 100

        print(f"\n{test_name}:")
        print(f"   Oscillations: {off_res['oscillations']} → {on_res['oscillations']} ({osc_imp:+.1f}%)")
        print(f"   Stability:    {off_res['stability_score']:.3f} → {on_res['stability_score']:.3f} ({stab_imp:+.1f}%)")

    print("\n💡 CONCLUSION:")
    # Check if hysteresis shows significant effect in boundary tests
    hot_osc_off = all_results["OFF"]["B: HOT Boundary Noise"]["oscillations"]
    hot_osc_on = all_results["ON"]["B: HOT Boundary Noise"]["oscillations"]
    warm_osc_off = all_results["OFF"]["C: WARM Boundary Noise"]["oscillations"]
    warm_osc_on = all_results["ON"]["C: WARM Boundary Noise"]["oscillations"]

    if hot_osc_on < hot_osc_off * 0.7 and warm_osc_on < warm_osc_off * 0.7:
        print("✅ HYSTERESIS IS HIGHLY EFFECTIVE: Significantly reduced oscillations in boundary tests.")
    elif hot_osc_on < hot_osc_off * 0.9 or warm_osc_on < warm_osc_off * 0.9:
        print("✅ HYSTERESIS SHOWS SOME EFFECT: Reduced oscillations in at least one boundary test.")
    else:
        print("⚠️  HYSTERESIS EFFECT NOT CLEARLY VISIBLE: Boundary tests did not show significant improvement.")
        print("   Possible causes: threshold gaps too narrow, or heat signal too aggressive.")

    print("\n🏁 Benchmark complete.")
