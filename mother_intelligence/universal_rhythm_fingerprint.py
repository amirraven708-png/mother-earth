import numpy as np
import hashlib
from collections import Counter
from typing import List, Dict, Any, Union, Optional

class UniversalRhythmFingerprint:
    """
    تبدیل هر نوع داده (متن، باینری، سری زمانی، سیگنال) به دنباله‌ای از ۵ کلاس ریتمیک
    و ایجاد امضای ریتمیک قابل جستجو، مقایسه و تشخیص الگو.
    """
    def __init__(self, mode: str = "auto", chunk_size: Optional[int] = None):
        self.mode = mode
        self.chunk_size = chunk_size or 1

    def _chunkify(self, data: Union[str, bytes, np.ndarray]) -> List[Any]:
        if isinstance(data, str):
            if self.mode == "word":
                return data.split()
            else:
                return list(data)
        elif isinstance(data, (bytes, bytearray)):
            return list(data)
        elif isinstance(data, np.ndarray):
            return list(data.flatten())
        else:
            raise ValueError("نوع داده پشتیبانی نمی‌شود")

    def _chunk_to_features(self, chunk) -> Dict[str, float]:
        if isinstance(chunk, (int, np.integer)):
            val = float(chunk) / 255.0
            return {"energy": val, "gradient": 0.0}
        elif isinstance(chunk, str):
            if not chunk.strip():
                return {"energy": 0.0, "silence": 1.0}
            has_punct = any(c in "!?" for c in chunk)
            has_excl = '!' in chunk
            has_ques = '?' in chunk
            length = len(chunk)
            energy = min(1.0, length / 20.0)
            return {"energy": energy, "excl": float(has_excl), "ques": float(has_ques)}
        elif isinstance(chunk, float):
            return {"energy": abs(chunk), "gradient": 0.0}
        else:
            return {"energy": 0.5}

    def map_chunk_to_class(self, chunk, prev_class: Optional[int] = None) -> int:
        feat = self._chunk_to_features(chunk)
        energy = feat.get("energy", 0.5)

        if isinstance(chunk, str) and chunk.strip():
            if feat.get("ques", 0) > 0:
                return 0
            if feat.get("excl", 0) > 0:
                return 1
            if len(chunk) > 20:
                return 2
            if len(chunk) < 5:
                return 3
            return 4
        elif isinstance(chunk, (int, float)):
            if energy > 0.85:
                return 0
            elif energy < 0.15:
                return 4
            elif energy > 0.6:
                return 1
            elif energy > 0.3:
                return 2
            else:
                return 3
        else:
            return 4

    def compute_rhythm_sequence(self, data) -> List[int]:
        chunks = self._chunkify(data)
        sequence = []
        prev = None
        for ch in chunks:
            cls = self.map_chunk_to_class(ch, prev)
            sequence.append(cls)
            prev = cls
        return sequence

    def fingerprint(self, data) -> Dict[str, Any]:
        seq = self.compute_rhythm_sequence(data)
        if not seq:
            return {"error": "empty data"}

        counter = Counter(seq)
        total = len(seq)
        distribution = {i: counter.get(i, 0) / total for i in range(5)}

        transition = np.zeros((5, 5))
        for (a, b) in zip(seq[:-1], seq[1:]):
            transition[a][b] += 1
        row_sums = transition.sum(axis=1, keepdims=True)
        transition = np.divide(transition, row_sums, out=np.zeros_like(transition), where=row_sums != 0)

        entropy = -sum(p * np.log2(p) for p in distribution.values() if p > 0)

        uniform = np.ones(5) / 5
        observed = np.array([distribution[i] for i in range(5)])
        coherence = 1.0 - np.linalg.norm(observed - uniform) / np.linalg.norm(uniform)

        seq_bytes = bytes(seq)
        hash_val = hashlib.sha256(seq_bytes).hexdigest()[:16]

        original_size = len(data) if isinstance(data, (str, bytes)) else len(seq)
        fingerprint_size = len(seq)
        compression_ratio = original_size / max(1, fingerprint_size)

        return {
            "sequence": seq,
            "sequence_compact": seq_bytes,
            "distribution": distribution,
            "transition_matrix": transition.tolist(),
            "entropy": entropy,
            "coherence": coherence,
            "hash": hash_val,
            "original_size": original_size,
            "fingerprint_size": fingerprint_size,
            "compression_ratio": compression_ratio,
            "class_labels": ["گشایش", "زایش", "موج", "فرود", "سکوت"]
        }

    def compare(self, fp1: Dict, fp2: Dict) -> float:
        dist1 = np.array([fp1["distribution"][i] for i in range(5)])
        dist2 = np.array([fp2["distribution"][i] for i in range(5)])
        dot = np.dot(dist1, dist2)
        norm = np.linalg.norm(dist1) * np.linalg.norm(dist2)
        return dot / (norm + 1e-9)

    def reconstruct_text_from_rhythm(self, sequence: List[int], template_words: Optional[List[str]] = None) -> str:
        if template_words is None:
            template_words = {
                0: ["چه", "چگونه", "آیا", "شاید"],
                1: ["عالی!", "آفرین!", "خوب!"],
                2: ["و", "در", "به", "از", "طولانی"],
                3: ["پایان", "کم", "کوتاه", "بازگشت"],
                4: ["...", "  ", ".", " "]
            }
        words = []
        for cls in sequence:
            wlist = template_words.get(cls, [" "])
            words.append(wlist[hash(str(cls)) % len(wlist)])
        return " ".join(words)

if __name__ == "__main__":
    uf = UniversalRhythmFingerprint(mode="auto")
    sample = "امیر جان، این یک آزمایش است. آیا کار می‌کند؟ بله! عالی."
    fp = uf.fingerprint(sample)
    print("اثر انگشت نمونه:", fp["hash"], "coherence:", fp["coherence"])
