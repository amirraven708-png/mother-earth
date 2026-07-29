"""
fault_tolerance.py
Rhythm-based Fault Tolerance for Wave Mother

Key concepts:
- Fault = Phase Disruption
- Recovery = Phase Re-alignment
- Replica = Harmonic Echo
- Heartbeat = Rhythm Pulse

No timestamps, no timeouts — only phase and rhythm.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from collections import deque

# ============================================================
# 1. Enums & Status
# ============================================================
class NodeStatus(Enum):
    ALIVE = "alive"
    DESYNC = "desync"
    RECOVERING = "recovering"
    DEAD = "dead"

@dataclass
class RhythmicNodeStatus:
    """Status of a node in the network"""
    node_id: str
    phase: float = 0.0
    tick: int = 0
    omega: float = 1.0
    pulse_strength: float = 0.0
    status: NodeStatus = NodeStatus.ALIVE
    last_pulse_tick: int = 0
    phase_history: deque = field(default_factory=lambda: deque(maxlen=10))
    hpoo_score: float = 0.5
    recovery_vector: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "phase": self.phase,
            "tick": self.tick,
            "omega": self.omega,
            "pulse_strength": self.pulse_strength,
            "status": self.status.value,
            "last_pulse_tick": self.last_pulse_tick,
            "hpoo_score": self.hpoo_score,
        }

# ============================================================
# 2. Harmonic Heartbeat
# ============================================================
@dataclass
class HarmonicPulse:
    """Pulse sent by a node to prove it's alive"""
    node_id: str
    phase: float
    tick: int
    omega: float
    hpoo_score: float
    fingerprint: str = ""

class HarmonicHeartbeat:
    """
    Manages harmonic pulse generation and validation.
    A node is considered alive if its phase aligns with the network.
    """

    def __init__(self, tolerance: float = 0.35, harmonic_window: int = 5):
        self.tolerance = tolerance
        self.harmonic_window = harmonic_window  # number of missed pulses to declare DEAD

    def generate_pulse(self, node_status: RhythmicNodeStatus) -> HarmonicPulse:
        """Generate a harmonic pulse from a node's current status"""
        return HarmonicPulse(
            node_id=node_status.node_id,
            phase=node_status.phase,
            tick=node_status.tick,
            omega=node_status.omega,
            hpoo_score=node_status.hpoo_score,
            fingerprint=f"{node_status.node_id}:{node_status.tick}:{node_status.phase:.4f}"
        )

    def validate_pulse(self, pulse: HarmonicPulse, network_phase: float) -> Tuple[bool, float]:
        """Validate a pulse against the network phase"""
        phase_error = abs(math.atan2(math.sin(pulse.phase - network_phase), math.cos(pulse.phase - network_phase)))
        is_aligned = phase_error <= self.tolerance
        return is_aligned, phase_error

    def detect_desync(self, node_status: RhythmicNodeStatus, network_phase: float, current_tick: int) -> NodeStatus:
        """Detect if a node is desynced based on phase drift"""
        phase_error = abs(math.atan2(math.sin(node_status.phase - network_phase), math.cos(node_status.phase - network_phase)))

        if phase_error <= self.tolerance:
            return NodeStatus.ALIVE

        # Check if node has been desynced for too long
        ticks_since_pulse = current_tick - node_status.last_pulse_tick
        if ticks_since_pulse > self.harmonic_window:
            return NodeStatus.DEAD

        return NodeStatus.DESYNC

# ============================================================
# 3. Self-Healing Engine
# ============================================================
class SelfHealingEngine:
    """
    Recovers dead/desynced nodes using phase alignment and stored recovery vectors.
    """

    def __init__(self, tolerance: float = 0.35, max_recovery_ticks: int = 10):
        self.tolerance = tolerance
        self.max_recovery_ticks = max_recovery_ticks

    def restore_recovery_vector(self, node_status: RhythmicNodeStatus, recovery_vector: Dict) -> RhythmicNodeStatus:
        """Restore a node from a recovery vector"""
        node_status.phase = recovery_vector.get("phase", 0.0)
        node_status.tick = recovery_vector.get("tick", 0)
        node_status.omega = recovery_vector.get("omega", 1.0)
        node_status.hpoo_score = recovery_vector.get("hpoo_score", 0.5)
        node_status.status = NodeStatus.RECOVERING
        return node_status

    def apply_recovery_phase(self, node_status: RhythmicNodeStatus, network_phase: float, steps: int = 1) -> RhythmicNodeStatus:
        """Gradually align a recovering node's phase to the network"""
        if node_status.status != NodeStatus.RECOVERING:
            return node_status

        phase_error = math.atan2(math.sin(network_phase - node_status.phase), math.cos(network_phase - node_status.phase))
        correction = phase_error / max(1, steps)
        node_status.phase = (node_status.phase + correction) % (2 * math.pi)

        # Check if fully recovered
        if abs(phase_error) <= self.tolerance:
            node_status.status = NodeStatus.ALIVE

        return node_status

    def build_recovery_vector(self, node_status: RhythmicNodeStatus, fingerprint: str = "") -> Dict:
        """Build a recovery vector from a node's status"""
        return {
            "phase": node_status.phase,
            "tick": node_status.tick,
            "omega": node_status.omega,
            "hpoo_score": node_status.hpoo_score,
            "fingerprint": fingerprint or f"{node_status.node_id}:{node_status.tick}:{node_status.phase:.4f}"
        }

