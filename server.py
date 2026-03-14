import asyncio
import json
import threading
import http.server
import functools
from pathlib import Path
from datetime import datetime
import websockets

# ── In-memory state ───────────────────────────────────────────────────────────
clients = {}   # ws -> {"username": str}
rooms   = {}   # room_name -> set of usernames

for r in ["general", "random", "tech"]:
    rooms[r] = set()

# ── Helpers ───────────────────────────────────────────────────────────────────
def now():
    return datetime.now().strftime("%I:%M %p").lstrip("0")

async def ws_send(ws, obj):
    try:
        await ws.send(json.dumps(obj))
    except Exception:
        pass

async def broadcast(obj, exclude=None):
    for ws in list(clients):
        if ws is not exclude:
            await ws_send(ws, obj)

async def broadcast_user_list():
    users = [c["username"] for c in clients.values()]
    await broadcast({"type": "users", "users": users})

async def broadcast_room_list(target=None):
    room_list = [{"name": n, "members": len(m)} for n, m in rooms.items()]
    msg = {"type": "rooms", "rooms": room_list}
    if target:
        await ws_send(target, msg)
    else:
        await broadcast(msg)

def get_ws_by_username(username):
    for ws, data in clients.items():
        if data["username"] == username:
            return ws
    return None

async def broadcast_to_room(room, obj):
    if room not in rooms:
        return
    members = rooms[room]
    for ws, data in list(clients.items()):
        if data["username"] in members:
            await ws_send(ws, obj)

# ── Message handlers ──────────────────────────────────────────────────────────
async def handle_login(ws, msg):
    username = (msg.get("username") or "").strip()[:20]
    if len(username) < 2:
        await ws_send(ws, {"type": "error", "message": "Username must be at least 2 characters."})
        return
    if any(c["username"] == username for c in clients.values()):
        await ws_send(ws, {"type": "error", "message": "Username already taken."})
        return
    clients[ws] = {"username": username}
    await ws_send(ws, {"type": "login_ok", "username": username})
    await broadcast_room_list(ws)
    await broadcast_user_list()
    await broadcast({"type": "system", "text": f"{username} joined the chat.", "time": now()}, exclude=ws)

async def handle_join_room(ws, msg):
    user = clients.get(ws)
    if not user:
        return
    room = (msg.get("room") or "").strip()[:20]
    if not room:
        return
    if room not in rooms:
        if len(rooms) >= 20:
            await ws_send(ws, {"type": "error", "message": "Max rooms reached."})
            return
        rooms[room] = set()
    rooms[room].add(user["username"])
    await ws_send(ws, {"type": "joined_room", "room": room})
    await broadcast_to_room(room, {
        "type": "room_message", "room": room,
        "from": "System",
        "text": f"{user['username']} joined #{room}",
        "time": now()
    })
    await broadcast_room_list()

async def handle_leave_room(ws, msg):
    user = clients.get(ws)
    room = msg.get("room")
    if not user or room not in rooms:
        return
    rooms[room].discard(user["username"])
    await broadcast_to_room(room, {
        "type": "room_message", "room": room,
        "from": "System",
        "text": f"{user['username']} left #{room}",
        "time": now()
    })
    await broadcast_room_list()

async def handle_room_message(ws, msg):
    user = clients.get(ws)
    room = msg.get("room")
    text = (msg.get("text") or "").strip()[:500]
    if not user or not text:
        return
    if room not in rooms or user["username"] not in rooms[room]:
        await ws_send(ws, {"type": "error", "message": "You are not in that room."})
        return
    await broadcast_to_room(room, {
        "type": "room_message", "room": room,
        "from": user["username"],
        "text": text,
        "time": now()
    })

async def handle_private(ws, msg):
    user = clients.get(ws)
    to   = msg.get("to")
    text = (msg.get("text") or "").strip()[:500]
    if not user or not text:
        return
    target_ws = get_ws_by_username(to)
    if not target_ws:
        await ws_send(ws, {"type": "error", "message": f'User "{to}" not found.'})
        return
    m = {"type": "private_message", "from": user["username"], "to": to, "text": text, "time": now()}
    await ws_send(target_ws, m)
    await ws_send(ws, m)

# ── Connection handler ────────────────────────────────────────────────────────
async def handler(ws):
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            t = msg.get("type")
            if   t == "login":        await handle_login(ws, msg)
            elif t == "join_room":    await handle_join_room(ws, msg)
            elif t == "leave_room":   await handle_leave_room(ws, msg)
            elif t == "room_message": await handle_room_message(ws, msg)
            elif t == "private":      await handle_private(ws, msg)
    finally:
        user = clients.pop(ws, None)
        if user:
            for members in rooms.values():
                members.discard(user["username"])
            await broadcast({"type": "system", "text": f"{user['username']} left the chat.", "time": now()})
            await broadcast_user_list()
            await broadcast_room_list()

# ── HTTP server (serves public/) ──────────────────────────────────────────────
def run_http():
    public_dir = Path(__file__).parent / "public"
    Handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(public_dir),
                                )
    httpd = http.server.HTTPServer(("", 3000), Handler)
    print("  HTTP  →  http://localhost:3000")
    httpd.serve_forever()

# ── Entry point ───────────────────────────────────────────────────────────────
async def main():
    threading.Thread(target=run_http, daemon=True).start()
    print("  WS    →  ws://localhost:3001")
    print("\nOpen http://localhost:3000 in your browser.\nPress Ctrl+C to stop.\n")
    async with websockets.serve(handler, "", 3001):
        await asyncio.Future()   # run forever

if __name__ == "__main__":
    asyncio.run(main())
