#!/usr/bin/env python3
"""
kuramoto_engine.py
موتور همگام‌سازی Kuramoto به‌عنوان لایه دینامیک روی ACIOMD State Layer

جریان داده:
  Event Stream → ACIOMD Solver → SoftDampingController → PhaseState Registry → KuramotoEngine → Synchronized Phase Field

مدل ریاضی:
  dθ_i/dt = ω_i + K * Σ_j A_ij * sin(θ_j - θ_i - α_ij)

که در آن:
  - θ_i: فاز نود i
  - ω_i: فرکانس ذاتی نود
  - A_ij: وزن ارتباط شبکه
  - K: شدت همگرایی (coupling strength)
  - α_ij: تأخیر فاز (Phase Delay)
"""

import numpy as np
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

# ========================== ۱. مدل داده ==========================

@dataclass
class PhaseState:
    """وضعیت فاز یک نود در ACIOMD"""
    phase: float = 0.0
    frequency: float = 1.0
    stability: float = 0.5
    confidence: float = 0.7
    metadata: Dict = field(default_factory=dict)

@dataclass
class OscillatorNode:
    """نوسانگر Kuramoto با وضعیت فاز و فرکانس ذاتی"""
    id: str
    phase_state: PhaseState
    natural_frequency: float = 1.0
    metadata: Dict = field(default_factory=dict)

@dataclass
class PhaseLink:
    """اتصال بین دو نوسانگر"""
    source: str
    target: str
    weight: float = 1.0
    phase_delay: float = 0.0
    metadata: Dict = field(default_factory=dict)

# ========================== ۲. SoftDampingController (شبیه‌سازی) ==========================

class SoftDampingController:
    """
    کنترل‌کننده میرایی نرم برای جلوگیری از پرش‌های ناگهانی فاز
    """
    def __init__(self, damping_factor: float = 0.15, tolerance: float = 0.01):
        self.damping_factor = damping_factor
        self.tolerance = tolerance
        self._history: Dict[str, List[float]] = defaultdict(list)

    def update(self, current_state: PhaseState, predicted_phase: float, timestamp: float) -> PhaseState:
        """
        اعمال میرایی نرم روی فاز پیش‌بینی‌شده
        """
        # تفاوت فاز
        diff = predicted_phase - current_state.phase
        
        # نرمال‌سازی اختلاف فاز به بازه [-π, π]
        diff = math.atan2(math.sin(diff), math.cos(diff))
        
        # اعمال میرایی
        if abs(diff) > self.tolerance:
            corrected_phase = current_state.phase + self.damping_factor * diff
        else:
            corrected_phase = predicted_phase
        
        # نرمال‌سازی به بازه [0, 2π]
        corrected_phase = corrected_phase % (2 * math.pi)
        
        # ذخیره تاریخچه
        self._history["phases"].append(corrected_phase)
        if len(self._history["phases"]) > 100:
            self._history["phases"].pop(0)
        
        return PhaseState(
            phase=corrected_phase,
            frequency=current_state.frequency,
            stability=current_state.stability,
            confidence=current_state.confidence,
            metadata=current_state.metadata
        )

# ========================== ۳. KuramotoEngine ==========================

