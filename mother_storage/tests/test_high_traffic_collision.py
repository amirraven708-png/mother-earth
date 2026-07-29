#!/usr/bin/env python3
"""
test_high_traffic_collision.py
شبیه‌سازی برخورد امواج، حرکت خطی میرا و حافظه بیضوی در نودهای BubbleDB
"""

import sys
import os
# اضافه کردن مسیر mother_storage به PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import math
from wave_dpu_core_v2 import WaveflowGraphEngine, WavePulse

def draw_oscillator_bar(val: float, limit: float = 0.5, width: int = 30) -> str:
    """نمایشگر متنی برای رصد نوسانگر خطی (مهاجرت داده در BubbleDB)"""
    pos = int((val + limit) / (2 * limit) * width)
    pos = max(0, min(width, pos))
    bar = ['-'] * (width + 1)
    bar[width // 2] = '|'  # نقطه تعادل (RAM / هسته داغ)
    
    if pos != width // 2:
        bar[pos] = '█'     # موقعیت فعلی داده
    else:
        bar[pos] = '◉'     # داده در مرکز تعادل مستقر است
        
    return "".join(bar)

def test_interference_and_damping():
    # راه‌اندازی موتور گراف موجی با گام زمانی ۵۰ میلی‌ثانیه
    engine = WaveflowGraphEngine(default_window_ms=50.0)
    
    # تابع پردازشی ساده (عبور مستقیم دیتا)
    def passthrough(data):
        return data

    # اضافه کردن نود روتر حافظه
    # ضریب میرایی 0.95 تنظیم شده تا نوسان‌ها به وضوح قابل مشاهده باشند
    engine.add_node("Memory_Router", passthrough, decay=0.95)
    target_node = engine.nodes["Memory_Router"]
    
    print("\n🌊 فاز ۱: تداخل امواج (Interference Phase)")
    print("تزریق پیوسته دو موج سینوسی با فرکانس‌های متفاوت (ω1=1.2, ω2=1.8)")
    print(f"{'Tick':<5} | {'Force':<8} | {'Drift X (Position)':<20} | {'Phase (φ)':<9} | {'BubbleDB State (x)'}")
    print("-" * 85)

    # اجرای ۶۰ چرخه (Tick)
    for cycle in range(1, 61):
        # در ۱۵ چرخه اول، امواج به صورت پیوسته تزریق می‌شوند
        if cycle <= 15:
            p1 = WavePulse(f"c{cycle}_p1", payload="Stream_A", harmonic_freq=1.2, amplitude=2.0)
            p2 = WavePulse(f"c{cycle}_p2", payload="Stream_B", harmonic_freq=1.8, amplitude=2.0)
            engine.inject_pulse("Memory_Router", p1)
            engine.inject_pulse("Memory_Router", p2)
        
        elif cycle == 16:
            print("\n🍂 فاز ۲: آزادسازی و میرایی نرم (Damped Relaxation Phase)")
            print("توقف پالس‌ها؛ مشاهده بازگشت نوسان‌گر به تعادل و حفظ تاریخچه فاز")
            print("-" * 85)

        # محاسبه نیروی تداخل (فقط برای نمایش در لاگ قبل از اعمال در موتور)
        force = target_node.calculate_interference_force() if target_node.inbox else 0.0

        # اجرای یک گام زمانی پردازش
        engine.tick_cycle()
        
        # استخراج متغیرهای فیزیکی پس از پردازش
        x = target_node.drift_x
        phi = target_node.accumulated_phase
        
        # ساخت نوار بصری
        visual_x = draw_oscillator_bar(x, limit=0.8, width=30)
        
        # چاپ وضعیت سیستم
        print(f"{cycle:<5} | {force:>8.3f} | {x:>8.4f}             | {phi:>9.4f} | [{visual_x}]")

if __name__ == "__main__":
    test_interference_and_damping()
