from dataclasses import dataclass, field
from typing import Dict, Any
from observer_manifold import ObserverState
import time

@dataclass
class ObservedWaveEvent:
    observer_context: ObserverState
    event_payload: Dict[str, Any]
    event_type: str
    source_id: str
    timestamp: float = field(default_factory=time.time)
