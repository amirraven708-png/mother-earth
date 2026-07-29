#!/usr/bin/env python3
"""
test_star_integration.py
Test Star Consensus Integration with mock BubbleDB and Evolution
"""

import sys
import os
import random
import threading
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from consensus.star_consensus import StarConsensus
from consensus.integration import StarConsensusIntegration, NetworkState


# ============================================================
# Mock Classes
# ============================================================

class MockBubbleDB:
    """Simplified BubbleDB mock for testing"""
    def __init__(self, node_id: str, initial_phase: float = 0.5):
        self.node_id = node_id
        self._phase = initial_phase
        self._heat = 0.3
        self._records = 100
        self._migration_count = 0
        self._tick = 0
        
    def get_stats(self):
        return {
            "avg_phase": self._phase,
            "avg_heat": self._heat,
            "total_records": self._records,
            "migration_stats": {f"m_{i}": 1 for i in range(self._migration_count)},
            "tick_count": self._tick
        }
    
    def tick(self):
        self._tick += 1
        # Simulate slight phase drift
        self._phase = (self._phase + random.uniform(-0.01, 0.01)) % 1.0
        
    def apply_drift(self, drift: float):
        self._phase = (self._phase + drift) % 1.0


class MockEvolutionCoordinator:
    """Mock evolution coordinator for testing mutation gating"""
    def __init__(self):
        self.history = []
    
    def propose_mutation(self, proposal: Dict) -> str:
        mutation_id = f"mut_{len(self.history):04d}"
        self.history.append({"id": mutation_id, "proposal": proposal})
        return mutation_id
    
    def get_history(self):
        return self.history


# ============================================================
# Test Functions
# ============================================================

def test_integration_uniform():
    """Test integration with uniform drift (should approve)"""
    print("\n" + "="*70)
    print("📌 TEST: Uniform Drift (should maintain credibility)")
    print("="*70)
    
    # Setup
    consensus = StarConsensus(emergency_threshold=0.15, min_nodes=3, credibility_threshold=0.6)
    nodes = [MockBubbleDB(f"Node_{i}", initial_phase=0.5 + (i-2)*0.02) for i in range(5)]
    integration = StarConsensusIntegration(nodes[0], consensus)
    
    # Simulate rounds
    stars = {}
    for round_num in range(1, 8):
        # Uniform drift: all nodes move together
        common_drift = random.uniform(-0.02, 0.02)
        for node in nodes:
            node.apply_drift(common_drift)
            node.tick()
        
        # Generate stars
        for node in nodes:
            state = integration.collect_node_state(node.node_id)
            star = integration.consensus.draw_star(state)
            stars[node.node_id] = star
            integration.consensus.receive_star(node.node_id, star)
        
        # Validate network state
        network_state = integration.validate_network_state(stars)
        
        print(f"Round {round_num}: consensus={network_state.consensus}, "
              f"cred={network_state.credibility:.2f}, max_dist={network_state.max_distance:.3f}")
        
        # Test mutation authorization
        proposal = {"id": f"mut_{round_num}", "type": "test", "params": {"value": round_num}}
        result = integration.authorize_mutation(proposal, network_state)
        print(f"   → Mutation approved: {result['approved']}, reason: {result.get('reason', 'ok')}")
    
    final_state = integration.health_check()
    print(f"\nHealth check: {final_state}")
    
    return final_state["healthy"]


def test_integration_divergent():
    """Test integration with divergent drift (should reject)"""
    print("\n" + "="*70)
    print("📌 TEST: Divergent Drift (should lose credibility)")
    print("="*70)
    
    consensus = StarConsensus(emergency_threshold=0.15, min_nodes=3, credibility_threshold=0.6)
    nodes = [MockBubbleDB(f"Node_{i}", initial_phase=0.5 + (i-2)*0.02) for i in range(5)]
    integration = StarConsensusIntegration(nodes[0], consensus)
    
    stars = {}
    for round_num in range(1, 8):
        # Divergent drift: each node moves independently
        for node in nodes:
            node.apply_drift(random.uniform(-0.05, 0.05))
            node.tick()
        
        for node in nodes:
            state = integration.collect_node_state(node.node_id)
            star = integration.consensus.draw_star(state)
            stars[node.node_id] = star
            integration.consensus.receive_star(node.node_id, star)
        
        network_state = integration.validate_network_state(stars)
        
        print(f"Round {round_num}: consensus={network_state.consensus}, "
              f"cred={network_state.credibility:.2f}, max_dist={network_state.max_distance:.3f}")
        
        proposal = {"id": f"mut_{round_num}", "type": "test", "params": {"value": round_num}}
        result = integration.authorize_mutation(proposal, network_state)
        print(f"   → Mutation approved: {result['approved']}, reason: {result.get('reason', 'ok')}")
    
    final_state = integration.health_check()
    print(f"\nHealth check: {final_state}")
    
    return final_state["healthy"]


def test_integration_recovery():
    """Test recovery after divergence"""
    print("\n" + "="*70)
    print("📌 TEST: Recovery after Divergence")
    print("="*70)
    
    consensus = StarConsensus(emergency_threshold=0.15, min_nodes=3, credibility_threshold=0.6)
    nodes = [MockBubbleDB(f"Node_{i}", initial_phase=0.5 + (i-2)*0.02) for i in range(5)]
    integration = StarConsensusIntegration(nodes[0], consensus)
    
    stars = {}
    
    # Phase 1: Divergent drift (8 rounds)
    print("\n   Phase 1: Diverging...")
    for round_num in range(1, 9):
        for node in nodes:
            node.apply_drift(random.uniform(-0.06, 0.06))
            node.tick()
        
        for node in nodes:
            state = integration.collect_node_state(node.node_id)
            star = integration.consensus.draw_star(state)
            stars[node.node_id] = star
            integration.consensus.receive_star(node.node_id, star)
        
        network_state = integration.validate_network_state(stars)
        print(f"   Round {round_num}: cred={network_state.credibility:.2f}, max_dist={network_state.max_distance:.3f}")
    
    # Phase 2: Recovery (uniform drift, low magnitude)
    print("\n   Phase 2: Recovering...")
    for round_num in range(1, 9):
        common_drift = random.uniform(-0.01, 0.01)
        for node in nodes:
            node.apply_drift(common_drift)
            node.tick()
        
        for node in nodes:
            state = integration.collect_node_state(node.node_id)
            star = integration.consensus.draw_star(state)
            stars[node.node_id] = star
            integration.consensus.receive_star(node.node_id, star)
        
        network_state = integration.validate_network_state(stars)
        print(f"   Round {round_num}: cred={network_state.credibility:.2f}, max_dist={network_state.max_distance:.3f}")
    
    final_state = integration.health_check()
    print(f"\nHealth check: {final_state}")
    
    return final_state["healthy"]


# ============================================================
# Main Execution
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧪 STAR CONSENSUS INTEGRATION TEST SUITE")
    print("="*70)
    
    results = []
    
    # Test 1: Uniform drift
    result1 = test_integration_uniform()
    results.append(("Uniform Drift", result1))
    
    # Test 2: Divergent drift
    result2 = test_integration_divergent()
    results.append(("Divergent Drift", result2))
    
    # Test 3: Recovery
    result3 = test_integration_recovery()
    results.append(("Recovery", result3))
    
    print("\n" + "="*70)
    print("📈 INTEGRATION TEST SUMMARY")
    print("="*70)
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {name}: {status}")
    
    print("\n" + "="*70)
    print("🏁 Integration tests complete.")
    print("="*70)
