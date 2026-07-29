#!/usr/bin/env python3
"""
kuma_003_adaptive_topology.py
موتور توپولوژی تطبیقی، خرابی زنجیره‌ای و مسیریابی فاز-آگاه

سناریوهای تست:
  ۱. حذف چندگانه (Multiple Node Failure) — 5/20 نود یا بیشتر
  ۲. شبکه ناقص (Sparse & Small-World Topology) — تست روی گراف‌های مختلف
  ۳. مسیریابی فاز-آگاه (Phase-Aware Routing) — انتخاب مسیر بر اساس فاز

معیارهای خروجی:
  - Resilience under cascade failures
  - Recovery time vs number of failures
  - Routing cost vs phase alignment
  - Small-world vs complete graph comparison
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

# ========================== ۲. تعریف WaveNode (در صورت نیاز) ==========================

# اگر WaveNode در جای دیگر تعریف نشده، اینجا تعریف می‌شود
class WaveNode:
    """یک نود در شبکه موجی"""
    def __init__(self, id: str, phase_state: PhaseState, natural_frequency: float = 1.0, 
                 geometry_theta: float = 0.3, metadata: Dict = None):
        self.id = id
        self.phase_state = phase_state
        self.natural_frequency = natural_frequency
        self.geometry_theta = geometry_theta
        self.metadata = metadata or {}

# ========================== ۳. مدل‌های داده ==========================

@dataclass
class TopologyConfig:
    """پیکربندی توپولوژی شبکه"""
    topology_type: str = "complete"      # "complete", "small_world", "sparse", "ring"
    num_nodes: int = 20
    small_world_prob: float = 0.1        # احتمال اتصال مجدد در small-world
    sparse_degree: int = 3               # درجه اتصال در شبکه sparse
    routing_beta: float = 0.5            # وزن اختلاف فاز در مسیریابی

@dataclass
class RoutingResult:
    """نتیجه مسیریابی فاز-آگاه"""
    path: List[str]
    total_cost: float
    phase_cost: float
    latency_cost: float
    selected_paths: List[List[str]]

# ========================== ۴. توپولوژی‌های مختلف ==========================

def create_topology(config: TopologyConfig) -> Tuple[List[WaveNode], List[PhaseLink]]:
    """
    ایجاد توپولوژی بر اساس پیکربندی
    """
    num_nodes = config.num_nodes
    nodes = []
    links = []
    
    # ایجاد نودها
    for i in range(num_nodes):
        phase = np.random.uniform(0, 2 * np.pi)
        freq = 0.8 + 0.4 * (i / max(1, num_nodes - 1))
        nodes.append(WaveNode(
            id=f"node_{i:03d}",
            phase_state=PhaseState(phase=phase, frequency=freq),
            natural_frequency=freq,
            geometry_theta=0.3 + 0.1 * (i / max(1, num_nodes - 1))
        ))
    
    # ایجاد لینک‌ها بر اساس توپولوژی
    if config.topology_type == "complete":
        for i in range(num_nodes):
            for j in range(num_nodes):
                if i != j:
                    links.append(PhaseLink(
                        source=f"node_{i:03d}",
                        target=f"node_{j:03d}",
                        weight=1.0,
                        phase_delay=random.uniform(0, 0.05)
                    ))
    
    elif config.topology_type == "small_world":
        # شروع با گراف حلقوی
        for i in range(num_nodes):
            j = (i + 1) % num_nodes
            links.append(PhaseLink(
                source=f"node_{i:03d}",
                target=f"node_{j:03d}",
                weight=1.0,
                phase_delay=random.uniform(0, 0.05)
            ))
            links.append(PhaseLink(
                source=f"node_{j:03d}",
                target=f"node_{i:03d}",
                weight=1.0,
                phase_delay=random.uniform(0, 0.05)
            ))
        
        # اضافه کردن اتصالات تصادفی (Small-World)
        extra_links = int(num_nodes * config.small_world_prob * num_nodes / 2)
        existing = set()
        for _ in range(extra_links):
            i = random.randint(0, num_nodes - 1)
            j = random.randint(0, num_nodes - 1)
            if i != j and (i, j) not in existing and (j, i) not in existing:
                existing.add((i, j))
                links.append(PhaseLink(
                    source=f"node_{i:03d}",
                    target=f"node_{j:03d}",
                    weight=1.0,
                    phase_delay=random.uniform(0, 0.1)
                ))
    
    elif config.topology_type == "sparse":
        # گراف با درجه ثابت
        for i in range(num_nodes):
            neighbors = []
            for d in range(1, config.sparse_degree + 1):
                j = (i + d) % num_nodes
                if j != i:
                    neighbors.append(j)
            for j in neighbors:
                links.append(PhaseLink(
                    source=f"node_{i:03d}",
                    target=f"node_{j:03d}",
                    weight=1.0,
                    phase_delay=random.uniform(0, 0.05)
                ))
    
    elif config.topology_type == "ring":
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
    
    return nodes, links

# ========================== ۵. موتور توپولوژی تطبیقی ==========================

class AdaptiveTopologyEngine:
    """
    موتور توپولوژی تطبیقی، خرابی زنجیره‌ای و مسیریابی فاز-آگاه
    """
    
    def __init__(self, layer: WaveSynchronizationLayer):
        self.layer = layer
    
    # ===== ۱. سناریو: حذف چندگانه =====
    
    def simulate_multiple_node_drop(self, num_to_drop: int = 5, recovery_steps: int = 300) -> Dict:
        """
        شبیه‌سازی حذف چند نود به‌طور همزمان
        
        Args:
            num_to_drop: تعداد نودهایی که حذف می‌شوند
            recovery_steps: تعداد گام برای بازیابی
        """
        print(f"💀 Simulating multiple node drop ({num_to_drop} nodes)...")
        
        # انتخاب نودها
        node_ids = [n.id for n in self.layer._topology.nodes]
        if len(node_ids) <= num_to_drop:
            return {"error": "Not enough nodes"}
        
        dropped_nodes = random.sample(node_ids, num_to_drop)
        
        # ذخیره وضعیت اولیه
        initial_R = self.layer.kuramoto.compute_order_parameter(
            [OscillatorNode(id=n.id, phase_state=n.phase_state, natural_frequency=n.natural_frequency)
             for n in self.layer._topology.nodes]
        )
        
        # حذف نودها
        for node_id in dropped_nodes:
            self.layer.remove_node(node_id)
        
        # اجرای گام‌ها
        R_history = []
        recovery_time = None
        
        for step in range(recovery_steps):
            result = self.layer.step()
            R_history.append(result["order_parameter"])
            
            # اگر R به بالای 0.85 برگشت، بازیابی کامل
            if result["order_parameter"] > 0.85 and step > 20 and recovery_time is None:
                recovery_time = step
        
        if recovery_time is None:
            recovery_time = recovery_steps
        
        final_R = R_history[-1] if R_history else 0
        success = final_R > 0.85
        
        return {
            "scenario": "multiple_node_drop",
            "success": success,
            "dropped_nodes": dropped_nodes,
            "num_dropped": num_to_drop,
            "recovery_time": recovery_time,
            "final_R": final_R,
            "R_history": R_history,
            "resilience_score": final_R / initial_R if initial_R > 0 else 0
        }
    
    # ===== ۲. سناریو: مقایسه توپولوژی‌ها =====
    
    def compare_topologies(self, topologies: List[str] = ["complete", "small_world", "sparse", "ring"], steps: int = 300) -> Dict:
        """
        مقایسه عملکرد توپولوژی‌های مختلف
        
        Args:
            topologies: لیست توپولوژی‌های مورد نظر
            steps: تعداد گام‌ها
        """
        print(f"📊 Comparing topologies: {topologies}")
        
        results = {}
        
        for topo_type in topologies:
            print(f"   Testing {topo_type}...")
            
            # ایجاد توپولوژی جدید
            config = TopologyConfig(
                topology_type=topo_type,
                num_nodes=20
            )
            nodes, links = create_topology(config)
            
            # بازسازی لایه
            self.layer._topology.nodes = nodes
            self.layer._topology.links = links
            
            # اجرای گام‌ها
            R_history = []
            for _ in range(steps):
                result = self.layer.step()
                R_history.append(result["order_parameter"])
            
            final_R = R_history[-1] if R_history else 0
            avg_R = np.mean(R_history[-50:]) if len(R_history) >= 50 else final_R
            stability = np.std(R_history[-50:]) if len(R_history) >= 50 else 0
            
            results[topo_type] = {
                "final_R": final_R,
                "avg_R": avg_R,
                "stability": stability,
                "num_links": len(links),
                "num_nodes": len(nodes)
            }
        
        return results
    
    # ===== ۳. سناریو: مسیریابی فاز-آگاه =====
    
    def compute_phase_aware_routing(self, source: str, target: str, beta: float = 0.5) -> RoutingResult:
        """
        محاسبه مسیر بهینه بر اساس فاز و تأخیر
        
        Args:
            source: شناسه نود مبدأ
            target: شناسه نود مقصد
            beta: وزن اختلاف فاز در هزینه مسیر
        """
        # دریافت فازهای فعلی
        phases = {}
        for node in self.layer._topology.nodes:
            phases[node.id] = node.phase_state.phase
        
        # ایجاد گراف وزنی
        graph = defaultdict(list)
        for link in self.layer._topology.links:
            phase_diff = abs(phases.get(link.source, 0) - phases.get(link.target, 0))
            phase_diff = math.atan2(math.sin(phase_diff), math.cos(phase_diff))
            
            # هزینه = تأخیر + β * اختلاف فاز
            latency = link.phase_delay
            cost = latency + beta * abs(phase_diff)
            
            graph[link.source].append({
                "target": link.target,
                "cost": cost,
                "latency": latency,
                "phase_diff": phase_diff
            })
        
        # Dijkstra برای یافتن کوتاه‌ترین مسیر
        import heapq
        distances = {node.id: float('inf') for node in self.layer._topology.nodes}
        distances[source] = 0
        predecessors = {node.id: None for node in self.layer._topology.nodes}
        pq = [(0, source)]
        
        while pq:
            dist, node = heapq.heappop(pq)
            if dist > distances[node]:
                continue
            if node == target:
                break
            for neighbor in graph[node]:
                new_dist = dist + neighbor["cost"]
                if new_dist < distances[neighbor["target"]]:
                    distances[neighbor["target"]] = new_dist
                    predecessors[neighbor["target"]] = node
        
        # بازسازی مسیر
        path = []
        current = target
        while current is not None:
            path.append(current)
            current = predecessors[current]
        path.reverse()
        
        # محاسبه هزینه‌ها
        total_latency = 0
        total_phase_diff = 0
        for i in range(len(path) - 1):
            src = path[i]
            dst = path[i + 1]
            for neighbor in graph[src]:
                if neighbor["target"] == dst:
                    total_latency += neighbor["latency"]
                    total_phase_diff += abs(neighbor["phase_diff"])
                    break
        
        total_cost = total_latency + beta * total_phase_diff
        
        return RoutingResult(
            path=path,
            total_cost=total_cost,
            phase_cost=total_phase_diff,
            latency_cost=total_latency,
            selected_paths=[path]
        )
    
    # ===== ۴. سناریو: خرابی زنجیره‌ای =====
    
    def simulate_cascade_failure(self, initial_failure: int = 1, max_failures: int = 10) -> Dict:
        """
        شبیه‌سازی خرابی زنجیره‌ای: با حذف یک نود، نودهای همسایه تحت تأثیر قرار می‌گیرند
        
        Args:
            initial_failure: تعداد نودهای اولیه که حذف می‌شوند
            max_failures: حداکثر تعداد خرابی‌های زنجیره‌ای
        """
        print(f"🔥 Simulating cascade failure (starting with {initial_failure} nodes)...")
        
        failed_nodes = []
        R_history = []
        
        # انتخاب نودهای اولیه
        node_ids = [n.id for n in self.layer._topology.nodes]
        initial_nodes = random.sample(node_ids, initial_failure)
        failed_nodes.extend(initial_nodes)
        
        # حذف نودها
        for node_id in initial_nodes:
            self.layer.remove_node(node_id)
        
        # اجرای گام‌ها و بررسی خرابی زنجیره‌ای
        for step in range(200):
            result = self.layer.step()
            R_history.append(result["order_parameter"])
            
            # اگر coherence خیلی پایین بیاید، نودهای بیشتری حذف می‌شوند
            if result["order_parameter"] < 0.3 and len(failed_nodes) < max_failures:
                # پیدا کردن نودهایی که هم‌فازی ضعیفی دارند
                weak_nodes = []
                for node in self.layer._topology.nodes:
                    diff = node.phase_state.phase - result["mean_phase"]
                    diff = math.atan2(math.sin(diff), math.cos(diff))
                    if abs(diff) > math.pi / 2:
                        weak_nodes.append(node.id)
                
                # حذف برخی از نودهای ضعیف
                if weak_nodes:
                    to_remove = random.sample(weak_nodes, min(2, len(weak_nodes)))
                    for node_id in to_remove:
                        self.layer.remove_node(node_id)
                        failed_nodes.append(node_id)
                        print(f"   🔥 Cascade: removed {node_id}")
        
        final_R = R_history[-1] if R_history else 0
        success = final_R > 0.7
        
        return {
            "scenario": "cascade_failure",
            "success": success,
            "failed_nodes": failed_nodes,
            "num_failures": len(failed_nodes),
            "final_R": final_R,
            "R_history": R_history
        }

# ========================== ۶. تست جامع KUMA-003 ==========================

def run_kuma_003_tests():
    """
    اجرای همه سناریوهای KUMA-003
    """
    print("\n" + "="*70)
    print("🧪 KUMA-003: Adaptive Topology, Failure Cascades & Phase-Aware Routing")
    print("="*70 + "\n")
    
    # ۱. ایجاد شبکه اولیه (20 نود، کامل)
    print("📡 Creating base network with 20 nodes (complete topology)...")
    layer = WaveSynchronizationLayer(
        coupling_strength=2.5,
        dt=0.01,
        damping_factor=0.15
    )
    layer.create_network(num_nodes=20, topology="complete")
    
    # همگام‌سازی اولیه
    print("⏳ Initial synchronization (200 steps)...")
    for _ in range(200):
        layer.step()
    
    initial_status = layer.get_network_status()
    print(f"   Initial R = {initial_status['order_parameter']:.4f}")
    
    # ۲. ایجاد موتور
    engine = AdaptiveTopologyEngine(layer)
    
    results = []
    
    # سناریو ۱: حذف چندگانه
    print("\n" + "-"*50)
    result1 = engine.simulate_multiple_node_drop(num_to_drop=5, recovery_steps=300)
    results.append(result1)
    print(f"   Multiple Drop: success={result1['success']}, recovery_time={result1['recovery_time']}, resilience={result1['resilience_score']:.3f}")
    
    # سناریو ۲: مقایسه توپولوژی‌ها
    print("\n" + "-"*50)
    result2 = engine.compare_topologies(topologies=["complete", "small_world", "sparse", "ring"], steps=300)
    results.append(result2)
    print("   Topology Comparison:")
    for topo, data in result2.items():
        print(f"      {topo}: R={data['final_R']:.4f}, links={data['num_links']}, stability={data['stability']:.4f}")
    
    # سناریو ۳: مسیریابی فاز-آگاه
    print("\n" + "-"*50)
    # بازیابی همگام‌سازی برای مسیریابی
    for _ in range(100):
        layer.step()
    
    # انتخاب دو نود تصادفی
    node_ids = [n.id for n in layer._topology.nodes]
    if len(node_ids) >= 2:
        src, dst = random.sample(node_ids, 2)
        routing_result = engine.compute_phase_aware_routing(src, dst, beta=0.5)
        print(f"   Phase-Aware Routing: {src} → {dst}")
        print(f"      Path: {' → '.join(routing_result.path)}")
        print(f"      Total Cost: {routing_result.total_cost:.4f}")
        print(f"      Phase Cost: {routing_result.phase_cost:.4f}")
        print(f"      Latency Cost: {routing_result.latency_cost:.4f}")
        results.append({
            "scenario": "phase_aware_routing",
            "success": len(routing_result.path) > 1,
            "path": routing_result.path,
            "cost": routing_result.total_cost
        })
    
    # سناریو ۴: خرابی زنجیره‌ای
    print("\n" + "-"*50)
    # بازسازی شبکه
    layer.create_network(num_nodes=20, topology="complete")
    for _ in range(200):
        layer.step()
    
    result4 = engine.simulate_cascade_failure(initial_failure=2, max_failures=8)
    results.append(result4)
    print(f"   Cascade Failure: success={result4['success']}, num_failures={result4['num_failures']}, final_R={result4['final_R']:.4f}")
    
    # ۶. گزارش نهایی
    print("\n" + "="*70)
    print("📊 KUMA-003 FINAL REPORT")
    print("="*70)
    
    print(f"\n{'Scenario':<25} | {'Success':<10} | {'Key Metric':<25}")
    print("-"*65)
    
    for r in results:
        if "scenario" not in r:
            continue
        
        key_metric = ""
        if r["scenario"] == "multiple_node_drop":
            key_metric = f"recovery={r.get('recovery_time', 'N/A')}s, R={r.get('final_R', 0):.3f}"
        elif r["scenario"] == "topology_comparison":
            best = max(r.items(), key=lambda x: x[1].get("final_R", 0) if isinstance(x[1], dict) else 0)
            key_metric = f"best={best[0]}, R={best[1]['final_R']:.3f}" if isinstance(best[1], dict) else ""
        elif r["scenario"] == "phase_aware_routing":
            key_metric = f"path={len(r.get('path', []))} nodes, cost={r.get('cost', 0):.3f}"
        elif r["scenario"] == "cascade_failure":
            key_metric = f"failures={r.get('num_failures', 0)}, final_R={r.get('final_R', 0):.3f}"
        
        status = "✅" if r.get("success", False) else "❌"
        name = r.get("scenario", "unknown")
        print(f"{name:<25} | {status:<10} | {key_metric:<25}")
    
    print("\n" + "="*70)
    print("🏁 KUMA-003 Test Complete")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_kuma_003_tests()
