#!/usr/bin/env python3
"""
test_elliptic_integration.py
سه تست اصلی برای ادغام Elliptic Memory با Distributed BubbleDB:

1. Multiple Attractors: آیا سیستم نزدیک‌ترین جاذب را انتخاب می‌کند؟
2. Gradual Drift: آیا سیستم قبل از فروپاشی هشدار می‌دهد؟
3. Direct Integration: آیا recovery vector به‌درستی ذخیره و بازیابی می‌شود؟
"""

import sys
import os
import math
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from mother_storage.distributed_bubbledb import DistributedBubbleDB, DistributedBubbleDBConfig
from mother_intelligence.elliptic_memory_engine import EllipticMemoryEngine

# ============================================================
# TEST 1: Multiple Attractors
# ============================================================
def test_multiple_attractors():
    print("\n" + "="*70)
    print("🧪 TEST 1: Multiple Attractors")
    print("   سیستم باید نزدیک‌ترین جاذب را انتخاب کند")
    print("="*70)

    db = DistributedBubbleDB()
    engine = EllipticMemoryEngine()

    # ایجاد دو جاذب
    attractor1 = (0.5, 0.3)  # (L, theta)
    attractor2 = (1.5, 1.2)

    # دو حباب با حالت‌های مختلف
    bubble1 = engine.create_bubble("bubble_A", phase=0.0, L=0.45, theta=0.28)
    bubble2 = engine.create_bubble("bubble_B", phase=0.0, L=1.55, theta=1.18)

    # همگرایی هر دو
    bubble1 = engine.converge_to_equilibrium(bubble1, max_steps=50)
    bubble2 = engine.converge_to_equilibrium(bubble2, max_steps=50)

    print(f"✅ Attractor A: L={bubble1.L:.3f}, theta={bubble1.theta:.3f}, energy={bubble1.energy:.6f}")
    print(f"✅ Attractor B: L={bubble2.L:.3f}, theta={bubble2.theta:.3f}, energy={bubble2.energy:.6f}")

    # ایجاد یک حباب جدید در میانه
    bubble_mid = engine.create_bubble("bubble_mid", phase=0.0, L=1.0, theta=0.7)
    print(f"\n🔄 Bubble mid: L={bubble_mid.L:.3f}, theta={bubble_mid.theta:.3f}")

    # همگرایی
    bubble_mid = engine.converge_to_equilibrium(bubble_mid, max_steps=100)
    print(f"   After convergence: L={bubble_mid.L:.3f}, theta={bubble_mid.theta:.3f}, energy={bubble_mid.energy:.6f}")

    # تشخیص نزدیک‌ترین جاذب
    dist_to_A = math.sqrt((bubble_mid.L - attractor1[0])**2 + (bubble_mid.theta - attractor1[1])**2)
    dist_to_B = math.sqrt((bubble_mid.L - attractor2[0])**2 + (bubble_mid.theta - attractor2[1])**2)

    print(f"\n📊 Distance to Attractor A: {dist_to_A:.4f}")
    print(f"📊 Distance to Attractor B: {dist_to_B:.4f}")

    if dist_to_A < dist_to_B:
        print("✅ Near A: system chose the closer attractor.")
    else:
        print("⚠️ System may not be choosing the closest attractor. Check convergence.")

    return bubble_mid

