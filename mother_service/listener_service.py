from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import httpx, logging, os, uvicorn, json, time, asyncio
from temporal_contracts import BatchEventPayload
from realtimescalewriter import TimeLatticeWriter, AsyncpgPoolAdapter, WriterConfig, CLOUD_PROFILE, WaveEvent as DBWaveEvent
from observer_manifold import ObserverState
from observer_api_middleware import observer_tracking_middleware
from raven_integration import RavenIntegration, harmonic_chain

logger = logging.getLogger("ListenerGateway")
writer_instance = None
BUBBLE_URL = os.environ.get("BUBBLE_URL", "http://localhost:5000")
metrics = {"total_requests":0, "total_events":0, "total_accepted":0, "total_blocks_mined":0,
           "avg_latency":0, "last_minute_events":0, "last_minute_start":time.time(),
           "observer_interferences":[], "pending_mining_tasks":0}

mining_queue = asyncio.Queue()

async def background_miner():
    while True:
        item = await mining_queue.get()
        events = item["events"]; observer = item["observer"]; source_id = item["source_id"]
        combined_payload = {"batch_id": item["request_id"], "count": len(events), "events": [e[0] for e in events]}
        result = await RavenIntegration.submit_rhythmic_event(observer, combined_payload, source_id)
        if result and result.get("status") == "block_mined": metrics["total_blocks_mined"] += 1
        metrics["pending_mining_tasks"] -= 1
        mining_queue.task_done()

miner_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global writer_instance, miner_task
    config = CLOUD_PROFILE
    try:
        pool = AsyncpgPoolAdapter(config); await pool.connect(); writer_instance = TimeLatticeWriter(config, pool)
    except: writer_instance = TimeLatticeWriter(config, AsyncpgPoolAdapter(config))
    await writer_instance.start()
    miner_task = asyncio.create_task(background_miner())
    yield
    if miner_task: miner_task.cancel()
    if writer_instance: await writer_instance.stop()

app = FastAPI(lifespan=lifespan)
app.middleware("http")(observer_tracking_middleware)

@app.get("/health")
async def health():
    return {"status":"ok"}

@app.get("/metrics")
async def get_metrics():
    global metrics
    current = time.time()
    if current - metrics["last_minute_start"] > 60: metrics["last_minute_events"] = 0; metrics["last_minute_start"] = current
    return {
        "total_requests": metrics["total_requests"],
        "total_events": metrics["total_events"],
        "total_accepted": metrics["total_accepted"],
        "total_blocks_mined": metrics["total_blocks_mined"],
        "avg_latency": round(metrics["avg_latency"],4),
        "last_minute_events": metrics["last_minute_events"],
        "pending_mining_tasks": metrics["pending_mining_tasks"],
        "chain_state": RavenIntegration.get_chain_status()
    }

@app.get("/rhythm/state")
async def get_rhythm_state(request: Request):
    from integrate_observer import ObserverIntegration
    state = ObserverIntegration.get_rhythmic_state()
    observer = getattr(request.state, "observer", None)
    if observer: state["current_observer"] = observer.to_dict()
    state["chain"] = RavenIntegration.get_chain_status()
    return state

@app.post("/api/v1/events/batch")
async def ingest_batch(request: Request, payload: BatchEventPayload):
    global metrics
    start = time.time()
    req_id = f"req_{int(start*1000)}"
    metrics["total_requests"] += 1
    observer = getattr(request.state, "observer", ObserverState.capture("api",(0,0,0)))
    accepted = 0; events_to_mine = []
    async with httpx.AsyncClient(timeout=None) as client:
        for ev in payload.events:
            try:
                ep = {"lambda": ev.lambda_val, "theta": ev.theta_val, "force": ev.force_f, "weight": ev.weight_w,
                      "pixel_id": ev.pixel_id, "x": ev.x, "y": ev.y}
                dbev = DBWaveEvent(time=ev.time, pixel_id=ev.pixel_id, x=ev.x, y=ev.y, lambda_val=ev.lambda_val,
                                   theta_val=ev.theta_val, force_f=ev.force_f, weight_w=ev.weight_w,
                                   dsc_symbol=ev.dsc_symbol, frame_id=ev.frame_id, source_id=payload.source_id)
                if await writer_instance.enqueue_event(dbev):
                    accepted += 1; metrics["total_events"] += 1; metrics["total_accepted"] += 1
                    events_to_mine.append((ep, observer))
            except: pass
    BATCH_SIZE = 100
    for i in range(0, len(events_to_mine), BATCH_SIZE):
        batch = events_to_mine[i:i+BATCH_SIZE]
        if batch:
            await mining_queue.put({"events":batch, "observer":observer, "source_id":payload.source_id, "request_id":req_id})
            metrics["pending_mining_tasks"] += 1
    elapsed = time.time()-start
    metrics["avg_latency"] = (metrics["avg_latency"]*(metrics["total_requests"]-1)+elapsed)/metrics["total_requests"]
    metrics["last_minute_events"] += accepted
    return {"status":"success", "request_id":req_id, "total":len(payload.events), "accepted":accepted,
            "queued_for_mining":len(events_to_mine), "pending_mining_tasks":metrics["pending_mining_tasks"],
            "observer_id":observer.observer_id, "interference":observer.calculate_interference(), "latency":round(elapsed,4)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
