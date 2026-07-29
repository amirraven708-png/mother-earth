#!/usr/bin/env python3
"""
test_star_consensus.py
Test Star Consensus with Dynamic Credibility
"""

import sys
import os
import random
import threading
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from consensus.star_consensus import StarConsensus, Star
from consensus.block_clock import BlockClock


class MockGossipNode:
    def __init__(self, node_id: str, consensus: StarConsensus, clock: BlockClock,
                 initial_phase: float = 0.5):
        self.node_id = node_id
        self.consensus = consensus
        self.clock = clock
        self.peers: Dict[str, 'MockGossipNode'] = {}
        self.received_stars: Dict[str, Star] = {}
        self.is_alive = True
        self._phase_offset = initial_phase
        self._phase_drift = 0.0
        self._lock = threading.Lock()

    def register_peer(self, peer: 'MockGossipNode'):
        self.peers[peer.node_id] = peer

    def get_state(self) -> Dict:
        phase = (self._phase_offset + self._phase_drift) % 1.0
        return {
            "phase": phase,
            "heat": random.uniform(0.1, 0.9),
            "density": random.uniform(0.2, 0.8),
            "migration_count": random.randint(0, 100),
            "gossip_round": len(self.received_stars)
        }

    def draw_and_broadcast(self):
        state = self.get_state()
        star = self.consensus.draw_star(state)
        with self._lock:
            self.consensus.receive_star(self.node_id, star)
        for peer in self.peers.values():
            if peer.is_alive:
                peer.receive_star(self.node_id, star)

    def receive_star(self, node_id: str, star: Star):
        if not self.is_alive:
            return
        with self._lock:
            self.consensus.receive_star(node_id, star)
            self.received_stars[node_id] = star

    def apply_drift(self, drift: float):
        self._phase_drift += drift

    def get_phase(self) -> float:
        return (self._phase_offset + self._phase_drift) % 1.0

    def get_status(self):
        return self.consensus.get_consensus_status()


def run_simulation(num_nodes: int = 5, rounds: int = 10,
                   drift_magnitude: float = 0.0,
                   drift_type: str = "uniform",  # "uniform" or "divergent"
                   initial_spread: float = 0.02,
                   emergency_threshold: float = 0.15,
                   credibility_threshold: float = 0.6):
    """
    Simulate star consensus with different drift patterns.
    - uniform: all nodes drift together (should NOT affect credibility)
    - divergent: nodes drift apart (should reduce credibility)
    """
    print("\n" + "="*70)
    print(f"🌟 STAR CONSENSUS with DYNAMIC CREDIBILITY")
    print(f"   Nodes: {num_nodes}, Rounds: {rounds}")
    print(f"   Drift type: {drift_type}, magnitude: {drift_magnitude}")
    print(f"   emergency_threshold: {emergency_threshold}")
    print(f"   credibility_threshold: {credibility_threshold}")
    print("="*70)

    # Create nodes with initial phase spread
    nodes: List[MockGossipNode] = []
    for i in range(num_nodes):
        consensus = StarConsensus(
            emergency_threshold=emergency_threshold,
            min_nodes=3,
            credibility_threshold=credibility_threshold,
            window_size=8
        )
        clock = BlockClock(initial_clock=0.0)
        initial_phase = 0.5 + (i - (num_nodes-1)/2) * initial_spread
        initial_phase = initial_phase % 1.0
        node = MockGossipNode(f"Node_{i}", consensus, clock, initial_phase)
        nodes.append(node)

    # Register peers
    for node in nodes:
        for other in nodes:
            if other != node:
                node.register_peer(other)

    history = []

    for round_num in range(1, rounds + 1):
        print(f"\n--- Round {round_num} ---")

        # Apply drift
        if drift_magnitude > 0:
            if drift_type == "uniform":
                # All nodes drift by the same amount (common phase shift)
                common_drift = random.uniform(-drift_magnitude, drift_magnitude)
                for node in nodes:
                    node.apply_drift(common_drift)
            else:  # divergent
                # Each node drifts independently
                for node in nodes:
                    node.apply_drift(random.uniform(-drift_magnitude, drift_magnitude))

        # Draw and broadcast stars
        for node in nodes:
            node.draw_and_broadcast()

        # Collect statuses
        statuses = [node.get_status() for node in nodes]
        agreements = [s["consensus"] for s in statuses]
        max_dists = [s["max_distance"] for s in statuses if s["max_distance"] is not None]
        credibilities = [s["credibility"] for s in statuses]
        phases = [s["collective_phase"] for s in statuses if s["collective_phase"] is not None]

        agreement_ratio = sum(agreements) / len(agreements) if agreements else 0
        avg_max_dist = sum(max_dists) / len(max_dists) if max_dists else 0
        avg_cred = sum(credibilities) / len(credibilities) if credibilities else 0
        avg_phase = sum(phases) / len(phases) if phases else 0

        # Print per-node details
        for i, node in enumerate(nodes):
            s = statuses[i]
            print(f"   {node.node_id}: consensus={s['consensus']}, "
                  f"max_dist={s['max_distance']:.3f}, cred={s['credibility']:.2f}, "
                  f"own_phase={node.get_phase():.3f}")

        print(f"   Summary: agreement={agreement_ratio:.0%}, "
              f"avg_max_dist={avg_max_dist:.3f}, avg_cred={avg_cred:.2f}")

        history.append({
            "round": round_num,
            "agreement_ratio": agreement_ratio,
            "avg_max_dist": avg_max_dist,
            "avg_cred": avg_cred,
            "avg_phase": avg_phase
        })

    # Final summary
    print("\n" + "="*70)
    print("📊 SIMULATION SUMMARY")
    print("="*70)
    final = history[-1] if history else {}
    print(f"   Final agreement: {final.get('agreement_ratio', 0):.0%}")
    print(f"   Final avg max distance: {final.get('avg_max_dist', 0):.3f}")
    print(f"   Final avg credibility: {final.get('avg_cred', 0):.2f}")

    # Show credibility trend
    print("\n   Credibility trend:")
    for h in history[::2]:  # every other round for brevity
        print(f"      Round {h['round']}: cred={h['avg_cred']:.2f}, "
              f"agreement={h['agreement_ratio']:.0%}, max_dist={h['avg_max_dist']:.3f}")

    return history


