#!/usr/bin/env python3
"""
kuma_003_1_routing_fix.py
اصلاح مسیریابی فاز-آگاه KUMA-003

تغییرات:
  ۱. تبدیل گراف به بدون‌جهت (undirected) برای مسیریابی
  ۲. اصلاح بازسازی مسیر Dijkstra
  ۳. اضافه کردن Local Coherence Cost به هزینه مسیر
  ۴. تست routing روی توپولوژی‌های مختلف

Cost_ij = L_ij + β * |θ_i - θ_j| + γ * (1 - R_local)
"""

import numpy as np
import math
import random
import heapq
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

# ========================== ۱. واردات ==========================

try:
    from mother_intelligence.wave_synchronization_layer import WaveSynchronizationLayer
    from mother_intelligence.kuramoto_engine import KuramotoEngine, OscillatorNode, PhaseState, PhaseLink
except ImportError:
    from wave_synchronization_layer import WaveSynchronizationLayer
    from kuramoto_engine import KuramotoEngine, OscillatorNode, PhaseState, PhaseLink

# ========================== ۲. مدل‌های داده ==========================

@dataclass
class RoutingResult:
    """نتیجه مسیریابی فاز-آگاه"""
    path: List[str]
    total_cost: float
    phase_cost: float
    latency_cost: float
    coherence_cost: float
    success: bool
    selected_paths: List[List[str]]

# ========================== ۳. موتور مسیریابی اصلاح‌شده ==========================

class PhaseAwareRouter:
    """
    مسیریاب فاز-آگاه با گراف بدون‌جهت و هزینه‌های محلی
    """
    
    def __init__(self, layer: WaveSynchronizationLayer, beta: float = 0.5, gamma: float = 0.3):
        self.layer = layer
        self.beta = beta
        self.gamma = gamma
    
    def _get_phases(self) -> Dict[str, float]:
        """دریافت فازهای فعلی نودها"""
        return {node.id: node.phase_state.phase for node in self.layer._topology.nodes}
    
    def _get_local_coherence(self, node_id: str) -> float:
        """محاسبه هم‌نوایی محلی یک نود با همسایگانش"""
        # پیدا کردن همسایگان
        neighbors = []
        for link in self.layer._topology.links:
            if link.source == node_id:
                neighbors.append(link.target)
            elif link.target == node_id:
                neighbors.append(link.source)
        
        if not neighbors:
            return 0.5
        
        # فاز نود
        phases = self._get_phases()
        node_phase = phases.get(node_id, 0)
        
        # میانگین اختلاف فاز با همسایگان
        diffs = []
        for n in neighbors:
            if n in phases:
                diff = phases[n] - node_phase
                diff = math.atan2(math.sin(diff), math.cos(diff))
                diffs.append(abs(diff))
        
        if not diffs:
            return 0.5
        
        avg_diff = sum(diffs) / len(diffs)
        # تبدیل به coherence (هرچه اختلاف کمتر، coherence بالاتر)
        return max(0, 1 - avg_diff / math.pi)
    
    def compute_routing(self, source: str, target: str) -> RoutingResult:
        """
        محاسبه مسیر بهینه با گراف بدون‌جهت
        
        Args:
            source: شناسه نود مبدأ
            target: شناسه نود مقصد
        """
        if source == target:
            return RoutingResult(
                path=[source],
                total_cost=0,
                phase_cost=0,
                latency_cost=0,
                coherence_cost=0,
                success=True,
                selected_paths=[[source]]
            )
        
        # دریافت فازها
        phases = self._get_phases()
        
        # ایجاد گراف بدون‌جهت
        graph = defaultdict(list)
        for link in self.layer._topology.links:
            # جهت‌های دوطرفه
            for src, dst in [(link.source, link.target), (link.target, link.source)]:
                if src not in phases or dst not in phases:
                    continue
                
                # ۱. اختلاف فاز
                phase_diff = phases[dst] - phases[src]
                phase_diff = math.atan2(math.sin(phase_diff), math.cos(phase_diff))
                phase_cost = abs(phase_diff)
                
                # ۲. تأخیر
                latency = link.phase_delay
                
                # ۳. هم‌نوایی محلی (coherence)
                local_coherence = self._get_local_coherence(dst)
                coherence_cost = 1 - local_coherence
                
                # ۴. هزینه کل
                total_cost = latency + self.beta * phase_cost + self.gamma * coherence_cost
                
                graph[src].append({
                    "target": dst,
                    "cost": total_cost,
                    "latency": latency,
                    "phase_diff": phase_diff,
                    "coherence": local_coherence
                })
        
        # اگر گراف خالی است
        if not graph:
            return RoutingResult(
                path=[],
                total_cost=float('inf'),
                phase_cost=float('inf'),
                latency_cost=float('inf'),
                coherence_cost=float('inf'),
                success=False,
                selected_paths=[]
            )
        
        # Dijkstra
        distances = {node.id: float('inf') for node in self.layer._topology.nodes}
        distances[source] = 0
        predecessors = {node.id: None for node in self.layer._topology.nodes}
        cost_details = {node.id: {"latency": 0, "phase": 0, "coherence": 0} for node in self.layer._topology.nodes}
        
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
                    cost_details[neighbor["target"]] = {
                        "latency": cost_details[node]["latency"] + neighbor["latency"],
                        "phase": cost_details[node]["phase"] + neighbor["phase_diff"],
                        "coherence": cost_details[node]["coherence"] + (1 - neighbor["coherence"])
                    }
                    heapq.heappush(pq, (new_dist, neighbor["target"]))
        
        # بررسی وجود مسیر
        if predecessors[target] is None:
            return RoutingResult(
                path=[],
                total_cost=float('inf'),
                phase_cost=float('inf'),
                latency_cost=float('inf'),
                coherence_cost=float('inf'),
                success=False,
                selected_paths=[]
            )
        
        # بازسازی مسیر
        path = []
        current = target
        while current is not None:
            path.append(current)
            current = predecessors[current]
        path.reverse()
        
        return RoutingResult(
            path=path,
            total_cost=distances[target],
            phase_cost=cost_details[target]["phase"],
            latency_cost=cost_details[target]["latency"],
            coherence_cost=cost_details[target]["coherence"],
            success=True,
            selected_paths=[path]
        )
    
    def test_all_topologies(self, topologies: List[str] = ["complete", "small_world", "sparse", "ring"]) -> Dict:
        """
        تست مسیریابی روی توپولوژی‌های مختلف
        """
        results = {}
        
        for topo_type in topologies:
            print(f"   Testing routing on {topo_type}...")
            
            # ایجاد توپولوژی
            from kuma_003_adaptive_topology import TopologyConfig, create_topology
            config = TopologyConfig(topology_type=topo_type, num_nodes=20)
            nodes, links = create_topology(config)
            
            # بازسازی لایه
            self.layer._topology.nodes = nodes
            self.layer._topology.links = links
            
            # همگام‌سازی اولیه
            for _ in range(100):
                self.layer.step()
            
            # انتخاب دو نود تصادفی
            node_ids = [n.id for n in nodes]
            if len(node_ids) < 2:
                results[topo_type] = {"success": False, "error": "Not enough nodes"}
                continue
            
            src, dst = random.sample(node_ids, 2)
            
            # مسیریابی
            result = self.compute_routing(src, dst)
            
            results[topo_type] = {
                "success": result.success,
                "path_length": len(result.path) if result.path else 0,
                "cost": result.total_cost,
                "source": src,
                "target": dst
            }
            
            if result.success:
                print(f"      {src} → {dst}: path={' → '.join(result.path[:5])}{'...' if len(result.path)>5 else ''}, cost={result.total_cost:.3f}")
            else:
                print(f"      {src} → {dst}: ❌ No path found")
        
        return results

