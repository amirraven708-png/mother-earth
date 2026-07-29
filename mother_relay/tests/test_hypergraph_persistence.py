#!/usr/bin/env python3
"""
test_hypergraph_persistence.py
Test that Hypergraph maintains credibility after node failure
"""

import sys
import os
import random
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from mother_relay.consensus.star_consensus import StarConsensus
from mother_relay.consensus.integration import StarConsensusIntegration


class MockBubbleDB:
    def __init__(self, node_id: str, phase: float = 0.5, heat: float = 0.3):
        self.node_id = node_id
        self._phase = phase
        self._heat = heat
        self._records = 100
        self._migration = 0
        self._tick = 0
        self._alive = True
    
    def get_stats(self):
        return {
            "avg_phase": self._phase,
            "avg_heat": self._heat,
            "total_records": self._records,
            "migration_stats": {},
            "tick_count": self._tick
        }
    
    def tick(self):
        self._tick += 1
    
    def set_alive(self, alive: bool):
        self._alive = alive


def test_persistence():
    print("\n" + "="*70)
    print("🧪 TEST: Hypergraph Persistence (Credibility survives node failure)")
    print("="*70)
    
    # Setup 5 nodes with slightly different phases
    configs = [
        ("Node_0", 0.5, 0.3),
        ("Node_1", 0.52, 0.4),
        ("Node_2", 0.1, 0.8),
        ("Node_3", 0.12, 0.7),
        ("Node_4", 0.48, 0.35),
    ]
    
    nodes = []
    consensus = StarConsensus(credibility_threshold=0.6, window_size=8)
    integration = None
    
    for i, (nid, phase, heat) in enumerate(configs):
        node = MockBubbleDB(nid, phase, heat)
        nodes.append(node)
        if i == 0:
            integration = StarConsensusIntegration(node, consensus)
    
    # Phase 1: Build credibility (10 rounds)
    print("\n📌 Phase 1: Building credibility...")
    for round_num in range(1, 11):
        stars = {}
        for node in nodes:
            state = integration.collect_node_state(node.node_id)
            star = integration.consensus.draw_star(state)
            stars[node.node_id] = star
            integration.consensus.receive_star(node.node_id, star)
            node.tick()
        
        network_state = integration.validate_network_state(stars)
        if round_num % 3 == 0:
            print(f"  Round {round_num}: cred={network_state.credibility:.2f}, consensus={network_state.consensus}")
    
    # Store initial health
    initial_health = integration.health_check()
    print(f"\n  Initial Health: {initial_health}")
    
    # Phase 2: Simulate node failure (Node_2 goes down)
    print("\n📌 Phase 2: Node_2 failure...")
    nodes[2].set_alive(False)
    
    # Remove Node_2 from consensus cache
    if "Node_2" in integration.consensus._star_cache:
        del integration.consensus._star_cache["Node_2"]
    
    # Run 5 more rounds without Node_2
    for round_num in range(11, 16):
        stars = {}
        for node in nodes:
            if node._alive:
                state = integration.collect_node_state(node.node_id)
                star = integration.consensus.draw_star(state)
                stars[node.node_id] = star
                integration.consensus.receive_star(node.node_id, star)
            node.tick()
        
        network_state = integration.validate_network_state(stars)
        print(f"  Round {round_num}: cred={network_state.credibility:.2f}, consensus={network_state.consensus}")
    
    # Phase 3: Recover Node_2
    print("\n📌 Phase 3: Node_2 recovery...")
    nodes[2].set_alive(True)
    nodes[2]._phase = 0.1  # restore original phase
    
    # Run 5 more rounds with Node_2 back
    for round_num in range(16, 21):
        stars = {}
        for node in nodes:
            if node._alive:
                state = integration.collect_node_state(node.node_id)
                star = integration.consensus.draw_star(state)
                stars[node.node_id] = star
                integration.consensus.receive_star(node.node_id, star)
            node.tick()
        
        network_state = integration.validate_network_state(stars)
        print(f"  Round {round_num}: cred={network_state.credibility:.2f}, consensus={network_state.consensus}")
    
    # Final health
    final_health = integration.health_check()
    print(f"\n📊 Final Health: {final_health}")
    
    # Check cluster summary
    cluster_summary = integration.get_cluster_summary()
    print(f"\n📊 Final Cluster Summary: {cluster_summary}")
    
    # Test passed if credibility recovered after failure
    passed = final_health["credibility"] > 0.6 and final_health["healthy"] == True
    print(f"\n{'✅' if passed else '⚠️'} Persistence Test {'PASSED' if passed else 'needs review'}")
    return passed


if __name__ == "__main__":
    test_persistence()
    print("\n🏁 Test complete.")
