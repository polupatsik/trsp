from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_websocket_message():
    with client.websocket_connect("/ws/rooms/python?username=alice") as ws:
        ws.receive_json()

        ws.send_json({
            "type": "message",
            "text": "hello"
        })

        data = ws.receive_json()

        assert data["type"] == "message"
        assert data["text"] == "hello"
