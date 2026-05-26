from fastapi.testclient import TestClient
from app.main import app
from app.storage import tasks

client = TestClient(app)


def setup_function():
    tasks.clear()


def test_create_task():
    response = client.post(
        "/tasks",
        headers={"X-User-Id": "10"},
        json={
            "title": "Test task",
            "description": "Desc",
            "status": "todo",
            "priority": 3
        }
    )

    assert response.status_code == 201


def test_short_title():
    response = client.post(
        "/tasks",
        headers={"X-User-Id": "10"},
        json={
            "title": "ab",
            "description": "Desc",
            "status": "todo",
            "priority": 3
        }
    )

    assert response.status_code == 422


def test_no_auth():
    response = client.get("/tasks")

    assert response.status_code == 401
