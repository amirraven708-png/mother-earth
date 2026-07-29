import socket, threading, json, time, hashlib, sys
NODE_ID = sys.argv[1]
PORT = int(sys.argv[2])
PEERS = sys.argv[3:]
BRIDGE_PORT = 9000
state = {"node": NODE_ID, "rhythm": 0, "phase": 0, "version": 0}
seen = set()
local_chain = []

def make_hash(data):
    raw = json.dumps(data, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]

def send(peer, packet):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(json.dumps(packet).encode(), ("127.0.0.1", int(peer)))
    sock.close()

def broadcast(packet, include_bridge=True):
    for peer in PEERS: send(peer, packet)
    if include_bridge: send(BRIDGE_PORT, packet)

def create_packet():
    p = {"origin": NODE_ID, "rhythm": state["rhythm"], "phase": state["phase"], "version": state["version"], "time": time.time()}
    p["hash"] = make_hash(p)
    return p

def process(packet):
    pid = packet["hash"]
    if pid in seen: return
    seen.add(pid)
    local_chain.append(packet)
    print(f"[{NODE_ID}] Wave from {packet['origin']}: r={packet['rhythm']} p={packet['phase']}")
    broadcast(packet)

def listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", PORT))
    print(f"{NODE_ID} listening {PORT} (bridge: {BRIDGE_PORT})")
    while True:
        data, addr = sock.recvfrom(4096)
        try:
            packet = json.loads(data.decode())
            process(packet)
        except: pass

def console():
    while True:
        value = input(f"{NODE_ID}> ")
        state["rhythm"] += 1
        state["phase"] = int(value)
        state["version"] += 1
        packet = create_packet()
        seen.add(packet["hash"])
        local_chain.append(packet)
        broadcast(packet)

threading.Thread(target=listener, daemon=True).start()
console()
