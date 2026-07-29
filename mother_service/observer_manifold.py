import hashlib, time, uuid
from typing import Tuple

class ObserverState:
    def __init__(self, observer_id, spatial_coords, logical_tick=0):
        self.observer_id = observer_id; self.spatial_coords = spatial_coords; self.logical_tick = logical_tick
    @classmethod
    def capture(cls, node_id, coords):
        return cls(f"{node_id}:{uuid.uuid4().hex[:6]}", coords, int(time.time()*1000))
    def calculate_interference(self):
        return sum(c**2 for c in self.spatial_coords) % 1.0
    def to_hash(self):
        return hashlib.sha256(f"{self.observer_id}:{self.spatial_coords}:{self.logical_tick}".encode()).hexdigest()
    def to_dict(self):
        return {"observer_id": self.observer_id, "coords": list(self.spatial_coords), "logical_tick": self.logical_tick}

system_hlc = lambda: int(time.time() * 1000)
