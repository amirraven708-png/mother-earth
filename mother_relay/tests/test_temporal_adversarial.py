#!/usr/bin/env python3
"""
test_temporal_adversarial.py – Release Gate with Temporal Consensus
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from mother_relay.consensus.temporal_star import TemporalStarConsensus
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

    def apply_drift(self, drift: float):
        self._phase = (self._phase + drift) % 1.0

    def set_alive(self, alive: bool):
        self._alive = alive


class ImmutableCore:
    def __init__(self, min_stability: float = 0.6):
        self.min_stability = min_stability
        self.veto_count = 0

    def check(self, simulated_state: dict) -> tuple:
        stability = simulated_state.get("stability", 0.0)
        if stability < self.min_stability:
            self.veto_count += 1
            return False, f"Hard Veto: stability={stability:.2f} < {self.min_stability:.2f}"
        return True, "ok"


class Sandbox:
    def run(self, proposal: dict, current_state: dict, malicious: bool = False) -> dict:
        if malicious:
            return {"stability": 0.45, "energy_cost": 0.5, "adaptability": 0.95}
        return {"stability": 0.9, "energy_cost": 0.5, "adaptability": 0.8}


class Evaluator:
    def calculate_fitness(self, state: dict) -> float:
        return 0.92 if state.get("stability", 0) < 0.5 else 0.75


def test_temporal_adversarial():
    print("\n" + "="*70)
    print("🧪 TEMPORAL STAR CONSENSUS – ADVERSARIAL GATE")
    print("   3 scenarios with Temporal Phase Schedule")
    print("="*70)

    node_configs = [
        ("Node_0", 0.50, 0.3),
        ("Node_1", 0.52, 0.4),
        ("Node_2", 0.10, 0.8),
        ("Node_3", 0.12, 0.7),
        ("Node_4", 0.48, 0.35),
    ]

    nodes = []
    consensus = TemporalStarConsensus(emergency_threshold=0.12, min_nodes=3,
                                      credibility_threshold=0.6, window_size=10)
    integration = None

    for i, (nid, phase, heat) in enumerate(node_configs):
        node = MockBubbleDB(nid, phase, heat)
        nodes.append(node)
        if i == 0:
            integration = StarConsensusIntegration(node, consensus)

    immutable_core = ImmutableCore(min_stability=0.6)
    sandbox = Sandbox()
    evaluator = Evaluator()
    results = {}

    # ============================================================
    # SCENARIO 1: Uniform Drift
    # ============================================================
    print("\n📌 SCENARIO 1: Uniform Drift")
    for round_num in range(1, 11):
        common_drift = 0.02
        for node in nodes:
            node.apply_drift(common_drift)
            state = integration.collect_node_state(node.node_id)
            star = consensus.draw_temporal_star(state)
            consensus.receive_star(node.node_id, star)
            node.tick()

        status = consensus.get_consensus_status()
        if round_num % 3 == 0:
            print(f"  Round {round_num}: cred={status['credibility']:.2f}, score={status['score']:.3f}, consensus={status['consensus']}")

    scenario1_passed = status["consensus"] and status["credibility"] > 0.6
    results["scenario1"] = {"description": "Uniform Drift", "passed": scenario1_passed}

    # ============================================================
    # SCENARIO 2: Divergent Drift (deterministic)
    # ============================================================
    print("\n📌 SCENARIO 2: Divergent Drift")
    for node, (_, phase, _) in zip(nodes, node_configs):
        node._phase = phase
        node._tick = 0
    consensus.reset_tracker()
    consensus.clear_cache()

    divergent_drifts = {"Node_0": +0.12, "Node_1": -0.12, "Node_2": +0.18, "Node_3": -0.18, "Node_4": +0.10}

    for round_num in range(1, 11):
        for node in nodes:
            drift = divergent_drifts[node.node_id] * (round_num / 10.0)
            node.apply_drift(drift)
            state = integration.collect_node_state(node.node_id)
            star = consensus.draw_temporal_star(state)
            consensus.receive_star(node.node_id, star)
            node.tick()

        status = consensus.get_consensus_status()
        if round_num % 3 == 0:
            print(f"  Round {round_num}: cred={status['credibility']:.2f}, score={status['score']:.3f}, consensus={status['consensus']}, temporal={status.get('temporal_agreement',0):.2f}")

    proposal = {"id": "mut_divergent", "node_id": "Node_0"}
    # Rebuild network state from consensus status
    ns = integration.validate_network_state(consensus._star_cache)
    auth = integration.authorize_mutation(proposal, ns)

    print(f"  Mutation auth: {auth['approved']}, reason={auth.get('reason','ok')}")

    scenario2_passed = (status["credibility"] < 0.6 and not auth["approved"])
    results["scenario2"] = {"description": "Divergent Drift", "passed": scenario2_passed}

    # ============================================================
    # SCENARIO 3: Malicious + Hard Veto
    # ============================================================
    print("\n📌 SCENARIO 3: Malicious Mutation + Hard Veto")
    for node, (_, phase, _) in zip(nodes, node_configs):
        node._phase = phase
        node._tick = 0
    consensus.reset_tracker()
    consensus.clear_cache()

    for round_num in range(1, 8):
        for node in nodes:
            state = integration.collect_node_state(node.node_id)
            star = consensus.draw_temporal_star(state)
            consensus.receive_star(node.node_id, star)
            node.tick()

    status = consensus.get_consensus_status()
    print(f"  Stable consensus: cred={status['credibility']:.2f}, score={status['score']:.3f}")

    forced_proposal = {"id": "mut_malicious", "node_id": "Node_0",
                       "star_signature": {"path": [50,50,50,50,50], "credibility": 1.0}}

    simulated = sandbox.run(forced_proposal, {}, malicious=True)
    fitness = evaluator.calculate_fitness(simulated)
    core_passed, reason = immutable_core.check(simulated)
    print(f"  Fitness: {fitness:.2f}, Stability: {simulated['stability']:.2f}, Core: {'VETO' if not core_passed else 'PASS'} → {reason}")

    scenario3_passed = not core_passed
    results["scenario3"] = {"description": "Malicious + Hard Veto", "passed": scenario3_passed}

    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "="*70)
    print("📊 FINAL RELEASE GATE")
    print("="*70)

    all_passed = True
    for key, res in results.items():
        status = "✅ PASSED" if res["passed"] else "❌ FAILED"
        print(f"  {res['description']}: {status}")
        if not res["passed"]:
            all_passed = False

    print("\n🏁 RELEASE GATE:", "✅ PASSED" if all_passed else "❌ FAILED")
    return all_passed


if __name__ == "__main__":
    test_temporal_adversarial()
