#!/usr/bin/env python3
"""
benchmark_c2_test.py
True WARM Boundary Noise Test — measures hysteresis effect on COLD↔WARM transitions

Heat oscillates around 0.30-0.38 to cross warm_enter (0.35) and warm_exit (0.20/0.35)
"""

import sys
import os
import math
import random
from collections import defaultdict
from typing import Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from distributed_bubbledb import DistributedBubbleDB, DistributedBubbleDBConfig
from tld_tuner_module import TLDMemoryController, MemoryTier

# ============================================================
# 1. Configuration for WARM Boundary (ISOLATED HYSTERESIS)
# ============================================================
# OFF: Symmetric thresholds (no hysteresis)
HYSTERESIS_OFF_PARAMS = {
    "hot_enter": 0.70,
    "hot_exit": 0.70,
    "warm_enter": 0.35,
    "warm_exit": 0.35,
    "base_decay_rate": 0.0,
    "access_heat_gain": 0.0,
}

# ON: Hysteresis only at WARM boundary (warm_enter != warm_exit)
HYSTERESIS_ON_PARAMS = {
    "hot_enter": 0.70,
    "hot_exit": 0.70,
    "warm_enter": 0.35,
    "warm_exit": 0.20,
    "base_decay_rate": 0.0,
    "access_heat_gain": 0.0,
}

# ============================================================
# 2. Heat Generator for True WARM Boundary
# ============================================================
def warm_boundary_noise_c2(tick: int) -> float:
    """
    Oscillates around 0.34 with amplitude 0.04
    Range: 0.30 — 0.38 (crosses warm_enter=0.35)
    """
    base = 0.34
    noise = 0.04 * math.sin(tick * 1.5 + 0.3)
    return max(0.0, min(1.0, base + noise))

# ============================================================
# 3. Core Benchmark Runner
# ============================================================
def run_benchmark(params: Dict, heat_generator, num_records: int = 30, num_ticks: int = 200, label: str = "Test"):
    """Run a single benchmark with given parameters"""
    print(f"\n{'─'*60}")
    print(f"📊 {label}")
    print(f"{'─'*60}")

    config = DistributedBubbleDBConfig(initial_state="cold", calibrator_params=params)
    db = DistributedBubbleDB(config)

    # Inject records starting from COLD
    for i in range(num_records):
        key = f"rec_{i:04d}"
        phase_vec = {"R": 0.5, "V": 0.1, "R_fp": 0.0, "D_eff": 0.2, "H": 0.5, "B": 0.5, "BR": 0.3}
        db.put(key, f"val_{i}", phase_vec)
        db.records[key]['heat'] = 0.0  # start from COLD

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

    # Oscillations: A → B → A pattern (true oscillation detection)
    for key, history in tier_history.items():
        for i in range(2, len(history)):
            if history[i-2] == history[i] and history[i-2] != history[i-1]:
                oscillations += 1

    total_migrations = sum(transitions.values())
    oscillation_rate = oscillations / max(1, total_migrations)
    stability_score = 1.0 - min(1.0, oscillation_rate)

    # Residence Time
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

    print(f"   Total Migrations: {total_migrations}")
    print(f"   Oscillations (A→B→A): {oscillations}")
    print(f"   Oscillation Rate: {oscillation_rate:.4f}")
    print(f"   Stability Score: {stability_score:.4f}")
    print(f"   Avg Residence: HOT={avg_residence.get('HOT', 0):.1f} WARM={avg_residence.get('WARM', 0):.1f} COLD={avg_residence.get('COLD', 0):.1f} ticks")

    return {
        "total_migrations": total_migrations,
        "oscillations": oscillations,
        "oscillation_rate": oscillation_rate,
        "stability_score": stability_score,
        "avg_residence": avg_residence,
        "transitions": transitions,
    }

