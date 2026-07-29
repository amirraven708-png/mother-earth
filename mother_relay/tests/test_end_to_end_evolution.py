#!/usr/bin/env python3
"""
test_end_to_end_evolution.py
Unified Evolution Loop Test: Drift → Consensus → Mutation → Fitness → Recovery
"""

import sys
import os
import random
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from mother_relay.consensus.star_consensus import StarConsensus
from mother_relay.consensus.integration import StarConsensusIntegration
from mother_relay.evolution.star_memory import StarEvolutionMemory, StarRecord


class MockBubbleDB:
    def __init__(self, node_id: str, phase: float = 0.5, heat: float = 0.3):
        self.node_id = node_id
        self._phase = phase
        self._heat = heat
        self._records = 100
        self._migration = 0
        self._tick = 0
        self._alive = True
        self._params = {"base_value": 1.0}
    
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
    
    def apply_drift(self, drift: float):
        self._phase = (self._phase + drift) % 1.0
    
    def set_alive(self, alive: bool):
        self._alive = alive
    
    def mutate(self, new_value: float):
        self._params["base_value"] = new_value


class SimpleSandbox:
    """Simulate mutation effects on system state"""
    def run(self, proposal: dict, current_state: dict) -> dict:
        # Simulate that mutation improves stability if value < 2.0
        value = proposal.get("params", {}).get("value", 1.0)
        stability = 1.0 - abs(value - 1.0) / 10.0
        return {
            "stability": max(0, stability),
            "energy_cost": 0.5 + abs(value - 1.0) * 0.1,
            "adaptability": 0.5 + (1.0 - abs(value - 1.0) / 5.0)
        }


class SimpleEvaluator:
    def calculate_fitness(self, simulated_state: dict) -> float:
        stability = simulated_state.get("stability", 0.5)
        adaptability = simulated_state.get("adaptability", 0.5)
        energy = simulated_state.get("energy_cost", 1.0)
        fitness = (stability * 0.4 + adaptability * 0.3 + (1.0/energy) * 0.3)
        return fitness


