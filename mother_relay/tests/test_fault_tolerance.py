#!/usr/bin/env python3
"""
test_fault_tolerance.py
Fault Tolerance Test — 5 nodes, simulated failures, phase recovery
"""

import sys
import os
import math
import random
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from fault_tolerance import FaultToleranceManager, HarmonicPulse, NodeStatus

def run_fault_tolerance_test():
    print("\n" + "="*70)
    print("🛡 FAULT TOLERANCE TEST — 5 Nodes")
    print("="*70)

    # 1. Create network with 5 nodes
    ft = FaultToleranceManager(tolerance=0.35, harmonic_window=5)

    # Initialize nodes with random phases
    nodes = ["Node_A", "Node_B", "Node_C", "Node_D", "Node_E"]
    initial_phases = [random.uniform(0, 2*math.pi) for _ in range(5)]

    for i, node_id in enumerate(nodes):
        ft.register_node(node_id, initial_phases[i], omega=1.0)
        print(f"✅ Registered {node_id} with phase={initial_phases[i]:.3f}")

    print("\n📍 Initial Phase Lock Status:")
    network_phase = ft.get_average_phase()
    print(f"   Network Phase: {network_phase:.3f}")

    for node_id in nodes:
        phase = ft.get_node_phase(node_id)
        status = ft.get_status(node_id)
        print(f"   {node_id}: phase={phase:.3f}, status={status['status']}")

    # 2. Simulate 10 ticks to stabilize
    print("\n⏳ Stabilizing network (10 ticks)...")
    for tick in range(10):
        # Simulate pulses from each node
        for node_id in nodes:
            node_status = ft.nodes[node_id]
            pulse = ft.heartbeat.generate_pulse(node_status)
            ft.receive_pulse(pulse)
        ft.tick(network_phase)
        network_phase = ft.get_average_phase()

    print("\n✅ Network stabilized:")
    for node_id in nodes:
        status = ft.get_status(node_id)
        phase = ft.get_node_phase(node_id)
        print(f"   {node_id}: phase={phase:.3f}, status={status['status']}")

    # 3. Kill two nodes
    print("\n💀 Killing Node_C and Node_E...")
    ft.declare_dead("Node_C")
    ft.declare_dead("Node_E")

    # 4. Simulate 5 ticks to detect death
    print("\n⏳ Detecting failure (5 ticks)...")
    for tick in range(5):
        # Other nodes send pulses
        for node_id in ["Node_A", "Node_B", "Node_D"]:
            node_status = ft.nodes[node_id]
            pulse = ft.heartbeat.generate_pulse(node_status)
            ft.receive_pulse(pulse)
        ft.tick(ft.get_average_phase())

    print("\n📊 After failure detection:")
    for node_id in nodes:
        status = ft.get_status(node_id)
        print(f"   {node_id}: status={status['status']}")

    # 5. Initiate recovery for dead nodes
    print("\n🔄 Initiating recovery...")
    # Build recovery vectors from last known state
    for node_id in ["Node_C", "Node_E"]:
        # For testing, we use the current network phase as recovery target
        recovery_vector = {
            "phase": ft.get_average_phase(),
            "tick": ft._current_tick,
            "omega": 1.0,
            "hpoo_score": 0.7,
            "fingerprint": f"recover_{node_id}"
        }
        ft.initiate_recovery(node_id, recovery_vector)

    # 6. Simulate recovery ticks
    print("\n⏳ Recovering nodes (15 ticks)...")
    for tick in range(15):
        network_phase = ft.get_average_phase()
        # All nodes send pulses (including recovering ones)
        for node_id in nodes:
            node_status = ft.nodes[node_id]
            if node_status.status != NodeStatus.DEAD:
                pulse = ft.heartbeat.generate_pulse(node_status)
                ft.receive_pulse(pulse)
        ft.tick(network_phase)

        # Show progress every 5 ticks
        if (tick + 1) % 5 == 0:
            status_summary = ft.get_network_status()
            print(f"   Tick {tick+1}: alive={status_summary['alive']}, recovering={status_summary['recovering']}, dead={status_summary['dead']}")

    # 7. Final status
    print("\n" + "="*70)
    print("📊 FINAL STATE")
    print("="*70)

    network_status = ft.get_network_status()
    print(f"Network Status:")
    print(f"   Total Nodes: {network_status['total_nodes']}")
    print(f"   Alive: {network_status['alive']}")
    print(f"   Desync: {network_status['desync']}")
    print(f"   Recovering: {network_status['recovering']}")
    print(f"   Dead: {network_status['dead']}")

    print("\nNode Details:")
    phase_errors = []
    network_phase = ft.get_average_phase()
    for node_id in nodes:
        status = ft.get_status(node_id)
        phase = ft.get_node_phase(node_id)
        phase_error = abs(math.atan2(math.sin(phase - network_phase), math.cos(phase - network_phase))) if phase else 0
        phase_errors.append(phase_error)
        print(f"   {node_id}: status={status['status']}, phase={phase:.3f}, error={phase_error:.4f}")

    # 8. Success criteria
    print("\n" + "="*70)
    print("📈 TEST RESULTS")
    print("="*70)

    recovered = sum(1 for n in nodes if ft.nodes[n].status == NodeStatus.ALIVE)
    expected_alive = 5  # all should be alive after recovery

    if recovered == expected_alive:
        print("✅ All nodes recovered successfully!")
        print(f"   Recovery successful for Node_C and Node_E")
    else:
        print(f"⚠️ Only {recovered}/{expected_alive} nodes alive")

    avg_phase_error = sum(phase_errors) / len(phase_errors)
    print(f"   Average Phase Error: {avg_phase_error:.4f} rad")
    if avg_phase_error < 0.35:
        print("   ✅ Phase alignment is within tolerance")
    else:
        print("   ⚠️ Phase alignment exceeds tolerance")

    print("\n" + "="*70)
    print("🏁 Fault Tolerance Test Complete")
    print("="*70)

    return network_status

if __name__ == "__main__":
    run_fault_tolerance_test()
