import hashlib, time
class RhythmMatrix:
    def __init__(self): self.matrix = {}
    def compute_from_event(self, observed_event):
        p = observed_event.event_payload
        vals = [v for v in p.values() if isinstance(v, (int, float))]
        return sum(vals) if vals else 0.0
    def get_rhythmic_hash(self, tick):
        return hashlib.sha256(f"rhythm:{tick}:{time.time()}".encode()).hexdigest()

rhythm_matrix = RhythmMatrix()