# ============================================================
# 4. Fault Tolerance Manager
# ============================================================
class FaultToleranceManager:
    """
    Main fault tolerance manager for the Wave Mother network.
    """

    def __init__(self, tolerance: float = 0.35, harmonic_window: int = 5):
        self.tolerance = tolerance
        self.harmonic_window = harmonic_window
        self.heartbeat = HarmonicHeartbeat(tolerance, harmonic_window)
        self.healer = SelfHealingEngine(tolerance)
        self.nodes: Dict[str, RhythmicNodeStatus] = {}
        self._pulse_history: Dict[str, List[HarmonicPulse]] = {}
        self._network_phase = 0.0
        self._current_tick = 0

    def register_node(self, node_id: str, initial_phase: float = 0.0, omega: float = 1.0) -> RhythmicNodeStatus:
        """Register a new node in the network"""
        status = RhythmicNodeStatus(
            node_id=node_id,
            phase=initial_phase,
            omega=omega,
            status=NodeStatus.ALIVE,
            hpoo_score=0.5
        )
        self.nodes[node_id] = status
        self._pulse_history[node_id] = []
        return status

    def receive_pulse(self, pulse: HarmonicPulse):
        """Process a received harmonic pulse"""
        if pulse.node_id not in self.nodes:
            # Unknown node — register it
            self.register_node(pulse.node_id, pulse.phase, pulse.omega)

        node_status = self.nodes[pulse.node_id]
        node_status.phase = pulse.phase
        node_status.tick = pulse.tick
        node_status.omega = pulse.omega
        node_status.hpoo_score = pulse.hpoo_score
        node_status.last_pulse_tick = self._current_tick
        node_status.pulse_strength = min(1.0, node_status.pulse_strength + 0.1)

        # Check alignment
        is_aligned, phase_error = self.heartbeat.validate_pulse(pulse, self._network_phase)
        if is_aligned:
            node_status.status = NodeStatus.ALIVE
        else:
            node_status.status = NodeStatus.DESYNC

        # Store pulse history
        self._pulse_history[pulse.node_id].append(pulse)
        if len(self._pulse_history[pulse.node_id]) > 20:
            self._pulse_history[pulse.node_id].pop(0)

    def tick(self, network_phase: float):
        """Advance one tick"""
        self._current_tick += 1
        self._network_phase = network_phase

        # Check each node's status
        for node_id, status in list(self.nodes.items()):
            if status.status == NodeStatus.ALIVE:
                # Check if still alive
                new_status = self.heartbeat.detect_desync(status, network_phase, self._current_tick)
                if new_status != status.status:
                    status.status = new_status
                    if new_status == NodeStatus.DEAD:
                        print(f"💀 Node {node_id} declared DEAD (phase drift detected)")

            elif status.status == NodeStatus.RECOVERING:
                # Apply recovery phase step
                status = self.healer.apply_recovery_phase(status, network_phase, steps=3)
                self.nodes[node_id] = status
                if status.status == NodeStatus.ALIVE:
                    print(f"🔄 Node {node_id} RECOVERED (phase re-aligned)")

    def declare_dead(self, node_id: str) -> bool:
        """Manually declare a node dead (for testing)"""
        if node_id not in self.nodes:
            return False
        self.nodes[node_id].status = NodeStatus.DEAD
        print(f"💀 Node {node_id} killed (manual)")
        return True

    def initiate_recovery(self, node_id: str, recovery_vector: Optional[Dict] = None) -> bool:
        """Initiate recovery for a dead/desynced node"""
        if node_id not in self.nodes:
            return False

        node_status = self.nodes[node_id]
        if recovery_vector:
            node_status = self.healer.restore_recovery_vector(node_status, recovery_vector)
        else:
            # Build from current status
            recovery_vector = self.healer.build_recovery_vector(node_status)
            node_status = self.healer.restore_recovery_vector(node_status, recovery_vector)

        self.nodes[node_id] = node_status
        print(f"🔄 Node {node_id} recovery initiated")
        return True

    def get_status(self, node_id: str) -> Optional[Dict]:
        """Get a node's status"""
        if node_id not in self.nodes:
            return None
        return self.nodes[node_id].to_dict()

    def get_network_status(self) -> Dict:
        """Get overall network status"""
        alive = sum(1 for n in self.nodes.values() if n.status == NodeStatus.ALIVE)
        desync = sum(1 for n in self.nodes.values() if n.status == NodeStatus.DESYNC)
        recovering = sum(1 for n in self.nodes.values() if n.status == NodeStatus.RECOVERING)
        dead = sum(1 for n in self.nodes.values() if n.status == NodeStatus.DEAD)

        return {
            "total_nodes": len(self.nodes),
            "alive": alive,
            "desync": desync,
            "recovering": recovering,
            "dead": dead,
            "network_phase": self._network_phase,
            "current_tick": self._current_tick
        }

    def get_node_phase(self, node_id: str) -> Optional[float]:
        """Get a node's current phase"""
        if node_id not in self.nodes:
            return None
        return self.nodes[node_id].phase

    def get_average_phase(self) -> float:
        """Calculate average network phase"""
        phases = [n.phase for n in self.nodes.values() if n.status != NodeStatus.DEAD]
        if not phases:
            return 0.0
        return math.atan2(sum(math.sin(p) for p in phases), sum(math.cos(p) for p in phases)) % (2 * math.pi)
