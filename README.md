# Real-time Chat App

A full-stack real-time chat application: pick a display name, join or create a
room, and exchange messages live with everyone else in the room. Messages are
persisted, so a room's history is still there when you come back.

## Features

- **Live messaging** over WebSockets — messages broadcast to everyone in the
  room the moment they are sent
- **Multiple rooms** — join or create a room just by typing its name
- **Presence** — join/leave announcements and a live member list per room
- **Persistent history** — every message is stored with its timestamp and can
  be re-read through the REST API
- **Validation** — empty usernames/room names are rejected at the WebSocket
  handshake; empty messages are ignored

## How the WebSocket flow works

```
React UI ──HTTP──▶ GET /rooms/{room}/messages   (load history)
   │
   └──WS────▶ /ws/{room}?username={name}
                 1. Server validates name + room, accepts the socket,
                    broadcasts a "join" event (with the member list)
                 2. Client sends {"content": "..."} → server saves the
                    message, then broadcasts a "message" event to the room
                 3. On disconnect, server broadcasts a "leave" event
```

Every event is a small JSON object: `type` (`join` / `message` / `leave`),
`room`, `username`, `content`, `members`, and `timestamp`.

## Architecture

```
frontend/ (Vite + React) ──HTTP/WS──▶ app/ (FastAPI)
                                          │
                                app/main.py — REST + WebSocket endpoints,
                                              ConnectionManager (rooms/presence)
                                          │
                                app/models.py (SQLAlchemy)
                                SQLite by default, PostgreSQL via DATABASE_URL
```

| Path | Purpose |
| --- | --- |
| `app/main.py` | FastAPI application: REST endpoints, WebSocket endpoint, connection manager |
| `app/models.py` / `app/database.py` | SQLAlchemy message model and session setup |
| `app/schemas.py` | Pydantic response models |
| `tests/` | pytest suite (WebSocket + REST, via FastAPI TestClient) |
| `frontend/src/chatClient.js` | REST + WebSocket client module |
| `frontend/src/App.jsx` | Join screen, room list, chat view, member list |

## Tech stack

- **Backend:** Python, FastAPI, WebSockets, SQLAlchemy, Pydantic, uvicorn
- **Database:** SQLite by default; PostgreSQL supported via `DATABASE_URL`
- **Frontend:** React, Vite
- **Tests:** pytest (FastAPI TestClient with WebSocket support)
- **Packaging:** Docker + docker-compose (API + PostgreSQL)

## Setup

### Backend

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload    # http://localhost:8000  (docs at /docs)
```

### Frontend

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

The frontend expects the API at `http://localhost:8000`; set `VITE_API_URL`
before running Vite to change it.

### Docker (optional)

```bash
docker compose up --build        # API on :8000 backed by PostgreSQL
```

## API reference

### `GET /health`

```json
{ "status": "ok" }
```

### `GET /rooms`

Rooms that have messages or connected members, with live member counts and
total message counts.

```json
{ "rooms": [ { "room": "general", "members": 2, "message_count": 14 } ] }
```

### `GET /rooms/{room}/messages?limit=50`

Recent message history for a room, oldest first (limit 1–200).

### `WS /ws/{room}?username={name}`

Connect to chat in a room. Send `{"content": "your message"}`; receive
`join`, `message`, and `leave` events as described above.

## Running the tests

```bash
pytest
```

The suite covers two clients exchanging a message in the same room, join/leave
presence, the history and rooms endpoints, empty-username rejection, and
empty-message handling. Tests run against a temporary SQLite database.

## Configuration

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./chat.db` | SQLAlchemy database URL (e.g. `postgresql+psycopg2://user:pass@host:5432/db`) |
| `VITE_API_URL` (frontend) | `http://localhost:8000` | API base URL used by the React app |
