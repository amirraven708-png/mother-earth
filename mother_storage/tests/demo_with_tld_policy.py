#!/usr/bin/env python3
"""
demo_with_tld_policy.py
نمایش کامل سیستم با خواندن سیاست حافظه از فایل TLD
"""

import sys
import os
import random
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from distributed_bubbledb import DistributedBubbleDB, DistributedBubbleDBConfig
from mother_language.tld_memory_policy_parser import parse_memory_policy, apply_policy_to_config

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
    print("🌊 Wave Mother — Full System with TLD Policy")
    print("=" * 80)
    
    # ۱. خواندن سیاست از فایل TLD (یا استفاده از نمونه‌ی داخلی)
    tld_file = "memory_policy.tld"
    if os.path.exists(tld_file):
        with open(tld_file, 'r') as f:
            tld_text = f.read()
        policy = parse_memory_policy(tld_text)
        print(f"📋 Loaded policy: {policy.get('name')}")
    else:
        # سیاست پیش‌فرض
        print("⚠️ No policy file found, using default parameters.")
        policy = {
            "name": "default",
            "params": {
                "hot_enter": 0.75,
                "hot_exit": 0.55,
                "warm_enter": 0.30,
                "warm_exit": 0.15,
                "decay_rate": 0.015,
                "access_gain": 0.25,
                "initial_state": "cold"
            }
        }
    
    # ۲. ایجاد پیکربندی
    config = DistributedBubbleDBConfig(
        initial_state="cold",
        replication_factors={"hot": 1, "warm": 2, "cold": 3}
    )
    # اعمال پارامترهای سیاست
    config_dict = {
        "initial_state": config.initial_state,
        "replication_factors": config.replication_factors,
    }
    updated_config = apply_policy_to_config(policy, config_dict)
    
    # ساخت آبجکت config جدید با مقادیر به‌روز
    config = DistributedBubbleDBConfig(
        initial_state=updated_config.get("initial_state", "cold"),
        replication_factors=updated_config.get("replication_factors", {"hot": 1, "warm": 2, "cold": 3}),
        calibrator_params=updated_config.get("calibrator_params")
    )
    db = DistributedBubbleDB(config)

    print(f"   Initial State: {config.initial_state}")
    print(f"   Calibrator Params: {config.calibrator_params}")
    print()

    # ۳. تزریق ۵۰۰ رکورد
    print("📥 Injecting 500 records...")
    for i in range(500):
        key = f"rec_{i:04d}"
        db.put(key, f"value_{i}", random_phase())

    # ۴. شبیه‌سازی چرخه‌ها
    print("⏳ Running 100 ticks with random access patterns...")
    for tick in range(1, 101):
        if random.random() < 0.3:
            keys = random.sample(list(db.records.keys()), k=min(50, len(db.records)))
            for k in keys:
                db.get(k)
        db.tick()
        if tick % 20 == 0:
            stats = db.get_stats()
            tier = stats["tier_counts"]
            print(f"  Tick {tick:3d}: HOT={tier['HOT']:4d}, WARM={tier['WARM']:4d}, COLD={tier['COLD']:4d}")

    # ۵. گزارش نهایی
    stats = db.get_stats()
    tier = stats["tier_counts"]
    total = sum(tier.values())
    print("\n" + "=" * 80)
    print("📊 FINAL SYSTEM STATE")
    print("=" * 80)
    print(f"Total Records: {total}")
    print("Tier Distribution:")
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