def test_scenarios():
    """Run three scenarios to validate dynamic credibility."""
    print("\n" + "="*70)
    print("🧪 DYNAMIC CREDIBILITY TEST SUITE")
    print("="*70)

    # Scenario 1: Uniform drift (all nodes move together)
    print("\n📌 Scenario 1: Uniform Drift (should maintain credibility)")
    hist1 = run_simulation(
        num_nodes=5, rounds=10,
        drift_magnitude=0.08,
        drift_type="uniform",
        initial_spread=0.02,
        emergency_threshold=0.15,
        credibility_threshold=0.6
    )
    final_cred1 = hist1[-1]["avg_cred"] if hist1 else 0

    # Scenario 2: Divergent drift (nodes drift apart)
    print("\n📌 Scenario 2: Divergent Drift (should lose credibility)")
    hist2 = run_simulation(
        num_nodes=5, rounds=10,
        drift_magnitude=0.08,
        drift_type="divergent",
        initial_spread=0.02,
        emergency_threshold=0.15,
        credibility_threshold=0.6
    )
    final_cred2 = hist2[-1]["avg_cred"] if hist2 else 0

    # Scenario 3: Recovery after divergence
    print("\n📌 Scenario 3: Recovery after Divergence")
    # Phase 3a: divergent for 8 rounds, then recover
    hist3a = run_simulation(
        num_nodes=5, rounds=8,
        drift_magnitude=0.08,
        drift_type="divergent",
        initial_spread=0.02,
        emergency_threshold=0.15,
        credibility_threshold=0.6
    )
    # Phase 3b: reduce drift to near zero
    print("\n   → Now reducing drift to recover...")
    hist3b = run_simulation(
        num_nodes=5, rounds=8,
        drift_magnitude=0.01,
        drift_type="uniform",
        initial_spread=0.02,
        emergency_threshold=0.15,
        credibility_threshold=0.6
    )
    final_cred3 = hist3b[-1]["avg_cred"] if hist3b else 0

    # Summary
    print("\n" + "="*70)
    print("📈 TEST SUMMARY")
    print("="*70)
    print(f"   Uniform drift final credibility: {final_cred1:.2f} (should be > 0.6)")
    print(f"   Divergent drift final credibility: {final_cred2:.2f} (should be < 0.6)")
    print(f"   Recovery final credibility: {final_cred3:.2f} (should be > 0.6)")

    if final_cred1 > 0.6 and final_cred2 < 0.6 and final_cred3 > 0.6:
        print("\n✅ DYNAMIC CREDIBILITY TEST PASSED: System distinguished uniform from divergent drift.")
    else:
        print("\n⚠️ DYNAMIC CREDIBILITY TEST: Results mixed. Check parameters.")
        print("   Try adjusting drift magnitude or emergency_threshold.")


if __name__ == "__main__":
    test_scenarios()

    print("\n" + "="*70)
    print("🏁 Star Consensus tests complete.")
    print("="*70)
