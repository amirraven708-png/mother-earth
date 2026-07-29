from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class TLDNode:
    name: str
    frozen: bool = False
    attributes: Dict[str, str] = field(default_factory=dict)

@dataclass
class TLDEdge:
    source: str
    target: str
    label: Optional[str] = None
    directed: bool = True
    type: str = "direct"

@dataclass
class TLDBox:
    name: Optional[str]
    elements: List[Any] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)

@dataclass
class TLDAST:
    elements: List[Any] = field(default_factory=list)
