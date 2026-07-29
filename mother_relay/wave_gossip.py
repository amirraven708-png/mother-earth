"""
wave_gossip.py
Wave Gossip Mesh — harmonic pulse propagation for Fault Tolerance
"""

import asyncio
import json
import socket
import threading
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from fault_tolerance import FaultToleranceManager, HarmonicPulse

@dataclass
class GossipMessage:
    type: str  # "pulse", "recovery"
    payload: Dict

class WaveGossipNode:
    """
    A gossip node that propagates harmonic pulses across the network.
    """

    def __init__(self, node_id: str, port: int, peers: List[str], ft_manager: FaultToleranceManager):
        self.node_id = node_id
        self.port = port
        self.peers = peers
        self.ft = ft_manager
        self.sock = None
        self.running = True
        self.seen_messages = set()

    def start(self):
        """Start the gossip listener"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", self.port))
        self.sock.settimeout(0.5)
        print(f"📡 Gossip node {self.node_id} listening on port {self.port}")

        listener = threading.Thread(target=self._listen, daemon=True)
        listener.start()

    def _listen(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                try:
                    msg = json.loads(data.decode())
                    self._process_message(msg)
                except json.JSONDecodeError:
                    pass
            except socket.timeout:
                continue
            except Exception:
                break

    def _process_message(self, msg: Dict):
        msg_id = f"{msg.get('source')}:{msg.get('seq', 0)}"
        if msg_id in self.seen_messages:
            return
        self.seen_messages.add(msg_id)
        if len(self.seen_messages) > 1000:
            self.seen_messages.clear()

        msg_type = msg.get("type")

        if msg_type == "pulse":
            # Convert to HarmonicPulse
            pulse = HarmonicPulse(
                node_id=msg["source"],
                phase=msg["phase"],
                tick=msg["tick"],
                omega=msg.get("omega", 1.0),
                hpoo_score=msg.get("hpoo_score", 0.5)
            )
            self.ft.receive_pulse(pulse)

        # Propagate to peers (but not back to sender)
        for peer in self.peers:
            if peer != str(self.port):
                self._send_to_peer(peer, msg)

    def _send_to_peer(self, peer_port: str, msg: Dict):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(json.dumps(msg).encode(), ("127.0.0.1", int(peer_port)))
            sock.close()
        except Exception:
            pass

    def send_pulse(self, phase: float, tick: int, omega: float = 1.0):
        """Send a harmonic pulse to all peers"""
        msg = {
            "type": "pulse",
            "source": self.node_id,
            "phase": phase,
            "tick": tick,
            "omega": omega,
            "hpoo_score": self.ft.nodes.get(self.node_id, self.ft.register_node(self.node_id)).hpoo_score,
            "seq": self.ft._current_tick
        }
        for peer in self.peers:
            self._send_to_peer(peer, msg)

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()
