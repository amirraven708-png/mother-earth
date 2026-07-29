#!/usr/bin/env python3
"""
test_integration_hypergraph.py
Test Integration with Hypergraph Clusters (multiple rounds)
"""

import sys
import os
import random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from mother_relay.consensus.star_consensus import StarConsensus
from mother_relay.consensus.integration import StarConsensusIntegration


class MockBubbleDB:
    def __init__(self, node_id: str, initial_phase: float = 0.5, heat: float = 0.3,
                 records: int = 100, migration: int = 0):
        self.node_id = node_id
        self._phase = initial_phase
        self._heat = heat
        self._records = records
        self._migration_count = migration
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


def test_hypergraph_integration():
    print("\n" + "="*70)
    print("🧪 TEST: Integration with Hypergraph Clusters (multiple rounds)")
    print("="*70)

    # Setup: 5 nodes with distinct phases and heat values
    nodes_config = [
        ("Node_0", 0.5, 0.3, 100, 5),
        ("Node_1", 0.52, 0.4, 120, 3),
        ("Node_2", 0.1, 0.8, 200, 10),
        ("Node_3", 0.12, 0.7, 180, 8),
        ("Node_4", 0.48, 0.35, 110, 4),
    ]
    
    nodes = []
    consensus = StarConsensus(
        emergency_threshold=0.15,
        min_nodes=3,
        credibility_threshold=0.6,
        window_size=10
    )
    integration = None
    
    # Create nodes and integration with first node
    for i, (nid, phase, heat, records, mig) in enumerate(nodes_config):
        node = MockBubbleDB(nid, phase, heat, records, mig)
        nodes.append(node)
        if i == 0:
            integration = StarConsensusIntegration(node, consensus)
    
    # Run multiple rounds to build credibility
    rounds = 6
    for round_num in range(1, rounds + 1):
        print(f"\n--- Round {round_num} ---")
        stars = {}
        
        # Each node draws its star (with distinct states)
        for node in nodes:
            state = integration.collect_node_state(node.node_id)
            star = integration.consensus.draw_star(state)
            stars[node.node_id] = star
            integration.consensus.receive_star(node.node_id, star)
            node.tick()
        
        # Validate network state (builds clusters)
        network_state = integration.validate_network_state(stars)
        
        print(f"  Consensus: {network_state.consensus}, Credibility: {network_state.credibility:.2f}, Max Dist: {network_state.max_distance:.3f}")
        
        # Show clusters after enough rounds
        if round_num == rounds:
            clusters = integration.get_clusters()
            print(f"\n  📊 Final Clusters ({len(clusters)}):")
            for c in clusters:
                print(f"    {c.id}: size={len(c.nodes)}, nodes={list(c.nodes)}")
            
            print("\n  📌 Testing mutations from different nodes:")
            for node_id in ["Node_0", "Node_2"]:
                proposal = {
                    "id": f"mut_{node_id}",
                    "node_id": node_id,
                    "type": "test",
                    "params": {"value": random.randint(1, 100)}
                }
                result = integration.authorize_mutation(proposal, network_state)
                cluster = integration.get_cluster_for_node(node_id)
                print(f"    {node_id}: cluster={cluster.id if cluster else 'none'}, "
                      f"approved={result['approved']}, reason={result.get('reason', 'ok')}")
    
    print("\n📈 Final Cluster Summary:")
    print(integration.get_cluster_summary())
    
    health = integration.health_check()
    print(f"\n💚 Health Check: {health}")
    
    # Expect at least 2 clusters and healthy system
    return len(integration.get_clusters()) >= 2 and health["healthy"]


if __name__ == "__main__":
    success = test_hypergraph_integration()
    print(f"\n{'✅' if success else '⚠️'} Test {'PASSED' if success else 'needs review'}")
    print("🏁 Test complete.")
