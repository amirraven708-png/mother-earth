#!/usr/bin/env python3
"""
test_full_evolution.py
تست کامل چرخه تکامل با اتصال به BubbleDB و Elliptic Memory
"""

import sys
import os
import math
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mother_evolution import EvolutionRuntime
from mother_intelligence.elliptic_memory_engine import EllipticMemoryEngine
from mother_storage.distributed_bubbledb import DistributedBubbleDB, DistributedBubbleDBConfig

def test_full_evolution():
    print("\n" + "="*70)
    print("🌱 MOTHER EVOLUTION — FULL CYCLE TEST")
    print("   Integration: BubbleDB + Elliptic Memory + Evolution Loop")
    print("="*70)

    # 1. Setup BubbleDB with Elliptic Memory
    db_config = DistributedBubbleDBConfig(initial_state="cold")
    db = DistributedBubbleDB(db_config)

    # 2. Create some records
    print("\n📦 Creating test records in BubbleDB...")
    for i in range(10):
        phase_vec = {"R": 0.5 + i*0.02, "theta": 0.3 + i*0.01}
        db.put(f"rec_{i:04d}", f"value_{i}", phase_vec, L=0.5, theta=0.3)

    # 3. Simulate system state (current state of memory)
    current_state = {
        "stability": 0.75,
        "energy": 0.42,
        "phase_error": 0.12,
        "adaptability": 0.60,
        "coupling_k": 0.5,
        "buffer_size": 1024,
        "decay_rate": 0.015,
        "records_count": len(db.records)
    }

    print(f"\n📊 Initial System State:")
    print(f"   Stability: {current_state['stability']:.3f}")
    print(f"   Energy: {current_state['energy']:.3f}")
    print(f"   Records: {current_state['records_count']}")

    # 4. Run Evolution
    print("\n" + "="*70)
    print("🧬 STARTING EVOLUTION LOOP")
    print("="*70)

    runtime = EvolutionRuntime()

    # Run multiple evolution cycles
    for cycle in range(3):
        print(f"\n{'─'*50}")
        print(f"🔄 Evolution Cycle {cycle + 1}")
        print(f"{'─'*50}")

        # Update state with some changes
        current_state["stability"] = max(0.5, current_state["stability"] - 0.05 * (cycle + 1))
        current_state["energy"] = min(1.0, current_state["energy"] + 0.1 * (cycle + 1))

        result = runtime.evolve(current_state)

        # If accepted, apply changes to BubbleDB
        if result["accepted"]:
            print(f"\n📦 Applying evolution to BubbleDB...")
            # Apply optimized parameters
            version = result["version"]
            print(f"   Active Version: {version}")

            # Simulate application of changes
            for key in list(db.records.keys())[:3]:
                rec = db.records[key]
                rec["heat"] = max(0.1, rec["heat"] - 0.02)
                rec["elliptic_bubble"].L = rec["heat"]
                db.records[key] = rec

    # 5. Final state
    print("\n" + "="*70)
    print("📊 FINAL SYSTEM STATE")
    print("="*70)

    stats = db.get_stats()
    elliptic_summary = db.get_elliptic_summary()

    print(f"\nActive Version: {runtime.get_version()}")
    print(f"Evolution History: {len(runtime.get_history())} mutations")

    print(f"\n📦 BubbleDB Stats:")
    print(f"   Records: {stats['total_records']}")
    print(f"   Avg Energy: {stats.get('avg_energy', 0):.3f}")
    print(f"   Tier Counts: {stats['tier_counts']}")

    print(f"\n🧬 Elliptic Memory Summary:")
    print(f"   Total Bubbles: {elliptic_summary['total_bubbles']}")
    print(f"   State Distribution: {elliptic_summary['state_distribution']}")
    print(f"   Avg Energy: {elliptic_summary['average_energy']:.4f}")

    print("\n✅ Evolution Complete!")

if __name__ == "__main__":
    test_full_evolution()