class KuramotoEngine:
    """
    موتور همگام‌سازی Kuramoto به‌عنوان لایه دینامیک روی ACIOMD
    
    ویژگی‌ها:
    - دریافت وضعیت فاز از ACIOMD State Layer
    - اعمال SoftDamping برای جلوگیری از پرش‌های ناگهانی
    - محاسبه پارامتر نظم (Order Parameter)
    - پشتیبانی از تأخیر فاز (Phase Delay) مبتنی بر PTF
    """
    
    def __init__(
        self,
        coupling_strength: float = 2.0,
        damping_controller: Optional[SoftDampingController] = None,
        dt: float = 0.01,
        use_phase_delay: bool = True
    ):
        self.K = coupling_strength
        self.dt = dt
        self.use_phase_delay = use_phase_delay
        self.damping_controller = damping_controller or SoftDampingController()
        self._order_parameter_history: List[float] = []
        self._phase_history: List[Dict[str, float]] = []
    
    def evolve(
        self,
        nodes: List[OscillatorNode],
        links: List[PhaseLink],
        dt: Optional[float] = None,
        timestamp: Optional[float] = None
    ) -> List[OscillatorNode]:
        """
        یک گام زمانی در تکامل فاز
        
        Args:
            nodes: لیست نوسانگرها
            links: لیست اتصالات بین نوسانگرها
            dt: گام زمانی (اختیاری)
            timestamp: زمان فعلی (اختیاری)
        
        Returns:
            لیست نوسانگرها با فازهای به‌روزرسانی‌شده
        """
        if dt is None:
            dt = self.dt
        
        if timestamp is None:
            import time
            timestamp = time.time()
        
        # ساخت نگاشت سریع برای نودها
        node_map = {node.id: node for node in nodes}
        
        # ساخت نگاشت اتصالات به ازای هر نود هدف
        link_map: Dict[str, List[PhaseLink]] = defaultdict(list)
        for link in links:
            link_map[link.target].append(link)
        
        updated_nodes = []
        
        for node in nodes:
            # ۱. محاسبه اندرکنش از همسایگان
            interaction = 0.0
            neighbor_links = link_map.get(node.id, [])
            
            for link in neighbor_links:
                neighbor = node_map.get(link.source)
                if neighbor is None:
                    continue
                
                # محاسبه تأخیر فاز
                phase_delay = link.phase_delay
                if self.use_phase_delay:
                    phase_delay = self.compute_phase_delay(link, neighbor, node)
                
                # اندرکنش Kuramoto
                diff = neighbor.phase_state.phase - node.phase_state.phase - phase_delay
                interaction += link.weight * math.sin(diff)
            
            # ۲. سرعت فاز
            phase_velocity = node.natural_frequency + self.K * interaction
            
            # ۳. پیش‌بینی فاز
            predicted_phase = node.phase_state.phase + phase_velocity * dt
            
            # ۴. اعمال میرایی نرم (Soft Damping)
            stable_state = self.damping_controller.update(
                node.phase_state,
                predicted_phase,
                timestamp
            )
            
            # ۵. ایجاد نود به‌روزرسانی‌شده
            updated_node = OscillatorNode(
                id=node.id,
                phase_state=stable_state,
                natural_frequency=node.natural_frequency,
                metadata=node.metadata
            )
            updated_nodes.append(updated_node)
        
        # ذخیره تاریخچه
        self._phase_history.append({
            node.id: node.phase_state.phase for node in updated_nodes
        })
        if len(self._phase_history) > 1000:
            self._phase_history.pop(0)
        
        # محاسبه پارامتر نظم
        order_param = self.compute_order_parameter(updated_nodes)
        self._order_parameter_history.append(order_param)
        if len(self._order_parameter_history) > 1000:
            self._order_parameter_history.pop(0)
        
        return updated_nodes
    
    def compute_order_parameter(self, nodes: List[OscillatorNode]) -> float:
        """
        محاسبه پارامتر نظم R
        
        R = |(1/N) Σ_j e^(iθ_j)|
        
        Returns:
            R ∈ [0, 1]: 1 = هم‌فاز کامل، 0 = آشوب کامل
        """
        if not nodes:
            return 0.0
        
        complex_sum = sum(
            math.cos(node.phase_state.phase) + 1j * math.sin(node.phase_state.phase)
            for node in nodes
        )
        R = abs(complex_sum) / len(nodes)
        return float(R)
    
    def compute_phase_delay(self, link: PhaseLink, source: OscillatorNode, target: OscillatorNode) -> float:
        """
        محاسبه تأخیر فاز بر اساس PTF (Phase Transfer Function)
        
        α_ij = f(distance_ij, depth_PTF, latency)
        """
        # این یک پیاده‌سازی ساده است؛ در نسخه واقعی از PTF استفاده می‌شود
        # می‌تواند بر اساس:
        # - فاصله شبکه (latency)
        # - عمق هندسی (geometric depth)
        # - بار نود (load)
        latency = link.metadata.get("latency", 0.0)
        geometric_depth = link.metadata.get("geometric_depth", 0.0)
        
        # وزن‌ها
        latency_weight = 0.7
        depth_weight = 0.3
        
        return latency * latency_weight + geometric_depth * depth_weight
    
    def get_order_parameter_history(self) -> List[float]:
        """دریافت تاریخچه پارامتر نظم"""
        return self._order_parameter_history.copy()
    
    def get_phase_history(self) -> List[Dict[str, float]]:
        """دریافت تاریخچه فازها"""
        return self._phase_history.copy()
    
    def get_sync_status(self, nodes: List[OscillatorNode]) -> Dict:
        """
        دریافت وضعیت همگام‌سازی
        
        Returns:
            {
                "order_parameter": float,
                "mean_phase": float,
                "phase_variance": float,
                "is_synchronized": bool
            }
        """
        if not nodes:
            return {"order_parameter": 0.0, "mean_phase": 0.0, "phase_variance": 0.0, "is_synchronized": False}
        
        phases = [node.phase_state.phase for node in nodes]
        mean_phase = sum(phases) / len(phases)
        variance = sum((p - mean_phase) ** 2 for p in phases) / len(phases)
        R = self.compute_order_parameter(nodes)
        
        return {
            "order_parameter": R,
            "mean_phase": mean_phase,
            "phase_variance": variance,
            "is_synchronized": R > 0.7
        }
    
    def reset(self):
        """بازنشانی تاریخچه"""
        self._order_parameter_history = []
        self._phase_history = []

