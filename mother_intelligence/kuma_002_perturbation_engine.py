#!/usr/bin/env python3
"""
kuma_002_perturbation_engine.py
موتور اختلال، بازیابی و بازپخش علّی برای Wave Synchronization Layer

سناریوهای تست:
  ۱. قطع نود (Node Drop) — بررسی بازگشت R(t)
  ۲. تأخیر PTF مصنوعی (Artificial Phase Delay) — پیدا کردن نقطه شکست
  ۳. بازپخش علّی (Causal Replay) — مقایسه State_replay با State_live
  ۴. GRF Supervisor — تبدیل GRF از ناظر به کنترل‌کننده تطبیقی

معیارهای خروجی:
  - Recovery Time (زمان بازیابی پس از اختلال)
  - Resilience Score (امتیاز تاب‌آوری)
  - Lyapunov Exponent (پایداری لیاپانوف)
"""

import numpy as np
import math
import time
import random
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque

# ========================== ۱. واردات ==========================

try:
    from mother_intelligence.wave_synchronization_layer import WaveSynchronizationLayer
    from mother_intelligence.kuramoto_engine import KuramotoEngine, OscillatorNode, PhaseState, PhaseLink
except ImportError:
    # برای اجرای مستقل
    from wave_synchronization_layer import WaveSynchronizationLayer
    from kuramoto_engine import KuramotoEngine, OscillatorNode, PhaseState, PhaseLink

# ========================== ۲. مدل‌های داده ==========================

@dataclass
class PerturbationConfig:
    """پیکربندی سناریوهای اختلال"""
    node_drop_probability: float = 0.1          # احتمال قطع نود در هر گام
    max_latency_seconds: float = 0.5            # حداکثر تأخیر مصنوعی (ثانیه)
    noise_amplitude: float = 0.1                # دامنه نویز فاز
    replay_window_size: int = 50                # اندازه پنجره بازپخش

@dataclass
class PerturbationResult:
    """نتیجه یک سناریوی اختلال"""
    scenario_name: str
    success: bool
    recovery_time: float = 0.0                  # زمان بازیابی (تعداد گام)
    resilience_score: float = 0.0               # امتیاز تاب‌آوری (0-1)
    lyapunov_exponent: float = 0.0              # توان لیاپانوف
    max_phase_error: float = 0.0                # حداکثر خطای فاز
    final_order_parameter: float = 0.0
    metadata: Dict = field(default_factory=dict)

# ========================== ۳. موتور اختلال ==========================

