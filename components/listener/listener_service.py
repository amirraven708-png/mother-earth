# listener_service.py
# نسخه بهینه‌شده با Mining غیرهمزمان و batch_size=100
# API بلافاصله پاسخ می‌دهد، Mining در پس‌زمینه انجام می‌شود

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import httpx
import logging
import os
import uvicorn
import json
import time
import asyncio
from collections import defaultdict

from temporal_contracts import BatchEventPayload
from realtimescalewriter import TimeLatticeWriter, AsyncpgPoolAdapter, WriterConfig, CLOUD_PROFILE, WaveEvent as DBWaveEvent

from observer_manifold import ObserverState
from unified_event_model import ObservedWaveEvent
from harmonic_rhythm_matrix import rhythm_matrix
from observer_api_middleware import observer_tracking_middleware
from raven_integration import RavenIntegration, harmonic_chain

logger = logging.getLogger("ListenerGateway")
writer_instance = None
BUBBLE_URL = os.environ.get("BUBBLE_URL", "http://localhost:5000")

metrics = {
    "total_requests": 0,
    "total_events": 0,
    "total_accepted": 0,
    "total_blocks_mined": 0,
    "avg_latency": 0,
    "last_minute_events": 0,
    "last_minute_start": time.time(),
    "observer_interferences": [],
    "pending_mining_tasks": 0,
}

# صف برای Mining غیرهمزمان
mining_queue = asyncio.Queue()

async def background_miner():
    """کارگر پس‌زمینه برای Mining بلاک‌ها"""
    while True:
        try:
            # دریافت کار از صف
            item = await mining_queue.get()
            events_to_mine = item["events"]
            observer = item["observer"]
            source_id = item["source_id"]
            request_id = item["request_id"]
            
            # ترکیب payloadها
            combined_payload = {
                "batch_id": request_id,
                "count": len(events_to_mine),
                "events": [e[0] for e in events_to_mine]
            }
            
            # ماینینگ
            block_result = await RavenIntegration.submit_rhythmic_event(
                observer=observer,
                event_payload=combined_payload,
                source_id=source_id
            )
            
            if block_result and block_result.get("status") == "block_mined":
                metrics["total_blocks_mined"] += 1
                logger.debug(f"⛓️ Block mined: {block_result.get('block_index')}")
            
            metrics["pending_mining_tasks"] -= 1
            mining_queue.task_done()
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Miner error: {e}")
            metrics["pending_mining_tasks"] -= 1
            mining_queue.task_done()

# راه‌اندازی miner در پس‌زمینه
miner_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global writer_instance, miner_task
    config = CLOUD_PROFILE
    config.dsn = os.environ.get("LATTICE_DSN", "")
    try:
        pool = AsyncpgPoolAdapter(config)
        await pool.connect()
        writer_instance = TimeLatticeWriter(config, pool)
    except Exception as e:
        logger.warning(f"Using FAKE_MODE: {e}")
        pool = AsyncpgPoolAdapter(config)
        writer_instance = TimeLatticeWriter(config, pool)
    await writer_instance.start()
    
    # راه‌اندازی miner پس‌زمینه
    miner_task = asyncio.create_task(background_miner())
    logger.info("🚀 Background miner started")
    
    yield
    
    # خاموش‌سازی
    if miner_task:
        miner_task.cancel()
    if writer_instance:
        await writer_instance.stop()
    logger.info("🛑 Listener stopped")

app = FastAPI(lifespan=lifespan)
app.middleware("http")(observer_tracking_middleware)

@app.get("/health")
async def health():
    return {"status": "ok", "writer_running": writer_instance is not None}

@app.get("/metrics")
async def get_metrics():
    global metrics
    current_time = time.time()
    if current_time - metrics["last_minute_start"] > 60:
        metrics["last_minute_events"] = 0
        metrics["last_minute_start"] = current_time
    
    avg_interference = sum(metrics["observer_interferences"][-100:]) / max(1, len(metrics["observer_interferences"][-100:]))
    
    return {
        "total_requests": metrics["total_requests"],
        "total_events": metrics["total_events"],
        "total_accepted": metrics["total_accepted"],
        "total_blocks_mined": metrics["total_blocks_mined"],
        "avg_latency": round(metrics["avg_latency"], 4),
        "last_minute_events": metrics["last_minute_events"],
        "avg_interference": round(avg_interference, 4),
        "queue_depth": writer_instance.queue.qsize() if writer_instance else 0,
        "pending_mining_tasks": metrics["pending_mining_tasks"],
        "chain_state": RavenIntegration.get_chain_status()
    }

