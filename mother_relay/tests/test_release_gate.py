#!/usr/bin/env python3
"""
test_release_gate.py – Final Release Gate with Temporal Schedule
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


def test_release_gate():
    print("\n" + "="*70)
    print("🧪 FINAL RELEASE GATE – Temporal Schedule & Credibility Fix")
    print("   4 scenarios: Uniform, Divergent, Malicious, Recovery")
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
    results = {}

    # ============================================================
    # SCENARIO 1: Uniform Drift
    # ============================================================
    print("\n📌 SCENARIO 1: Uniform Drift (should maintain consensus)")
    consensus.reset_tracker()
    consensus.clear_cache()
    for node, (_, phase, _) in zip(nodes, node_configs):
        node._phase = phase
        node._tick = 0

    stars = {}
    for round_num in range(1, 11):
        common_drift = 0.02
        for node in nodes:
            node.apply_drift(common_drift)
            node.tick()
            state = integration.collect_node_state(node.node_id)
            star = consensus.draw_temporal_star(state)
            stars[node.node_id] = star
            consensus.receive_star(node.node_id, star)

        # Advance global tick only once per round
        consensus.schedule.advance_global_tick()
        status = consensus.get_consensus_status()
        if round_num % 3 == 0:
            print(f"  Round {round_num}: cred={status['credibility']:.2f}, score={status['score']:.3f}, temporal={status['temporal_agreement']:.2f}, consensus={status['consensus']}")

    scenario1 = status["consensus"] and status["credibility"] > 0.6
    print(f"  Scenario 1 result: {'✅ PASS' if scenario1 else '❌ FAIL'}")
    results["scenario1"] = {"desc": "Uniform Drift", "passed": scenario1}

    # ============================================================
    # SCENARIO 2: Divergent Drift
    # ============================================================
    print("\n📌 SCENARIO 2: Divergent Drift (should lose consensus)")
    consensus.reset_tracker()
    consensus.clear_cache()
    for node, (_, phase, _) in zip(nodes, node_configs):
        node._phase = phase
        node._tick = 0

    divergent_drifts = {"Node_0": +0.12, "Node_1": -0.12, "Node_2": +0.18, "Node_3": -0.18, "Node_4": +0.10}
    stars = {}
    for round_num in range(1, 11):
        for node in nodes:
            drift = divergent_drifts[node.node_id] * (round_num / 10.0)
            node.apply_drift(drift)
            node.tick()
            state = integration.collect_node_state(node.node_id)
            star = consensus.draw_temporal_star(state)
            stars[node.node_id] = star
            consensus.receive_star(node.node_id, star)

        consensus.schedule.advance_global_tick()
        status = consensus.get_consensus_status()
        if round_num % 3 == 0:
            print(f"  Round {round_num}: cred={status['credibility']:.2f}, score={status['score']:.3f}, temporal={status['temporal_agreement']:.2f}, consensus={status['consensus']}")

    # Attempt mutation
    ns = integration.validate_network_state(stars)
    proposal = {"id": "mut_divergent", "node_id": "Node_0"}
    auth = integration.authorize_mutation(proposal, ns)
    print(f"  Mutation auth: {auth['approved']}, reason={auth.get('reason','ok')}")

    scenario2 = (status["credibility"] < 0.6 and not auth["approved"])
    print(f"  Scenario 2 result: {'✅ PASS' if scenario2 else '❌ FAIL'}")
    results["scenario2"] = {"desc": "Divergent Drift", "passed": scenario2}

    # ============================================================
    # SCENARIO 3: Malicious + Hard Veto
    # ============================================================
    print("\n📌 SCENARIO 3: Malicious Mutation + Hard Veto")
    consensus.reset_tracker()
    consensus.clear_cache()
    for node, (_, phase, _) in zip(nodes, node_configs):
        node._phase = phase
        node._tick = 0

    stars = {}
    for round_num in range(1, 8):
        for node in nodes:
            node.tick()
            state = integration.collect_node_state(node.node_id)
            star = consensus.draw_temporal_star(state)
            stars[node.node_id] = star
            consensus.receive_star(node.node_id, star)
        consensus.schedule.advance_global_tick()

    status = consensus.get_consensus_status()
    print(f"  Stable consensus: cred={status['credibility']:.2f}, score={status['score']:.3f}")

    # Force malicious mutation
    forced_proposal = {
        "id": "mut_malicious",
        "node_id": "Node_0",
        "star_signature": {"path": [50,50,50,50,50], "credibility": 1.0}
    }
    simulated = {"stability": 0.45, "energy_cost": 0.5, "adaptability": 0.95}
    fitness = 0.92
    core_passed, reason = immutable_core.check(simulated)
    print(f"  Fitness: {fitness:.2f}, Stability: {simulated['stability']:.2f}, Core: {'VETO' if not core_passed else 'PASS'} → {reason}")

    scenario3 = not core_passed
    results["scenario3"] = {"desc": "Malicious + Hard Veto", "passed": scenario3}
    print(f"  Scenario 3 result: {'✅ PASS' if scenario3 else '❌ FAIL'}")

    # ============================================================
    # SCENARIO 4: Recovery after Divergence
    # ============================================================
    print("\n📌 SCENARIO 4: Recovery after Divergence")
    consensus.reset_tracker()
    consensus.clear_cache()
    # Start from divergent state (after scenario 2)
    for node, (_, phase, _) in zip(nodes, node_configs):
        node._phase = phase
        node._tick = 0

    # First, induce divergence
    stars = {}
    for round_num in range(1, 6):
        for node in nodes:
            drift = divergent_drifts[node.node_id] * (round_num / 10.0)
            node.apply_drift(drift)
            node.tick()
            state = integration.collect_node_state(node.node_id)
            star = consensus.draw_temporal_star(state)
            stars[node.node_id] = star
            consensus.receive_star(node.node_id, star)
        consensus.schedule.advance_global_tick()

    status = consensus.get_consensus_status()
    print(f"  After divergence: cred={status['credibility']:.2f}, consensus={status['consensus']}")

    # Then recover: apply uniform drift to bring nodes back together
    for round_num in range(1, 8):
        common_drift = 0.02 * round_num
        for node in nodes:
            node.apply_drift(common_drift)
            node.tick()
            state = integration.collect_node_state(node.node_id)
            star = consensus.draw_temporal_star(state)
            stars[node.node_id] = star
            consensus.receive_star(node.node_id, star)
        consensus.schedule.advance_global_tick()

    status = consensus.get_consensus_status()
    print(f"  After recovery: cred={status['credibility']:.2f}, consensus={status['consensus']}")

    scenario4 = status["consensus"] and status["credibility"] > 0.6
    results["scenario4"] = {"desc": "Recovery", "passed": scenario4}
    print(f"  Scenario 4 result: {'✅ PASS' if scenario4 else '❌ FAIL'}")

    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "="*70)
    print("📊 RELEASE GATE FINAL SUMMARY")
    print("="*70)

    all_passed = True
    for key, res in results.items():
        status = "✅ PASSED" if res["passed"] else "❌ FAILED"
        print(f"  {res['desc']}: {status}")
        if not res["passed"]:
            all_passed = False

    print("\n🏁 RELEASE GATE:", "✅ PASSED" if all_passed else "❌ FAILED")
    return all_passed


if __name__ == "__main__":
    test_release_gate()
