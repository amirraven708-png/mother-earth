#!/usr/bin/env python3
"""
test_fault_tolerance_integrated.py (FIXED)
Integrated test: Fault Tolerance + Gossip + BubbleDB
Each node stores its own recovery vector in BubbleDB.
"""

import sys
import os
import math
import random
import time
import threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from fault_tolerance import FaultToleranceManager, HarmonicPulse, NodeStatus
from wave_gossip import WaveGossipNode
from mother_storage.distributed_bubbledb import DistributedBubbleDB, DistributedBubbleDBConfig

def test_integrated():
    print("\n" + "="*70)
    print("🛡 INTEGRATED FAULT TOLERANCE TEST (FIXED)")
    print("   Each node stores its own recovery vector")
    print("="*70)

    # 1. Setup
    ft = FaultToleranceManager(tolerance=0.35, harmonic_window=5)
    db_config = DistributedBubbleDBConfig(initial_state="cold")
    db = DistributedBubbleDB(db_config)

    # 2. Register nodes
    nodes = ["Node_1", "Node_2", "Node_3", "Node_4", "Node_5"]
    ports = [8001, 8002, 8003, 8004, 8005]

    for i, node_id in enumerate(nodes):
        phase = random.uniform(0, 2*math.pi)
        ft.register_node(node_id, phase, omega=1.0)
        print(f"✅ Registered {node_id} with phase={phase:.3f}")

    # 3. Store recovery vectors in BubbleDB (each node's own state)
    for node_id in nodes:
        node_status = ft.nodes[node_id]
        recovery_vector = ft.healer.build_recovery_vector(node_status)
        db.store_recovery_vector(node_id, recovery_vector)

    print("\n📦 Initial recovery vectors stored in BubbleDB")

    # 4. Setup Gossip
    gossip_nodes = []
    for i, node_id in enumerate(nodes):
        peer_ports = [str(ports[j]) for j in range(len(ports)) if j != i]
        gnode = WaveGossipNode(node_id, ports[i], peer_ports, ft)
        gnode.start()
        gossip_nodes.append(gnode)

    print("📡 Gossip network started")

    # 5. Phase locking
    print("\n⏳ Phase locking (15 ticks)...")
    for tick in range(15):
        network_phase = ft.get_average_phase()
        for i, node_id in enumerate(nodes):
            node_status = ft.nodes[node_id]
            pulse = ft.heartbeat.generate_pulse(node_status)
            gossip_nodes[i].send_pulse(pulse.phase, pulse.tick, pulse.omega)
            # Update recovery vector in BubbleDB periodically
            if tick % 5 == 0:
                recovery_vector = ft.healer.build_recovery_vector(node_status)
                db.store_recovery_vector(node_id, recovery_vector)
        ft.tick(network_phase)

    print("\n✅ Phase lock achieved:")
    for node_id in nodes:
        status = ft.get_status(node_id)
        print(f"   {node_id}: status={status['status']}, phase={status['phase']:.3f}")

    # 6. Kill Node_2 and Node_4
    print("\n💀 Killing Node_2 and Node_4...")
    ft.declare_dead("Node_2")
    ft.declare_dead("Node_4")

    # 7. Detect death
    print("\n⏳ Detecting failures (5 ticks)...")
    for tick in range(5):
        network_phase = ft.get_average_phase()
        for i, node_id in enumerate(nodes):
            if node_id not in ["Node_2", "Node_4"]:
                node_status = ft.nodes[node_id]
                pulse = ft.heartbeat.generate_pulse(node_status)
                gossip_nodes[i].send_pulse(pulse.phase, pulse.tick, pulse.omega)
                # Update recovery vectors for alive nodes
                recovery_vector = ft.healer.build_recovery_vector(node_status)
                db.store_recovery_vector(node_id, recovery_vector)
        ft.tick(network_phase)

    print("\n📊 After failure detection:")
    for node_id in nodes:
        status = ft.get_status(node_id)
        print(f"   {node_id}: status={status['status']}")

    # 8. Recover from BubbleDB (use each node's OWN recovery vector)
    print("\n🔄 Recovering from BubbleDB using node-specific recovery vectors...")
    for node_id in ["Node_2", "Node_4"]:
        recovery_vector = db.get_recovery_vector(node_id)
        if recovery_vector:
            ft.initiate_recovery(node_id, recovery_vector)
            print(f"   ✅ Recovery vector loaded for {node_id}: phase={recovery_vector.get('phase'):.3f}")
        else:
            print(f"   ⚠️ No recovery vector for {node_id}")

    # 9. Recovery ticks
    print("\n⏳ Recovering (20 ticks)...")
    for tick in range(20):
        network_phase = ft.get_average_phase()
        for i, node_id in enumerate(nodes):
            node_status = ft.nodes[node_id]
            pulse = ft.heartbeat.generate_pulse(node_status)
            gossip_nodes[i].send_pulse(pulse.phase, pulse.tick, pulse.omega)
            # Update recovery vectors for all nodes periodically
            if tick % 5 == 0:
                recovery_vector = ft.healer.build_recovery_vector(node_status)
                db.store_recovery_vector(node_id, recovery_vector)
        ft.tick(network_phase)

        if (tick + 1) % 5 == 0:
            status_summary = ft.get_network_status()
            print(f"   Tick {tick+1}: alive={status_summary['alive']}, recovering={status_summary['recovering']}, dead={status_summary['dead']}")

    # 10. Final status
    print("\n" + "="*70)
    print("📊 FINAL STATE")
    print("="*70)

    network_status = ft.get_network_status()
    print(f"Alive: {network_status['alive']}/{network_status['total_nodes']}")
    print(f"Desync: {network_status['desync']}")
    print(f"Recovering: {network_status['recovering']}")
    print(f"Dead: {network_status['dead']}")

    print("\nNode Details:")
    for node_id in nodes:
        status = ft.get_status(node_id)
        phase = ft.get_node_phase(node_id)
        print(f"   {node_id}: status={status['status']}, phase={phase:.3f}")

    if network_status['alive'] == 5:
        print("\n✅ ALL NODES RECOVERED SUCCESSFULLY!")
    else:
        print("\n⚠️ Some nodes still not recovered")

    # Cleanup
    for gnode in gossip_nodes:
        gnode.stop()

    print("\n🏁 Test complete.")
    return network_status

if __name__ == "__main__":
    test_integrated()
