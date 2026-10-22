const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const WS_URL = API_URL.replace(/^http/, "ws");

export async function fetchRooms() {
  const res = await fetch(`${API_URL}/rooms`);
  if (!res.ok) throw new Error("Failed to load rooms");
  return (await res.json()).rooms;
}

export async function fetchHistory(room) {
  const res = await fetch(`${API_URL}/rooms/${encodeURIComponent(room)}/messages`);
  if (!res.ok) throw new Error("Failed to load history");
  return res.json();
}

/** Connects to a room's WebSocket. Returns the socket. */
export function connectToRoom(room, username, onEvent) {
  const ws = new WebSocket(
    `${WS_URL}/ws/${encodeURIComponent(room)}?username=${encodeURIComponent(username)}`
  );
  ws.onmessage = (msg) => onEvent(JSON.parse(msg.data));
  return ws;
}
