import socket, json, time, httpx, asyncio
BRIDGE_PORT = 9000
CLOUD_API = "http://localhost:8000/api/v1/events/batch"
BATCH_INTERVAL = 2.0
MAX_BATCH_SIZE = 20

class WaveBridge:
    def __init__(self):
        self.event_buffer = []
        self.last_flush = time.time()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", BRIDGE_PORT))
        print(f"🌉 Wave Bridge listening on UDP:{BRIDGE_PORT}")

    async def run(self):
        loop = asyncio.get_event_loop()
        while True:
            data, addr = await loop.sock_recv(self.sock, 4096)
            try:
                packet = json.loads(data.decode())
                self.handle_packet(packet)
            except: pass
            if time.time() - self.last_flush > BATCH_INTERVAL and self.event_buffer:
                await self.flush()

    def handle_packet(self, packet):
        event = {
            "time": packet.get("time", time.time()),
            "pixel_id": hash(packet.get("origin", "?")) % 200 + 1,
            "x": 0, "y": 0,
            "lambda_val": packet.get("rhythm", 0),
            "theta_val": packet.get("phase", 0),
            "force_f": 0.5, "weight_w": 1.0,
            "dsc_symbol": f"WAVE_{packet.get('origin','?')}",
            "frame_id": int(packet.get("version", 0))
        }
        self.event_buffer.append(event)
        if len(self.event_buffer) >= MAX_BATCH_SIZE:
            asyncio.create_task(self.flush())

    async def flush(self):
        if not self.event_buffer: return
        payload = {"source_id": "wave_mesh", "events": self.event_buffer.copy()}
        self.event_buffer.clear()
        self.last_flush = time.time()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(CLOUD_API, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"📤 Batch sent ({data.get('accepted')} events), pending: {data.get('pending_mining_tasks')}")
        except Exception as e: print(f"❌ Flush failed: {e}")

if __name__ == "__main__":
    asyncio.run(WaveBridge().run())