@app.get("/rhythm/state")
async def get_rhythm_state(request: Request):
    from integrate_observer import ObserverIntegration
    state = ObserverIntegration.get_rhythmic_state()
    observer = getattr(request.state, "observer", None)
    if observer:
        state["current_observer"] = {
            "id": observer.observer_id,
            "interference": observer.calculate_interference(),
            "tick": observer.logical_tick
        }
    state["chain"] = RavenIntegration.get_chain_status()
    state["metrics"] = {
        "total_events": metrics["total_events"],
        "total_accepted": metrics["total_accepted"],
        "last_minute_events": metrics["last_minute_events"],
        "pending_mining_tasks": metrics["pending_mining_tasks"]
    }
    return state

@app.post("/api/v1/events/batch")
async def ingest_batch(request: Request, payload: BatchEventPayload):
    global metrics
    
    start_time = time.time()
    request_id = f"req_{int(start_time * 1000)}"
    metrics["total_requests"] += 1
    
    observer = getattr(request.state, "observer", ObserverState.capture("api", (0,0,0)))
    accepted = 0
    events_to_mine = []
    
    # پردازش همزمان رویدادها (سبک)
    async with httpx.AsyncClient(timeout=None) as client:
        for idx, event in enumerate(payload.events):
            try:
                event_payload = {
                    "lambda": event.lambda_val,
                    "theta": event.theta_val,
                    "force": event.force_f,
                    "weight": event.weight_w,
                    "pixel_id": event.pixel_id,
                    "x": event.x,
                    "y": event.y
                }
                
                db_event = DBWaveEvent(
                    time=event.time,
                    pixel_id=event.pixel_id,
                    x=event.x,
                    y=event.y,
                    lambda_val=event.lambda_val,
                    theta_val=event.theta_val,
                    force_f=event.force_f,
                    weight_w=event.weight_w,
                    dsc_symbol=event.dsc_symbol,
                    frame_id=event.frame_id,
                    source_id=payload.source_id,
                )
                success = await writer_instance.enqueue_event(db_event)
                if success:
                    accepted += 1
                    metrics["total_events"] += 1
                    metrics["total_accepted"] += 1
                    events_to_mine.append((event_payload, observer))
                    
                    # ارسال به BubbleDB (غیرهمزمان)
                    try:
                        await client.post(
                            f"{BUBBLE_URL}/insert",
                            json={
                                "key": f"{payload.source_id}:{event.pixel_id}:{int(event.time)}",
                                "value": json.dumps({
                                    "event": event.model_dump(),
                                    "observer": observer.to_dict()
                                })
                            },
                            timeout=None
                        )
                    except Exception as e:
                        logger.warning(f"BubbleDB insert failed: {e}")
                        
            except Exception as e:
                logger.error(f"Error processing event {idx}: {e}")
    
    # ✅ ارسال به صف Mining غیرهمزمان (هر ۱۰۰ رویداد یک بلاک)
    BATCH_SIZE = 100
    for i in range(0, len(events_to_mine), BATCH_SIZE):
        batch_events = events_to_mine[i:i+BATCH_SIZE]
        if batch_events:
            # ارسال به صف miner
            await mining_queue.put({
                "events": batch_events,
                "observer": observer,
                "source_id": payload.source_id,
                "request_id": request_id
            })
            metrics["pending_mining_tasks"] += 1
    
    elapsed = time.time() - start_time
    metrics["avg_latency"] = (metrics["avg_latency"] * (metrics["total_requests"] - 1) + elapsed) / metrics["total_requests"]
    metrics["last_minute_events"] += accepted
    metrics["observer_interferences"].append(observer.calculate_interference())
    if len(metrics["observer_interferences"]) > 1000:
        metrics["observer_interferences"] = metrics["observer_interferences"][-1000:]
    
    return {
        "status": "success",
        "request_id": request_id,
        "total": len(payload.events),
        "accepted": accepted,
        "queued_for_mining": len(events_to_mine),
        "pending_mining_tasks": metrics["pending_mining_tasks"],
        "observer_id": observer.observer_id,
        "interference": observer.calculate_interference(),
        "latency": round(elapsed, 4),
        "events_per_second": accepted / elapsed if elapsed > 0 else 0
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