# ========================== ۴. تسکست ==========================

if __name__ == "__main__":
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    print("🧪 Testing KuramotoEngine...\n")
    
    # ۱. ایجاد نودها با فرکانس‌های مختلف (شروع از حالت ناهم‌فاز)
    nodes = []
    for i in range(10):
        phase = np.random.uniform(0, 2 * np.pi)
        freq = 0.8 + 0.4 * (i / 9)  # فرکانس‌های مختلف
        nodes.append(OscillatorNode(
            id=f"node_{i}",
            phase_state=PhaseState(phase=phase, frequency=freq),
            natural_frequency=freq
        ))
    
    # ۲. ایجاد اتصالات (شبکه کامل)
    links = []
    for i in range(len(nodes)):
        for j in range(len(nodes)):
            if i != j:
                links.append(PhaseLink(
                    source=f"node_{j}",
                    target=f"node_{i}",
                    weight=1.0,
                    phase_delay=0.0
                ))
    
    # ۳. ایجاد موتور
    engine = KuramotoEngine(
        coupling_strength=2.5,
        dt=0.01
    )
    
    # ۴. اجرای تکامل
    R_history = []
    phase_history = []
    
    print("⏳ Running evolution for 1000 steps...")
    for step in range(1000):
        nodes = engine.evolve(nodes, links)
        if step % 50 == 0:
            R = engine.compute_order_parameter(nodes)
            R_history.append(R)
            print(f"   Step {step}: R = {R:.4f}")
    
    # ۵. وضعیت نهایی
    status = engine.get_sync_status(nodes)
    print(f"\n✅ Final Status:")
    print(f"   Order Parameter: {status['order_parameter']:.4f}")
    print(f"   Mean Phase: {status['mean_phase']:.4f}")
    print(f"   Phase Variance: {status['phase_variance']:.4f}")
    print(f"   Synchronized: {status['is_synchronized']}")
    
    # ۶. رسم نمودار
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(R_history, 'b-', linewidth=2)
    ax.axhline(y=0.7, color='r', linestyle='--', label='Synchronization Threshold (R=0.7)')
    ax.set_xlabel('Step (every 50 steps)')
    ax.set_ylabel('Order Parameter R')
    ax.set_title('Kuramoto Engine — Phase Synchronization over Time')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("kuramoto_engine_output.png", dpi=150)
    print("\n✅ Plot saved to kuramoto_engine_output.png")
    
    print("\n✅ KuramotoEngine test completed!")
