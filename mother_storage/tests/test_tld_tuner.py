#!/usr/bin/env python3
"""
test_tld_tuner.py
تست ماژول TLDTierCalibrator با ۲۰۰۰ رکورد و شبیه‌سازی دسترسی‌های تصادفی
"""

import sys
import os
import random
import time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tld_tuner_module import TLDMemoryController, MemoryTier

def generate_random_heat():
    return random.uniform(0.0, 0.3)

def run_tuner_test(num_records=2000, num_ticks=200):
    print("🧪 TLD Tuner — Balanced Tiering Test")
    print("=" * 80)
    print(f"Records: {num_records}, Ticks: {num_ticks}")
    print("=" * 80)

    controller = TLDMemoryController()
    records = {}

    # ۱. ایجاد رکوردها با heat پایین (شروع از COLD)
    print("\n📥 Initializing records...")
    for i in range(num_records):
        records[f"rec_{i:06d}"] = {
            "id": f"rec_{i:06d}",
            "heat": generate_random_heat(),
            "tier": MemoryTier.COLD,
            "age_ticks": 0,
            "access_count": 0
        }

    # ۲. اجرای چرخه‌ها با دسترسی‌های تصادفی
    print("⏳ Running cycles with random access patterns...")
    start_time = time.time()

    for tick in range(1, num_ticks + 1):
        # شبیه‌سازی دسترسی‌های تصادفی (۱۰٪ رکوردها در هر تیک)
        if random.random() < 0.3:
            for _ in range(int(num_records * 0.05)):
                key = random.choice(list(records.keys()))
                hits = random.randint(1, 3)
                records[key] = controller.touch_record(records[key], hits=hits)

        # پردازش چرخه (decay)
        for key, rec in records.items():
            records[key] = controller.process_tick(rec)

        # نمایش وضعیت هر ۵۰ تیک
        if tick % 50 == 0 or tick == 1:
            tier_counts = {"HOT": 0, "WARM": 0, "COLD": 0}
            for rec in records.values():
                tier_counts[rec['tier'].name] += 1
            print(f"  Tick {tick:3d}: HOT={tier_counts['HOT']:4d}, WARM={tier_counts['WARM']:4d}, COLD={tier_counts['COLD']:4d}")

    elapsed = time.time() - start_time

    # ۳. آمار نهایی
    print("\n" + "=" * 80)
    print("📊 FINAL STATISTICS")
    print("=" * 80)

    tier_counts = {"HOT": 0, "WARM": 0, "COLD": 0}
    total_heat = 0
    for rec in records.values():
        tier_counts[rec['tier'].name] += 1
        total_heat += rec['heat']

    avg_heat = total_heat / num_records

    print(f"\n⏱️  Time: {elapsed:.2f}s")
    print(f"📦 Records: {num_records}")
    print(f"🔥 Average Heat: {avg_heat:.3f}")
    print(f"📊 Migration Stats: {controller.stats}")

    print("\n📊 Tier Distribution:")
    for tier, count in tier_counts.items():
        pct = count / num_records * 100
        bar = "█" * int(pct / 2)
        print(f"   {tier:4s}: {count:5d} ({pct:5.1f}%) {bar}")

    # ۴. نتیجه‌گیری
    print("\n" + "=" * 80)
    print("📊 CONCLUSION")
    print("=" * 80)

    hot_pct = tier_counts["HOT"] / num_records * 100
    warm_pct = tier_counts["WARM"] / num_records * 100
    cold_pct = tier_counts["COLD"] / num_records * 100

    if hot_pct > 5 and cold_pct > 5 and warm_pct > 5:
        print("✅ Balanced distribution achieved: HOT, WARM, COLD all present.")
    else:
        print("⚠️  Distribution still skewed. Consider adjusting thresholds.")

    # بررسی نرخ مهاجرت
    total_migrations = controller.stats["total_migrations"]
    migration_rate = total_migrations / (num_records * (num_ticks / 100))
    print(f"🔄 Migration Rate: {migration_rate:.3f} per 100 ticks per record")

    if migration_rate < 0.5:
        print("✅ Migration rate is low and healthy.")
    else:
        print(f"⚠️  Migration rate might be high: {migration_rate:.3f}")

    # نرخ نوسان (oscillation) بین WARM و COLD
    warm_cold = controller.stats.get("warm_to_cold", 0) + controller.stats.get("cold_to_warm", 0)
    total_mig = controller.stats["total_migrations"]
    oscillation_ratio = warm_cold / max(1, total_mig)
    print(f"🔄 Oscillation Ratio (WARM↔COLD): {oscillation_ratio:.3f}")
    if oscillation_ratio < 0.6:
        print("✅ Low oscillation between WARM and COLD — hysteresis is effective.")
    else:
        print("⚠️  High oscillation between WARM and COLD — consider increasing hysteresis gaps.")

    print("\n✅ Test complete.")

if __name__ == "__main__":
    run_tuner_test()
