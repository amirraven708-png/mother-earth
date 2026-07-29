import json, time, hashlib, threading
from dataclasses import dataclass
from typing import Optional, Dict, List
from observer_manifold import ObserverState, system_hlc
from harmonic_rhythm_matrix import rhythm_matrix
from priority_generator import priority_core

@dataclass
class RhythmicBlock:
    index: int; rhythmic_hash: str; observer_hash: str; previous_hash: str; timestamp: float
    logical_tick: int; geometric_proof: str; payload: Dict; nonce: int = 0
    def compute_hash(self):
        raw = f"{self.index}:{self.rhythmic_hash}:{self.observer_hash}:{self.previous_hash}:{self.timestamp}:{self.logical_tick}:{self.geometric_proof}:{self.nonce}"
        return hashlib.sha256(raw.encode()).hexdigest()

class HarmonicChain:
    def __init__(self):
        self.blocks: List[RhythmicBlock] = []; self.difficulty = 4; self.lock = threading.Lock(); self._genesis()
    def _genesis(self):
        genesis = RhythmicBlock(0, "GENESIS", "GENESIS", "0"*64, time.time(), 0, "0", {"type":"genesis"})
        self.blocks.append(genesis)
    def get_last_hash(self): return self.blocks[-1].compute_hash() if self.blocks else "0"*64
    def mine_block(self, rhythmic_hash, observer, payload):
        with self.lock:
            proof = hashlib.sha256((rhythmic_hash + observer.to_hash()).encode()).hexdigest()[:8]
            block = RhythmicBlock(len(self.blocks), rhythmic_hash, observer.to_hash(), self.get_last_hash(),
                                  time.time(), observer.logical_tick, proof, payload, 0)
            target = "0" * self.difficulty
            while True:
                if block.compute_hash().startswith(target):
                    self.blocks.append(block)
                    return block
                block.nonce += 1
                if block.nonce > 1000000: return None
    def get_chain_state(self):
        return {"blocks": len(self.blocks), "last_hash": self.get_last_hash()[:16], "difficulty": self.difficulty}

harmonic_chain = HarmonicChain()

class RavenIntegration:
    @staticmethod
    async def submit_rhythmic_event(observer, event_payload, source_id="default"):
        from unified_event_model import ObservedWaveEvent
        observed = ObservedWaveEvent(observer, event_payload, "wave", source_id)
        rhythmic_hash = rhythm_matrix.get_rhythmic_hash(observer.logical_tick) or "00000000"
        block = harmonic_chain.mine_block(rhythmic_hash, observer, event_payload)
        if block: return {"status":"block_mined", "block_index":block.index, "rhythmic_hash":rhythmic_hash}
        return {"status":"mining_failed", "rhythmic_hash":rhythmic_hash}
    @staticmethod
    def get_chain_status(): return harmonic_chain.get_chain_state()
