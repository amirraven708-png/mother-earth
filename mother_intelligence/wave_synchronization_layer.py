#!/usr/bin/env python3
"""
wave_synchronization_layer.py
لایه همگام‌سازی موجی — اتصال KuramotoEngine به ACIOMD Solver

مسیر داده:
  Event Stream → ACIOMD Solver → SoftDampingController → KuramotoEngine → Synchronized Phase Field

ویژگی‌ها:
  - مدیریت شبکه چندنودی با همگام‌سازی زمان واقعی
  - اتصال به GRF (Global Rhythm Field) برای تولید ریتم جهانی
  - اتصال به Doors OS برای وضعیت ذهنی سیستم
  - اتصال به Raven Supervisor برای شناسایی نودهای خارج از فاز
"""

import numpy as np
import math
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

# ========================== ۱. واردات ماژول‌های موجود ==========================

try:
    from mother_intelligence.kuramoto_engine import KuramotoEngine, OscillatorNode, PhaseState, PhaseLink
except ImportError:
    # برای اجرای مستقل
    from kuramoto_engine import KuramotoEngine, OscillatorNode, PhaseState, PhaseLink

try:
    from mother_intelligence.adaptive_geometry_decoder import AdaptiveGeometryDecoder
except ImportError:
    # اگر ماژول موجود نباشد، یک شبیه‌ساز ساده استفاده می‌شود
    class AdaptiveGeometryDecoder:
        def __init__(self, **kwargs):
            self.current_theta = 0.3
        def step(self, t, y):
            return self.current_theta, 0.01

# ========================== ۲. مدل داده شبکه ==========================

@dataclass
class WaveNode:
    """یک نود در شبکه موجی"""
    id: str
    phase_state: PhaseState
    natural_frequency: float = 1.0
    geometry_theta: float = 0.3
    metadata: Dict = field(default_factory=dict)

@dataclass
class NetworkTopology:
    """توپولوژی شبکه"""
    nodes: List[WaveNode]
    links: List[PhaseLink]
    timestamp: float = field(default_factory=time.time)

# ========================== ۳. لایه همگام‌سازی موجی ==========================

