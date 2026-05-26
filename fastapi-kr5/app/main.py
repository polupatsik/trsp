import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.routers.tasks import router as tasks_router
from app.routers.users import router as users_router
from app.routers.admin import router as admin_router

app = FastAPI()

app.include_router(tasks_router)
app.include_router(users_router)
app.include_router(admin_router)

rooms = {}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "env": os.getenv("APP_ENV", "local")
    }


class RoomManager:
    def connect(self, room_id, username, websocket):
        if room_id not in rooms:
            rooms[room_id] = []

        rooms[room_id].append((username, websocket))

    def disconnect(self, room_id, username, websocket):
        if room_id in rooms:
            rooms[room_id] = [
                item for item in rooms[room_id]
                if item[1] != websocket
            ]

    async def broadcast(self, room_id, payload):
        if room_id in rooms:
            for _, ws in rooms[room_id]:
                await ws.send_json(payload)

    def get_users(self, room_id):
        return [u for u, _ in rooms.get(room_id, [])]


manager = RoomManager()


@app.websocket("/ws/rooms/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: str, username: str = ""):
    if not username.strip():
        await websocket.close(code=1008)
        return

    await websocket.accept()

    manager.connect(room_id, username, websocket)

    await manager.broadcast(
        room_id,
        {
            "type": "join",
            "username": username
        }
    )

    try:
        while True:
            data = await websocket.receive_json()

            text = data.get("text", "")

            if len(text) > 300:
                await websocket.send_json({
                    "type": "error",
                    "detail": "Message is too long"
                })
                continue

            await manager.broadcast(
                room_id,
                {
                    "type": "message",
                    "room_id": room_id,
                    "username": username,
                    "text": text
                }
            )

    except WebSocketDisconnect:
        manager.disconnect(room_id, username, websocket)


@app.get("/rooms/{room_id}/users")
def room_users(room_id: str):
    return {
        "room_id": room_id,
        "users": manager.get_users(room_id)
    }
