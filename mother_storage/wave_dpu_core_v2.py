"""
wave_dpu_core_v2.py
موتور گراف موجی برای شبیه‌سازی برخورد امواج و مهاجرت داده در BubbleDB
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, Callable, List, Optional

@dataclass
class WavePulse:
    """یک پالس موجی با فرکانس هارمونیک و دامنه"""
    id: str
    payload: Any
    harmonic_freq: float = 1.0
    amplitude: float = 1.0
    phase: float = 0.0

class WaveflowNode:
    """
    یک گره در گراف موجی با:
    - inbox: بافر ورودی
    - drift_x: موقعیت جابجایی داده (مهاجرت به سمت حافظه سرد)
    - accumulated_phase: فاز انباشته (حافظه بیضوی)
    """
    def __init__(self, name: str, process_fn: Callable, decay: float = 0.95):
        self.name = name
        self.process_fn = process_fn
        self.decay = decay  # ضریب میرایی (بازگشت به تعادل)
        self.inbox: List[WavePulse] = []
        self.drift_x: float = 0.0  # موقعیت جابجایی
        self.accumulated_phase: float = 0.0  # فاز انباشته
        self._last_force: float = 0.0

    def inject(self, pulse: WavePulse):
        """تزریق پالس به بافر ورودی"""
        self.inbox.append(pulse)

    def calculate_interference_force(self) -> float:
        """محاسبه نیروی تداخلی حاصل از پالس‌های موجود در بافر"""
        if not self.inbox:
            return 0.0
        # جمع بردارهای فرکانسی با فاز
        total_force = 0.0
        for p in self.inbox:
            total_force += p.amplitude * math.sin(p.harmonic_freq * math.pi + p.phase)
        return total_force

    def tick(self, dt: float = 0.05):
        """یک گام زمانی: پردازش بافر، به‌روزرسانی drift_x و phase"""
        # ۱. محاسبه نیروی تداخلی
        force = self.calculate_interference_force()
        self._last_force = force

        # ۲. به‌روزرسانی جابجایی (drift_x) با اعمال نیرو و میرایی
        # معادله: x_new = decay * x_old + force * dt
        self.drift_x = self.decay * self.drift_x + force * dt

        # ۳. به‌روزرسانی فاز انباشته (حافظه بیضوی)
        # فاز با نرخ تغییرات جابجایی به‌روز می‌شود
        self.accumulated_phase += self.drift_x * dt

        # ۴. پردازش داده‌های ورودی (در صورت وجود) و خالی کردن بافر
        if self.inbox:
            # پردازش با تابع کاربر
            for p in self.inbox:
                self.process_fn(p.payload)
            self.inbox.clear()

        return force

class WaveflowGraphEngine:
    """
    موتور گراف موجی: مدیریت گره‌ها و اجرای گام‌های زمانی
    """
    def __init__(self, default_window_ms: float = 50.0):
        self.default_window_ms = default_window_ms
        self.nodes: Dict[str, WaveflowNode] = {}
        self._time = 0.0

    def add_node(self, name: str, process_fn: Callable, decay: float = 0.95) -> WaveflowNode:
        """افزودن یک گره جدید به گراف"""
        node = WaveflowNode(name, process_fn, decay)
        self.nodes[name] = node
        return node

    def inject_pulse(self, node_name: str, pulse: WavePulse):
        """تزریق پالس به یک گره مشخص"""
        if node_name in self.nodes:
            self.nodes[node_name].inject(pulse)

    def tick_cycle(self, dt: float = 0.05):
        """اجرای یک گام زمانی برای همه گره‌ها"""
        self._time += dt
        for node in self.nodes.values():
            node.tick(dt)

    def get_node(self, name: str) -> Optional[WaveflowNode]:
        return self.nodes.get(name)
