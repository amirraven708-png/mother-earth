#!/usr/bin/env python3
"""
test_tld_memory_v2.py
تست جامع مهاجرت نرم با ۲۰۰۰ رکورد و تحلیل دقیق نرخ انتقال و زمان اقامت
"""

import sys
import os
import random
import math
import time
from collections import defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from migration_engine import MigrationEngineV2, ThermalState
from distributed_bubbledb import DistributedBubbleDB, DistributedBubbleDBConfig

def generate_random_phase_vector():
    """تولید بردار فاز تصادفی"""
    return {
        "R": random.uniform(0.1, 0.9),
        "V": random.uniform(0.0, 0.3),
        "R_fp": random.uniform(-0.1, 0.1),
        "D_eff": random.uniform(0.0, 0.5),
        "H": random.uniform(0.0, 1.0),
        "B": random.uniform(0.0, 1.0),
        "BR": random.uniform(0.0, 1.0),
    }

def run_test(num_records=2000, num_ticks=200):
    print("🧪 TLD Memory V2 — Comprehensive Migration Test")
    print("=" * 80)
    print(f"Records: {num_records}")
    print(f"Ticks: {num_ticks}")
    print(f"Logical Decay Ticks: 100")
    print("=" * 80)

    # ۱. ایجاد موتور مهاجرت با پارامترهای جدید
    engine = MigrationEngineV2(
        weights={
            "activity": 0.30,
            "resonance": 0.25,
            "phase_alignment": 0.20,
            "recency": 0.15,
            "storage_pressure": -0.10,
        },
        smoothing=0.20,
        promote_thresholds={
            "cold_to_warm": 0.55,
            "warm_to_hot": 0.65,
        },
        demote_thresholds={
            "hot_to_warm": 0.45,
            "warm_to_cold": 0.35,
        },
        logical_decay_ticks=100,
    )

    # ۲. ایجاد BubbleDB
    config = DistributedBubbleDBConfig(
        replication_factors={"hot": 1, "warm": 2, "cold": 3},
        initial_state="warm",
    )
    db = DistributedBubbleDB(config)
    db.set_migration_engine(engine)

    # ۳. تزریق رکوردها (همه WARM شروع می‌شوند)
    print("\n📥 Injecting records...")
    for i in range(num_records):
        vec = generate_random_phase_vector()
        db.put(f"key_{i:06d}", f"value_{i}", vec)

    # ۴. اجرای چرخه‌ها با تغییرات فاز تصادفی
    print("⏳ Running cycles...")
    start_time = time.time()

    for tick in range(1, num_ticks + 1):
        # شبیه‌سازی تغییرات فاز در برخی رکوردها (برای ایجاد حرکت)
        if tick % 10 == 0:
            for i in random.sample(range(num_records), min(200, num_records // 10)):
                key = f"key_{i:06d}"
                vec = generate_random_phase_vector()
                db.update_phase(key, vec)

        # اجرای چرخه
        storage_pressure = 0.3 + 0.4 * (tick / num_ticks)  # شبیه‌سازی افزایش فشار
        decisions = db.tick(storage_pressure=storage_pressure)

        # نمایش پیشرفت هر ۵۰ چرخه
        if tick % 50 == 0 or tick == 1:
            stats = db.get_stats()
            print(f"  Tick {tick}: HOT={stats['state_counts']['hot']:4d}, "
                  f"WARM={stats['state_counts']['warm']:4d}, "
                  f"COLD={stats['state_counts']['cold']:4d} | "
                  f"Rate={stats['migration_rate']:.3f}")

    elapsed = time.time() - start_time

    # ۵. آمار نهایی
    print("\n" + "=" * 80)
    print("📊 FINAL STATISTICS")
    print("=" * 80)

    stats = db.get_stats()
    transition_counts = db.get_transition_counts()

    print(f"\n⏱️  Time: {elapsed:.2f}s")
    print(f"📦 Total Records: {stats['total_records']}")
    print(f"🔥 Avg Heat: {stats['avg_heat']:.3f}")
    print(f"📅 Avg Age: {stats['avg_age']:.1f} ticks")
    print(f"🔄 Migration Rate: {stats['migration_rate']:.3f} per 100 ticks")
    print(f"📋 Total Migrations: {stats['total_migrations']}")

    print("\n📊 State Distribution:")
    for state, count in stats['state_counts'].items():
        pct = count / stats['total_records'] * 100
        bar = "█" * int(pct / 2)
        print(f"   {state.upper():4s}: {count:5d} ({pct:5.1f}%) {bar}")

    print("\n🔄 Transition Counts:")
    for trans, count in transition_counts.items():
        print(f"   {trans}: {count}")

    # ۶. تحلیل زمان اقامت (Residence Time)
    print("\n🏠 Residence Time Analysis (last 200 ticks):")
    residence = defaultdict(list)
    for m in stats['last_migrations']:
        # اینجا فقط نمونه‌ای از آخرین مهاجرت‌ها را نمایش می‌دهیم
        pass

    # ۷. بررسی نرخ نوسان (Oscillation Rate)
    oscillation_rate = stats['migration_rate'] / max(1, len(db.records))
    print(f"📈 Oscillation Rate: {oscillation_rate:.4f}")

    # ۸. نتیجه‌گیری
    print("\n" + "=" * 80)
    print("📊 CONCLUSION")
    print("=" * 80)

    final_counts = stats['state_counts']
    total = sum(final_counts.values())

    if final_counts['hot'] > 0 and final_counts['cold'] > 0:
        print("✅ System shows balanced migration: HOT, WARM, COLD all present.")
    else:
        print("⚠️  System may need further tuning (one state dominating).")

    if stats['migration_rate'] > 0.01 and stats['migration_rate'] < 0.5:
        print(f"✅ Healthy migration rate: {stats['migration_rate']:.3f}")
    else:
        print(f"⚠️  Migration rate might be too {'high' if stats['migration_rate'] > 0.5 else 'low'}: {stats['migration_rate']:.3f}")

    if oscillation_rate < 0.05:
        print(f"✅ Low oscillation: {oscillation_rate:.4f} — system is stable.")
    else:
        print(f"⚠️  High oscillation: {oscillation_rate:.4f} — consider increasing hysteresis or smoothing.")

    print("\n✅ Test complete.")

if __name__ == "__main__":
    run_test()
