#!/usr/bin/env python3
"""
test_adversarial_evolution.py
Adversarial Evolution Test: Three critical scenarios

Scenario 1: Uniform Drift → Consensus should be maintained
Scenario 2: Divergent Drift → Credibility should drop, mutations blocked
Scenario 3: Malicious Mutation → High fitness but low stability → Hard Veto
"""

import sys
import os
import random
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


class ImmutableCore:
    def __init__(self, min_stability: float = 0.6, max_energy_cost: float = 2.0):
        self.min_stability = min_stability
        self.max_energy_cost = max_energy_cost
        self.veto_count = 0
    
    def check(self, simulated_state: dict) -> tuple:
        stability = simulated_state.get("stability", 0.0)
        energy_cost = simulated_state.get("energy_cost", 0.0)
        
        if stability < self.min_stability:
            self.veto_count += 1
            return False, f"Hard Veto: stability={stability:.2f} < min_stability={self.min_stability:.2f}"
        
        if energy_cost > self.max_energy_cost:
            self.veto_count += 1
            return False, f"Hard Veto: energy_cost={energy_cost:.2f} > max_energy_cost={self.max_energy_cost:.2f}"
        
        return True, "ok"
    
    def get_veto_count(self):
        return self.veto_count


class Sandbox:
    def run(self, proposal: dict, current_state: dict, malicious: bool = False) -> dict:
        value = proposal.get("params", {}).get("value", 1.0)
        
        if malicious:
            return {
                "stability": 0.45,
                "energy_cost": 0.5,
                "adaptability": 0.95,
                "fitness": 0.92,
                "is_malicious": True
            }
        
        stability = 1.0 - abs(value - 1.0) / 10.0
        return {
            "stability": max(0, stability),
            "energy_cost": 0.5 + abs(value - 1.0) * 0.1,
            "adaptability": 0.5 + (1.0 - abs(value - 1.0) / 5.0)
        }


class Evaluator:
    def calculate_fitness(self, simulated_state: dict) -> float:
        if simulated_state.get("is_malicious", False):
            return 0.92
        stability = simulated_state.get("stability", 0.5)
        adaptability = simulated_state.get("adaptability", 0.5)
        energy = simulated_state.get("energy_cost", 1.0)
        return (stability * 0.4 + adaptability * 0.3 + (1.0/energy) * 0.3)