class WaveSynchronizationLayer:
    """
    لایه همگام‌سازی موجی — مدیریت شبکه چندنودی با Kuramoto + ACIOMD
    
    وظایف:
    - مدیریت نودها و اتصالات
    - اجرای گام‌های زمانی همگام‌سازی
    - اتصال به GRF (ریتم جهانی)
    - اتصال به Doors OS (حالت ذهنی)
    - اتصال به Raven Supervisor (شناسایی نودهای خارج از فاز)
    """
    
    def __init__(
        self,
        coupling_strength: float = 2.5,
        dt: float = 0.01,
        damping_factor: float = 0.15,
        use_phase_delay: bool = True
    ):
        self.K = coupling_strength
        self.dt = dt
        self.use_phase_delay = use_phase_delay
        
        # ایجاد کنترل‌کننده میرایی
        from kuramoto_engine import SoftDampingController
        self.damping_controller = SoftDampingController(damping_factor=damping_factor)
        
        # ایجاد موتور Kuramoto
        self.kuramoto = KuramotoEngine(
            coupling_strength=coupling_strength,
            damping_controller=self.damping_controller,
            dt=dt,
            use_phase_delay=use_phase_delay
        )
        
        # ایجاد دیکودر هندسه برای هر نود (شبیه‌سازی)
        self.geometry_decoders: Dict[str, AdaptiveGeometryDecoder] = {}
        
        # وضعیت شبکه
        self._topology: Optional[NetworkTopology] = None
        self._phase_history: List[Dict[str, float]] = []
        self._order_history: List[float] = []
        self._tick = 0
        
        # GRF (ریتم جهانی)
        self._grf_phase = 0.0
        self._grf_coherence = 0.0
        
        # Doors OS (حالت ذهنی)
        self._mind_state = "idle"
        self._mind_state_history: List[str] = []
        
        # Raven Supervisor (نودهای خارج از فاز)
        self._out_of_phase_nodes: List[str] = []
    
    # ========================== ۱. مدیریت شبکه ==========================
    
    def create_network(self, num_nodes: int = 10, topology: str = "complete") -> NetworkTopology:
        """
        ایجاد شبکه با تعداد نود مشخص
        
        Args:
            num_nodes: تعداد نودها
            topology: "complete" (کامل), "ring" (حلقوی), "star" (ستاره‌ای)
        """
        nodes = []
        links = []
        
        # ایجاد نودها با فازهای تصادفی
        for i in range(num_nodes):
            phase = np.random.uniform(0, 2 * np.pi)
            freq = 0.8 + 0.4 * (i / max(1, num_nodes - 1))
            nodes.append(WaveNode(
                id=f"node_{i:03d}",
                phase_state=PhaseState(phase=phase, frequency=freq),
                natural_frequency=freq,
                geometry_theta=0.3 + 0.1 * (i / max(1, num_nodes - 1))
            ))
            
            # ایجاد دیکودر هندسه برای هر نود
            self.geometry_decoders[f"node_{i:03d}"] = AdaptiveGeometryDecoder(
                initial_theta=0.3,
                omega=2.0 * np.pi * 1.0
            )
        
        # ایجاد اتصالات بر اساس توپولوژی
        if topology == "complete":
            for i in range(num_nodes):
                for j in range(num_nodes):
                    if i != j:
                        links.append(PhaseLink(
                            source=f"node_{i:03d}",
                            target=f"node_{j:03d}",
                            weight=1.0,
                            phase_delay=0.0
                        ))
        elif topology == "ring":
            for i in range(num_nodes):
                j = (i + 1) % num_nodes
                links.append(PhaseLink(
                    source=f"node_{i:03d}",
                    target=f"node_{j:03d}",
                    weight=1.0,
                    phase_delay=0.0
                ))
                links.append(PhaseLink(
                    source=f"node_{j:03d}",
                    target=f"node_{i:03d}",
                    weight=1.0,
                    phase_delay=0.0
                ))
        elif topology == "star":
            center = "node_000"
            for i in range(1, num_nodes):
                links.append(PhaseLink(
                    source=center,
                    target=f"node_{i:03d}",
                    weight=1.0,
                    phase_delay=0.0
                ))
        
        self._topology = NetworkTopology(nodes=nodes, links=links)
        return self._topology
    
    # ========================== ۲. گام زمانی ==========================
    
    def step(self, dt: Optional[float] = None) -> Dict:
        """
        یک گام زمانی در همگام‌سازی شبکه
        
        Returns:
            دیکشنری شامل:
            - order_parameter: پارامتر نظم
            - mean_phase: میانگین فاز
            - phase_variance: واریانس فاز
            - is_synchronized: وضعیت هم‌فازی
            - grf_phase: فاز GRF
            - mind_state: حالت ذهنی Doors OS
            - out_of_phase_nodes: نودهای خارج از فاز
        """
        if self._topology is None:
            raise ValueError("Network not created. Call create_network() first.")
        
        if dt is None:
            dt = self.dt
        
        self._tick += 1
        
        # ۱. تبدیل WaveNode به OscillatorNode
        oscillators = [
            OscillatorNode(
                id=node.id,
                phase_state=node.phase_state,
                natural_frequency=node.natural_frequency,
                metadata=node.metadata
            )
            for node in self._topology.nodes
        ]
        
        # ۲. اجرای KuramotoEngine
        updated_oscillators = self.kuramoto.evolve(oscillators, self._topology.links, dt)
        
        # ۳. به‌روزرسانی نودها با فازهای جدید
        oscillator_map = {osc.id: osc for osc in updated_oscillators}
        for node in self._topology.nodes:
            osc = oscillator_map.get(node.id)
            if osc:
                node.phase_state = osc.phase_state
        
        # ۴. به‌روزرسانی GRF (ریتم جهانی)
        self._update_grf()
        
        # ۵. به‌روزرسانی Doors OS (حالت ذهنی)
        self._update_mind_state()
        
        # ۶. شناسایی نودهای خارج از فاز
        self._detect_out_of_phase()
        
        # ۷. ذخیره تاریخچه
        self._phase_history.append({
            node.id: node.phase_state.phase for node in self._topology.nodes
        })
        if len(self._phase_history) > 1000:
            self._phase_history.pop(0)
        
        R = self.kuramoto.compute_order_parameter(updated_oscillators)
        self._order_history.append(R)
        if len(self._order_history) > 1000:
            self._order_history.pop(0)
        
        # ۸. وضعیت نهایی
        status = self.kuramoto.get_sync_status(updated_oscillators)
        
        return {
            "order_parameter": R,
            "mean_phase": status["mean_phase"],
            "phase_variance": status["phase_variance"],
            "is_synchronized": status["is_synchronized"],
            "grf_phase": self._grf_phase,
            "grf_coherence": self._grf_coherence,
            "mind_state": self._mind_state,
            "out_of_phase_nodes": self._out_of_phase_nodes,
            "tick": self._tick
        }
    
    # ========================== ۳. GRF (ریتم جهانی) ==========================
    
    def _update_grf(self):
        """به‌روزرسانی میدان ریتم جهانی (GRF)"""
        if not self._topology or not self._topology.nodes:
            return
        
        # محاسبه فاز میانگین
        phases = [node.phase_state.phase for node in self._topology.nodes]
        mean_phase = sum(phases) / len(phases)
        
        # محاسبه coherence از پارامتر نظم
        R = self.kuramoto.compute_order_parameter([
            OscillatorNode(
                id=node.id,
                phase_state=node.phase_state,
                natural_frequency=node.natural_frequency
            )
            for node in self._topology.nodes
        ])
        
        # به‌روزرسانی GRF
        self._grf_phase = mean_phase
        self._grf_coherence = R
        
        # تکامل GRF با زمان
        self._grf_phase += 0.01 * self._grf_coherence
        self._grf_phase = self._grf_phase % (2 * math.pi)
    
    # ========================== ۴. Doors OS (حالت ذهنی) ==========================
    
    def _update_mind_state(self):
        """به‌روزرسانی حالت ذهنی Doors OS"""
        if not self._topology or not self._topology.nodes:
            self._mind_state = "idle"
            return
        
        R = self.kuramoto.compute_order_parameter([
            OscillatorNode(
                id=node.id,
                phase_state=node.phase_state,
                natural_frequency=node.natural_frequency
            )
            for node in self._topology.nodes
        ])
        
        # تعیین حالت بر اساس R
        if R > 0.9:
            self._mind_state = "coherent"
        elif R > 0.7:
            self._mind_state = "converging"
        elif R > 0.4:
            self._mind_state = "transitioning"
        else:
            self._mind_state = "chaotic"
        
        self._mind_state_history.append(self._mind_state)
        if len(self._mind_state_history) > 100:
            self._mind_state_history.pop(0)
    
    # ========================== ۵. Raven Supervisor (نودهای خارج از فاز) ==========================
    
    def _detect_out_of_phase(self):
        """شناسایی نودهای خارج از فاز"""
        if not self._topology or len(self._topology.nodes) < 2:
            self._out_of_phase_nodes = []
            return
        
        # محاسبه فاز میانگین
        phases = [node.phase_state.phase for node in self._topology.nodes]
        mean_phase = sum(phases) / len(phases)
        
        # شناسایی نودهایی که فازشان بیش از π/2 از میانگین فاصله دارد
        self._out_of_phase_nodes = []
        for node in self._topology.nodes:
            diff = node.phase_state.phase - mean_phase
            diff = math.atan2(math.sin(diff), math.cos(diff))
            if abs(diff) > math.pi / 2:
                self._out_of_phase_nodes.append(node.id)
    
    # ========================== ۶. متدهای عمومی ==========================
    
    def get_network_status(self) -> Dict:
        """دریافت وضعیت کامل شبکه"""
        if self._topology is None:
            return {"status": "not_initialized"}
        
        return {
            "num_nodes": len(self._topology.nodes),
            "num_links": len(self._topology.links),
            "order_parameter": self.kuramoto.compute_order_parameter([
                OscillatorNode(
                    id=node.id,
                    phase_state=node.phase_state,
                    natural_frequency=node.natural_frequency
                )
                for node in self._topology.nodes
            ]),
            "grf_phase": self._grf_phase,
            "grf_coherence": self._grf_coherence,
            "mind_state": self._mind_state,
            "out_of_phase_nodes": len(self._out_of_phase_nodes),
            "tick": self._tick
        }
    
    def get_node_status(self, node_id: str) -> Optional[Dict]:
        """دریافت وضعیت یک نود"""
        if self._topology is None:
            return None
        
        for node in self._topology.nodes:
            if node.id == node_id:
                return {
                    "id": node.id,
                    "phase": node.phase_state.phase,
                    "frequency": node.phase_state.frequency,
                    "stability": node.phase_state.stability,
                    "geometry_theta": node.geometry_theta,
                    "is_out_of_phase": node_id in self._out_of_phase_nodes
                }
        return None
    
    def add_node(self, node_id: str, phase: Optional[float] = None, frequency: float = 1.0) -> bool:
        """افزودن نود جدید به شبکه"""
        if self._topology is None:
            return False
        
        if phase is None:
            phase = np.random.uniform(0, 2 * np.pi)
        
        new_node = WaveNode(
            id=node_id,
            phase_state=PhaseState(phase=phase, frequency=frequency),
            natural_frequency=frequency,
            geometry_theta=0.3
        )
        self._topology.nodes.append(new_node)
        self.geometry_decoders[node_id] = AdaptiveGeometryDecoder(
            initial_theta=0.3,
            omega=2.0 * np.pi * 1.0
        )
        
        # اتصال به همه نودهای موجود
        for node in self._topology.nodes:
            if node.id != node_id:
                self._topology.links.append(PhaseLink(
                    source=node_id,
                    target=node.id,
                    weight=1.0,
                    phase_delay=0.0
                ))
                self._topology.links.append(PhaseLink(
                    source=node.id,
                    target=node_id,
                    weight=1.0,
                    phase_delay=0.0
                ))
        
        return True
    
    def remove_node(self, node_id: str) -> bool:
        """حذف نود از شبکه"""
        if self._topology is None:
            return False
        
        # حذف نود
        self._topology.nodes = [n for n in self._topology.nodes if n.id != node_id]
        
        # حذف اتصالات مربوط به نود
        self._topology.links = [
            l for l in self._topology.links
            if l.source != node_id and l.target != node_id
        ]
        
        if node_id in self.geometry_decoders:
            del self.geometry_decoders[node_id]
        
        return True

