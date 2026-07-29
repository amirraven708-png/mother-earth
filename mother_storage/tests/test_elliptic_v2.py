#!/usr/bin/env python3
"""
test_elliptic_v2.py
تست نسخه دوم با Drift Detector و Recovery Vector کامل
"""

import sys
import os
import math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from mother_intelligence.elliptic_memory_engine import EllipticMemoryEngine
from mother_intelligence.drift_detector import DriftDetector
from mother_intelligence.recovery_vector import RecoveryVectorBuilder

def test_gradual_drift_with_detector():
    print("\n" + "="*70)
    print("🧪 TEST: Gradual Drift with Drift Detector")
    print("   تشخیص رانش قبل از فروپاشی")
    print("="*70)

    engine = EllipticMemoryEngine()
    detector = DriftDetector(energy_threshold=0.5)

    # ایجاد حباب
    bubble = engine.create_bubble("drift_test", phase=0.0, L=0.5, theta=0.3)

    drift_steps = [0.5, 0.7, 0.9, 1.1, 1.4, 1.8, 2.2, 2.8]

    print("\n📈 Drift simulation with detector:")
    print(f"{'Step':>6} | {'L':>6} | {'Energy':>10} | {'drifting':>10} | {'accelerating':>12} | {'critical':>10}")
    print("-"*65)

    for step, L in enumerate(drift_steps):
        bubble.L = L
        bubble.energy = engine.compute_energy(L, bubble.theta)
        status = detector.update(bubble.energy)

        print(f"{step:>6} | {L:>6.2f} | {bubble.energy:>10.4f} | {str(status['drifting']):>10} | {str(status['accelerating']):>12} | {str(status['critical']):>10}")

        if status["critical"]:
            print(f"\n⚠️  CRITICAL at L={L:.2f} (energy={bubble.energy:.4f})")
            break

    print("\n" + "="*70)
    print("📊 SUMMARY:")
    if status.get("critical", False):
        print("✅ Drift detector identified critical drift before collapse.")
    else:
        print("⚠️  Critical drift not detected — adjust thresholds.")

def test_recovery_vector_full():
    print("\n" + "="*70)
    print("🧪 TEST: Recovery Vector (Full Dynamic State)")
    print("   ذخیره و بازیابی وضعیت کامل دینامیکی")
    print("="*70)

    engine = EllipticMemoryEngine()
    bubble = engine.create_bubble("recovery_test", phase=0.0, L=0.6, theta=0.4)

    # شبیه‌سازی چند گام برای ایجاد تاریخچه
    for _ in range(5):
        bubble = engine.step_manifold(bubble)

    # ساخت بردار بازیابی کامل
    rv = RecoveryVectorBuilder.build(bubble, engine)

    print("✅ Recovery Vector built:")
    print(f"   target_L: {rv.target_state.L:.4f}")
    print(f"   target_theta: {rv.target_state.theta:.4f}")
    print(f"   velocity: dL={rv.velocity['dL']:.4f}, dtheta={rv.velocity['dtheta']:.4f}")
    print(f"   gradient: dV/dL={rv.gradient['dV_dL']:.4f}, dV/dtheta={rv.gradient['dV_dtheta']:.4f}")
    print(f"   basin_id: {rv.basin_id}")
    print(f"   trajectory length: {len(rv.trajectory)}")

    # شبیه‌سازی خرابی (L بزرگ)
    bubble.L = 3.0
    bubble.energy = engine.compute_energy(bubble.L, bubble.theta)
    print(f"\n💥 After damage: L={bubble.L:.3f}, energy={bubble.energy:.3f}")

    # بازیابی با بردار کامل
    RecoveryVectorBuilder.apply(bubble, rv)
    print(f"\n🔧 After recovery: L={bubble.L:.3f}, energy={bubble.energy:.6f}")

    if bubble.energy < 0.01:
        print("✅ Recovery successful! Energy restored to equilibrium.")
    else:
        print("⚠️  Recovery partially successful — energy still high.")

if __name__ == "__main__":
    test_gradual_drift_with_detector()
    test_recovery_vector_full()
