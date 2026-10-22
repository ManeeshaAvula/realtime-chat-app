import { useEffect, useRef, useState } from "react";
import { connectToRoom, fetchHistory, fetchRooms } from "./chatClient";

export default function App() {
  const [username, setUsername] = useState("");
  const [roomName, setRoomName] = useState("");
  const [rooms, setRooms] = useState([]);
  const [joined, setJoined] = useState(null); // { room, username }
  const [messages, setMessages] = useState([]);
  const [members, setMembers] = useState([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const wsRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    fetchRooms().then(setRooms).catch(() => {});
  }, [joined]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function join(room) {
    const name = username.trim();
    const target = room.trim();
    if (!name || !target) {
      setError("Enter a display name and a room name.");
      return;
    }
    setError("");
    try {
      const history = await fetchHistory(target);
      setMessages(
        history.map((m) => ({
          type: "message",
          username: m.username,
          content: m.content,
          timestamp: m.created_at,
        }))
      );
    } catch {
      setMessages([]);
    }
    const ws = connectToRoom(target, name, (evt) => {
      if (evt.type === "message") {
        setMessages((prev) => [...prev, evt]);
      } else {
        setMessages((prev) => [...prev, { ...evt, system: true }]);
      }
      if (evt.members) setMembers(evt.members);
    });
    ws.onerror = () => setError("WebSocket connection failed — is the API running?");
    wsRef.current = ws;
    setJoined({ room: target, username: name });
  }

  function leave() {
    wsRef.current?.close();
    wsRef.current = null;
    setJoined(null);
    setMessages([]);
    setMembers([]);
  }

  function send() {
    const text = draft.trim();
    if (!text || !wsRef.current) return;
    wsRef.current.send(JSON.stringify({ content: text }));
    setDraft("");
  }

  if (!joined) {
    return (
      <main className="join">
        <h1>Real-time Chat</h1>
        <p className="sub">Pick a name, join a room, and chat live.</p>
        <label>
          Display name
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="e.g. maneesha" />
        </label>
        <label>
          Room name
          <input
            value={roomName}
            onChange={(e) => setRoomName(e.target.value)}
            placeholder="e.g. general"
            onKeyDown={(e) => e.key === "Enter" && join(roomName)}
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button onClick={() => join(roomName)}>Join room</button>
        {rooms.length > 0 && (
          <section className="room-list">
            <h2>Existing rooms</h2>
            <ul>
              {rooms.map((r) => (
                <li key={r.room}>
                  <button className="link" onClick={() => join(r.room)}>
                    #{r.room}
                  </button>
                  <span>
                    {r.members} online · {r.message_count} messages
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    );
  }

  return (
    <main className="chat">
      <header>
        <h1>#{joined.room}</h1>
        <span>Signed in as {joined.username}</span>
        <button className="link" onClick={leave}>
          Leave room
        </button>
      </header>
      <div className="body">
        <section className="messages">
          {messages.map((m, i) =>
            m.system ? (
              <p key={i} className="system">
                {m.content}
              </p>
            ) : (
              <p key={i} className={m.username === joined.username ? "mine" : ""}>
                <strong>{m.username}</strong>{" "}
                <time>{new Date(m.timestamp).toLocaleTimeString()}</time>
                <br />
                {m.content}
              </p>
            )
          )}
          <div ref={bottomRef} />
        </section>
        <aside className="members">
          <h2>Members ({members.length})</h2>
          <ul>
            {members.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </aside>
      </div>
      <footer>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Type a message…"
        />
        <button onClick={send}>Send</button>
      </footer>
    </main>
  );
}