# ============================================================
# TEST 2: Gradual Drift
# ============================================================
def test_gradual_drift():
    print("\n" + "="*70)
    print("🧪 TEST 2: Gradual Drift")
    print("   سیستم باید قبل از فروپاشی هشدار دهد")
    print("="*70)

    db = DistributedBubbleDB()

    # ایجاد حباب با انرژی پایین
    phase_vec = {"R": 0.5, "theta": 0.3}
    db.put("drift_test", "value", phase_vec, L=0.5, theta=0.3)

    # شبیه‌سازی drift تدریجی
    drift_steps = [0.5, 0.7, 0.9, 1.1, 1.4, 1.8, 2.2]
    warnings = []

    print("\n📈 Drift simulation:")
    for step, L in enumerate(drift_steps):
        # به‌روزرسانی L
        rec = db.records["drift_test"]
        rec["elliptic_bubble"].L = L
        rec["elliptic_bubble"].energy = db.elliptic_engine.compute_energy(L, rec["elliptic_bubble"].theta)
        db.records["drift_test"] = rec

        # تشخیص انحراف
        is_deviating = db.detect_deviation("drift_test", threshold=0.05)
        is_collapsing = db.detect_collapse("drift_test", threshold=0.3)

        status = "✅" if not is_deviating else "⚠️" if is_deviating else "💥"
        warnings.append({
            "step": step,
            "L": L,
            "is_deviating": is_deviating,
            "is_collapsing": is_collapsing
        })
        print(f"   Step {step}: L={L:.2f}, energy={rec['elliptic_bubble'].energy:.4f}, deviating={is_deviating}, collapsing={is_collapsing}")

    # تحلیل
    deviating_steps = [w for w in warnings if w["is_deviating"]]
    collapsing_steps = [w for w in warnings if w["is_collapsing"]]

    print(f"\n📊 Summary:")
    print(f"   Total steps: {len(drift_steps)}")
    print(f"   Deviating steps: {len(deviating_steps)}")
    print(f"   Collapsing steps: {len(collapsing_steps)}")

    if len(deviating_steps) > 0:
        print("✅ Deviation detected before collapse.")
    else:
        print("⚠️ No deviation detected before collapse.")

    if len(collapsing_steps) > 0:
        print("✅ Collapse detection worked.")
    else:
        print("⚠️ Collapse not detected (threshold may be too high).")

# ============================================================
# TEST 3: Direct Integration
# ============================================================
def test_direct_integration():
    print("\n" + "="*70)
    print("🧪 TEST 3: Direct Integration")
    print("   Recovery Vector ذخیره و بازیابی می‌شود")
    print("="*70)

    db = DistributedBubbleDB()

    # ایجاد رکورد
    phase_vec = {"R": 0.6, "theta": 0.4}
    db.put("integration_test", "test_value", phase_vec, L=0.6, theta=0.4)

    # ذخیره recovery vector
    rec = db.records["integration_test"]
    bubble = rec["elliptic_bubble"]
    rv = db.elliptic_engine.build_recovery_vector(bubble)
    db.store_recovery_vector("integration_test", rv)

    print("✅ Recovery vector stored:")
    print(f"   target_phase: {rv.get('target_phase', 'N/A')}")
    print(f"   target_L: {rv.get('target_L', 'N/A')}")
    print(f"   target_theta: {rv.get('target_theta', 'N/A')}")

    # بازیابی
    retrieved_rv = db.get_recovery_vector("integration_test")
    if retrieved_rv:
        print("\n✅ Recovery vector retrieved successfully.")
        print(f"   Retrieved target_L: {retrieved_rv.get('target_L', 'N/A')}")
    else:
        print("❌ Failed to retrieve recovery vector.")

    # شبیه‌سازی خرابی
    rec["elliptic_bubble"].L = 3.0
    rec["elliptic_bubble"].energy = db.elliptic_engine.compute_energy(3.0, rec["elliptic_bubble"].theta)
    db.records["integration_test"] = rec
    print(f"\n💥 After damage: L={rec['elliptic_bubble'].L:.3f}, energy={rec['elliptic_bubble'].energy:.3f}")

    # بازیابی با recovery vector
    if retrieved_rv:
        bubble = db.elliptic_engine.apply_recovery_vector(
            db.records["integration_test"]["elliptic_bubble"],
            retrieved_rv
        )
        db.records["integration_test"]["elliptic_bubble"] = bubble
        print(f"\n🔧 After recovery: L={bubble.L:.3f}, energy={bubble.energy:.6f}")

        if bubble.energy < 0.01:
            print("✅ Recovery successful! Energy is back to equilibrium.")
        else:
            print("⚠️ Recovery not fully successful. Energy still high.")

# ============================================================
# RUN ALL TESTS
# ============================================================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🌊 ELLIPTIC MEMORY INTEGRATION TESTS")
    print("   Testing Multiple Attractors, Gradual Drift, and Recovery Vectors")
    print("="*70)

    test_multiple_attractors()
    test_gradual_drift()
    test_direct_integration()

    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETE")
    print("="*70)
