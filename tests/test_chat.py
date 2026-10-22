import pytest
from starlette.websockets import WebSocketDisconnect


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_two_clients_exchange_message_and_presence(client):
    with client.websocket_connect("/ws/lobby?username=alice") as alice:
        join_a = alice.receive_json()
        assert join_a["type"] == "join"
        assert join_a["members"] == ["alice"]

        with client.websocket_connect("/ws/lobby?username=bob") as bob:
            join_b = bob.receive_json()
            assert join_b["type"] == "join"
            assert join_b["members"] == ["alice", "bob"]

            # Alice also sees Bob's join announcement.
            alice_sees_join = alice.receive_json()
            assert alice_sees_join["type"] == "join"
            assert alice_sees_join["username"] == "bob"

            alice.send_json({"content": "hello bob"})
            msg_for_alice = alice.receive_json()
            msg_for_bob = bob.receive_json()
            assert msg_for_bob["type"] == "message"
            assert msg_for_bob["content"] == "hello bob"
            assert msg_for_bob["username"] == "alice"
            assert msg_for_bob["id"] == msg_for_alice["id"]
            assert msg_for_bob["timestamp"]

        # Bob disconnected: Alice receives the leave announcement.
        leave = alice.receive_json()
        assert leave["type"] == "leave"
        assert leave["username"] == "bob"
        assert leave["members"] == ["alice"]


def test_history_and_rooms_endpoints(client):
    with client.websocket_connect("/ws/history-room?username=carol") as carol:
        carol.receive_json()  # join event
        carol.send_json({"content": "first message"})
        carol.receive_json()
        carol.send_json({"content": "second message"})
        carol.receive_json()

    r = client.get("/rooms/history-room/messages")
    assert r.status_code == 200
    msgs = r.json()
    assert [m["content"] for m in msgs] == ["first message", "second message"]
    assert msgs[0]["username"] == "carol"
    assert msgs[0]["created_at"]

    r = client.get("/rooms")
    assert r.status_code == 200
    rooms = {room["room"]: room for room in r.json()["rooms"]}
    assert rooms["history-room"]["message_count"] == 2
    assert rooms["history-room"]["members"] == 0


def test_empty_username_rejected(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/lobby?username=") as ws:
            ws.receive_json()


def test_empty_message_ignored(client):
    with client.websocket_connect("/ws/quiet?username=dana") as dana:
        dana.receive_json()  # join
        dana.send_json({"content": "   "})
        dana.send_json({"content": "real one"})
        msg = dana.receive_json()
        assert msg["type"] == "message"
        assert msg["content"] == "real one"