def test_unified_evolution():
    print("\n" + "="*70)
    print("🧪 TEST: Unified Evolution Loop")
    print("   Drift → Consensus → Mutation → Fitness → Recovery")
    print("="*70)

    # 1. Setup network
    node_configs = [
        ("Node_0", 0.5, 0.3),
        ("Node_1", 0.52, 0.4),
        ("Node_2", 0.1, 0.8),
        ("Node_3", 0.12, 0.7),
        ("Node_4", 0.48, 0.35),
    ]
    
    nodes = []
    consensus = StarConsensus(credibility_threshold=0.6, window_size=10)
    integration = None
    memory = StarEvolutionMemory()
    
    for i, (nid, phase, heat) in enumerate(node_configs):
        node = MockBubbleDB(nid, phase, heat)
        nodes.append(node)
        if i == 0:
            integration = StarConsensusIntegration(node, consensus)
            integration.memory = memory  # attach memory
    
    sandbox = SimpleSandbox()
    evaluator = SimpleEvaluator()
    
    evolution_history = []
    
    # 2. Phase 1: Build credibility (10 rounds)
    print("\n📌 Phase 1: Building credibility...")
    stars = {}
    for round_num in range(1, 11):
        for node in nodes:
            if node._alive:
                state = integration.collect_node_state(node.node_id)
                star = integration.consensus.draw_star(state)
                stars[node.node_id] = star
                integration.consensus.receive_star(node.node_id, star)
                node.tick()
        
        network_state = integration.validate_network_state(stars)
        if round_num % 3 == 0:
            print(f"  Round {round_num}: cred={network_state.credibility:.2f}, consensus={network_state.consensus}")
    
    print(f"\n  Initial Health: {integration.health_check()}")
    
    # 3. Phase 2: Introduce drift (divergent)
    print("\n📌 Phase 2: Divergent drift (nodes move apart)...")
    for round_num in range(11, 16):
        for node in nodes:
            if node._alive:
                node.apply_drift(random.uniform(-0.03, 0.03))
                state = integration.collect_node_state(node.node_id)
                star = integration.consensus.draw_star(state)
                stars[node.node_id] = star
                integration.consensus.receive_star(node.node_id, star)
                node.tick()
        
        network_state = integration.validate_network_state(stars)
        print(f"  Round {round_num}: cred={network_state.credibility:.2f}, consensus={network_state.consensus}")
    
    # 4. Phase 3: Propose mutation
    print("\n📌 Phase 3: Proposing mutation...")
    mutation_proposal = {
        "id": "mut_001",
        "node_id": "Node_0",
        "type": "parameter_tuning",
        "params": {"value": 1.5}
    }
    
    # Get current network state
    network_state = integration.validate_network_state(stars)
    
    # Authorize mutation
    auth_result = integration.authorize_mutation(mutation_proposal, network_state)
    print(f"  Mutation authorization: {auth_result['approved']}, reason={auth_result.get('reason', 'ok')}")
    
    # 5. Phase 4: Apply mutation in sandbox
    if auth_result["approved"]:
        print("\n📌 Phase 4: Testing mutation in sandbox...")
        current_state = {"stability": 0.8, "energy_cost": 0.5, "adaptability": 0.7}
        simulated = sandbox.run(auth_result["proposal"], current_state)
        fitness = evaluator.calculate_fitness(simulated)
        print(f"  Simulated state: {simulated}")
        print(f"  Fitness: {fitness:.3f}")
        
        # 6. Record in evolution memory
        integration.record_mutation_result(auth_result["proposal"], "accepted" if fitness > 0.7 else "rejected", fitness)
        memory.add_from_proposal(auth_result["proposal"], "accepted" if fitness > 0.7 else "rejected", fitness)
        
        # 7. Apply to system if fitness is good
        if fitness > 0.7:
            print("\n📌 Phase 5: Applying mutation to system...")
            nodes[0].mutate(1.5)
            print("  Mutation applied successfully!")
            evolution_history.append({"mutation": "mut_001", "fitness": fitness, "result": "accepted"})
        else:
            print("\n📌 Phase 5: Mutation rejected (low fitness)")
            evolution_history.append({"mutation": "mut_001", "fitness": fitness, "result": "rejected"})
    else:
        print("\n❌ Mutation rejected by consensus")
    
    # 8. Phase 6: Recover after divergence
    print("\n📌 Phase 6: Recovering network...")
    for round_num in range(16, 21):
        # Reduce drift to near zero
        for node in nodes:
            if node._alive:
                node.apply_drift(random.uniform(-0.005, 0.005))
                state = integration.collect_node_state(node.node_id)
                star = integration.consensus.draw_star(state)
                stars[node.node_id] = star
                integration.consensus.receive_star(node.node_id, star)
                node.tick()
        
        network_state = integration.validate_network_state(stars)
        print(f"  Round {round_num}: cred={network_state.credibility:.2f}, consensus={network_state.consensus}")
    
    # 9. Final health check
    final_health = integration.health_check()
    cluster_summary = integration.get_cluster_summary()
    
    print("\n" + "="*70)
    print("📊 FINAL SYSTEM STATE")
    print("="*70)
    print(f"  Health: {final_health}")
    print(f"  Cluster Summary: {cluster_summary}")
    print(f"  Evolution History: {evolution_history}")
    
    # 10. Memory stats
    memory_stats = memory.get_stats()
    print(f"  Evolution Memory: {memory_stats}")
    
    # 11. Check if system survived drift and maintained credibility
    passed = (final_health["healthy"] and 
              final_health["credibility"] > 0.6 and
              len(evolution_history) > 0)
    
    print(f"\n{'✅' if passed else '⚠️'} Evolution Loop Test {'PASSED' if passed else 'needs review'}")
    return passed


if __name__ == "__main__":
    test_unified_evolution()
    print("\n🏁 End-to-End Evolution test complete.")
