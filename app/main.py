import re
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, SessionLocal, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Real-time Chat App", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

USERNAME_RE = re.compile(r"^[\w .'-]{1,32}$")
ROOM_RE = re.compile(r"^[\w-]{1,64}$")


def valid_name(value: str, pattern: re.Pattern) -> bool:
    return bool(value) and bool(pattern.match(value.strip()))


class ConnectionManager:
    """Tracks live WebSocket connections per room and broadcasts to them."""

    def __init__(self):
        self.active: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, room: str, username: str, websocket: WebSocket):
        await websocket.accept()
        self.active.setdefault(room, {})[username] = websocket

    def disconnect(self, room: str, username: str):
        room_map = self.active.get(room, {})
        room_map.pop(username, None)
        if not room_map:
            self.active.pop(room, None)

    def members(self, room: str) -> List[str]:
        return sorted(self.active.get(room, {}).keys())

    async def broadcast(self, room: str, payload: dict):
        for ws in list(self.active.get(room, {}).values()):
            await ws.send_json(payload)


manager = ConnectionManager()


def event(kind: str, room: str, username: str, content: str = "") -> dict:
    return {
        "type": kind,
        "room": room,
        "username": username,
        "content": content,
        "members": manager.members(room),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/rooms", response_model=schemas.RoomListOut)
def list_rooms(db: Session = Depends(get_db)):
    counts = (
        db.query(models.Message.room, func.count(models.Message.id))
        .group_by(models.Message.room)
        .all()
    )
    counts_map = {room: count for room, count in counts}
    room_names = set(counts_map) | set(manager.active)
    rooms = [
        schemas.RoomOut(
            room=name,
            members=len(manager.active.get(name, {})),
            message_count=counts_map.get(name, 0),
        )
        for name in sorted(room_names)
    ]
    return {"rooms": rooms}


@app.get("/rooms/{room}/messages", response_model=List[schemas.MessageOut])
def room_messages(
    room: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.Message)
        .filter(models.Message.room == room)
        .order_by(models.Message.id.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))


@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str = ""):
    username = username.strip()
    if not valid_name(username, USERNAME_RE) or not valid_name(room, ROOM_RE):
        await websocket.close(code=1008)  # policy violation: invalid name/room
        return

    await manager.connect(room, username, websocket)
    await manager.broadcast(room, event("join", room, username, f"{username} joined the room"))
    try:
        while True:
            data = await websocket.receive_json()
            content = str(data.get("content", "")).strip()
            if not content:
                continue
            db = SessionLocal()
            try:
                msg = models.Message(room=room, username=username, content=content)
                db.add(msg)
                db.commit()
                db.refresh(msg)
                payload = event("message", room, username, content)
                payload["id"] = msg.id
                payload["timestamp"] = msg.created_at.isoformat()
            finally:
                db.close()
            await manager.broadcast(room, payload)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(room, username)
        await manager.broadcast(room, event("leave", room, username, f"{username} left the room"))