class PerturbationEngine:
    """
    موتور تزریق اختلالات به شبکه موجی
    """
    
    def __init__(self, layer: WaveSynchronizationLayer, config: PerturbationConfig = None):
        self.layer = layer
        self.config = config or PerturbationConfig()
        self._perturbation_history: List[Dict] = []
        self._phase_history: List[Dict[str, float]] = []
        self._order_history: List[float] = []
    
    # ===== ۱. سناریو: قطع نود =====
    
    def simulate_node_drop(self, node_id: str, recovery_steps: int = 200) -> PerturbationResult:
        """
        شبیه‌سازی قطع یک نود و بازیابی آن
        
        Args:
            node_id: شناسه نود مورد نظر
            recovery_steps: تعداد گام برای بازیابی
        """
        print(f"💀 Simulating node drop for {node_id}...")
        
        # ذخیره وضعیت اولیه
        initial_R = self.layer.kuramoto.compute_order_parameter(
            [OscillatorNode(id=n.id, phase_state=n.phase_state, natural_frequency=n.natural_frequency)
             for n in self.layer._topology.nodes]
        )
        
        # حذف نود
        removed = self.layer.remove_node(node_id)
        if not removed:
            return PerturbationResult(
                scenario_name="node_drop",
                success=False,
                metadata={"error": f"Node {node_id} not found"}
            )
        
        # اجرای گام‌ها تا بازیابی
        R_history = []
        phase_errors = []
        
        for step in range(recovery_steps):
            result = self.layer.step()
            R_history.append(result["order_parameter"])
            
            # محاسبه خطای فاز نسبت به قبل از قطع
            current_phases = [n.phase_state.phase for n in self.layer._topology.nodes]
            phase_errors.append(np.std(current_phases) if current_phases else 0)
            
            # اگر R به بالای 0.9 برگشت، بازیابی کامل
            if result["order_parameter"] > 0.9 and step > 10:
                recovery_time = step
                break
        else:
            recovery_time = recovery_steps
        
        # محاسبه امتیاز تاب‌آوری
        final_R = R_history[-1] if R_history else 0
        resilience_score = final_R / (initial_R + 1e-9) if initial_R > 0 else 0
        
        # محاسبه توان لیاپانوف (تقریبی)
        lyapunov = self._estimate_lyapunov(R_history)
        
        return PerturbationResult(
            scenario_name="node_drop",
            success=final_R > 0.85,
            recovery_time=recovery_time,
            resilience_score=min(1.0, resilience_score),
            lyapunov_exponent=lyapunov,
            max_phase_error=max(phase_errors) if phase_errors else 0,
            final_order_parameter=final_R,
            metadata={
                "removed_node": node_id,
                "R_history": R_history,
                "phase_error_history": phase_errors
            }
        )
    
    # ===== ۲. سناریو: تأخیر PTF مصنوعی =====
    
    def simulate_phase_delay(self, max_delay: float = 1.0, steps: int = 500) -> PerturbationResult:
        """
        شبیه‌سازی تأخیر فاز افزایش‌یابنده (Ramp) برای یافتن نقطه شکست
        
        Args:
            max_delay: حداکثر تأخیر (ثانیه)
            steps: تعداد گام‌ها
        """
        print(f"⏱️ Simulating phase delay ramp (0 → {max_delay}s)...")
        
        delay_values = np.linspace(0, max_delay, steps)
        R_history = []
        delay_at_break = None
        
        for step, delay in enumerate(delay_values):
            # اعمال تأخیر به همه لینک‌ها
            for link in self.layer._topology.links:
                link.phase_delay = delay
            
            result = self.layer.step()
            R_history.append(result["order_parameter"])
            
            # اگر R به زیر 0.5 رسید، نقطه شکست
            if result["order_parameter"] < 0.5 and delay_at_break is None:
                delay_at_break = delay
        
        # محاسبه معیارها
        final_R = R_history[-1] if R_history else 0
        resilience_score = 1.0 - (delay_at_break / max_delay) if delay_at_break else 1.0  # اگر هیچ شکستی نبود، امتیاز کامل
        
        # ✅ اصلاح: اگر نقطه شکست پیدا نشد، یعنی سیستم مقاوم است → success=True
        success = True  # اگر هیچ شکستی رخ نداد، موفقیت است
        if delay_at_break is not None:
            # اگر شکست رخ داد، موفقیت فقط در صورتی است که تأخیر شکست زیاد باشد
            success = delay_at_break > 0.5 * max_delay  # حداقل نصف محدوده را تحمل کرده باشد
        
        return PerturbationResult(
            scenario_name="phase_delay_ramp",
            success=success,
            recovery_time=0,
            resilience_score=min(1.0, max(0.0, resilience_score)),
            lyapunov_exponent=self._estimate_lyapunov(R_history),
            max_phase_error=0,
            final_order_parameter=final_R,
            metadata={
                "break_delay": delay_at_break,
                "max_delay": max_delay,
                "R_history": R_history,
                "delay_values": delay_values.tolist()
            }
        )
    
    # ===== ۳. سناریو: بازپخش علّی =====
    
    def simulate_causal_replay(self, replay_steps: int = 100) -> PerturbationResult:
        """
        شبیه‌سازی بازپخش علّی: ذخیره وضعیت، بازپخش و مقایسه
        
        Args:
            replay_steps: تعداد گام‌های بازپخش
        """
        print(f"🔄 Simulating causal replay ({replay_steps} steps)...")
        
        # ۱. ذخیره وضعیت فعلی
        snapshot = self._capture_snapshot()
        
        # ۲. اجرای گام‌های عادی
        normal_history = []
        for _ in range(replay_steps):
            result = self.layer.step()
            normal_history.append(result["order_parameter"])
        
        # ۳. بازگرداندن به وضعیت ذخیره‌شده
        self._restore_snapshot(snapshot)
        
        # ۴. بازپخش با همان دنباله رویدادها
        replay_history = []
        for _ in range(replay_steps):
            result = self.layer.step()
            replay_history.append(result["order_parameter"])
        
        # ۵. مقایسه دو مسیر
        normal_np = np.array(normal_history)
        replay_np = np.array(replay_history)
        
        max_diff = np.max(np.abs(normal_np - replay_np))
        mean_diff = np.mean(np.abs(normal_np - replay_np))
        final_diff = abs(normal_np[-1] - replay_np[-1])
        
        # معیار موفقیت: اختلاف نهایی کمتر از 0.05
        success = final_diff < 0.05
        
        return PerturbationResult(
            scenario_name="causal_replay",
            success=success,
            recovery_time=0,
            resilience_score=1.0 - min(1.0, mean_diff * 10),
            lyapunov_exponent=self._estimate_lyapunov(normal_history),
            max_phase_error=float(max_diff),
            final_order_parameter=float(replay_np[-1]),
            metadata={
                "max_difference": float(max_diff),
                "mean_difference": float(mean_diff),
                "final_difference": float(final_diff),
                "normal_history": normal_history,
                "replay_history": replay_history
            }
        )
    
    # ===== ۴. سناریو: GRF Supervisor (کنترل تطبیقی) =====
    
    def simulate_grf_supervisor(self, steps: int = 500) -> PerturbationResult:
        """
        شبیه‌سازی GRF Supervisor: تنظیم تطبیقی K و damping بر اساس وضعیت شبکه
        """
        print(f"🎛️ Simulating GRF Supervisor ({steps} steps)...")
        
        K_history = []
        damping_history = []
        R_history = []
        
        initial_K = self.layer.K
        initial_damping = self.layer.damping_controller.damping_factor
        
        for step in range(steps):
            # ۱. محاسبه وضعیت فعلی
            status = self.layer.get_network_status()
            R = status["order_parameter"]
            mind_state = status["mind_state"]
            
            # ۲. منطق تطبیقی GRF Supervisor
            if mind_state == "chaotic":
                # افزایش coupling و damping برای همگرایی سریع‌تر
                new_K = min(3.0, self.layer.K + 0.02)
                new_damping = min(0.3, self.layer.damping_controller.damping_factor + 0.005)
            elif mind_state == "coherent":
                # کاهش تدریجی برای حفظ پایداری
                new_K = max(1.5, self.layer.K - 0.005)
                new_damping = max(0.05, self.layer.damping_controller.damping_factor - 0.002)
            else:  # transitioning
                new_K = self.layer.K  # حفظ وضعیت
                new_damping = self.layer.damping_controller.damping_factor
            
            # ۳. اعمال تغییرات
            self.layer.K = new_K
            self.layer.damping_controller.damping_factor = new_damping
            
            K_history.append(new_K)
            damping_history.append(new_damping)
            
            # ۴. یک گام
            result = self.layer.step()
            R_history.append(result["order_parameter"])
        
        # بازگرداندن مقادیر اولیه
        self.layer.K = initial_K
        self.layer.damping_controller.damping_factor = initial_damping
        
        final_R = R_history[-1] if R_history else 0
        stability = 1.0 - np.std(R_history[-100:]) if len(R_history) > 100 else 0
        
        return PerturbationResult(
            scenario_name="grf_supervisor",
            success=final_R > 0.85,
            recovery_time=0,
            resilience_score=stability,
            lyapunov_exponent=self._estimate_lyapunov(R_history),
            max_phase_error=0,
            final_order_parameter=final_R,
            metadata={
                "K_history": K_history,
                "damping_history": damping_history,
                "R_history": R_history,
                "final_K": new_K,
                "final_damping": new_damping
            }
        )
    
    # ===== ۵. توابع کمکی =====
    
    def _estimate_lyapunov(self, R_history: List[float]) -> float:
        """محاسبه تقریبی توان لیاپانوف از تاریخچه R"""
        if len(R_history) < 10:
            return 0.0
        
        # محاسبه مشتق R
        diff = np.diff(R_history)
        if len(diff) < 2:
            return 0.0
        
        # توان لیاپانوف = نرخ رشد انحراف
        # تقریب: log(|diff|) / step
        log_diff = np.log(np.abs(diff) + 1e-9)
        return np.mean(log_diff)
    
    def _capture_snapshot(self) -> Dict:
        """گرفتن snapshot از وضعیت شبکه"""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "phase": n.phase_state.phase,
                    "frequency": n.phase_state.frequency,
                    "geometry_theta": n.geometry_theta
                }
                for n in self.layer._topology.nodes
            ],
            "links": [
                {
                    "source": l.source,
                    "target": l.target,
                    "weight": l.weight,
                    "phase_delay": l.phase_delay
                }
                for l in self.layer._topology.links
            ],
            "K": self.layer.K,
            "damping": self.layer.damping_controller.damping_factor,
            "tick": self.layer._tick
        }
    
    def _restore_snapshot(self, snapshot: Dict):
        """بازگرداندن وضعیت از snapshot"""
        # بازسازی نودها
        for node_data in snapshot["nodes"]:
            for node in self.layer._topology.nodes:
                if node.id == node_data["id"]:
                    node.phase_state.phase = node_data["phase"]
                    node.phase_state.frequency = node_data["frequency"]
                    node.geometry_theta = node_data["geometry_theta"]
                    break
        
        # بازسازی لینک‌ها
        for link_data in snapshot["links"]:
            for link in self.layer._topology.links:
                if link.source == link_data["source"] and link.target == link_data["target"]:
                    link.weight = link_data["weight"]
                    link.phase_delay = link_data["phase_delay"]
                    break
        
        # بازسازی پارامترها
        self.layer.K = snapshot["K"]
        self.layer.damping_controller.damping_factor = snapshot["damping"]
        self.layer._tick = snapshot["tick"]

