#!/usr/bin/env python3
"""
test_elliptic_memory.py
تست یکپارچه موتور حافظه بیضوی
"""

import sys
import math
sys.path.insert(0, '.')

from mother_intelligence.elliptic_memory_engine import EllipticMemoryEngine
from mother_healing.decision_guard import DecisionGuard
from mother_healing.replay_engine import ReplayEngine
from mother_healing.generative_repair import GenerativeRepair

def test_elliptic_memory():
    print("\n" + "="*70)
    print("🧪 ELLIPTIC MEMORY — INTEGRATION TEST")
    print("="*70)

    # 1. ایجاد موتور حافظه بیضوی
    engine = EllipticMemoryEngine(tolerance=1e-6)

    # 2. ایجاد حباب
    bubble = engine.create_bubble("test_01", phase=0.0, L=0.5, theta=0.3)
    print(f"✅ Bubble created: id={bubble.bubble_id}, energy={bubble.energy:.3f}")

    # 3. حرکت روی منیفولد
    print("\n⏳ Moving on manifold (20 steps)...")
    for step in range(20):
        bubble = engine.step_manifold(bubble)
        if step % 5 == 0:
            print(f"  Step {step}: L={bubble.L:.3f}, theta={bubble.theta:.3f}, energy={bubble.energy:.3f}")

    # 4. ساخت recovery vector
    rv = engine.build_recovery_vector(bubble)
    print(f"\n📦 Recovery vector built: target_phase={rv['target_phase']:.3f}")

    # 5. شبیه‌سازی خروج از تعادل
    print("\n⚠️ Simulating deviation...")
    bubble.L = 2.0
    bubble.energy = engine.compute_energy(bubble.L, bubble.theta)
    print(f"   After deviation: L={bubble.L:.3f}, energy={bubble.energy:.3f}")

    # 6. Decision Guard
    guard = DecisionGuard(engine, energy_threshold=0.1)
    should_recover, reason = guard.should_recover(bubble)
    print(f"\n🛡 Decision Guard: should_recover={should_recover}, reason={reason}")

    # 7. Replay Engine
    replay = ReplayEngine()
    last_stable = replay.find_last_stable_attractor(bubble)
    print(f"\n🔄 Last stable attractor: {last_stable}")

    # 8. Generative Repair
    repair = GenerativeRepair(engine)
    bubble = repair.generate_new_state(bubble)
    print(f"\n🔧 After generative repair: L={bubble.L:.3f}, energy={bubble.energy:.3f}")

    # 9. همگرایی کامل
    print("\n⏳ Converging to equilibrium...")
    bubble = engine.converge_to_equilibrium(bubble, max_steps=100)
    print(f"   Final: L={bubble.L:.3f}, theta={bubble.theta:.3f}, energy={bubble.energy:.6f}")

    print("\n" + "="*70)
    print("✅ ELLIPTIC MEMORY TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    test_elliptic_memory()
