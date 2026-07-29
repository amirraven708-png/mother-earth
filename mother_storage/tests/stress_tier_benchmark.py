#!/usr/bin/env python3
"""
stress_tier_benchmark.py (FIXED)
Tier Migration Stress Test with full heat oscillation range (0 to 1)
"""

import sys
import os
import math
import random
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from distributed_bubbledb import DistributedBubbleDB, DistributedBubbleDBConfig
from tld_tuner_module import TLDTierCalibrator, TLDMemoryController, MemoryTier

def generate_oscillating_heat(tick: int, period: int = 40, amplitude: float = 1.2, baseline: float = 0.5) -> float:
    """Generates heat in [0, 1] with amplitude > 1 to force crossing all thresholds."""
    phase = (tick % period) / period * 2 * math.pi
    raw = baseline + amplitude * math.sin(phase)
    return max(0.0, min(1.0, raw))

def run_benchmark(hysteresis_enabled: bool = True, num_records: int = 30, num_ticks: int = 200):
    print(f"\n{'='*60}")
    print(f"🔬 STRESS TEST: {'HYSTERESIS ON' if hysteresis_enabled else 'HYSTERESIS OFF'}")
    print(f"Records: {num_records}, Ticks: {num_ticks}")
    print(f"{'='*60}")

    if hysteresis_enabled:
        params = {
            "hot_enter": 0.70,
            "hot_exit": 0.50,
            "warm_enter": 0.35,
            "warm_exit": 0.20,
            "base_decay_rate": 0.0,
            "access_heat_gain": 0.0,
        }
    else:
        params = {
            "hot_enter": 0.60,
            "hot_exit": 0.60,
            "warm_enter": 0.40,
            "warm_exit": 0.40,
            "base_decay_rate": 0.0,
            "access_heat_gain": 0.0,
        }

    config = DistributedBubbleDBConfig(initial_state="cold", calibrator_params=params)
    db = DistributedBubbleDB(config)

    for i in range(num_records):
        key = f"rec_{i:04d}"
        phase_vec = {"R": 0.5, "V": 0.1, "R_fp": 0.0, "D_eff": 0.2, "H": 0.5, "B": 0.5, "BR": 0.3}
        db.put(key, f"val_{i}", phase_vec)
        db.records[key]['heat'] = 0.0

    transition_counts = {
        "cold_to_warm": 0,
        "warm_to_hot": 0,
        "hot_to_warm": 0,
        "warm_to_cold": 0,
        "oscillations": 0
    }
    tier_history = defaultdict(list)
    last_tick_state = {}

    for tick in range(1, num_ticks + 1):
        target_heat = generate_oscillating_heat(tick, period=40, amplitude=1.2, baseline=0.5)
        for key in db.records.keys():
            db.records[key]['heat'] = target_heat
            old_tier = db.records[key]['tier']
            db.records[key] = db.controller.process_tick(db.records[key])
            new_tier = db.records[key]['tier']

            if old_tier != new_tier:
                trans_key = f"{old_tier.name.lower()}_to_{new_tier.name.lower()}"
                transition_counts[trans_key] = transition_counts.get(trans_key, 0) + 1

                if key in last_tick_state and tick - last_tick_state[key] < 5:
                    transition_counts["oscillations"] += 1
                last_tick_state[key] = tick

            tier_history[key].append(new_tier.name)

    total_migrations = sum(v for k, v in transition_counts.items() if k != "oscillations")
    false_migration_rate = transition_counts["oscillations"] / max(1, total_migrations)

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
    stability_score = 1.0 - min(1.0, transition_counts["oscillations"] / max(1, total_migrations))

    print("\n📊 MIGRATION METRICS:")
    print(f"   Total Migrations: {total_migrations}")
    print(f"   Cold → Warm:     {transition_counts['cold_to_warm']}")
    print(f"   Warm → Hot:      {transition_counts['warm_to_hot']}")
    print(f"   Hot → Warm:      {transition_counts['hot_to_warm']}")
    print(f"   Warm → Cold:     {transition_counts['warm_to_cold']}")
    print(f"   Oscillations:    {transition_counts['oscillations']}")
    print(f"   False Migration Rate: {false_migration_rate:.4f}")

    print("\n🏠 MEAN RESIDENCE TIME (Ticks):")
    for tier, avg in avg_residence.items():
        bar = "█" * int(avg / 2)
        print(f"   {tier:4s}: {avg:6.2f} ticks {bar}")

    print(f"\n⚖️  Tier Stability Score: {stability_score:.4f} (1.0 = perfect)")

    return {
        "total_migrations": total_migrations,
        "oscillations": transition_counts["oscillations"],
        "false_migration_rate": false_migration_rate,
        "stability_score": stability_score,
        "transitions": transition_counts,
        "avg_residence": avg_residence,
    }

if __name__ == "__main__":
    print("🌊 WAVE MOTHER: TIER MIGRATION STRESS TEST (FIXED)")
    print("===================================================")

    result_off = run_benchmark(hysteresis_enabled=False, num_records=30, num_ticks=200)
    result_on = run_benchmark(hysteresis_enabled=True, num_records=30, num_ticks=200)

    print("\n" + "="*60)
    print("📈 FINAL COMPARISON: HYSTERESIS ON vs OFF")
    print("="*60)
    print(f"{'Metric':<25} | {'Hysteresis OFF':<15} | {'Hysteresis ON':<15} | {'Improvement':<10}")
    print("-"*70)

    for label, key in [
        ("Total Migrations", "total_migrations"),
        ("Oscillations", "oscillations"),
        ("False Migration Rate", "false_migration_rate"),
        ("Stability Score", "stability_score"),
    ]:
        off_val = result_off[key]
        on_val = result_on[key]
        if isinstance(off_val, float):
            imp = (off_val - on_val) / max(0.001, off_val) * 100 if off_val != 0 else 0
            print(f"{label:<25} | {off_val:<15.4f} | {on_val:<15.4f} | {imp:>9.1f}%")
        else:
            imp = (off_val - on_val) / max(1, off_val) * 100 if off_val != 0 else 0
            print(f"{label:<25} | {off_val:<15} | {on_val:<15} | {imp:>9.1f}%")

    print("\n💡 CONCLUSION:")
    if result_on['oscillations'] < result_off['oscillations']:
        print("✅ Hysteresis is EFFECTIVE: Significantly reduced oscillations.")
    else:
        print("⚠️  Hysteresis effect minimal. Try adjusting thresholds (hot_enter/hot_exit/warm_enter/warm_exit).")

    if result_on['stability_score'] > result_off['stability_score']:
        print("✅ Tier Stability IMPROVED with hysteresis.")
    else:
        print("⚠️  Stability score did not improve. Check threshold calibration.")

    print("\n🏁 Benchmark complete.")