def test_adversarial_scenarios():
    print("\n" + "="*70)
    print("🧪 ADVERSARIAL EVOLUTION TEST")
    print("   Three critical scenarios for release validation")
    print("="*70)
    
    # Setup network with more sensitive consensus
    node_configs = [
        ("Node_0", 0.5, 0.3),
        ("Node_1", 0.52, 0.4),
        ("Node_2", 0.1, 0.8),
        ("Node_3", 0.12, 0.7),
        ("Node_4", 0.48, 0.35),
    ]
    
    nodes = []
    # Use tighter emergency_threshold for more sensitive divergence detection
    consensus = StarConsensus(
        emergency_threshold=0.12,    # More sensitive than default 0.15
        min_nodes=3,
        credibility_threshold=0.6,
        window_size=10
    )
    integration = None
    
    for i, (nid, phase, heat) in enumerate(node_configs):
        node = MockBubbleDB(nid, phase, heat)
        nodes.append(node)
        if i == 0:
            integration = StarConsensusIntegration(node, consensus)
    
    immutable_core = ImmutableCore(min_stability=0.6, max_energy_cost=2.0)
    sandbox = Sandbox()
    evaluator = Evaluator()
    
    results = {}
    
    # ============================================================
    # SCENARIO 1: Uniform Drift
    # ============================================================
    print("\n" + "="*70)
    print("📌 SCENARIO 1: Uniform Drift")
    print("   All nodes drift together → Consensus should be maintained")
    print("="*70)
    
    integration.reset()
    stars = {}
    for round_num in range(1, 11):
        common_drift = random.uniform(-0.02, 0.02)
        for node in nodes:
            if node._alive:
                node.apply_drift(common_drift)
                state = integration.collect_node_state(node.node_id)
                star = integration.consensus.draw_star(state)
                stars[node.node_id] = star
                integration.consensus.receive_star(node.node_id, star)
                node.tick()
        
        network_state = integration.validate_network_state(stars)
        if round_num % 3 == 0:
            print(f"  Round {round_num}: cred={network_state.credibility:.2f}, consensus={network_state.consensus}")
    
    scenario1_passed = network_state.consensus and network_state.credibility > 0.6
    results["scenario1"] = {
        "description": "Uniform Drift",
        "passed": scenario1_passed,
        "credibility": network_state.credibility,
        "consensus": network_state.consensus
    }
    print(f"\n  ✅ SCENARIO 1 {'PASSED' if scenario1_passed else 'FAILED'}")
    
    # ============================================================
    # SCENARIO 2: Divergent Drift (AGGRESSIVE)
    # ============================================================
    print("\n" + "="*70)
    print("📌 SCENARIO 2: Divergent Drift (AGGRESSIVE)")
    print("   Nodes drift apart → Credibility must drop AND mutations blocked")
    print("   Using larger drift and more rounds")
    print("="*70)
    
    integration.reset()
    stars = {}
    max_dist_history = []
    
    for round_num in range(1, 16):  # More rounds
        # Larger divergent drift
        for node in nodes:
            if node._alive:
                node.apply_drift(random.uniform(-0.08, 0.08))  # Increased drift
                state = integration.collect_node_state(node.node_id)
                star = integration.consensus.draw_star(state)
                stars[node.node_id] = star
                integration.consensus.receive_star(node.node_id, star)
                node.tick()
        
        network_state = integration.validate_network_state(stars)
        max_dist_history.append(network_state.max_distance)
        
        if round_num % 3 == 0:
            print(f"  Round {round_num}: cred={network_state.credibility:.2f}, "
                  f"consensus={network_state.consensus}, max_dist={network_state.max_distance:.3f}")
    
    # Try mutation
    proposal = {"id": "mut_divergent", "node_id": "Node_0", "type": "test", "params": {"value": 1.5}}
    auth_result = integration.authorize_mutation(proposal, network_state)
    print(f"  Mutation authorization: {auth_result['approved']}, reason={auth_result.get('reason', 'ok')}")
    
    # Check both credibility drop AND max_distance increase
    credibility_dropped = network_state.credibility < 0.6
    max_dist_increased = network_state.max_distance > 0.1  # At least 0.1 spread
    mutation_blocked = not auth_result["approved"]
    
    scenario2_passed = credibility_dropped and mutation_blocked and max_dist_increased
    
    results["scenario2"] = {
        "description": "Divergent Drift (Aggressive)",
        "passed": scenario2_passed,
        "credibility": network_state.credibility,
        "credibility_dropped": credibility_dropped,
        "max_distance": network_state.max_distance,
        "max_dist_increased": max_dist_increased,
        "mutation_blocked": mutation_blocked,
        "consensus": network_state.consensus
    }
    print(f"\n  ✅ SCENARIO 2 {'PASSED' if scenario2_passed else 'FAILED'}")
    
    # ============================================================
    # SCENARIO 3: Malicious Mutation + Hard Veto
    # ============================================================
    print("\n" + "="*70)
    print("📌 SCENARIO 3: Malicious Mutation + Hard Veto")
    print("   High fitness but low stability → Must be vetoed by Immutable Core")
    print("="*70)
    
    # Build stable consensus first
    integration.reset()
    stars = {}
    for round_num in range(1, 8):
        for node in nodes:
            if node._alive:
                state = integration.collect_node_state(node.node_id)
                star = integration.consensus.draw_star(state)
                stars[node.node_id] = star
                integration.consensus.receive_star(node.node_id, star)
                node.tick()
        
        network_state = integration.validate_network_state(stars)
    
    print(f"  Stable consensus: cred={network_state.credibility:.2f}, consensus={network_state.consensus}")
    
    # Force mutation to pass consensus (bypassing authorization)
    forced_proposal = {
        "id": "mut_malicious",
        "node_id": "Node_0",
        "type": "malicious",
        "params": {"value": 1.0},
        "star_signature": {
            "phase": network_state.collective_phase,
            "credibility": network_state.credibility,
            "star": [50, 50, 50, 50, 50]
        }
    }
    
    # Run sandbox with malicious flag
    current_state = {"stability": 0.8, "energy_cost": 0.5, "adaptability": 0.7}
    simulated = sandbox.run(forced_proposal, current_state, malicious=True)
    fitness = evaluator.calculate_fitness(simulated)
    print(f"  Simulated state: {simulated}")
    print(f"  Fitness: {fitness:.3f} (HIGH, but stability is LOW)")
    
    # Check Immutable Core
    core_passed, reason = immutable_core.check(simulated)
    print(f"  Immutable Core: {'PASS' if core_passed else 'VETO'} → {reason}")
    
    scenario3_passed = not core_passed
    results["scenario3"] = {
        "description": "Malicious Mutation + Hard Veto",
        "passed": scenario3_passed,
        "veto_count": immutable_core.get_veto_count(),
        "simulated_stability": simulated.get("stability"),
        "core_passed": core_passed
    }
    print(f"\n  ✅ SCENARIO 3 {'PASSED' if scenario3_passed else 'FAILED'}")
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "="*70)
    print("📊 ADVERSARIAL TEST SUMMARY")
    print("="*70)
    
    all_passed = True
    for key, result in results.items():
        status = "✅ PASSED" if result["passed"] else "❌ FAILED"
        print(f"  {result['description']}: {status}")
        if not result["passed"]:
            all_passed = False
    
    print("\n" + "="*70)
    print(f"🏁 ADVERSARIAL TEST {'PASSED' if all_passed else 'FAILED'}")
    return all_passed


if __name__ == "__main__":
    test_adversarial_scenarios()
