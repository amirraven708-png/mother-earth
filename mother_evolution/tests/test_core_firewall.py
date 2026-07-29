#!/usr/bin/env python3
"""
test_core_firewall.py
تست Core Firewall و حافظه تکاملی
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mother_evolution import EvolutionRuntime

def test_core_firewall():
    print("\n" + "="*70)
    print("🛡️ CORE FIREWALL TEST")
    print("   Testing immutable rules enforcement")
    print("="*70)

    runtime = EvolutionRuntime()

    # سناریو ۱: پیشنهاد خوب (پایدار)
    print("\n📌 Scenario 1: Stable proposal")
    state1 = {
        "stability": 0.75,
        "energy": 0.42,
        "phase_error": 0.12,
        "adaptability": 0.60,
        "coupling_k": 0.5,
        "buffer_size": 1024,
        "decay_rate": 0.015
    }
    result1 = runtime.evolve(state1)
    print(f"\nResult: accepted={result1['accepted']}, version={result1['version']}")

    # سناریو ۲: پیشنهاد با پایداری پایین (زیر حداقل)
    print("\n📌 Scenario 2: Unstable proposal (stability too low)")
    state2 = {
        "stability": 0.45,
        "energy": 0.42,
        "phase_error": 0.12,
        "adaptability": 0.60,
        "coupling_k": 0.5,
        "buffer_size": 1024,
        "decay_rate": 0.015
    }
    result2 = runtime.evolve(state2)
    print(f"\nResult: accepted={result2['accepted']}, version={result2['version']}")
    if not result2['accepted']:
        print(f"   Reason: {result2.get('reason', 'N/A')}")

    # سناریو ۳: پیشنهاد با انرژی بالا (بیش از حد)
    print("\n📌 Scenario 3: High energy proposal")
    state3 = {
        "stability": 0.75,
        "energy": 1.2,
        "phase_error": 0.12,
        "adaptability": 0.60,
        "coupling_k": 0.5,
        "buffer_size": 1024,
        "decay_rate": 0.015
    }
    result3 = runtime.evolve(state3)
    print(f"\nResult: accepted={result3['accepted']}, version={result3['version']}")

    # نمایش حافظه تکاملی
    print("\n" + "="*70)
    print("📊 EVOLUTION MEMORY")
    print("="*70)
    memory = runtime.controller.core.get_evolution_memory(limit=5)
    for record in memory:
        status = "✅" if record["decision"] else "❌"
        print(f"{status} {record['mutation_id']} | fitness={record['fitness']:.3f} | version={record['version']}")

    print("\n📈 DECISION STATS:")
    stats = runtime.controller.core.get_decision_stats()
    for mut_type, data in stats.items():
        print(f"   {mut_type}: accepted={data['accepted']}, rejected={data['rejected']}, avg_fitness={data['avg_fitness']:.3f}")

    print("\n✅ Core Firewall test complete.")

if __name__ == "__main__":
    test_core_firewall()
