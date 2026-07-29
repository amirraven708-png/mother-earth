#!/usr/bin/env python3
"""
kuma_004_wave_perception.py
KUMA-004: Mother Cognitive Layer — Wave Perception Engine

تشخیص الگوهای موجی از روی:
  - GRF Phase
  - Coherence (R)
  - Variance
  - Phase-Aware Routing paths
  - Node phase deviations

خروجی:
  - Wave Pattern Type
  - Wave Status
  - Network State
  - Risk Indicators
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# ========================== ۱. الگوهای موجی ==========================

class WavePatternType(Enum):
    """انواع الگوهای موجی قابل تشخیص"""
    STABLE = "stable"               # موج پایدار
    TRANSIENT = "transient"         # موج گذرا (در حال تغییر)
    COLLAPSING = "collapsing"       # موج در حال فروپاشی
    AMPLIFYING = "amplifying"       # موج در حال تقویت
    COHERENT = "coherent"           # هم‌فاز کامل
    OUT_OF_PHASE = "out_of_phase"   # خارج از فاز
    CHAOTIC = "chaotic"             # آشوب فازی
    DIVERGING = "diverging"         # در حال واگرایی
    CONVERGING = "converging"       # در حال همگرایی

class WaveStatus(Enum):
    """وضعیت جاری موج"""
    HEALTHY = "healthy"
    DEGRADING = "degrading"
    CRITICAL = "critical"
    RECOVERING = "recovering"
    STABLE = "stable"
    UNSTABLE = "unstable"

class NetworkState(Enum):
    """وضعیت کلی شبکه"""
    SYNCHRONIZED = "synchronized"
    DESYNCHRONIZED = "desynchronized"
    PARTIAL = "partial"
    FRAGMENTED = "fragmented"
    EMERGENT = "emergent"

# ========================== ۲. مدل داده الگوی موجی ==========================

@dataclass
class WavePattern:
    """الگوی موجی تشخیص‌داده‌شده"""
    pattern_type: WavePatternType
    status: WaveStatus
    network_state: NetworkState
    coherence: float
    phase: float
    variance: float
    risk_score: float                     # 0-1
    deviation_score: float                # 0-1
    node_count: int
    out_of_phase_nodes: List[str]
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "type": self.pattern_type.value,
            "status": self.status.value,
            "network_state": self.network_state.value,
            "coherence": self.coherence,
            "phase": self.phase,
            "variance": self.variance,
            "risk_score": self.risk_score,
            "deviation_score": self.deviation_score,
            "node_count": self.node_count,
            "out_of_phase_nodes": self.out_of_phase_nodes,
            "metadata": self.metadata
        }

# ========================== ۳. Wave Perception Engine ==========================

class WavePerceptionEngine:
    """
    موتور ادراک موجی — تشخیص الگوهای موجی از شبکه
    
    ورودی‌ها:
      - GRF Phase
      - Coherence (R)
      - Variance
      - Node phases
      - Routing paths (اختیاری)
    
    خروجی‌ها:
      - WavePattern (نوع، وضعیت، ریسک، انحراف)
    """
    
    def __init__(self, layer):
        self.layer = layer
        self._history: List[Dict] = []
        self._pattern_history: List[WavePattern] = []
    
    # ===== ۱. استخراج ویژگی‌ها =====
    
    def _extract_features(self) -> Dict[str, Any]:
        """استخراج ویژگی‌های اساسی از شبکه"""
        if self.layer._topology is None:
            return {"error": "No network"}
        
        nodes = self.layer._topology.nodes
        if not nodes:
            return {"error": "No nodes"}
        
        # فازها
        phases = [node.phase_state.phase for node in nodes]
        mean_phase = sum(phases) / len(phases)
        variance = sum((p - mean_phase) ** 2 for p in phases) / len(phases)
        
        # محاسبه R (پارامتر نظم)
        complex_sum = sum(math.cos(p) + 1j * math.sin(p) for p in phases)
        R = abs(complex_sum) / len(phases)
        
        # GRF Phase
        grf_phase = self.layer._grf_phase
        
        # انحرافات
        deviations = []
        out_of_phase_nodes = []
        for node in nodes:
            diff = node.phase_state.phase - mean_phase
            diff = math.atan2(math.sin(diff), math.cos(diff))
            deviations.append(abs(diff))
            if abs(diff) > math.pi / 2:
                out_of_phase_nodes.append(node.id)
        
        avg_deviation = sum(deviations) / len(deviations) if deviations else 0
        max_deviation = max(deviations) if deviations else 0
        
        # تعداد نودها
        num_nodes = len(nodes)
        
        return {
            "phases": phases,
            "mean_phase": mean_phase,
            "variance": variance,
            "R": R,
            "grf_phase": grf_phase,
            "avg_deviation": avg_deviation,
            "max_deviation": max_deviation,
            "out_of_phase_nodes": out_of_phase_nodes,
            "num_nodes": num_nodes
        }
    
    # ===== ۲. تشخیص الگو =====
    
    def perceive(self) -> WavePattern:
        """
        درک و تشخیص الگوی موجی فعلی شبکه
        """
        features = self._extract_features()
        if "error" in features:
            return WavePattern(
                pattern_type=WavePatternType.CHAOTIC,
                status=WaveStatus.UNSTABLE,
                network_state=NetworkState.FRAGMENTED,
                coherence=0.0,
                phase=0.0,
                variance=0.0,
                risk_score=1.0,
                deviation_score=1.0,
                node_count=0,
                out_of_phase_nodes=[],
                metadata={"error": features["error"]}
            )
        
        R = features["R"]
        variance = features["variance"]
        avg_deviation = features["avg_deviation"]
        max_deviation = features["max_deviation"]
        out_of_phase_nodes = features["out_of_phase_nodes"]
        num_nodes = features["num_nodes"]
        mean_phase = features["mean_phase"]
        grf_phase = features["grf_phase"]
        
        # ===== تشخیص نوع موج =====
        
        # ۱. هم‌فاز کامل
        if R > 0.95 and variance < 0.01:
            pattern_type = WavePatternType.COHERENT
            status = WaveStatus.HEALTHY
            network_state = NetworkState.SYNCHRONIZED
            risk_score = 0.0
            deviation_score = 0.0
        
        # ۲. پایدار
        elif R > 0.85 and variance < 0.05:
            pattern_type = WavePatternType.STABLE
            status = WaveStatus.STABLE
            network_state = NetworkState.SYNCHRONIZED
            risk_score = 0.05
            deviation_score = 0.05
        
        # ۳. در حال همگرایی
        elif R > 0.6 and variance < 0.1:
            pattern_type = WavePatternType.CONVERGING
            status = WaveStatus.RECOVERING
            network_state = NetworkState.PARTIAL
            risk_score = 0.2
            deviation_score = 0.2
        
        # ۴. گذرا
        elif R > 0.5 and variance < 0.2:
            pattern_type = WavePatternType.TRANSIENT
            status = WaveStatus.DEGRADING
            network_state = NetworkState.PARTIAL
            risk_score = 0.4
            deviation_score = 0.3
        
        # ۵. در حال تقویت
        elif R > 0.4 and avg_deviation < 0.5:
            pattern_type = WavePatternType.AMPLIFYING
            status = WaveStatus.RECOVERING
            network_state = NetworkState.PARTIAL
            risk_score = 0.3
            deviation_score = 0.4
        
        # ۶. در حال فروپاشی
        elif R > 0.2 and avg_deviation > 0.5:
            pattern_type = WavePatternType.COLLAPSING
            status = WaveStatus.CRITICAL
            network_state = NetworkState.FRAGMENTED
            risk_score = 0.8
            deviation_score = 0.7
        
        # ۷. خارج از فاز
        elif len(out_of_phase_nodes) > num_nodes * 0.3:
            pattern_type = WavePatternType.OUT_OF_PHASE
            status = WaveStatus.UNSTABLE
            network_state = NetworkState.DESYNCHRONIZED
            risk_score = 0.7
            deviation_score = 0.8
        
        # ۸. در حال واگرایی
        elif R < 0.3 and variance > 0.2:
            pattern_type = WavePatternType.DIVERGING
            status = WaveStatus.UNSTABLE
            network_state = NetworkState.DESYNCHRONIZED
            risk_score = 0.9
            deviation_score = 0.9
        
        # ۹. آشوب
        else:
            pattern_type = WavePatternType.CHAOTIC
            status = WaveStatus.UNSTABLE
            network_state = NetworkState.FRAGMENTED
            risk_score = 1.0
            deviation_score = 1.0
        
        # ایجاد الگو
        pattern = WavePattern(
            pattern_type=pattern_type,
            status=status,
            network_state=network_state,
            coherence=R,
            phase=mean_phase,
            variance=variance,
            risk_score=risk_score,
            deviation_score=deviation_score,
            node_count=num_nodes,
            out_of_phase_nodes=out_of_phase_nodes,
            metadata=features
        )
        
        # ذخیره تاریخچه
        self._pattern_history.append(pattern)
        if len(self._pattern_history) > 100:
            self._pattern_history.pop(0)
        
        return pattern
    
    # ===== ۳. تشخیص روند =====
    
    def detect_trend(self, window: int = 10) -> Dict[str, Any]:
        """
        تشخیص روند تغییرات الگو در پنجره زمانی
        """
        if len(self._pattern_history) < window:
            return {"status": "insufficient_data"}
        
        recent = self._pattern_history[-window:]
        R_values = [p.coherence for p in recent]
        risk_values = [p.risk_score for p in recent]
        
        # روند R
        R_trend = (R_values[-1] - R_values[0]) / window
        
        # روند ریسک
        risk_trend = (risk_values[-1] - risk_values[0]) / window
        
        # تشخیص وضعیت
        if R_trend > 0.01 and risk_trend < -0.01:
            trend_status = "improving"
        elif R_trend < -0.01 and risk_trend > 0.01:
            trend_status = "degrading"
        else:
            trend_status = "stable"
        
        return {
            "trend_status": trend_status,
            "R_trend": R_trend,
            "risk_trend": risk_trend,
            "current_R": R_values[-1],
            "current_risk": risk_values[-1]
        }
    
    # ===== ۴. گزارش =====
    
    def get_perception_report(self) -> Dict:
        """
        دریافت گزارش کامل ادراکی
        """
        pattern = self.perceive()
        trend = self.detect_trend()
        
        return {
            "pattern": pattern.to_dict(),
            "trend": trend,
            "history_length": len(self._pattern_history)
        }

# ========================== ۴. تست ==========================

def run_kuma_004_test():
    """
    تست Wave Perception Engine
    """
    print("\n" + "="*70)
    print("🧠 KUMA-004: Mother Cognitive Layer — Wave Perception Engine")
    print("="*70 + "\n")
    
    # ۱. ایجاد شبکه
    try:
        from mother_intelligence.wave_synchronization_layer import WaveSynchronizationLayer
        from mother_intelligence.kuma_003_adaptive_topology import TopologyConfig, create_topology
    except ImportError:
        from wave_synchronization_layer import WaveSynchronizationLayer
        from kuma_003_adaptive_topology import TopologyConfig, create_topology
    
    layer = WaveSynchronizationLayer(
        coupling_strength=2.5,
        dt=0.01,
        damping_factor=0.15
    )
    layer.create_network(num_nodes=20, topology="complete")
    
    # ۲. همگام‌سازی و جمع‌آوری ادراک
    perception = WavePerceptionEngine(layer)
    
    print("⏳ Running perception over 200 steps...")
    patterns = []
    
    for step in range(200):
        layer.step()
        if step % 20 == 0:
            pattern = perception.perceive()
            patterns.append(pattern)
            print(f"   Step {step:3d}: {pattern.pattern_type.value} (R={pattern.coherence:.3f}, risk={pattern.risk_score:.3f})")
    
    # ۳. گزارش نهایی
    print("\n" + "-"*50)
    print("📊 FINAL PERCEPTION REPORT")
    print("-"*50)
    
    report = perception.get_perception_report()
    pattern = report["pattern"]
    trend = report["trend"]
    
    print(f"\n🔮 Current Pattern: {pattern['type']}")
    print(f"   Status: {pattern['status']}")
    print(f"   Network State: {pattern['network_state']}")
    print(f"   Coherence (R): {pattern['coherence']:.4f}")
    print(f"   Risk Score: {pattern['risk_score']:.4f}")
    print(f"   Out of Phase Nodes: {len(pattern['out_of_phase_nodes'])}")
    
    print(f"\n📈 Trend: {trend.get('trend_status', 'N/A')}")
    print(f"   R Trend: {trend.get('R_trend', 0):.4f}")
    print(f"   Risk Trend: {trend.get('risk_trend', 0):.4f}")
    
    print("\n" + "="*70)
    print("🏁 KUMA-004 Perception Test Complete")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_kuma_004_test()