# ========================== ۴. تست جامع ==========================

def run_routing_fix_test():
    """
    اجرای تست اصلاح مسیریابی
    """
    print("\n" + "="*70)
    print("🧪 KUMA-003.1: Routing Fix — Phase-Aware Routing Test")
    print("="*70 + "\n")
    
    # ۱. ایجاد شبکه پایه
    print("📡 Creating base network with 20 nodes (complete topology)...")
    layer = WaveSynchronizationLayer(
        coupling_strength=2.5,
        dt=0.01,
        damping_factor=0.15
    )
    layer.create_network(num_nodes=20, topology="complete")
    
    # همگام‌سازی
    print("⏳ Initial synchronization (200 steps)...")
    for _ in range(200):
        layer.step()
    
    initial_status = layer.get_network_status()
    print(f"   Initial R = {initial_status['order_parameter']:.4f}")
    
    # ۲. ایجاد مسیریاب
    router = PhaseAwareRouter(layer, beta=0.5, gamma=0.3)
    
    # ۳. تست روی توپولوژی‌های مختلف
    print("\n📊 Testing routing on different topologies...")
    results = router.test_all_topologies(["complete", "small_world", "sparse", "ring"])
    
    # ۴. تست مسیریابی محلی
    print("\n" + "-"*50)
    print("🔍 Detailed routing test on complete topology...")
    
    node_ids = [n.id for n in layer._topology.nodes]
    src, dst = random.sample(node_ids, 2)
    result = router.compute_routing(src, dst)
    
    if result.success:
        print(f"   {src} → {dst}")
        print(f"      Path: {' → '.join(result.path)}")
        print(f"      Total Cost: {result.total_cost:.4f}")
        print(f"      Latency Cost: {result.latency_cost:.4f}")
        print(f"      Phase Cost: {result.phase_cost:.4f}")
        print(f"      Coherence Cost: {result.coherence_cost:.4f}")
    else:
        print(f"   ❌ No path found from {src} to {dst}")
    
    # ۵. گزارش نهایی
    print("\n" + "="*70)
    print("📊 KUMA-003.1 ROUTING FIX REPORT")
    print("="*70)
    
    print(f"\n{'Topology':<15} | {'Success':<10} | {'Path Length':<15} | {'Cost':<12}")
    print("-"*60)
    
    for topo, data in results.items():
        status = "✅" if data.get("success", False) else "❌"
        path_len = data.get("path_length", 0)
        cost = data.get("cost", float('inf'))
        cost_str = f"{cost:.3f}" if cost != float('inf') else "∞"
        print(f"{topo:<15} | {status:<10} | {path_len:<15} | {cost_str:<12}")
    
    print("\n" + "="*70)
    print("🏁 KUMA-003.1 Routing Fix Complete")
    print("="*70 + "\n")
    
    return results

if __name__ == "__main__":
    run_routing_fix_test()
