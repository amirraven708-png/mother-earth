import asyncio, logging
from dataclasses import dataclass

logger = logging.getLogger("TimeLatticeWriter")

@dataclass
class WaveEvent:
    time: float; pixel_id: int; x: int; y: int; lambda_val: float; theta_val: float
    force_f: float; weight_w: float; dsc_symbol: str; frame_id: int; source_id: str

@dataclass
class WriterConfig:
    dsn: str = ""; fake_mode: bool = True

CLOUD_PROFILE = WriterConfig()

class AsyncpgPoolAdapter:
    def __init__(self, config): self.config = config
    async def connect(self): pass
    async def close(self): pass

class TimeLatticeWriter:
    def __init__(self, config, pool):
        self.config = config; self.pool = pool; self.queue = asyncio.Queue(); self._running = False
    async def start(self): self._running = True; asyncio.create_task(self._writer_loop())
    async def stop(self): self._running = False
    async def enqueue_event(self, event): await self.queue.put(event); return True
    async def _writer_loop(self):
        while self._running:
            try:
                event = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                self.queue.task_done()
            except asyncio.TimeoutError: pass
            except Exception as e: logger.error(f"Writer error: {e}")
