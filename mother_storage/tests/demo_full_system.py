#!/usr/bin/env python3
"""
demo_full_system.py
نمایش کامل سیستم با DistributedBubbleDB + TLDTierCalibrator
"""

import sys
import os
import random
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from distributed_bubbledb import DistributedBubbleDB, DistributedBubbleDBConfig

def random_phase():
    return {
        "R": random.uniform(0.1, 0.9),
        "V": random.uniform(0.0, 0.3),
        "R_fp": random.uniform(-0.1, 0.1),
        "D_eff": random.uniform(0.0, 0.5),
        "H": random.uniform(0.0, 1.0),
        "B": random.uniform(0.0, 1.0),
        "BR": random.uniform(0.0, 1.0),
    }

def demo():
    print("🌊 Wave Mother — Full System Demo with TLD Tiering")
    print("=" * 80)
    
    # ۱. پیکربندی با پارامترهای کالیبراتور (قابل تنظیم از TLD)
    config = DistributedBubbleDBConfig(
        initial_state="cold",
        calibrator_params={
            "hot_enter": 0.75,
            "hot_exit": 0.55,
            "warm_enter": 0.30,
            "warm_exit": 0.15,
            "base_decay_rate": 0.015,
            "access_heat_gain": 0.25,
        }
    )
    db = DistributedBubbleDB(config)

    # ۲. تزریق ۵۰۰ رکورد
    print("\n📥 Injecting 500 records (starting from COLD)...")
    for i in range(500):
        key = f"rec_{i:04d}"
        db.put(key, f"value_{i}", random_phase())

    # ۳. شبیه‌سازی چرخه‌های زمانی با دسترسی‌های تصادفی
    print("\n⏳ Running 100 ticks with random access patterns...")
    for tick in range(1, 101):
        # دسترسی تصادفی به ۱۰٪ رکوردها
        if random.random() < 0.3:
            keys = random.sample(list(db.records.keys()), k=min(50, len(db.records)))
            for k in keys:
                db.get(k)  # touch_record به‌طور خودکار اعمال می‌شود

        # چرخه‌ی زمانی (decay)
        db.tick()

        # نمایش هر ۲۰ تیک
        if tick % 20 == 0:
            stats = db.get_stats()
            tier = stats["tier_counts"]
            print(f"  Tick {tick:3d}: HOT={tier['HOT']:4d}, WARM={tier['WARM']:4d}, COLD={tier['COLD']:4d}")

    # ۴. گزارش نهایی
    stats = db.get_stats()
    tier = stats["tier_counts"]
    total = sum(tier.values())
    print("\n" + "=" * 80)
    print("📊 FINAL SYSTEM STATE")
    print("=" * 80)
    print(f"Total Records: {total}")
    print(f"Tier Distribution:")
    for t, count in tier.items():
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {t:4s}: {count:5d} ({pct:5.1f}%) {bar}")
    print(f"\nMigration Stats:")
    for k, v in stats["migration_stats"].items():
        print(f"  {k}: {v}")
    print(f"\nAverage Heat: {stats['avg_heat']:.3f}")
    print("\n✅ Demo complete.")

if __name__ == "__main__":
    demo()