# ========================== ۷. تست ==========================

if __name__ == "__main__":
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    print("🧪 Testing WaveSynchronizationLayer...\n")
    
    # ۱. ایجاد شبکه با ۲۰ نود
    layer = WaveSynchronizationLayer(
        coupling_strength=2.5,
        dt=0.01,
        damping_factor=0.15
    )
    
    print("📡 Creating network with 20 nodes (complete topology)...")
    layer.create_network(num_nodes=20, topology="complete")
    print(f"   ✅ {len(layer._topology.nodes)} nodes, {len(layer._topology.links)} links")
    
    # ۲. اجرای ۱۰۰۰ گام
    print("\n⏳ Running 1000 steps...")
    R_history = []
    grf_history = []
    mind_history = []
    out_of_phase_history = []
    
    for step in range(1000):
        result = layer.step()
        if step % 50 == 0:
            R_history.append(result["order_parameter"])
            grf_history.append(result["grf_coherence"])
            mind_history.append(result["mind_state"])
            out_of_phase_history.append(len(result["out_of_phase_nodes"]))
            print(f"   Step {step:4d}: R={result['order_parameter']:.4f}, state={result['mind_state']}, out_of_phase={len(result['out_of_phase_nodes'])}")
    
    # ۳. وضعیت نهایی
    print(f"\n✅ Final Status:")
    status = layer.get_network_status()
    print(f"   Order Parameter: {status['order_parameter']:.4f}")
    print(f"   GRF Phase: {status['grf_phase']:.4f}")
    print(f"   GRF Coherence: {status['grf_coherence']:.4f}")
    print(f"   Mind State: {status['mind_state']}")
    print(f"   Out of Phase Nodes: {status['out_of_phase_nodes']}")
    
    # ۴. رسم نمودار
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    
    # ۱. پارامتر نظم
    axes[0].plot(range(0, 1000, 50), R_history, 'b-', linewidth=2)
    axes[0].axhline(y=0.7, color='r', linestyle='--', label='Synchronization Threshold')
    axes[0].set_ylabel('Order Parameter R')
    axes[0].set_title('Kuramoto Synchronization')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # ۲. GRF Coherence
    axes[1].plot(range(0, 1000, 50), grf_history, 'g-', linewidth=2)
    axes[1].set_ylabel('GRF Coherence')
    axes[1].set_title('Global Rhythm Field Coherence')
    axes[1].grid(True, alpha=0.3)
    
    # ۳. نودهای خارج از فاز
    axes[2].plot(range(0, 1000, 50), out_of_phase_history, 'r-', linewidth=2)
    axes[2].set_ylabel('Out of Phase Nodes')
    axes[2].set_xlabel('Step')
    axes[2].set_title('Raven Supervisor — Out of Phase Nodes Detection')
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("wave_synchronization_layer_output.png", dpi=150)
    print("\n✅ Plot saved to wave_synchronization_layer_output.png")
    
    print("\n✅ WaveSynchronizationLayer test completed!")
