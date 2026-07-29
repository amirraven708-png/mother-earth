#!/usr/bin/env python3
"""
test_distributed_trial.py
تست ماژول Distributed Trial با ۳ نود شبیه‌سازی‌شده
"""

import sys
import os
import time
import random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mother_evolution.distributed_trial import DistributedTrialCoordinator, TrialResult

class MockGossip:
    def __init__(self, node_id):
        self.node_id = node_id
        self.messages = []
        self.nodes = {}

    def register_node(self, node_id, coordinator):
        self.nodes[node_id] = coordinator

    def send_to_node(self, node_id, msg):
        if node_id in self.nodes:
            self.nodes[node_id].receive_gossip(msg)

    def broadcast(self, msg):
        for node_id, coord in self.nodes.items():
            if node_id != self.node_id:
                coord.receive_gossip(msg)

class SimpleSandbox:
    def run(self, current_state, proposal):
        return {
            "stability": 0.82,
            "energy_cost": 0.36,
            "adaptability": 0.73
        }

class SimpleEvaluator:
    def observe(self, state):
        return state

    def calculate_fitness(self, metrics):
        energy_factor = 1.0 / (metrics.get("energy_cost", 1.0) + 1e-8)
        stability = metrics.get("stability", 0.5)
        adaptability = metrics.get("adaptability", 0.5)
        ellipse_balance = 1.0 - abs(stability - adaptability)
        fitness = energy_factor * 0.3 + stability * 0.3 + adaptability * 0.2 + ellipse_balance * 0.2
        return fitness if fitness > 0.65 else -1.0

def test_distributed_trial():
    print("\n" + "="*70)
    print("🌊 DISTRIBUTED TRIAL TEST")
    print("   3 nodes sharing evolution mutations")
    print("="*70)

    nodes = ["Node_A", "Node_B", "Node_C"]
    gossip_nodes = {n: MockGossip(n) for n in nodes}

    coordinators = {}
    for node_id in nodes:
        coordinators[node_id] = DistributedTrialCoordinator(
            node_id=node_id,
            gossip_layer=gossip_nodes[node_id],
            min_consensus=0.6
        )

    for node_id in nodes:
        for other in nodes:
            if other != node_id:
                gossip_nodes[node_id].register_node(other, coordinators[other])

    proposal = {
        "id": "mut_9999",
        "optimized_parameters": {
            "coupling_k": 0.475,
            "buffer_size": 2048,
            "decay_rate": 0.013
        },
        "mutation_type": "adaptive_tuning"
    }

    print("\n📤 Node_A proposing mutation:")
    print(f"   {proposal}")

    target_nodes = ["Node_B", "Node_C"]
    trial_id = coordinators["Node_A"].propose_mutation(proposal, target_nodes)
    print(f"\n📡 Trial ID: {trial_id}")

    print("\n🧪 Running trials on Node_B, Node_C, and Node_A...")
    sandbox = SimpleSandbox()
    evaluator = SimpleEvaluator()

    # اجرای محلی و گزارش از نود B
    result_b = coordinators["Node_B"].run_local_trial(
        proposal, {"stability": 0.75, "energy": 0.42}, evaluator, sandbox
    )
    coordinators["Node_B"].report_trial_result(trial_id, result_b)

    # اجرای محلی و گزارش از نود C
    result_c = coordinators["Node_C"].run_local_trial(
        proposal, {"stability": 0.70, "energy": 0.50}, evaluator, sandbox
    )
    coordinators["Node_C"].report_trial_result(trial_id, result_c)

    # اجرای محلی در نود A (مبدأ)
    result_a = coordinators["Node_A"].run_local_trial(
        proposal, {"stability": 0.78, "energy": 0.38}, evaluator, sandbox
    )
    result_a.trial_id = trial_id  # اتصال صریح trial_id
    coordinators["Node_A"]._process_result(result_a)

    print("\n📊 Final Status:")
    status = coordinators["Node_A"].get_trial_status(trial_id)
    if status:
        print(f"   Trial {trial_id}: {status.get('status')}")
        print(f"   Acceptance Rate: {status.get('acceptance_rate', 0):.2f}")
        print(f"   Avg Fitness: {status.get('avg_fitness', 0):.2f}")
    else:
        print(f"   Trial {trial_id} completed and moved to history.")

    history = coordinators["Node_A"].get_history()
    print(f"\n📜 Evolution History ({len(history)} records):")
    for record in history:
        print(f"   {record['trial_id']}: {record['status']} (rate={record['acceptance_rate']:.2f})")

    print("\n✅ Distributed Trial test complete.")

if __name__ == "__main__":
    test_distributed_trial()