# ============================================================
# 4. Main Execution
# ============================================================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🌊 WAVE MOTHER: TRUE WARM BOUNDARY NOISE TEST (C2)")
    print("="*70)
    print("Testing hysteresis effect on COLD↔WARM transitions.")
    print(f"Heat range: 0.30 — 0.38 (crosses warm_enter=0.35)")
    print(f"OFF: warm_enter={HYSTERESIS_OFF_PARAMS['warm_enter']}, warm_exit={HYSTERESIS_OFF_PARAMS['warm_exit']} (symmetric)")
    print(f"ON : warm_enter={HYSTERESIS_ON_PARAMS['warm_enter']}, warm_exit={HYSTERESIS_ON_PARAMS['warm_exit']} (hysteresis)")
    print(f"HOT thresholds: enter={HYSTERESIS_OFF_PARAMS['hot_enter']}, exit={HYSTERESIS_OFF_PARAMS['hot_exit']} (same in both)\n")

    print("▶ HYSTERESIS OFF")
    result_off = run_benchmark(HYSTERESIS_OFF_PARAMS, warm_boundary_noise_c2, label="C2: WARM Boundary (OFF)")

    print("\n▶ HYSTERESIS ON")
    result_on = run_benchmark(HYSTERESIS_ON_PARAMS, warm_boundary_noise_c2, label="C2: WARM Boundary (ON)")

    # ============================================================
    # 5. Comparison
    # ============================================================
    print("\n" + "="*70)
    print("📊 COMPARISON: HYSTERESIS OFF vs ON (C2)")
    print("="*70)

    metrics = [
        ("total_migrations", "less"),
        ("oscillations", "less"),
        ("oscillation_rate", "less"),
        ("stability_score", "more"),
    ]

    print(f"{'Metric':<25} | {'OFF':<15} | {'ON':<15} | {'Improvement':<12}")
    print("-"*70)

    for label, direction in metrics:
        off_val = result_off[label]
        on_val = result_on[label]

        if isinstance(off_val, float):
            if direction == "less":
                imp = (off_val - on_val) / max(0.001, off_val) * 100 if off_val != 0 else 0
                imp_display = f"{imp:>+9.1f}%"
            else:  # more is better
                imp = (on_val - off_val) / max(0.001, off_val) * 100 if off_val != 0 else 0
                imp_display = f"{imp:>+9.1f}%"
            print(f"{label:<25} | {off_val:<15.4f} | {on_val:<15.4f} | {imp_display}")
        else:
            if direction == "less":
                imp = (off_val - on_val) / max(1, off_val) * 100 if off_val != 0 else 0
                imp_display = f"{imp:>+9.1f}%"
            else:
                imp = (on_val - off_val) / max(1, off_val) * 100 if off_val != 0 else 0
                imp_display = f"{imp:>+9.1f}%"
            print(f"{label:<25} | {off_val:<15} | {on_val:<15} | {imp_display}")

    # ============================================================
    # 6. Conclusion
    # ============================================================
    print("\n" + "="*70)
    print("📈 CONCLUSION: C2 — WARM Boundary Noise")
    print("="*70)

    if result_on["oscillations"] < result_off["oscillations"] * 0.5:
        print("✅ HYSTERESIS IS HIGHLY EFFECTIVE at WARM boundary: oscillations reduced >50%.")
        print("   The system successfully prevents COLD↔WARM churn near the threshold.")
    elif result_on["oscillations"] < result_off["oscillations"] * 0.8:
        print("✅ HYSTERESIS SHOWS EFFECT at WARM boundary: oscillations reduced.")
        print("   The system reduces churn but not as dramatically as HOT boundary.")
    elif result_off["total_migrations"] == 0:
        print("⚠️  TEST INCONCLUSIVE: No migrations occurred in either mode.")
        print("   Heat range may still be too low. Consider adjusting warm_enter to 0.32.")
    else:
        print("⚠️  HYSTERESIS EFFECT NOT CLEAR at WARM boundary.")
        print("   Consider increasing gap between warm_enter and warm_exit.")
        print(f"   Current warm_enter={HYSTERESIS_ON_PARAMS['warm_enter']}, warm_exit={HYSTERESIS_ON_PARAMS['warm_exit']}")

    # Display key numbers
    print(f"\n   OFF: migrations={result_off['total_migrations']}, oscillations={result_off['oscillations']}")
    print(f"   ON : migrations={result_on['total_migrations']}, oscillations={result_on['oscillations']}")

    print("\n🏁 Benchmark C2 complete.")
