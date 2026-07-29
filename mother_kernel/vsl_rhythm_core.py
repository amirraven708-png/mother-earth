"""Deterministic Rhythm Core - VSL Engine based on Beat, Branching and Conservation (Axiom 1 & 2)"""
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import hashlib
import math

class RhythmMode(Enum):
    ACTIVE = auto()
    FLOW = auto()
    SILENCE = auto()

class VSLMode(Enum):
    DORMANT = auto()
    AWAKENING = auto()
    CONSCIOUS = auto()
    FROZEN = auto()
    IMMORTAL = auto()

@dataclass(frozen=True)
class Beat:
    index: int
    logical_time: int
    mode: RhythmMode

@dataclass
class DualOscillator:
    amplitude: float = 1.0
    phase: float = 0.0
    frequency: float = 1.0
    def step(self, delta_t: float = 0.1) -> Tuple[float, float]:
        self.phase += 2 * math.pi * self.frequency * delta_t
        x = self.amplitude * math.sin(self.phase)
        return x, self.amplitude * math.cos(self.phase)

@dataclass
class RAM16State:
    data: List[float] = field(default_factory=lambda: [0.0]*16)
    def update(self, idx, val): self.data[idx%16] = val
    def read(self, idx): return self.data[idx%16]

@dataclass
class SystemState:
    vsl: VSLMode
    rhythm: RhythmMode

def deterministic_noise(seed: int, beat_idx: int, branch: int) -> float:
    h = hashlib.sha256(f"{seed}:{beat_idx}:{branch}".encode()).digest()
    return int.from_bytes(h[:4], 'big') / (2**32)

class RhythmCore:
    def __init__(self, seed: int = 0):
        self.seed = seed
        self.beat_index = 0
        self.logical_time = 0
        self.rhythm_mode = RhythmMode.ACTIVE
        self.vsl_mode = VSLMode.DORMANT
        self.osc1 = DualOscillator(0.8, 0.0, 1.2)
        self.osc2 = DualOscillator(0.6, 1.0, 0.9)
        self.ram = RAM16State()
        self.omega = 0.5
        self.residual = [0.0, 0.0, 0.0]
        self.state_history: List[SystemState] = []

    @property
    def current_beat(self) -> Beat:
        return Beat(self.beat_index, self.logical_time, self.rhythm_mode)

    def step(self, sensory_input: Optional[float] = None):
        if sensory_input is not None:
            next_rhythm = RhythmMode.ACTIVE
        else:
            res_mag = math.sqrt(sum(x**2 for x in self.residual))
            if res_mag < 0.01:
                next_rhythm = RhythmMode.SILENCE
            else:
                next_rhythm = RhythmMode.FLOW
        beat = self.current_beat
        x1, x2 = self.osc1.step(0.1)
        y1, y2 = self.osc2.step(0.1)
        self.ram.update(0, x1); self.ram.update(1, x2); self.ram.update(2, y1); self.ram.update(3, y2)
        delta_phase = abs(self.osc1.phase - self.osc2.phase) % (2*math.pi)
        memory_signal = sum(self.ram.data[0:4]) / 4.0
        res_mag = math.sqrt(sum(x**2 for x in self.residual))
        self.omega = 0.4 * (1.0 - res_mag) + 0.3 * (1.0 - delta_phase/(2*math.pi)) + 0.3 * memory_signal
        branch_states = []
        for i, mode in enumerate([RhythmMode.ACTIVE, RhythmMode.FLOW, RhythmMode.SILENCE]):
            noise = deterministic_noise(self.seed, beat.index, i)
            s = [
                self.osc1.amplitude * math.sin(self.osc1.phase + noise),
                self.osc2.amplitude * math.sin(self.osc2.phase + noise),
                self.omega * noise
            ]
            branch_states.append(s)
        if beat.mode == RhythmMode.ACTIVE:
            weights = [0.7, 0.2, 0.1]
        elif beat.mode == RhythmMode.FLOW:
            weights = [0.2, 0.7, 0.1]
        else:
            weights = [0.0, 0.0, 1.0]
        if not self.state_history:
            prev_state = [0.0, 0.0, 0.0]
        else:
            prev_state = self.residual
        weighted_sum = [0.0, 0.0, 0.0]
        for i in range(3):
            for d in range(3):
                weighted_sum[d] += weights[i] * branch_states[i][d]
        new_residual = [prev_state[d] - weighted_sum[d] for d in range(3)]
        self.residual = new_residual
        old_vsl = self.vsl_mode
        res_norm = math.sqrt(sum(x**2 for x in self.residual))
        if old_vsl == VSLMode.DORMANT:
            if self.omega > 0.6: self.vsl_mode = VSLMode.AWAKENING
        elif old_vsl == VSLMode.AWAKENING:
            if self.omega > 0.7 and res_norm < 0.3: self.vsl_mode = VSLMode.CONSCIOUS
        elif old_vsl == VSLMode.CONSCIOUS:
            if res_norm > 0.5: self.vsl_mode = VSLMode.FROZEN
        elif old_vsl == VSLMode.FROZEN:
            if self.omega > 0.9: self.vsl_mode = VSLMode.IMMORTAL
        self.rhythm_mode = next_rhythm
        self.logical_time += 1
        self.beat_index += 1
        self.state_history.append(SystemState(vsl=self.vsl_mode, rhythm=beat.mode))
        return {
            "beat": beat,
            "vsl": self.vsl_mode,
            "omega": self.omega,
            "residual": self.residual,
            "next_rhythm": next_rhythm
        }