# ========================== ۴. تست جامع ==========================

def run_kuma_002_tests():
    """
    اجرای همه سناریوهای KUMA-002
    """
    print("\n" + "="*70)
    print("🧪 KUMA-002: Perturbation, Recovery & Causal Replay Engine")
    print("="*70 + "\n")
    
    # ۱. ایجاد شبکه با ۲۰ نود
    print("📡 Creating network with 20 nodes (complete topology)...")
    layer = WaveSynchronizationLayer(
        coupling_strength=2.5,
        dt=0.01,
        damping_factor=0.15
    )
    layer.create_network(num_nodes=20, topology="complete")
    
    # ۲. همگام‌سازی اولیه
    print("⏳ Initial synchronization (200 steps)...")
    for _ in range(200):
        layer.step()
    
    initial_status = layer.get_network_status()
    print(f"   Initial R = {initial_status['order_parameter']:.4f}")
    print(f"   Initial Mind State = {initial_status['mind_state']}")
    
    # ۳. ایجاد موتور اختلال
    config = PerturbationConfig(
        node_drop_probability=0.1,
        max_latency_seconds=0.5,
        noise_amplitude=0.1,
        replay_window_size=50
    )
    engine = PerturbationEngine(layer, config)
    
    # ۴. اجرای سناریوها
    results = []
    
    # سناریو ۱: قطع نود
    print("\n" + "-"*50)
    result1 = engine.simulate_node_drop("node_005", recovery_steps=300)
    results.append(result1)
    print(f"   Node Drop: success={result1.success}, recovery_time={result1.recovery_time}, resilience={result1.resilience_score:.3f}")
    
    # سناریو ۲: تأخیر PTF
    print("\n" + "-"*50)
    result2 = engine.simulate_phase_delay(max_delay=1.0, steps=300)
    results.append(result2)
    break_delay = result2.metadata.get("break_delay", "N/A")
    if isinstance(break_delay, float):
        print(f"   Phase Delay Ramp: break_delay={break_delay:.2f}s, resilience={result2.resilience_score:.3f}")
    else:
        print(f"   Phase Delay Ramp: break_delay=N/A (no break found, system is resilient!), resilience={result2.resilience_score:.3f}")
    
    # سناریو ۳: بازپخش علّی
    print("\n" + "-"*50)
    result3 = engine.simulate_causal_replay(replay_steps=100)
    results.append(result3)
    max_diff = result3.metadata.get("max_difference", 0)
    print(f"   Causal Replay: success={result3.success}, max_diff={max_diff:.4f}, resilience={result3.resilience_score:.3f}")
    
    # سناریو ۴: GRF Supervisor
    print("\n" + "-"*50)
    result4 = engine.simulate_grf_supervisor(steps=300)
    results.append(result4)
    print(f"   GRF Supervisor: success={result4.success}, final_R={result4.final_order_parameter:.4f}, resilience={result4.resilience_score:.3f}")
    
    # ۵. گزارش نهایی
    print("\n" + "="*70)
    print("📊 KUMA-002 FINAL REPORT")
    print("="*70)
    
    print(f"\n{'Scenario':<20} | {'Success':<10} | {'Resilience':<12} | {'Key Metric':<20}")
    print("-"*70)
    
    for r in results:
        key_metric = ""
        if r.scenario_name == "node_drop":
            key_metric = f"recovery={r.recovery_time}s"
        elif r.scenario_name == "phase_delay_ramp":
            break_delay = r.metadata.get('break_delay')
            if break_delay is not None:
                key_metric = f"break={break_delay:.2f}s"
            else:
                key_metric = f"no_break (>{r.metadata.get('max_delay', 1.0):.1f}s)"
        elif r.scenario_name == "causal_replay":
            max_diff = r.metadata.get('max_difference', 0)
            key_metric = f"diff={max_diff:.4f}"
        elif r.scenario_name == "grf_supervisor":
            key_metric = f"R={r.final_order_parameter:.4f}"
        
        status = "✅" if r.success else "❌"
        print(f"{r.scenario_name:<20} | {status:<10} | {r.resilience_score:<12.3f} | {key_metric:<20}")
    
    # ۶. امتیاز کلی
    avg_resilience = sum(r.resilience_score for r in results) / len(results)
    all_passed = all(r.success for r in results)
    
    print("\n" + "="*70)
    print(f"📈 Overall KUMA-002 Score: {avg_resilience:.3f} / 1.0")
    print(f"🏆 All tests passed: {all_passed}")
    print("="*70 + "\n")
    
    return results

if __name__ == "__main__":
    run_kuma_002_tests()
