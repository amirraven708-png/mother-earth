from pydantic import BaseModel
from typing import List

class EventItem(BaseModel):
    time: float; pixel_id: int; x: int; y: int
    lambda_val: float; theta_val: float; force_f: float; weight_w: float
    dsc_symbol: str; frame_id: int

class BatchEventPayload(BaseModel):
    source_id: str
    events: List[EventItem]
